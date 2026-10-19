import numpy as np
import pandas as pd
from smartCache import SmartCacheManager
import time, math


class DataManager:

    def __init__(self, cache_manager, COINS, analyzer):

        self.cache_manager = cache_manager
        self.COINS = COINS
        self.analyzer = analyzer

    def tf_filter(self, response, tf):
        """
         saatlik zaman dilimi için coin filtreleme - Güçlü sinyal kombinasyonları
        Args:
            response: Coin verilerini içeren dictionary
        Returns:
            dict: {'passed': bool, 'score': int, 'reason': str}
        """

        signals = response.get("signals", {})
        indicators = response.get("indicators", {})
        context = response.get("trend_analysis", {}).get("context", {})

        # if tf == "4h":
        #     tf_data = SmartCacheManager.cache_storage.get(tf, {}).get("data", [])
        # elif tf == "1h":
        #     tf_data = SmartCacheManager.cache_storage.get(tf, {}).get("data", [])

        # context = response.get("trend_analysis", {}).get("context", {})
        # ema_alignment = context.get("ema_alignment", "")
        # if ema_alignment == "STRONG_BEARISH":
        #      return {'passed': False, 'score': 0, 'reason': 'EMA Alignment - Strong Bearish Trend'}

        macd_bullish_signal = (
            signals.get("red_dark_to_light_stable", False)  # 3 dark red to light red
            or signals.get("three_red_to_green", False)  # 3  light red  to green
            or signals.get(
                "three_dark_red_to_green",
                False,  # 3 dark red to light green (bullish_weak)
            )
        )

        # === ÇOK GÜÇLÜ SİNYALLER (Tek başına yeterli) ===
        # Triple Confluence (Süper güçlü)
        if (
            (signals.get("macd_buy", False) or macd_bullish_signal)
            and (signals.get("rsi_buy", False) or signals.get("tight_rsi_buy", False))
            and (signals.get("bb_buy", False) or signals.get("bb_buy_buffer", False))
        ):
            return {
                "passed": True,
                "score": 96,
                "reason": f"{tf} : Triple Bullish Confluence (MACD+RSI+BB)",
            }

        #  Bollinger Bands Buy Sinyalleri

        #   BB ve RSI BUY
        if signals.get("bb_buy", False) and signals.get("rsi_buy", False):
            return {
                "passed": True,
                "score": 95,
                "reason": f"{tf} :Bollinger Bands Buy + RSI Buy",
            }
        #  BB VE RSİ TIGHT BUY
        if signals.get("bb_buy", False) and signals.get("tight_rsi_buy", False):
            return {
                "passed": True,
                "score": 85,
                "reason": f"{tf} :Bollinger Bands Buy + RSI Tight Buy",
            }

        #  BB VE bearish_weak
        if signals.get("bb_buy", False) and macd_bullish_signal:
            return {
                "passed": True,
                "score": 80,
                "reason": f"{tf} :Bollinger Bands Buy + MACD Weak Bearish",
            }
        #  BB OR BB_BUFFER VE RSİ > 0
        if (
            signals.get("bb_buy", False) or signals.get("bb_buy_buffer", False)
        ) and indicators.get("rsi_diff") >= 0:
            return {
                "passed": True,
                "score": 70,
                "reason": f"{tf} | Bollinger Bands Buy + RSI DIFF > 0 => DİFF:{indicators.get('rsi_diff')}",
            }
        if (
            signals.get("bb_buy", False) or signals.get("bb_buy_buffer", False)
        ) and indicators.get("rsi_diff") >= 0:
            return {
                "passed": True,
                "score": 70,
                "reason": f"{tf} | Bollinger Bands Buy + RSI DIFF > 0 => DİFF:{indicators.get('rsi_diff')}",
            }

        if signals.get("bb_buy", False) or signals.get("bb_buy_buffer", False):
            info = "Buffer" if signals.get("bb_buy_buffer", False) else ""
            return {
                "passed": True,
                "score": 60,
                "reason": f"{tf} | Bollinger Bands Buy : {info}",
            }
        # RSI + MACD Kombinasyonu

        # RSI BUY 30 YADA 35 DEN YUKSELDI
        if (25 < indicators.get("rsi") < 35 and indicators.get("rsi_diff") >= 0) or (
            signals.get("rsi_buy", False) or signals.get("tight_rsi_buy", False)
        ):

            rsi_info = (
                f" rsi_diff : {indicators.get('rsi_diff')}"
                if 25 < indicators.get("rsi") < 35 and indicators.get("rsi_diff") >= 0
                else (
                    "RSI BUY sinyali"
                    if signals.get("rsi_buy", False)
                    or signals.get("tight_rsi_buy", False)
                    else "NO REASON"
                )
            )

            if signals.get("macd_buy", False):

                return {
                    "passed": True,
                    "score": 70,
                    "reason": f"{tf} : {rsi_info} + MACD Buy Signal",
                }
            elif macd_bullish_signal:
                return {
                    "passed": True,
                    "score": 60,
                    "reason": f"{tf} | {rsi_info} + MACD R->WEAK BULLISH OR GREEN ",
                }

        # if (50 < indicators.get("rsi") < 65 and indicators.get("rsi_diff") >= 0) and signals.get("three_weak_to_strong_green",False):
        #     rsi_info = (
        #         f"rsi_diff : {indicators.get('rsi_diff')} 3 Light to Dark Green"
        #     )

        #     return {
        #         "passed": True,
        #         "score": 40,
        #         "reason": f"{tf} | {rsi_info} + MACD RED-> GREEN ",
        #     }
        # ❌
        if (
            signals.get("red_dark_to_light_stable")
            and 25 < indicators.get("rsi") < 55
            and indicators.get("rsi_diff") >= 0
        ):
            return {
                "passed": True,
                "score": 40,
                "reason": f"{tf} | 3 Bearish Strong > 1 Weak 25 < rsi+ < 55 ",
            }

        if signals.get("red_dark_to_light_stable"):
            return {
                "passed": True,
                "score": 40,
                "reason": f"{tf} | 3 Bearish Strong > 1 Weak    ",
            }
        if tf not in ["15m", "30m"]:
            if (
                signals.get("green_light_to_dark_stable")
                and not signals.get("bb_sell")
                and 25 < indicators.get("rsi") < 50
                and indicators.get("rsi_diff") >= 0
            ):
                return {
                    "passed": False,  # False
                    "score": 40,
                    "reason": f"{tf} | Bullish Weak > Bullish Strong ",
                }

        if tf in ["30m"]:  # ["30m","1h","4h","1d"]:
            # Golden Cross (En güçlü trend dönüş sinyali)
            if signals.get("golden_cross", False) and indicators.get("rsi_diff") > 1:
                death_Cross = signals.get("death_cross", False)
                if not death_Cross and not signals.get("bb_sell", False):
                    print(f"Death Cross: {context.get('death_cross', False)}")
                    return {
                        "passed": True,
                        "score": 75,
                        "reason": f"{tf} | Golden Cross - RSI ⬆ Very Strong Bull Signal",
                    }

        # === FİLTRELEME KURALLARI ===

        # Negatif sinyaller (eleme kriterleri)
        # negative_signals = []

        # if signals.get("death_cross", False):
        #     return {'passed': False, 'score': 0, 'reason': 'Death Cross - Strong Bear Signal'}

        # if signals.get("zero_cross_bearish", False) and signals.get("bearish_strong", False):
        #     return {'passed': False, 'score': 0, 'reason': 'MACD Zero Cross Down + Strong Bearish'}

        # if (signals.get("rsi_sell", False) and
        #     signals.get("macd_sell", False) and
        #     signals.get("bb_sell", False)):
        #     return {'passed': False, 'score': 0, 'reason': 'Triple Bearish Confluence'}

        return {"passed": False, "score": 0, "reason": f"{tf} :No strong signals found"}

    def daily_picker(self, response, timeframe):
        
        symbol = response.get("symbol", "UNKNOWN")
        d1_data = SmartCacheManager.cache_storage.get("1d", {}).get("data", [])
        symbol_data_1d = next(
            (item for item in d1_data if item.get("symbol") == symbol), None
        )
        
        

    def daily_filter(self, response, timeframe):
        """
        1 günlük zaman dilimi için coin filtreleme

        Args:
            cache_response: Coin verilerini içeren dictionary

        Returns:
            bool: True ise coin uygun, False ise elenmeli
        """

        symbol = response.get("symbol", "UNKNOWN")
        w1_data = SmartCacheManager.cache_storage.get("1w", {}).get("data", [])
        d1_data = SmartCacheManager.cache_storage.get("1d", {}).get("data", [])
        h12_data = SmartCacheManager.cache_storage.get("12h", {}).get("data", [])
        h8_data = SmartCacheManager.cache_storage.get("8h", {}).get("data", [])
        h6_data = SmartCacheManager.cache_storage.get("6h", {}).get("data", [])
        h4_data = SmartCacheManager.cache_storage.get("4h", {}).get("data", [])
        h1_data = SmartCacheManager.cache_storage.get("1h", {}).get("data", [])
        m30_data = SmartCacheManager.cache_storage.get("30m", {}).get("data", [])
        m15_data = SmartCacheManager.cache_storage.get("15m", {}).get("data", [])

        symbol_data_1w = next(
            (item for item in w1_data if item.get("symbol") == symbol), None
        )

        symbol_data_1d = next(
            (item for item in d1_data if item.get("symbol") == symbol), None
        )

        symbol_data_12h = next(
            (item for item in h12_data if item.get("symbol") == symbol), None
        )
        symbol_data_8h = next(
            (item for item in h8_data if item.get("symbol") == symbol), None
        )

        symbol_data_6h = next(
            (item for item in h6_data if item.get("symbol") == symbol), None
        )

        symbol_data_4h = next(
            (item for item in h4_data if item.get("symbol") == symbol), None
        )

        symbol_data_1h = next(
            (item for item in h1_data if item.get("symbol") == symbol), None
        )

        symbol_data_30m = next(
            (item for item in m30_data if item.get("symbol") == symbol), None
        )
        symbol_data_15m = next(
            (item for item in m15_data if item.get("symbol") == symbol), None
        )
        symbol_check_data = {
            "15m": symbol_data_15m,
            "30m": symbol_data_30m,
            "1h": symbol_data_1h,
            "4h": symbol_data_4h,
            "6h": symbol_data_6h,
            "8h": symbol_data_8h,
            "12h": symbol_data_12h,
            "1d": symbol_data_1d,
            "1w": symbol_data_1w,
        }

        timeframe_filter_list = {
            "15m": ["15m", "30m", "1h", "4h"],
            "30m": [
                "30m",
                "1h",
                "4h",
            ],
            "1h": [
                "1h",
                "4h",
            ],
            "4h": ["4h", "8h", "12h"],
            "6h": ["6h", "12h"],
            "8h": ["8h", "1d"],
            "12h": ["12h", "1d"],
            "1d": ["1d"],
            "1w": ["1d"],
        }
        print(f"timeframe: {timeframe}")
        for tf in timeframe_filter_list[timeframe]:

            tf_signals = symbol_check_data[tf]["signals"]
            tf_indicators = symbol_check_data[tf]["indicators"]
            print(f"tf >{tf} symbol: {symbol}")
            if (
                tf_signals.get("death_cross")
                or tf_signals.get("rsi_sell")
                or tf_signals.get("bb_sell")
                or tf_signals.get("macd_sell")
                # or tf_signals.get("green_dark_to_light_stable")  #  3 Bullish strong 1 bullish weak
                # or tf_signals.get("red_light_to_dark_stable")   #  3 Bearish weak to Bearish strong
                or tf_signals.get(
                    "green_light_to_red_stable"
                )  #  3 bullish waek to Bearish weak or strong
                or tf_signals.get(
                    "one_strong_to_two_weak_green"
                )  # 1 Bullish strong 2 bullish weak
            ):
                return False

        # # RSI kontrolü - 70 üzeri eleme
        # rsi = response.get("indicators", {}).get("rsi", 0)
        # signals = response.get("signals", {})
        # if rsi > 70:
        #     return False
        # # MACD sell sinyali kontrolü
        # if signals.get("macd_sell", False) or signals.get("macd_sell", False):
        #     return False

        d1_signals = symbol_data_1d["signals"]
        d1_indicators = symbol_data_1d["indicators"]

        h4_signals = symbol_data_4h["signals"]
        h4_indicators = symbol_data_4h["indicators"]

        if timeframe in ["15m", "30m", "1h"]:
            if h4_signals.get("count_bullish_weak") > 4:
                return False
            elif h4_signals.get("count_bullish_strong") > 4:
                return False

        if timeframe == "4h":
            if d1_signals.get("count_bullish_weak") > 3:
                return False
            elif d1_signals.get("count_bullish_strong") > 3:
                return False

        d1_rsi_trend = d1_indicators.get("rsi_trend", "UNKOWN")
        d1_rsi_diff = d1_indicators.get("rsi_diff")
        d1_rsi = d1_indicators.get("rsi")
        d1_trend = d1_indicators.get("current_tf_trend", "UNKOWN")
        d1_rsi_overbought_zone = d1_signals.get("d1_rsi_overbought_zone", False)
        d1_bearish_strong = d1_signals.get("bearish_strong", False)
        d1_bearish_weak = d1_signals.get("bearish_weak", False)
        d1_bullish_weak = d1_signals.get("bullish_weak", False)

        h4_death_cross = h4_signals.get("death_cross")
        h4_bearish_strong = h4_signals.get("bearish_strong")

        # if symbol == "WUSDT":
        #     print(
        #         f"h4_death_cross : {h4_death_cross} 1d rsi h4_bearish_strong: {h4_bearish_strong} d1_macd_sell : {d1_macd_sell}",
        #         end="  ",
        #     )
        #     print(
        #         f"d1_rsi : {d1_rsi} 1d rsi d1_bullish_weak: {d1_bullish_weak} d1_rsi_diff : {d1_rsi_diff}"
        #     )

        if (
            d1_signals.get("death_cross")
            or d1_signals.get("rsi_sell")
            or d1_signals.get("bb_sell")
            or d1_signals.get("macd_sell")
        ):
            return False

        if h4_death_cross and h4_bearish_strong:
            return False

        if d1_bullish_weak and d1_rsi_diff < 0:  # ✅
            return False

        if d1_rsi >= 48 and d1_rsi_diff < 0:
            return False

        if 25 < d1_rsi <= 48 and d1_bearish_strong and d1_rsi_diff < 0:
            return False
        if d1_rsi > 75 and d1_signals.get("bb_sell"):
            return False

        # Tüm filtreleri geçti
        return True

    def get_filtered_symbols(self, timeframe):
        """
        cache_response listesindeki coinleri filtrele

        Args:
            cache_response: Liste halinde coin verileri

        Returns:
            list: Filtrelenmiş coin listesi
        """

        response, should_continue = self.check_and_handle_cache(
            timeframe=timeframe, include_trend=True, force_refresh=False
        )

        if should_continue:
            print("Cache'den veri alınamadı, gerçek zamanlı analiz yapılıyor...")
            response = self.real_time_analysis(timeframe="1d", include_trend=True)

        daily_filtered_coins = []
        #  Timeframe  repononse daily filter
        for coin_data in response:
            symbol = coin_data.get("symbol", "UNKNOWN")

            if self.daily_filter(coin_data, timeframe):

                print(f"✅ {symbol} - Filtreyi geçti")
                daily_filtered_coins.append(coin_data.get("symbol", "UNKNOWN"))
            else:
                symbol = coin_data.get("symbol", "UNKNOWN")
                print(f"❌ {symbol} - Elendi")

        print(f"[Daily Filter]:{len(daily_filtered_coins)} tane filtreyi geçti.")
        check_this_tf = ["15m", "30m", "1h", "4h", "1d"]
        filtered_coins = {}

        for tf in check_this_tf:

            response, should_continue = self.check_and_handle_cache(
                timeframe=tf, include_trend=True, force_refresh=False
            )
            filtered_coins[tf] = []
            #
            for coin_data in response:
                symbol = coin_data.get("symbol", "UNKNOWN")
                if symbol in daily_filtered_coins:
                    response_filter = self.tf_filter(coin_data, tf)
                    if response_filter.get("passed", False):
                        reason = response_filter.get("reason", False)
                        print(f"✅ {symbol} - {tf} Filtreyi geçti Reason:{reason}")
                        response_filter["symbol"] = symbol
                        filtered_coins[tf].append(response_filter)

        for tf in check_this_tf:
            print(
                f"[GET FILTER]   {len(filtered_coins[tf])} tanesi {tf.upper()} filtreyi geçti"
            )

        return filtered_coins

    def check_and_handle_cache(
        self, timeframe="None", include_trend=False, force_refresh=False
    ):
        """
        Cache'li timeframe'ler için cache kontrol eder ve uygun response döndürür

        Args:
            timeframe (str): Kontrol edilecek timeframe
            include_trend (bool): Trend verisi eklenip eklenmeyeceği
            force_refresh (bool): Cache'i zorla yenileyip yenilemeyeceği

        Returns:
            tuple: (response_data, should_continue)
                - response_data: JSON response verisi (eğer cache'den döndürülecekse)
                - should_continue: API işleminin devam etmesi gerekip gerekmediği (bool)
        """

        # Cache'li timeframe'ler için cache kontrol et
        if timeframe in SmartCacheManager.CACHE_CONFIG and not force_refresh:
            print(f"[API] Cache kontrol ediliyor: {timeframe}")
            cached_data = self.cache_manager.get_cached_data(timeframe)

            if cached_data and cached_data["is_fresh"]:  # Cache taze ise
                print(f"[API] Cache'den döndürülüyor: {timeframe}")
                results = cached_data["data"]

                # Trend verisini ekle
                if include_trend:
                    results = self.add_trend_data_to_results(results)

                return results, False  # Cache'den döndür, işlemi durdur

            elif cached_data and not cached_data["is_updating"]:  # Cache eski ise
                print(f"[API] Cache eski, arka planda güncelleniyor: {timeframe}")
                # Arka planda güncelle, eski cache'i döndür
                self.cache_manager.update_cache_async(timeframe)
                results = cached_data["data"]

                # Trend verisini ekle
                if include_trend:
                    results = self.add_trend_data_to_results(results)

                return results, False  # Eski cache'i döndür, işlemi durdur

            elif cached_data and cached_data["is_updating"]:  # Cache güncelleniyorsa
                print(
                    f"[API] Cache güncelleniyor, mevcut veri döndürülüyor: {timeframe}"
                )
                results = cached_data["data"]

                # Trend verisini ekle
                if include_trend:
                    results = self.add_trend_data_to_results(results)

                return results, False  # Mevcut veriyi döndür, işlemi durdur

            else:
                print(
                    f"[API] Cache bulunamadı, gerçek zamanlı analiz yapılacak: {timeframe}"
                )
                return None, True  # Cache yok, işleme devam et

        else:
            # Cache'li olmayan timeframe veya force_refresh durumu
            return None, True  # İşleme devam et

    def add_trend_data_to_results(self, results):
        """Analiz sonuçlarına trend verilerini ekler"""
        try:
            print("[TREND] Trend verileri alınıyor...")

            # Trend cache'inden tüm verileri al
            trend_data = self.cache_manager.get_trend_data()

            if not trend_data:
                print("[TREND] Trend verileri bulunamadı")
                return results

            # Her analiz sonucuna trend verisini ekle
            enhanced_results = []
            trend_added_count = 0

            for analysis in results:
                symbol = analysis.get("symbol")
                if symbol and symbol in trend_data:
                    # Trend verisini ekle

                    analysis["trend_analysis"] = trend_data[symbol]
                    trend_added_count += 1
                else:
                    # Trend verisi yoksa default değer
                    analysis["trend_analysis"] = {
                        "trend": "UNKNOWN",
                        "strength": 0,
                        "confidence": "LOW",
                        "details": "Trend data not available",
                    }

                enhanced_results.append(analysis)

            print(
                f"[TREND] {trend_added_count}/{len(results)} sembole trend verisi eklendi"
            )
            return enhanced_results

        except Exception as e:
            print(f"[TREND] Trend verisi ekleme hatası: {e}")
            # Hata durumunda orijinal sonuçları döndür
            return results

    def real_time_analysis(self, timeframe="1h", include_trend=True):

        # Cache yoksa veya force refresh varsa - gerçek zamanlı analiz
        print(f"[API] Gerçek zamanlı analiz: {timeframe}")

        symbols = self.COINS
        total = len(symbols)
        results = []
        start_time = time.time()

        for index, symbol in enumerate(symbols, start=1):
            try:
                analysis = self.analyzer.analyze_symbol(
                    symbol, interval=timeframe, limit=200
                )
                # Temizle ve JSON serializable yap
                clean_analysis = self.convert_to_json_serializable(analysis)
                results.append(clean_analysis)

            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
                continue

            # Her 50 sembolde bir bilgi ver
            if index % 50 == 0:
                print(f"[{index}/{total}] analiz ediliyor...")

        # Trend verisini ekle
        if include_trend:
            results = self.add_trend_data_to_results(results)

        elapsed = time.time() - start_time
        print(f"[API] Analiz tamamlandı: {len(results)} sembol, {elapsed:.1f}s")
        return results

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
            # float ise NaN kontrolü yap
            if isinstance(obj, float) and math.isnan(obj):
                return None
            return float(obj)

        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif pd.isna(obj):  # pandas NaN ve None kontrolü
            return None
        elif hasattr(obj, "item"):  # pandas scalar
            return self.convert_to_json_serializable(obj.item())
        else:
            return obj
