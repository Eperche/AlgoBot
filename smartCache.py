import math
from talibAnalysis import TechnicalAnalyzer, SupportResistanceAnalyzer
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import threading
import time
from typing import Dict, Optional
import sys


class SmartCacheManager:

    # Cache konfigürasyonu - trend analizi eklendi
    # İnterval dakika cinsinden, cache süresi de dakika cinsinden

    CACHE_CONFIG = {
        "15m": {
            "update_interval": 1,
            "cache_duration": 0.5,
        },  # 1 dakikada bir güncelle, 60 saniye cache
        "30m": {
            "update_interval": 1,
            "cache_duration": 0.5,
        },  # 1 dakikada bir güncelle, 60 saniye cache
        "1h": {
            "update_interval": 1,
            "cache_duration": 1,
        },  # 1 dakikada bir güncelle, 60 saniye cache
        "4h": {"update_interval": 10, "cache_duration": 3},
        "6h": {"update_interval": 10, "cache_duration": 5},
        "8h": {"update_interval": 20, "cache_duration": 40},
        "12h": {"update_interval": 20, "cache_duration": 40},
        "1d": {"update_interval": 20, "cache_duration": 30},
        "1w": {
            "update_interval": 1000,
            "cache_duration": 2000,
        },  # Haftalık güncelleme, 2000 dakika cache
        # YENİ: Trend hesaplaması için özel config
        "trend": {"interval": 120, "symbols_batch": 50},  # 2 dakikada bir, 50'şer grup
    }

    # Cache storage - trend cache eklendi
    cache_storage = {}
    cache_locks = {}
    background_threads = {}

    # Her timeframe için lock (trend dahil)
    for tf in CACHE_CONFIG.keys():
        cache_locks[tf] = threading.RLock()  # Her timeframe için ayrı lock kullanıyoruz
        if tf == "trend":
            cache_storage[tf] = {
                "data": {},  # trend için dict kullanıyoruz
                "last_update": None,
                "is_updating": False,
                "next_check": None,
            }
        else:
            cache_storage[tf] = {
                "data": [],  # diğerleri için list
                "last_update": None,
                "is_updating": False,
                "next_check": None,
            }

    def __init__(self, analyzer: TechnicalAnalyzer, COINS: Optional[list] = None):
        self.analyzer = analyzer  # TechnicalAnalyzer instance
        self.COINS = COINS
        self.is_running = True

        self.trend_score = {
            3: "STRONG_BULLISH",
            2: "BULLISH",
            1: "WEAK_BULLISH",
            0: "NEUTRAL",
            -1: "WEAK_BEARISH",
            -2: "BEARISH",
            -3: "STRONG_BEARISH",
        }

    def convert_to_json_serializable(self, obj):
        """Numpy/pandas tiplerini JSON serializable hale getirir ve NaN'ları None yapar."""
        if isinstance(obj, dict):
            return {
                key: self.convert_to_json_serializable(value)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [self.convert_to_json_serializable(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32, float)):
            if isinstance(obj, float) and math.isnan(obj):
                return None
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, (pd.Series, pd.DataFrame)):
            return obj.to_dict()  # veya başka bir mantıklı dönüşüm
        elif pd.isna(obj):  # obj scalar ise çalışır
            return None
        elif hasattr(obj, "item"):  # pandas scalar
            return self.convert_to_json_serializable(obj.item())
        else:
            return obj

    def should_update_cache(self, timeframe: str) -> bool:
        """Cache güncellenip güncellenmeyeceğini kontrol et"""
        if timeframe not in SmartCacheManager.CACHE_CONFIG:
            return False

        with SmartCacheManager.cache_locks[timeframe]:
            cache_data = SmartCacheManager.cache_storage[timeframe]

            # Hiç güncellenmemişse güncelle
            if not cache_data["last_update"]:
                return True

            # Trend için farklı kontrol
            if timeframe == "trend":
                now = datetime.now()
                interval = SmartCacheManager.CACHE_CONFIG[timeframe]["interval"]
                time_diff = (now - cache_data["last_update"]).total_seconds()
                return time_diff >= interval

            # Cache süresi dolmuşsa güncelle
            now = datetime.now()
            cache_duration = SmartCacheManager.CACHE_CONFIG[timeframe][
                "cache_duration"
            ]  # dakika cinsinden
            time_diff = (
                now - cache_data["last_update"]
            ).total_seconds() / 60  # dakika cinsinden

            return time_diff >= cache_duration

    def is_cache_fresh(self, timeframe: str) -> bool:
        """Cache taze mi kontrol et"""
        if timeframe not in SmartCacheManager.CACHE_CONFIG:
            return False

        with SmartCacheManager.cache_locks[timeframe]:
            cache_data = SmartCacheManager.cache_storage[timeframe]

            if not cache_data["last_update"] or not cache_data["data"]:
                return False

            now = datetime.now()

            # Trend için farklı freshness kontrolü
            if timeframe == "trend":
                interval = SmartCacheManager.CACHE_CONFIG[timeframe]["interval"]
                time_diff = (now - cache_data["last_update"]).total_seconds()
                return time_diff < (interval * 0.8)

            # Cache'in %80'i geçmişse fresh değil
            cache_duration = SmartCacheManager.CACHE_CONFIG[timeframe]["cache_duration"]
            time_diff = (now - cache_data["last_update"]).total_seconds() / 60

            return time_diff < (cache_duration * 0.8)

    def calculate_trend_analysis(self):
        """Tüm semboller için trend analizi yap ve cache'e kaydet"""
        with SmartCacheManager.cache_locks["trend"]:
            if SmartCacheManager.cache_storage["trend"]["is_updating"]:
                print("[TREND] Trend hesaplaması devam ediyor, atlanıyor...")
                return
            SmartCacheManager.cache_storage["trend"]["is_updating"] = True

        try:
            print("[TREND] Trend analizi başlatılıyor...")
            trend_data = {}
            total_symbols = len(self.COINS)
            batch_size = SmartCacheManager.CACHE_CONFIG["trend"]["symbols_batch"]
            batch_size = len(self.COINS) // 2

            for i in range(0, total_symbols, batch_size):
                batch_symbols = self.COINS[i : i + batch_size]
                print(
                    f"[TREND] Batch {i//batch_size + 1}: {len(batch_symbols)} sembol işleniyor..."
                )

                for symbol in batch_symbols:
                    try:
                        # Trend analizini yap
                        trend_analysis = self.analyze_big_picture_trend(symbol)
                        trend_data[symbol] = self.convert_to_json_serializable(
                            trend_analysis
                        )

                    except Exception as e:
                        print(f"[TREND] {symbol} trend hesaplaması hatası: {e}")
                        trend_data[symbol] = {
                            "trend": "ERROR",
                            "strength": 0,
                            "confidence": "LOW",
                            "error": str(e),
                        }

                # Batch arası kısa mola
                time.sleep(0.5)

            # Cache'i güncelle
            with SmartCacheManager.cache_locks["trend"]:
                SmartCacheManager.cache_storage["trend"]["data"] = trend_data
                SmartCacheManager.cache_storage["trend"]["last_update"] = datetime.now()
                SmartCacheManager.cache_storage["trend"]["is_updating"] = False

            print(f"[TREND] Trend analizi tamamlandı: {len(trend_data)} sembol")

        except Exception as e:
            print(f"[TREND] Genel trend hesaplama hatası: {e}")
            with SmartCacheManager.cache_locks["trend"]:
                SmartCacheManager.cache_storage["trend"]["is_updating"] = False

    def analyze_big_picture_trend(self, symbol):
        """
        Gelişmiş tek sembol trend analizi - S/R ve EMA hierarchy dahil
        """
        try:
            # 1. Temel trend analizi (mevcut logic)
            base_trend = self._calculate_base_trend(symbol)

            # if base_trend['trend'] == 'ERROR':
            #     return base_trend

            # 2. Support/Resistance context analizi
            sr_context = self._get_sr_context(symbol)

            # 3. EMA trend hierarchy analizi
            trend = self._get_trend_context(symbol)

            # 4. Enhanced trend score hesaplama
            enhanced_result = self._calculate_enhanced_trend_score(
                base_trend, sr_context, trend
            )
            # input(f"symbol: {symbol} - {enhanced_result}")
            return enhanced_result

        except Exception as e:
            print(f"[ERROR] {symbol} trend analizi hatası: {str(e)}")
            return {
                "trend": "ERROR",
                "strength": 0,
                "confidence": "LOW",
                "error": str(e),
            }

    def _calculate_base_trend(self, symbol):
        """Mevcut trend analizi logic'i"""
        try:
            # Cache'den verileri al
            h1_data = SmartCacheManager.cache_storage.get("1h", {}).get("data", [])
            h4_data = SmartCacheManager.cache_storage.get("4h", {}).get("data", [])

            # İlgili sembole ait verileri bul
            h1_symbol_data = None
            h4_symbol_data = None

            if isinstance(h1_data, list):
                h1_symbol_data = next(
                    (item for item in h1_data if item.get("symbol") == symbol), None
                )
            if isinstance(h4_data, list):
                h4_symbol_data = next(
                    (item for item in h4_data if item.get("symbol") == symbol), None
                )

            if not h1_symbol_data or not h4_symbol_data:
                return {
                    "trend": "UNKNOWN",
                    "strength": 0,
                    "confidence": "LOW",
                    "details": "Insufficient data",
                }

            # 4H - Ana trend yönü (daha önemli)
            h4_trend_score = 0
            h4_signals = h4_symbol_data.get("signals", {})
            h4_indicators = h4_symbol_data.get("indicators", {})

            # Golden/Death Cross (en güçlü sinyal)
            if h4_signals.get("golden_cross", False):
                h4_trend_score += 3
            elif h4_signals.get("death_cross", False):
                h4_trend_score -= 3

            # MACD trend
            if h4_signals.get("macd_buy", False):
                h4_trend_score += 2
            elif h4_signals.get("macd_sell", False):
                h4_trend_score -= 2

            # RSI trend bias
            rsi_4h = h4_indicators.get("rsi", 50)
            if rsi_4h > 55:
                h4_trend_score += 1
            elif rsi_4h < 45:
                h4_trend_score -= 1

            # 1H - Momentum doğrulaması
            h1_trend_score = 0
            h1_signals = h1_symbol_data.get("signals", {})
            h1_indicators = h1_symbol_data.get("indicators", {})

            # MACD momentum
            macd_1h = h1_indicators.get("macd", {})
            if isinstance(macd_1h, dict):
                histogram = macd_1h.get("histogram", 0)
                if histogram > 0:
                    h1_trend_score += 1
                elif histogram < 0:
                    h1_trend_score -= 1

            # BB momentum
            if h1_signals.get("bb_buy", False):
                h1_trend_score += 1
            elif h1_signals.get("bb_sell", False):
                h1_trend_score -= 1

            # RSI momentum
            if h1_signals.get("rsi_buy", False):
                h1_trend_score += 1
            elif h1_signals.get("rsi_sell", False):
                h1_trend_score -= 1

            # Toplam trend skoru (4H daha ağırlıklı)
            total_score = (h4_trend_score * 0.7) + (h1_trend_score * 0.3)

            return {
                "h4_score": h4_trend_score,
                "h1_score": h1_trend_score,
                "total_score": total_score,
            }

        except Exception as e:
            return {
                "trend": "ERROR",
                "strength": 0,
                "confidence": "LOW",
                "error": str(e),
            }

    def _get_sr_context(self, symbol):
        """Support/Resistance context analizi"""

        try:
            # 4H data'sını kullan (daha güvenilir S/R seviyeleri)
            h4_data = SmartCacheManager.cache_storage.get("4h", {}).get("data", [])
            symbol_data = next(
                (item for item in h4_data if item.get("symbol") == symbol), None
            )

            if not symbol_data:
                return {
                    "sr_score": 0,
                    "context": "NO_DATA",
                    "key_levels": {},
                    "confidence": 0,
                }

            # OHLCV datasını DataFrame'e çevir
            df = self._convert_to_dataframe(symbol_data)  # df ohlcv

            if df is None or len(df) < 20:
                return {
                    "sr_score": 0,
                    "context": "INSUFFICIENT_DATA",
                    "key_levels": {},
                    "confidence": 0,
                }

            # S/R analizi
            sr_analyzer = SupportResistanceAnalyzer(df, tf="4h")
            sr_result = sr_analyzer.analyze()

            sr_score = 0
            context = "NEUTRAL"

            # S/R sinyallerine göre trend skoru
            signals = sr_result["signals"]

            if signals["resistance_break"] and signals["volume_confirmation"]:
                sr_score += 4  # Güçlü bullish + volume
                context = "RESISTANCE_BREAK_VOLUME"
            elif signals["resistance_break"]:
                sr_score += 3  # Güçlü bullish
                context = "RESISTANCE_BREAK"
            elif signals["support_bounce"] and signals["volume_confirmation"]:
                sr_score += 3  # Orta bullish + volume
                context = "SUPPORT_BOUNCE_VOLUME"
            elif signals["support_bounce"]:
                sr_score += 2  # Orta bullish
                context = "SUPPORT_BOUNCE"
            elif signals["support_break"] and signals["volume_confirmation"]:
                sr_score -= 4  # Güçlü bearish + volume
                context = "SUPPORT_BREAK_VOLUME"
            elif signals["support_break"]:
                sr_score -= 3  # Güçlü bearish
                context = "SUPPORT_BREAK"
            elif signals["resistance_rejection"]:
                sr_score -= 2  # Orta bearish
                context = "RESISTANCE_REJECTION"
            elif signals["near_resistance"]:
                sr_score -= 1  # Hafif bearish bias
                context = "NEAR_RESISTANCE"
            elif signals["near_support"]:
                sr_score += 1  # Hafif bullish bias
                context = "NEAR_SUPPORT"

            return {
                "sr_score": sr_score,
                "context": context,
                "key_levels": sr_result["summary"]["key_levels"],
                "confidence": sr_result["summary"]["confidence"],
                "volume_confirmation": signals.get("volume_confirmation", False),
            }

        except Exception as e:
            return {
                "sr_score": 0,
                "context": "ERROR",
                "key_levels": {},
                "confidence": 0,
                "error": str(e),
            }

    def _get_trend_context(self, symbol):
        """EMA hierarchy trend analizi"""
        try:
            ema_score = 0
            ema_details = {}

            # Her timeframe için EMA durumu
            timeframes = ["1h", "4h", "1d"]
            weights = {"1h": 0.25, "4h": 0.25, "1d": 0.5}

            for tf in timeframes:
                tf_data = SmartCacheManager.cache_storage.get(tf, {}).get("data", [])
                symbol_data = next(
                    (item for item in tf_data if item.get("symbol") == symbol), None
                )

                if tf == "4h":
                    if symbol_data and "signals" in symbol_data:
                        h4_signals = symbol_data["signals"]
                        h4_indicators = symbol_data["indicators"]
                        
                        h4_golden_cross = h4_signals.get("golden_cross ", False) and h4_signals.get("bullish_strong ", False)
                        h4_death_cross = h4_signals.get("death_cross ", False) 
 
                if tf == "1h":
                    if symbol_data and "signals" in symbol_data:
                        h1_signals = symbol_data["signals"]
                        h1_indicators = symbol_data["indicators"]
                        
 

                if tf == "1d":
                    if symbol_data and "signals" in symbol_data:
                        
                        
                        d1_indicators = symbol_data["indicators"]
                        d1_signals = symbol_data["signals"]
                        
 


                if symbol_data and "indicators" in symbol_data:
                    indicators = symbol_data["indicators"]

                    # EMA short > EMA long kontrolü
                    ema_short = indicators.get("ema_short", 0)
                    ema_long = indicators.get("ema_long", 0)
                    current_price = symbol_data.get("last_price", 0)

                    tf_score = 0

                    if ema_short > 0 and ema_long > 0:
                        if ema_short > ema_long:
                            # Bullish EMA alignment
                            if current_price > ema_short:
                                tf_score = 3  # Güçlü bullish: Fiyat EMA'ların üstünde
                            elif current_price > ema_long:
                                tf_score = 2  # Orta bullish: Fiyat EMA'lar arasında
                            else:
                                tf_score = 1  # Zayıf bullish: EMA'lar bullish ama fiyat altında
                        else:
                            # Bearish EMA alignment
                            if current_price < ema_short:
                                tf_score = -3  # Güçlü bearish: Fiyat EMA'ların altında
                            elif current_price < ema_long:
                                tf_score = -2  # Orta bearish: Fiyat EMA'lar arasında
                            else:
                                tf_score = (
                                    -1
                                )  # Zayıf bearish: EMA'lar bearish ama fiyat üstünde

                    # Ağırlıklı toplama ekle
                    ema_score += tf_score * weights[tf]

                    ema_details[tf] = {
                        "ema_short": ema_short,
                        "ema_long": ema_long,
                        "current_price": current_price,
                        "score": tf_score,
                        "alignment": self.trend_score[tf_score]
                    }

            # Normalize et
            normalized_score = ema_score / 3.0

            if normalized_score >= 0.67:
                alignment = "STRONG_BULLISH"  # %67+ bullish güç
            elif normalized_score >= 0.33:
                alignment = "BULLISH"  # %33+ bullish güç
            elif normalized_score <= -0.67:
                alignment = "STRONG_BEARISH"  # %67+ bearish güç
            elif normalized_score <= -0.33:
                alignment = "BEARISH"  # %33+ bearish güç
            else:
                alignment = "NEUTRAL"  # Kararsız bölge

            return {
                "ema_score": ema_score,
                "alignment": alignment,
                "golden_cross":h4_golden_cross,
                "death_cross": h4_death_cross,
                
                "details": ema_details,
                 
                "1h_signals": h1_signals,
                "1h_indicators":h1_indicators,
                
                "4h_signals": h4_signals,
                "4h_indicators":h4_indicators,
                
                "1d_signals": d1_signals,
                "1d_indicators":d1_indicators,
                
 
            }

        except Exception as e:
            return {
                "ema_score": 0,
                "alignment": "ERROR",
                "details": {},
                "error": str(e),
            }

    def _calculate_enhanced_trend_score(self, base_trend, sr_context, trend_data):
        """Gelişmiş trend skoru hesaplama"""
        try:
            # Ağırlıklı skorlama
            weights = {
                "base_indicators": 0.45,  # Mevcut MACD, RSI, etc.
                "support_resistance": 0.35,  # S/R context (artırıldı)
                "ema_hierarchy": 0.20,  # EMA trend
            }

            # Skorları al
            base_score = base_trend.get("total_score", 0)
            sr_score = sr_context.get("sr_score", 0)
            ema_score = trend_data.get("ema_score", 0)

            # Ağırlıklı toplam
            final_score = (
                base_score * weights["base_indicators"]
                + sr_score * weights["support_resistance"]
                + ema_score * weights["ema_hierarchy"]
            )

            # Trend belirleme (daha katı kriterler)
            if final_score >= 3.5:
                trend_direction = "STRONG_BULLISH"
                confidence = "HIGH"
            elif final_score >= 2:
                trend_direction = "BULLISH"
                confidence = "HIGH" if final_score >= 2.5 else "MEDIUM"
            elif final_score >= 0.5:
                trend_direction = "WEAK_BULLISH"
                confidence = "LOW"
            elif final_score <= -3.5:
                trend_direction = "STRONG_BEARISH"
                confidence = "HIGH"
            elif final_score <= -2:
                trend_direction = "BEARISH"
                confidence = "HIGH" if final_score <= -2.5 else "MEDIUM"
            elif final_score <= -0.5:
                trend_direction = "WEAK_BEARISH"
                confidence = "LOW"
            else:
                trend_direction = "NEUTRAL"
                confidence = "LOW"

            # Confidence boost koşulları
            if sr_context.get("volume_confirmation", False):
                if confidence == "MEDIUM":
                    confidence = "HIGH"
                elif confidence == "LOW":
                    confidence = "MEDIUM"
            """
            sr_context > verileri böyle geliyor.
            'sr_score': sr_score,
            'context': context,
            'key_levels': sr_result['summary']['key_levels'],
            'confidence': sr_result['summary']['confidence'],
            'volume_confirmation': signals.get('volume_confirmation', False)
            """
            return {
                "trend": trend_direction,
                "strength": abs(final_score),
                "confidence": confidence,
                "final_score": final_score,
                "breakdown": {
                    "base_score": base_score,
                    "sr_score": sr_score,
                    "ema_score": ema_score,
                    "h4_score": base_trend.get("h4_score", 0),
                    "h1_score": base_trend.get("h1_score", 0),
                },
                "context": {
                    
                    
                    
                    "sr_context": sr_context.get("context", "UNKNOWN"),
                    "alignment": trend_data.get("alignment", "UNKNOWN"),
                    
                    
                    "1h_signals" :trend_data.get("1h_signals", False),
                    "1h_indicators" :trend_data.get("1h_indicators", False),
                    "4h_signals" :trend_data.get("4h_signals", False),
                    "4h_indicators" :trend_data.get("4h_indicators", False),
                    "1d_signals" :trend_data.get("1d_signals", False),
                    "1d_indicators" :trend_data.get("1d_indicators", False),

                    "key_levels": sr_context.get("key_levels", {}),
                    "volume_confirmation": sr_context.get("volume_confirmation", False),
                },
                "last_update": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"[ERROR] Gelişmiş trend skoru hesaplama hatası: {str(e)}")
            return {
                "trend": "ERROR",
                "strength": 0,
                "confidence": "LOW",
                "final_score": 0,
                "error": str(e),
                "last_update": datetime.now().isoformat(),
            }

    def _convert_to_dataframe(self, symbol_data):
        """Cache datasını DataFrame'e çevir"""
        try:
            # Bu kısım senin data structure'ına göre implement edilmeli
            # Örnek implementasyon:

            if "ohlcv" not in symbol_data:
                return None

            ohlcv_data = symbol_data["ohlcv"]

            # Eğer ohlcv_data list of dict ise
            if isinstance(ohlcv_data, list) and len(ohlcv_data) > 0:
                df = pd.DataFrame(ohlcv_data)

                # Column isimlerini standartlaştır
                column_mapping = {
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                }

                df = df.rename(columns=column_mapping)

                # Gerekli columnlar var mı kontrol et
                required_columns = ["Open", "High", "Low", "Close"]
                if all(col in df.columns for col in required_columns):

                    return df

            return None

        except Exception as e:
            print(f"DataFrame conversion error: {str(e)}")
            return None

    def get_trend_data(self, symbol=None):
        """Trend verilerini getir"""
        with SmartCacheManager.cache_locks["trend"]:
            trend_cache = SmartCacheManager.cache_storage.get("trend", {})

            if not trend_cache.get("data"):
                return None if symbol else {}

            if symbol:
                return trend_cache.get("data", {}).get(symbol)
            else:
                return trend_cache.get("data", {})

    def update_cache_async(self, timeframe: str):
        """Arka planda cache güncelle"""

        def update_worker():
            # Trend için özel işlem
            if timeframe == "trend":
                self.calculate_trend_analysis()
                return

            with SmartCacheManager.cache_locks[timeframe]:
                if SmartCacheManager.cache_storage[timeframe]["is_updating"]:
                    print(f"[CACHE-{timeframe}] Zaten güncelleniyor...")
                    return  # Zaten güncelleniyor
                SmartCacheManager.cache_storage[timeframe]["is_updating"] = True

            try:
                print(f"[CACHE-{timeframe}] Güncelleme başlatılıyor...")
                start_time = time.time()

                symbols = self.COINS
                total = len(symbols)
                results = []

                for index, symbol in enumerate(symbols, start=1):
                    try:
                        analysis = self.analyzer.analyze_symbol(
                            symbol, interval=timeframe, limit=200
                        )

                        clean_analysis = self.convert_to_json_serializable(analysis)

                        results.append(clean_analysis)

                    except Exception as e:
                        print(f"[CACHE-{timeframe}] Error analyzing {symbol}: {e}")
                        # sys.exit()
                        continue

                    if index % 50 == 0:
                        print(f"[CACHE-{timeframe}] [{index}/{total}] işlendi...")

                # Cache'i güncelle
                with SmartCacheManager.cache_locks[timeframe]:
                    SmartCacheManager.cache_storage[timeframe]["data"] = results
                    SmartCacheManager.cache_storage[timeframe][
                        "last_update"
                    ] = datetime.now()
                    SmartCacheManager.cache_storage[timeframe]["is_updating"] = False

                elapsed = time.time() - start_time
                print(
                    f"[CACHE-{timeframe}] Tamamlandı! {len(results)} sembol, {elapsed:.1f}s"
                )

            except Exception as e:
                print(f"[CACHE-{timeframe}] Hata: {e}")
                with SmartCacheManager.cache_locks[timeframe]:
                    SmartCacheManager.cache_storage[timeframe]["is_updating"] = False

        # Thread başlat
        thread = threading.Thread(target=update_worker)
        thread.start()
        return thread

    def get_cached_data(self, timeframe: str) -> Optional[Dict]:
        print(f"[STEP 0] {timeframe} için get_cached_data başladı")

        if timeframe not in SmartCacheManager.CACHE_CONFIG:
            print(f"[CACHE] {timeframe} için yapılandırma yok.")
            return None

        print(f"[STEP 1] Lock alınmaya çalışılıyor: {timeframe}")
        with SmartCacheManager.cache_locks[timeframe]:
            print(f"[STEP 2] Lock alındı: {timeframe}")

            cache_data = SmartCacheManager.cache_storage[timeframe]

            if not cache_data["data"]:
                print(f"[CACHE] {timeframe} için veri yok.")
                return None

            print(f"[STEP 3] Veri bulundu. Last update: {cache_data['last_update']}")
            try:
                last_update = cache_data["last_update"]
                print(f"[STEP 4] Last update okundu: {last_update}")

                iso = last_update.isoformat() if last_update else None
                print(f"[STEP 5] isoformat hazır: {iso}")

                is_fresh = self.is_cache_fresh(timeframe)
                print(f"[STEP 6] is_cache_fresh döndü: {is_fresh}")

                # Trend için farklı response formatı
                if timeframe == "trend":
                    return {
                        "timeframe": timeframe,
                        "data": cache_data["data"].copy(),
                        "last_update": iso,
                        "total_symbols": len(cache_data["data"]),
                        "is_fresh": is_fresh,
                        "is_updating": cache_data["is_updating"],
                    }
                else:
                    return {
                        "timeframe": timeframe,
                        "data": cache_data["data"].copy(),
                        "last_update": iso,
                        "total_symbols": len(cache_data["data"]),
                        "is_fresh": is_fresh,
                        "is_updating": cache_data["is_updating"],
                    }
            except Exception as e:
                print(f"[ERROR] Bir hata oluştu: {e}")
                return None

    def start_background_scheduler(self):
        """Arka plan zamanlayıcısını başlat - trend analizi dahil"""

        def scheduler():
            while self.is_running:
                try:
                    for timeframe in SmartCacheManager.CACHE_CONFIG.keys():
                        if self.should_update_cache(timeframe):
                            print(f"[SCHEDULER] {timeframe} güncellenecek...")
                            self.update_cache_async(timeframe)

                    # En kısa interval kadar bekle (trend interval'ını da göz önünde bulundur)
                    intervals = []
                    for tf, config in SmartCacheManager.CACHE_CONFIG.items():
                        if tf == "trend":
                            intervals.append(
                                config["interval"] // 60
                            )  # saniyeyi dakikaya çevir
                        else:
                            intervals.append(config["update_interval"])  #

                    min_interval = min(intervals)
                    print(f"[SCHEDULER] {min_interval} dakika bekleniyor...")
                    time.sleep(min_interval * 60)  # dakika -> saniye

                except Exception as e:
                    print(f"[SCHEDULER] Hata: {e}")
                    time.sleep(60)  # Hata durumunda 1dk bekle

        scheduler_thread = threading.Thread(target=scheduler, daemon=True)
        scheduler_thread.start()
        print("[SCHEDULER] Arka plan zamanlayıcısı başlatıldı (trend analizi dahil)")

    def initialize_cache(self):
        """Uygulama başlangıcında cache'leri yükle"""
        print("[INIT] Cache başlatılıyor...")
        threads = []

        # İlk cache yüklemesi (trend hariç)
        for timeframe in SmartCacheManager.CACHE_CONFIG.keys():
            if timeframe == "trend":
                continue  # Trend'i sonra hesaplayacağız

            print(f"[INIT] {timeframe} cache yükleniyor...")
            thread = self.update_cache_async(timeframe)
            threads.append(thread)

        # Cache'lerin yüklenmesini bekle
        for thread in threads:
            thread.join()
        print("[INIT] Temel cache'ler yüklendi.")

        # İlk trend hesaplaması
        print("[INIT] İlk trend analizi yapılıyor...")
        self.calculate_trend_analysis()

        # input(f"{SmartCacheManager.cache_storage['trend']['data']}")

        # Scheduler'ı başlat
        time.sleep(2)
        self.start_background_scheduler()
        print("[INIT] Sistem hazır!")




    def stop(self):
        """Cache manager'ı durdur"""
        self.is_running = False
        print("[CACHE] SmartCacheManager durduruldu.")
