import pandas as pd
import numpy as np
import talib
from typing import List, Dict, Tuple, Optional
from marketData import BinanceMarketData
from scipy.signal import find_peaks, argrelextrema


class MACD:

    def __init__(
        self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
    ):

        self.configs = {
            "15m": {"fast": 12, "slow": 26, "signal": 9},  # Standart - hızlı sinyaller
            "30m": {"fast": 12, "slow": 26, "signal": 9},  # Standart - hızlı sinyaller
            "1h": {"fast": 11, "slow": 26, "signal": 9},  # Standart - genel kullanım
            "4h": {"fast": 11, "slow": 26, "signal": 9},
            "6h": {"fast": 11, "slow": 26, "signal": 9},
            "8h": {"fast": 11, "slow": 26, "signal": 9},
            "12h": {"fast": 11, "slow": 26, "signal": 9},
            "1d": {"fast": 11, "slow": 26, "signal": 8},  # Standart - günlük analiz
            "1w": {"fast": 5, "slow": 13, "signal": 8},  # Haftalık - makro trend
        }

        # Divergence parametreleri
        self.divergence_params = {
            "prominence_factor": 0.1,  # Peak detection hassasiyeti
            "min_distance": 5,  # Peak'ler arası minimum mesafe
            "lookback_points": 3,  # Kaç nokta geriye bakılacak
        }

        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def calculate(
        self, data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Dict[str, pd.Series]:
        """MACD hesaplama"""
        macd_line, signal_line, histogram = talib.MACD(
            data.values, fastperiod=fast, slowperiod=slow, signalperiod=signal
        )
        return {
            "macd": pd.Series(macd_line, index=data.index),
            "signal": pd.Series(signal_line, index=data.index),
            "histogram": pd.Series(histogram, index=data.index),
        }

    def generate_signals(
        self,
        macd_data: Dict[str, pd.Series],
        price_data=None,
        include_histogram: bool = True,
        include_zero_line: bool = True,
        include_divergence: bool = True,
    ) -> Dict[str, pd.Series]:
        """
        MACD tabanlı tüm al/sat sinyalleri

        Args:
            macd_data: calculate() metodundan dönen MACD verileri
            price_data: Fiyat verisi (divergence için gerekli, dict with 'close' key veya pd.Series)
            include_histogram: Histogram sinyallerini dahil et
            include_zero_line: Zero line sinyallerini dahil et
            include_divergence: Divergence sinyallerini dahil et

        Returns:
            Dict with all signal types
        """
        macd_line = macd_data["macd"]
        signal_line = macd_data["signal"]

        # 1. Temel MACD sinyalleri (çizgi kesişimleri)
        basic_buy = (macd_line > signal_line) & (
            macd_line.shift(1) <= signal_line.shift(1)
        )  #  MACD çizgisi sinyal çizgisini yukarı keserse  → AL
        basic_sell = (macd_line < signal_line) & (
            macd_line.shift(1) >= signal_line.shift(1)
        )

        signals = {
            "macd_buy": basic_buy,
            "macd_sell": basic_sell,
            "buy_basic": basic_buy,
            "sell_basic": basic_sell,
        }

        # 2. Histogram sinyalleri
        if include_histogram:
            histogram_signals = self.generate_histogram_signals(macd_data)
            histogram_transitions = self.generate_histogram_transitions(
                histogram_signals, macd_data
            )
            signals.update(
                {
                    "bullish_strong": histogram_signals["bullish_strong"],
                    "bullish_weak": histogram_signals["bullish_weak"],
                    "bearish_strong": histogram_signals["bearish_strong"],
                    "bearish_weak": histogram_signals["bearish_weak"],
                }
            )

            signals.update(histogram_transitions)

        # 3. Zero line sinyalleri
        if include_zero_line:
            zero_signals = self.generate_macd_zero_cross_signals(macd_data)
            zero_cross = self.generate_centerline_signals(macd_data)
            signals.update(
                {
                    "zero_cross_bullish": zero_cross["zero_cross_bullish"],
                    "zero_cross_bearish": zero_cross["zero_cross_bearish"],
                    "zero_buy": zero_signals["zero_buy"],
                    "zero_sell": zero_signals["zero_sell"],
                    "buy_zero": zero_signals["zero_buy"],
                    "sell_zero": zero_signals["zero_sell"],
                }
            )

        # 4. Divergence sinyalleri
        divergence_buy = pd.Series(False, index=macd_line.index)
        divergence_sell = pd.Series(False, index=macd_line.index)

        if include_divergence and price_data is not None:
            try:
                div_signals = self.get_divergence_signals(
                    price_data, macd_data, advanced=True
                )

                # Divergence buy sinyallerini boolean series'e çevir
                for signal in div_signals["buy_signals"]:
                    if signal["index"] < len(divergence_buy):
                        divergence_buy.iloc[signal["index"]] = True

                # Divergence sell sinyallerini boolean series'e çevir
                for signal in div_signals["sell_signals"]:
                    if signal["index"] < len(divergence_sell):
                        divergence_sell.iloc[signal["index"]] = True

            except Exception as e:
                print(f"Divergence hesaplama hatası: {e}")
                # Hata durumunda boş series kullan
                pass

        signals.update(
            {
                "buy_divergence": divergence_buy,
                "sell_divergence": divergence_sell,
                "divergence_buy": divergence_buy,
                "divergence_sell": divergence_sell,
            }
        )

        # 5. Birleşik güçlü sinyaller
        combined_buy = basic_buy
        combined_sell = basic_sell

        if include_histogram:
            combined_buy = combined_buy | histogram_signals["bullish_strong"]
            combined_sell = combined_sell | histogram_signals["bullish_weak"]

        if include_zero_line:
            combined_buy = combined_buy | zero_signals["zero_buy"]
            combined_sell = combined_sell | zero_signals["zero_sell"]

        if include_divergence:
            combined_buy = combined_buy | divergence_buy
            combined_sell = combined_sell | divergence_sell

        # Süper güçlü sinyaller (multiple confirmation)
        if include_histogram and include_zero_line:
            # Güçlü AL: En az 2 farklı sinyal türü
            strong_buy = (
                (
                    basic_buy
                    & (
                        zero_signals["zero_buy"]
                        | histogram_signals["bullish_strong"]
                        | divergence_buy
                    )
                )
                | (
                    zero_signals["zero_buy"]
                    & (histogram_signals["bullish_strong"] | divergence_buy)
                )
                | (histogram_signals["bullish_strong"] & divergence_buy)
            )

            # Güçlü SAT: En az 2 farklı sinyal türü
            strong_sell = (
                (
                    basic_sell
                    & (
                        zero_signals["zero_sell"]
                        | histogram_signals["bullish_weak"]
                        | divergence_sell
                    )
                )
                | (
                    zero_signals["zero_sell"]
                    & (histogram_signals["bullish_weak"] | divergence_sell)
                )
                | (histogram_signals["bullish_weak"] & divergence_sell)
            )

            signals.update({"buy_strong": strong_buy, "sell_strong": strong_sell})

        # 6. Tüm sinyalleri birleştir
        signals.update({"buy_all": combined_buy, "sell_all": combined_sell})

        return signals

    def generate_histogram_signals(self, macd_data):
        """Histogram tabanlı momentum sinyalleri (bullish ve bearish)"""
        histogram = macd_data["histogram"]

        # Mutlak değişim kontrolü
        hist_growing = histogram.abs() > histogram.abs().shift(1)
        hist_shrinking = histogram.abs() < histogram.abs().shift(1)

        # Bullish (pozitif histogram)
        bullish_strengthening = (histogram > 0) & hist_growing  # yukarı yön güçleniyor
        bullish_weakening = (histogram > 0) & hist_shrinking  # yukarı yön zayıflıyor

        # Bearish (negatif histogram)
        bearish_strengthening = (histogram < 0) & hist_growing  # aşağı yön güçleniyor
        bearish_weakening = (histogram < 0) & hist_shrinking  # aşağı yön zayıflıyor

        return {
            "bullish_strong": bullish_strengthening,
            "bullish_weak": bullish_weakening,
            "bearish_strong": bearish_strengthening,
            "bearish_weak": bearish_weakening,
        }

    def generate_histogram_transitions(self, histogram_signals, macd_data):
        """Histogram renk geçişlerini yakalayan fonksiyon - Yaklaşım 1 ve 3 entegre"""

        def check_consecutive_count(signal_series, check_last=8):
            last_values = signal_series.tail(check_last)
            values_list = last_values.tolist()

            consecutive_count = 0
            for value in reversed(values_list):
                if value:
                    consecutive_count += 1
                else:
                    break

            return consecutive_count

        histogram = macd_data["histogram"]

        histogram_now_bullish_strong = histogram_signals["bullish_strong"]
        histogram_now_bullish_weak = histogram_signals["bullish_weak"]
        histogram_now_bearish_strong = histogram_signals["bearish_strong"]
        histogram_now_bearish_weak = histogram_signals["bearish_weak"]
        # === YAKLAŞIM 1: SÜREKLI 3 BAR (STABLE) ===
        # 3 bar'lık geçmiş sinyaller
        prev_1_bullish_strong = histogram_signals["bullish_strong"].shift(1)
        prev_1_bullish_weak = histogram_signals["bullish_weak"].shift(1)
        prev_1_bearish_strong = histogram_signals["bearish_strong"].shift(1)
        prev_1_bearish_weak = histogram_signals["bearish_weak"].shift(1)

        prev_2_bullish_strong = histogram_signals["bullish_strong"].shift(2)
        prev_2_bullish_weak = histogram_signals["bullish_weak"].shift(2)
        prev_2_bearish_strong = histogram_signals["bearish_strong"].shift(2)
        prev_2_bearish_weak = histogram_signals["bearish_weak"].shift(2)

        prev_3_bullish_strong = histogram_signals["bullish_strong"].shift(3)
        prev_3_bullish_weak = histogram_signals["bullish_weak"].shift(3)
        prev_3_bearish_strong = histogram_signals["bearish_strong"].shift(3)
        prev_3_bearish_weak = histogram_signals["bearish_weak"].shift(3)

        count_bullish_weak = check_consecutive_count(histogram_signals["bullish_weak"])
        count_bullish_strong = check_consecutive_count(
            histogram_signals["bullish_strong"]
        )
        count_bearish_weak = check_consecutive_count(histogram_signals["bearish_weak"])
        count_bearish_strong = check_consecutive_count(
            histogram_signals["bearish_strong"]
        )

        # 3 bar sürekli aynı → geçiş (STABLE)
        green_dark_to_light_stable = (
            prev_3_bullish_strong
            & prev_2_bullish_strong
            & prev_1_bullish_strong
            & histogram_signals["bullish_weak"]
        )

        green_light_to_dark_stable = (
            prev_3_bullish_weak
            & prev_2_bullish_weak
            & prev_1_bullish_weak
            & histogram_signals["bullish_strong"]
        )

        green_light_to_red_stable = (
            prev_3_bullish_weak
            & prev_2_bullish_weak
            & prev_1_bullish_weak
            & (histogram_signals["bearish_strong"] | histogram_signals["bearish_weak"])
        )

        red_dark_to_light_stable = (
            prev_3_bearish_strong
            & prev_2_bearish_strong
            & prev_1_bearish_strong
            & histogram_signals["bearish_weak"]
        )

        red_light_to_dark_stable = (
            prev_3_bearish_weak
            & prev_2_bearish_weak
            & prev_1_bearish_weak
            & histogram_signals["bearish_strong"]
        )
        red_light_to_green_stable = (
            prev_3_bearish_weak
            & prev_2_bearish_weak
            & prev_1_bearish_weak
            & (histogram_signals["bullish_weak"] | histogram_signals["bullish_strong"])
        )
        # === YAKLAŞIM 3: TREND BAZLI (MOMENTUM) ===
        # 3 bar'lık momentum analizi
        momentum_3bar = histogram.rolling(3).mean()
        momentum_prev_3bar = momentum_3bar.shift(1)
        momentum_change = momentum_3bar - momentum_prev_3bar

        # Güçlü momentum değişimi (threshold ayarlanabilir)
        strong_momentum_change = momentum_change.abs() > 0.01

        # Trend bazlı geçişler
        green_trend_weakening = (
            (momentum_3bar > 0)
            & (momentum_change < 0)
            & strong_momentum_change
            & histogram_signals["bullish_weak"]
        )

        green_trend_strengthening = (
            (momentum_3bar > 0)
            & (momentum_change > 0)
            & strong_momentum_change
            & histogram_signals["bullish_strong"]
        )

        red_trend_weakening = (
            (momentum_3bar < 0)
            & (momentum_change > 0)
            & strong_momentum_change
            & histogram_signals["bearish_weak"]
        )

        red_trend_strengthening = (
            (momentum_3bar < 0)
            & (momentum_change < 0)
            & strong_momentum_change
            & histogram_signals["bearish_strong"]
        )

        # === KALIP/PATTERN BAZLI SİNYALLER ===
        # 3 weak'den sonra 1 strong (toparlanma sinyali)
        three_weak_to_strong_green = (
            prev_3_bullish_weak
            & prev_2_bullish_weak
            & prev_1_bullish_weak
            & histogram_signals["bullish_strong"]
        )

        three_weak_to_strong_red = (
            prev_3_bearish_weak
            & prev_2_bearish_weak
            & prev_1_bearish_weak
            & histogram_signals["bearish_strong"]
        )

        # 3 strong'dan sonra 1 weak (zayıflama başlangıcı)

        three_strong_to_weak_green = (
            prev_3_bullish_strong
            & prev_2_bullish_strong
            & prev_1_bullish_strong
            & histogram_signals["bullish_weak"]
        )
        one_strong_to_two_weak_green = (
            prev_2_bullish_strong
            & prev_1_bullish_weak
            & histogram_signals["bullish_weak"]
        )

        three_strong_to_weak_red = (
            prev_3_bearish_strong
            & prev_2_bearish_strong
            & prev_1_bearish_strong
            & histogram_signals["bearish_weak"]
        )

        # 2 weak + 1 strong + 1 weak (false breakout)
        false_breakout_green = (
            prev_3_bullish_weak
            & prev_2_bullish_weak
            & prev_1_bullish_strong
            & histogram_signals["bullish_weak"]
        )

        false_breakout_red = (
            prev_3_bearish_weak
            & prev_2_bearish_weak
            & prev_1_bearish_strong
            & histogram_signals["bearish_weak"]
        )

        # Alternatif kalıp: weak-strong-weak-strong (dalgalanma)
        alternating_pattern_green = (
            prev_3_bullish_weak
            & prev_2_bullish_strong
            & prev_1_bullish_weak
            & histogram_signals["bullish_strong"]
        )

        alternating_pattern_red = (
            prev_3_bearish_weak
            & prev_2_bearish_strong
            & prev_1_bearish_weak
            & histogram_signals["bearish_strong"]
        )

        # === MOMENTUM DEĞİŞİMİ SİNYALLERİ ===
        # 3 açık kırmızı → 1 yeşil (bullish momentum dönüşü)
        three_red_to_green = (
            prev_3_bearish_weak
            & prev_2_bearish_weak
            & prev_1_bearish_weak
            & (histogram_signals["bullish_weak"] | histogram_signals["bullish_strong"])
        )

        # 3 açık yeşil → 1 kırmızı (bearish momentum dönüşü)
        three_green_to_red = (
            prev_3_bullish_weak
            & prev_2_bullish_weak
            & prev_1_bullish_weak
            & (histogram_signals["bearish_weak"] | histogram_signals["bearish_strong"])
        )

        # 3 koyu kırmızı → 1 yeşil (güçlü bullish dönüş)
        three_dark_red_to_green = (
            prev_3_bearish_strong
            & prev_2_bearish_strong
            & prev_1_bearish_strong
            & (histogram_signals["bullish_weak"] | histogram_signals["bullish_strong"])
        )

        # 3 koyu yeşil → 1 kırmızı (güçlü bearish dönüş)
        three_dark_green_to_red = (
            prev_3_bullish_strong
            & prev_2_bullish_strong
            & prev_1_bullish_strong
            & (histogram_signals["bearish_weak"] | histogram_signals["bearish_strong"])
        )

        # === ORIJINAL GEÇIŞLER (1 BAR) ===
        # Önceki barın sinyalleri
        prev_bullish_strong = histogram_signals["bullish_strong"].shift(1)
        prev_bullish_weak = histogram_signals["bullish_weak"].shift(1)
        prev_bearish_strong = histogram_signals["bearish_strong"].shift(1)
        prev_bearish_weak = histogram_signals["bearish_weak"].shift(1)

        # GEÇİŞLER
        return {
            "histogram_now_bullish_strong": histogram_now_bullish_strong,
            "histogram_now_bullish_weak": histogram_now_bullish_weak,
            "histogram_now_bearish_strong": histogram_now_bearish_strong,
            "histogram_now_bearish_weak": histogram_now_bearish_weak,
            "prev_1_bullish_strong": prev_1_bullish_strong,
            "prev_1_bullish_weak": prev_1_bullish_weak,
            "prev_1_bearish_strong": prev_1_bearish_strong,
            "prev_1_bearish_weak": prev_1_bearish_weak,
            "prev_2_bullish_strong": prev_2_bullish_strong,
            "prev_2_bullish_weak": prev_2_bullish_weak,
            "prev_2_bearish_strong": prev_2_bearish_strong,
            "prev_2_bearish_weak": prev_2_bearish_weak,
            "prev_3_bullish_strong": prev_3_bullish_strong,
            "prev_3_bullish_weak": prev_3_bullish_weak,
            "prev_3_bearish_strong": prev_3_bearish_strong,
            "prev_3_bearish_weak": prev_3_bearish_weak,
            "count_bullish_weak": count_bullish_weak,
            "count_bullish_strong": count_bullish_strong,
            "count_bearish_weak": count_bearish_weak,
            "count_bearish_strong": count_bearish_strong,
            # Orijinal 1 bar geçişler
            "green_dark_to_light": prev_bullish_strong
            & histogram_signals["bullish_weak"],  # Koyu yeşil → Açık yeşil
            "green_light_to_dark": prev_bullish_weak
            & histogram_signals["bullish_strong"],  # Açık yeşil → Koyu yeşil
            "red_dark_to_light": prev_bearish_strong
            & histogram_signals["bearish_weak"],  # Koyu kırmızı → Açık kırmızı
            "red_light_to_dark": prev_bearish_weak
            & histogram_signals["bearish_strong"],  # Açık kırmızı → Koyu kırmızı
            "red_dark_to_green": prev_bearish_strong
            & (histogram_signals["bullish_strong"] | histogram_signals["bullish_weak"]),
            "red_light_to_green": prev_bearish_weak
            & (histogram_signals["bullish_strong"] | histogram_signals["bullish_weak"]),
            # Yaklaşım 1: Sürekli 3 bar (STABLE - En güvenilir)
            "green_dark_to_light_stable": green_dark_to_light_stable,
            "green_light_to_dark_stable": green_light_to_dark_stable,
            "green_light_to_red_stable": green_light_to_red_stable,
            "red_dark_to_light_stable": red_dark_to_light_stable,
            "red_light_to_dark_stable": red_light_to_dark_stable,
            "red_light_to_green_stable": red_light_to_green_stable,
            # Yaklaşım 3: Trend bazlı (MOMENTUM - En hassas)
            "green_trend_weakening": green_trend_weakening,
            "green_trend_strengthening": green_trend_strengthening,
            "red_trend_weakening": red_trend_weakening,
            "red_trend_strengthening": red_trend_strengthening,
            # Kalıp/Pattern bazlı sinyaller (YENİ!)
            "three_weak_to_strong_green": three_weak_to_strong_green,  # 3 açık yeşil → 1 koyu yeşil (toparlanma)
            "three_weak_to_strong_red": three_weak_to_strong_red,  # 3 açık kırmızı → 1 koyu kırmızı (güçlenme)
            "three_strong_to_weak_green": three_strong_to_weak_green,  # 3 koyu yeşil → 1 açık yeşil (zayıflama başlangıcı)
            "one_strong_to_two_weak_green": one_strong_to_two_weak_green,  # 1koyu yeşil → 2 açık yeşil (zayıflama başlangıcı)
            "three_strong_to_weak_red": three_strong_to_weak_red,  # 3 koyu kırmızı → 1 açık kırmızı (zayıflama başlangıcı)
            "false_breakout_green": false_breakout_green,  # 2 açık + 1 koyu + 1 açık (sahte kırılım)
            "false_breakout_red": false_breakout_red,  # 2 açık + 1 koyu + 1 açık (sahte kırılım)
            "alternating_pattern_green": alternating_pattern_green,  # açık-koyu-açık-koyu (dalgalanma)
            "alternating_pattern_red": alternating_pattern_red,  # açık-koyu-açık-koyu (dalgalanma)
            # Momentum değişimi sinyalleri (YENİ!)
            "three_red_to_green": three_red_to_green,  # 3 açık kırmızı → yeşil (bullish dönüş)
            "three_green_to_red": three_green_to_red,  # 3 açık yeşil → kırmızı (bearish dönüş)
            "three_dark_red_to_green": three_dark_red_to_green,  # 3 koyu kırmızı → yeşil (güçlü bullish dönüş)
            "three_dark_green_to_red": three_dark_green_to_red,  # 3 koyu yeşil → kırmızı (güçlü bearish dönüş)
            # Ek bilgiler
            "momentum_3bar": momentum_3bar,
            "momentum_change": momentum_change,
            "strong_momentum_change": strong_momentum_change,
        }

    def generate_centerline_signals(self, macd_data):
        """MACD histogramının sıfır çizgisini kesişim sinyalleri"""
        histogram = macd_data["histogram"]

        # Sıfır çizgisi kesişimleri
        hist_above_zero = histogram > 0
        hist_below_zero = histogram < 0

        # Kesişim noktaları (bir önceki barla karşılaştırma)
        zero_cross_up = (histogram > 0) & (
            histogram.shift(1) <= 0
        )  # Sıfırdan yukarı kesişim
        zero_cross_down = (histogram < 0) & (
            histogram.shift(1) >= 0
        )  # Sıfırdan aşağı kesişim

        return {
            "zero_cross_bullish": zero_cross_up,  # Histogram sıfırı yukarı kesti (bullish)
            "zero_cross_bearish": zero_cross_down,  # Histogram sıfırı aşağı kesti (bearish)
            "above_zero": hist_above_zero,  # Histogram pozitif bölgede
            "below_zero": hist_below_zero,  # Histogram negatif bölgede
        }

    def generate_macd_zero_cross_signals(self, macd_data):
        """Zero line kesişim sinyalleri"""
        macd_line = macd_data["macd"]

        # Zero line kesişimleri
        zero_cross_up = (macd_line > 0) & (macd_line.shift(1) <= 0)
        zero_cross_down = (macd_line < 0) & (macd_line.shift(1) >= 0)

        return {
            "zero_buy": zero_cross_up,  # Daha az yanlış sinyal
            "zero_sell": zero_cross_down,
        }

    def get_signal_summary(self, signals: Dict[str, pd.Series]) -> Dict[str, int]:
        """Sinyal özetini döndürür"""
        summary = {}
        for signal_name, signal_series in signals.items():
            summary[signal_name] = signal_series.sum()
        return summary

    def get_latest_signals(
        self, signals: Dict[str, pd.Series], n: int = 5
    ) -> Dict[str, list]:
        """Son N adet sinyali döndürür"""
        latest = {}
        for signal_name, signal_series in signals.items():
            recent_signals = signal_series.tail(n)
            latest[signal_name] = recent_signals[recent_signals == True].index.tolist()
        return latest

    # YENİ GELIŞMIŞ DIVERGENCE METHODLARI
    def _find_peaks_and_troughs(self, data):
        """Peak ve trough noktalarını bulur"""
        data_array = data.values if isinstance(data, pd.Series) else data

        prominence = (
            np.std(data_array) * self.divergence_params["prominence_factor"]
        )  # Prominence :
        min_dist = self.divergence_params["min_distance"]

        peaks, _ = find_peaks(data_array, prominence=prominence, distance=min_dist)
        troughs, _ = find_peaks(-data_array, prominence=prominence, distance=min_dist)

        return peaks, troughs

    def _calculate_trend_slope(self, indices, values):
        """Trend çizgisinin eğimini hesaplar"""
        if len(indices) < 2:
            return 0

        indices = np.array(indices)
        values = np.array(values)

        slope, _ = np.polyfit(indices, values, 1)
        return slope

    def _get_recent_points(self, all_indices, data, num_points=None):
        """Son N noktayı alır"""
        if num_points is None:
            num_points = self.divergence_params["lookback_points"]

        if len(all_indices) < 2:
            return [], []

        recent_indices = (
            all_indices[-num_points:] if len(all_indices) >= num_points else all_indices
        )

        if isinstance(data, pd.Series):
            recent_values = [data.iloc[i] for i in recent_indices]
        else:
            recent_values = [data[i] for i in recent_indices]

        return recent_indices, recent_values

    def detect_advanced_divergence(self, price_data, macd_data):
        """
        Gelişmiş divergence detection - Trend çizgisi analizi

        Bullish Divergence:
        - Fiyat trend çizgisi: Aşağı (slope < 0)
        - MACD trend çizgisi: Yukarı (slope > 0)

        Bearish Divergence:
        - Fiyat trend çizgisi: Yukarı (slope > 0)
        - MACD trend çizgisi: Aşağı (slope < 0)
        """
        price = price_data["close"] if isinstance(price_data, dict) else price_data
        macd_line = macd_data["macd"]

        results = {
            "bullish_divergences": [],
            "bearish_divergences": [],
            "debug_info": {},
        }

        # Peak ve trough noktalarını bul
        price_peaks, price_troughs = self._find_peaks_and_troughs(price)
        macd_peaks, macd_troughs = self._find_peaks_and_troughs(macd_line)

        # Debug bilgileri
        results["debug_info"] = {
            "price_peaks_count": len(price_peaks),
            "price_troughs_count": len(price_troughs),
            "macd_peaks_count": len(macd_peaks),
            "macd_troughs_count": len(macd_troughs),
        }

        # BULLISH DIVERGENCE - Dip noktaları analizi
        if len(price_troughs) >= 2 and len(macd_troughs) >= 2:
            price_indices, price_values = self._get_recent_points(
                price_troughs, price
            )  #
            macd_indices, macd_values = self._get_recent_points(macd_troughs, macd_line)

            if len(price_indices) >= 2 and len(macd_indices) >= 2:
                price_slope = self._calculate_trend_slope(price_indices, price_values)
                macd_slope = self._calculate_trend_slope(macd_indices, macd_values)

                # Bullish divergence kontrolü
                if price_slope < 0 and macd_slope > 0:
                    results["bullish_divergences"].append(
                        {
                            "type": "bullish",
                            "last_index": price_indices[-1],
                            "last_price": price_values[-1],
                            "price_slope": price_slope,
                            "macd_slope": macd_slope,
                            "strength": abs(price_slope) + abs(macd_slope),
                            "price_points": list(zip(price_indices, price_values)),
                            "macd_points": list(zip(macd_indices, macd_values)),
                        }
                    )

        # BEARISH DIVERGENCE - Tepe noktaları analizi
        if len(price_peaks) >= 2 and len(macd_peaks) >= 2:
            price_indices, price_values = self._get_recent_points(price_peaks, price)
            macd_indices, macd_values = self._get_recent_points(macd_peaks, macd_line)

            if len(price_indices) >= 2 and len(macd_indices) >= 2:
                price_slope = self._calculate_trend_slope(price_indices, price_values)
                macd_slope = self._calculate_trend_slope(macd_indices, macd_values)

                # Bearish divergence kontrolü
                if price_slope > 0 and macd_slope < 0:
                    results["bearish_divergences"].append(
                        {
                            "type": "bearish",
                            "last_index": price_indices[-1],
                            "last_price": price_values[-1],
                            "price_slope": price_slope,
                            "macd_slope": macd_slope,
                            "strength": abs(price_slope) + abs(macd_slope),
                            "price_points": list(zip(price_indices, price_values)),
                            "macd_points": list(zip(macd_indices, macd_values)),
                        }
                    )

        return results

    def get_divergence_signals(self, price_data, macd_data, advanced=True):
        """
        Divergence sinyalleri oluştur

        Args:
            price_data: Fiyat verisi (dict with 'close' key veya pd.Series)
            macd_data: MACD verisi (calculate() methodundan dönen dict)
            advanced: True ise gelişmiş analiz, False ise basit analiz
        """
        if advanced:
            divergence_results = self.detect_advanced_divergence(price_data, macd_data)
        else:
            # Basit method için placeholder
            return {"buy_signals": [], "sell_signals": [], "divergence_info": {}}

        # Sinyalleri formatla
        signals = {
            "buy_signals": [],
            "sell_signals": [],
            "divergence_info": divergence_results,
        }

        # Bullish divergence sinyalleri
        for div in divergence_results["bullish_divergences"]:
            signals["buy_signals"].append(
                {
                    "index": div["last_index"],
                    "type": "buy",
                    "reason": "bullish_divergence",
                    "strength": div["strength"],
                    "price": div["last_price"],
                    "details": f"Fiyat eğim: {div['price_slope']:.4f}, MACD eğim: {div['macd_slope']:.4f}",
                }
            )

        # Bearish divergence sinyalleri
        for div in divergence_results["bearish_divergences"]:
            signals["sell_signals"].append(
                {
                    "index": div["last_index"],
                    "type": "sell",
                    "reason": "bearish_divergence",
                    "strength": div["strength"],
                    "price": div["last_price"],
                    "details": f"Fiyat eğim: {div['price_slope']:.4f}, MACD eğim: {div['macd_slope']:.4f}",
                }
            )

        return signals


class TechnicalAnalyzer:

    def __init__(self, market_data_client):
        self.market_data_client = market_data_client
        self.macd = MACD()  # MACD sınıfını başlat

    def _prepare_data(
        self, symbol: str = "LTCUSDT", interval: str = None, limit: int = 100
    ) -> pd.DataFrame:
        """OHLCV verisini DataFrame formatına dönüştürür"""
        raw_data = self.market_data_client.get_ohlcv(
            symbol=symbol, interval=interval, limit=limit
        )
        # input(f"Veri alındı, işleniyor...{raw_data}")
        df = pd.DataFrame(raw_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df, raw_data

    # Hareketli Ortalamalar (TA-Lib)
    def sma(self, data: pd.Series, period: int = 20) -> pd.Series:
        """Basit Hareketli Ortalama"""
        return pd.Series(talib.SMA(data.values, timeperiod=period), index=data.index)

    def ema(self, data: pd.Series, period: int = 12) -> pd.Series:
        """Üstel Hareketli Ortalama"""
        return pd.Series(talib.EMA(data.values, timeperiod=period), index=data.index)

    def wma(self, data: pd.Series, period: int = 20) -> pd.Series:
        """Ağırlıklı Hareketli Ortalama"""
        return pd.Series(talib.WMA(data.values, timeperiod=period), index=data.index)

    def tema(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Triple Exponential Moving Average"""
        return pd.Series(talib.TEMA(data.values, timeperiod=period), index=data.index)

    def dema(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Double Exponential Moving Average"""
        return pd.Series(talib.DEMA(data.values, timeperiod=period), index=data.index)

    # Momentum İndikatörleri
    def rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Göreceli Güç Endeksi"""
        return pd.Series(talib.RSI(data.values, timeperiod=period), index=data.index)

    def stochastic(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        fastk_period: int = 14,
        slowk_period: int = 3,
        slowd_period: int = 3,
    ) -> Dict[str, pd.Series]:
        """Stokastik Osilatör"""
        slowk, slowd = talib.STOCH(
            high.values,
            low.values,
            close.values,
            fastk_period=fastk_period,
            slowk_period=slowk_period,
            slowd_period=slowd_period,
        )
        return {
            "k_percent": pd.Series(slowk, index=close.index),
            "d_percent": pd.Series(slowd, index=close.index),
        }

    def williams_r(
        self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> pd.Series:
        """Williams %R"""
        return pd.Series(
            talib.WILLR(high.values, low.values, close.values, timeperiod=period),
            index=close.index,
        )

    def cci(
        self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> pd.Series:
        """Commodity Channel Index"""
        return pd.Series(
            talib.CCI(high.values, low.values, close.values, timeperiod=period),
            index=close.index,
        )

    def roc(self, data: pd.Series, period: int = 10) -> pd.Series:
        """Rate of Change"""
        return pd.Series(talib.ROC(data.values, timeperiod=period), index=data.index)

    def momentum(self, data: pd.Series, period: int = 10) -> pd.Series:
        """Momentum"""
        return pd.Series(talib.MOM(data.values, timeperiod=period), index=data.index)

    # Volatilite İndikatörleri
    # def bollinger_bands(self, data: pd.Series, period: int = 30, std_dev: float = 2) -> Dict[str, pd.Series]:
    #     """Bollinger Bantları"""
    #     upper, middle, lower = talib.BBANDS(data.values,
    #                                        timeperiod=period,
    #                                        nbdevup=std_dev,
    #                                        nbdevdn=std_dev)
    #     return {
    #         'upper': pd.Series(upper, index=data.index),
    #         'middle': pd.Series(middle, index=data.index),
    #         'lower': pd.Series(lower, index=data.index)
    #     }
    def bollinger_bands(
        self,
        data: pd.Series,
        period: int = 30,
        std_dev: float = 2,
        buffer_percent: float = 5,
    ) -> Dict[str, pd.Series]:
        """Bollinger Bantları - Normalize edilmiş ve ekstra tampon bantlarla"""

        # Fiyatları büyük sayılara çevir (örn: x1000000)
        scale_factor = 1000000
        scaled_data = data * scale_factor

        upper, middle, lower = talib.BBANDS(
            scaled_data.values, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev
        )

        # Sonuçları geri ölçekle
        upper_band = pd.Series(upper / scale_factor, index=data.index)
        middle_band = pd.Series(middle / scale_factor, index=data.index)
        lower_band = pd.Series(lower / scale_factor, index=data.index)

        # Lower bandın %5'lik yukarısını ekle
        buffer_multiplier = buffer_percent / 100

        # Lower bandın üstüne %5 ekle (yukarıya)
        lower_extended = lower_band * (1 + buffer_multiplier)

        return {
            "upper": upper_band,  # Orijinal upper
            "middle": middle_band,  # Orta hat
            "lower": lower_band,  # Orijinal lower
            "lower_buffer": lower_extended,  # Lower + %5 (yukarıda)
        }

    def atr(
        self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> pd.Series:
        """Average True Range"""
        return pd.Series(
            talib.ATR(high.values, low.values, close.values, timeperiod=period),
            index=close.index,
        )

    def natr(
        self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> pd.Series:
        """Normalized Average True Range"""
        return pd.Series(
            talib.NATR(high.values, low.values, close.values, timeperiod=period),
            index=close.index,
        )

    def trange(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """True Range"""
        return pd.Series(
            talib.TRANGE(high.values, low.values, close.values), index=close.index
        )

    # Trend İndikatörleri
    def adx(
        self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> Dict[str, pd.Series]:
        """Average Directional Index"""
        adx = talib.ADX(high.values, low.values, close.values, timeperiod=period)
        plus_di = talib.PLUS_DI(
            high.values, low.values, close.values, timeperiod=period
        )
        minus_di = talib.MINUS_DI(
            high.values, low.values, close.values, timeperiod=period
        )

        return {
            "adx": pd.Series(adx, index=close.index),
            "plus_di": pd.Series(plus_di, index=close.index),
            "minus_di": pd.Series(minus_di, index=close.index),
        }

    def parabolic_sar(
        self,
        high: pd.Series,
        low: pd.Series,
        acceleration: float = 0.02,
        maximum: float = 0.2,
    ) -> pd.Series:
        """Parabolic SAR"""
        return pd.Series(
            talib.SAR(
                high.values, low.values, acceleration=acceleration, maximum=maximum
            ),
            index=high.index,
        )

    def aroon(
        self, high: pd.Series, low: pd.Series, period: int = 14
    ) -> Dict[str, pd.Series]:
        """Aroon"""
        aroon_down, aroon_up = talib.AROON(high.values, low.values, timeperiod=period)
        return {
            "aroon_up": pd.Series(aroon_up, index=high.index),
            "aroon_down": pd.Series(aroon_down, index=high.index),
        }

    def aroonosc(self, high: pd.Series, low: pd.Series, period: int = 14) -> pd.Series:
        """Aroon Oscillator"""
        return pd.Series(
            talib.AROONOSC(high.values, low.values, timeperiod=period), index=high.index
        )

    # Hacim İndikatörleri
    def obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """On-Balance Volume"""
        return pd.Series(talib.OBV(close.values, volume.values), index=close.index)

    def ad(
        self, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
    ) -> pd.Series:
        """Accumulation/Distribution Line"""
        return pd.Series(
            talib.AD(high.values, low.values, close.values, volume.values),
            index=close.index,
        )

    def adosc(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        fast: int = 3,
        slow: int = 10,
    ) -> pd.Series:
        """Accumulation/Distribution Oscillator"""
        return pd.Series(
            talib.ADOSC(
                high.values,
                low.values,
                close.values,
                volume.values,
                fastperiod=fast,
                slowperiod=slow,
            ),
            index=close.index,
        )

    # Pattern Recognition (Mum Formasyonları)
    def doji(
        self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series
    ) -> pd.Series:
        """Doji Pattern"""
        return pd.Series(
            talib.CDLDOJI(open_.values, high.values, low.values, close.values),
            index=close.index,
        )

    def hammer(
        self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series
    ) -> pd.Series:
        """Hammer Pattern"""
        return pd.Series(
            talib.CDLHAMMER(open_.values, high.values, low.values, close.values),
            index=close.index,
        )

    def engulfing(
        self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series
    ) -> pd.Series:
        """Engulfing Pattern"""
        return pd.Series(
            talib.CDLENGULFING(open_.values, high.values, low.values, close.values),
            index=close.index,
        )

    def morning_star(
        self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series
    ) -> pd.Series:
        """Morning Star Pattern"""
        return pd.Series(
            talib.CDLMORNINGSTAR(open_.values, high.values, low.values, close.values),
            index=close.index,
        )

    def evening_star(
        self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series
    ) -> pd.Series:
        """Evening Star Pattern"""
        return pd.Series(
            talib.CDLEVENINGSTAR(open_.values, high.values, low.values, close.values),
            index=close.index,
        )

    def generate_rsi_signals(
        self,
        rsi: pd.Series,
        oversold: int = 30,
        overbought: int = 70,
        tight_oversold: int = 35,
        tight_overbought: int = 65,
        very_tight_oversold: int = 50,
    ) -> Dict[str, pd.Series]:
        """RSI tabanlı al/sat sinyalleri (normal ve dar aralık)"""

        # Normal aralık sinyalleri (30-70)
        buy_signals = (rsi > oversold) & (
            rsi.shift(1) <= oversold
        )  # şimdiki rsi 30 dan büyük ama önceden degildi .
        sell_signals = (rsi < overbought) & (rsi.shift(1) >= overbought)

        # Dar aralık sinyalleri (35-65) - Daha muhafazakar
        tight_buy_signals = (rsi > tight_oversold) & (rsi.shift(1) <= tight_oversold)
        tight_sell_signals = (rsi < tight_overbought) & (
            rsi.shift(1) >= tight_overbought
        )

        very_tight_buy_signals = (rsi > very_tight_oversold) & (
            rsi.shift(1) <= very_tight_oversold
        )

        # RSI pozisyon durumu
        rsi_bullish = rsi > 50  # RSI 50 üzerinde (boğa bölgesi)
        rsi_bearish = rsi < 50  # RSI 50 altında (ayı bölgesi)

        # Aşırı bölge durumları
        rsi_oversold_zone = rsi < oversold  # Aşırı satım bölgesinde
        rsi_overbought_zone = rsi > overbought  # Aşırı alım bölgesinde

        return {
            "rsi_buy": buy_signals,
            "rsi_sell": sell_signals,
            "tight_rsi_buy": tight_buy_signals,  # Daha güvenli alım
            "tight_rsi_sell": tight_sell_signals,  # Daha güvenli satım
            "very_tight_rsi_buy": very_tight_buy_signals,  # Daha az güvenli alım
            "rsi_bullish": rsi_bullish,  # RSI pozitif bölgede
            "rsi_bearish": rsi_bearish,  # RSI negatif bölgede
            "rsi_oversold_zone": rsi_oversold_zone,  # Aşırı satım durumu
            "rsi_overbought_zone": rsi_overbought_zone,  # Aşırı alım durumu
        }

    def generate_bollinger_signals(
        self, close: pd.Series, bollinger_data: Dict[str, pd.Series]
    ) -> Dict[str, pd.Series]:
        """Bollinger Bands tabanlı al/sat sinyalleri"""
        upper = bollinger_data["upper"]
        lower = bollinger_data["lower"]
        lower_buffer = bollinger_data["lower"] * 0.97

        buy_signals_buffer = (close <= lower_buffer) & (
            close.shift(1) > lower_buffer.shift(1)
        )
        buy_signals = (close <= lower) & (close.shift(1) > lower.shift(1))
        sell_signals = (close >= upper) & (close.shift(1) < upper.shift(1))

        return {
            "bb_buy": buy_signals,
            "bb_buy_buffer": buy_signals_buffer,
            "bb_sell": sell_signals,
        }

    def generate_golden_cross_signals(
        self, short_ma: pd.Series, long_ma: pd.Series
    ) -> Dict[str, pd.Series]:
        """Golden Cross/Death Cross sinyalleri"""
        buy_signals = (short_ma > long_ma) & (
            short_ma.shift(1) <= long_ma.shift(1)
        )  # Golden Cross
        sell_signals = (short_ma < long_ma) & (
            short_ma.shift(1) >= long_ma.shift(1)
        )  # Death Cross

        return {"golden_cross": buy_signals, "death_cross": sell_signals}

    def calculate_current_tf_trend(self, ema_short, ema_long, current_price):

        tf_score = 0

        if ema_short > 0 and ema_long > 0:
            if ema_short > ema_long:
                # Bullish EMA alignment
                if current_price > ema_short:
                    tf_score = (
                        "STRONG_BULLISH"  # Güçlü bullish: Fiyat EMA'ların üstünde
                    )
                elif current_price > ema_long:
                    tf_score = "BULLISH"  # Orta bullish: Fiyat EMA'lar arasında
                else:
                    tf_score = "WEAK BULLISH"  # Zayıf bullish: EMA'lar bullish ama fiyat altında
            else:
                # Bearish EMA alignment
                if current_price < ema_short:
                    tf_score = (
                        "STRONG_BEARISH"  # Güçlü bearish: Fiyat EMA'ların altında
                    )
                elif current_price < ema_long:
                    tf_score = "BEARISH"  # Orta bearish: Fiyat EMA'lar arasında
                else:
                    tf_score = "WEAK_BEARISH"  # Zayıf bearish: EMA'lar bearish ama fiyat üstünde

        return {"tf_score": tf_score}

    # Kapsamlı Analiz Fonksiyonu
    def analyze_symbol(
        self, symbol: str = "LTCUSDT", interval: str = None, limit: int = 200
    ) -> Dict:
        """Sembol için kapsamlı teknik analiz"""
        # print(f"Analiz ediliyor: {symbol} - Interval: {interval} - Limit: {limit}")
        df, raw_data = self._prepare_data(symbol, interval, limit)

        analysis = {
            "symbol": symbol,
            "last_price": df["close"].iloc[-1],
            "indicators": {},
            "patterns": {},
            "signals": {},
        }
        analysis["ohlcv"] = raw_data

        volume_sma = df["volume"].rolling(window=20).mean()
        # Volume ratio - mevcut volume vs ortalama volume
        volume_ratio = df["volume"] / df["volume_sma"]

        # Timeframe'e göre dinamik EMA periyotları
        ema_configs = {
            "15m": (9, 21),  # Hızlı scalping
            "30m": (12, 26),  # İyi ayar
            "1h": (9, 26),  # Sen 1h kullanıyorsun, bu iyi
            "4h": (9, 26),  # 38,76'dan çok daha iyi
            "6h": (20, 50),  # Daha makul
            "8h": (30, 60),  # Çok daha hızlı
            "12h": (30, 60),  # Çok daha hızlı
            "1d": (20, 50),  # 50,200 çok yavaş
            "1w": (10, 21),  # Haftalık için daha reaktif
        }

        fast_period, slow_period = ema_configs.get(interval, (21, 50))

        # EMA hesaplamaları
        # print(f"EMA hesaplanıyor: fast_period={fast_period}, slow_period={slow_period}")

        ema_short = self.ema(df["close"], fast_period)  # FAST period ile SHORT EMA
        ema_long = self.ema(df["close"], slow_period)  # SLOW period ile LONG EMA

        # Hareketli ortalamalar
        sma_20 = self.sma(df["close"], 20)
        ema_12 = self.ema(df["close"], 12)
        ema_26 = self.ema(df["close"], 26)

        trend_signal = self.calculate_current_tf_trend(
            ema_short=ema_short.iloc[-1],
            ema_long=ema_long.iloc[-1],
            current_price=df["close"].iloc[-1],
        )

        analysis["indicators"]["current_tf_trend"] = trend_signal["tf_score"]

        analysis["indicators"]["sma_20"] = sma_20.iloc[-1]
        analysis["indicators"]["ema_12"] = ema_12.iloc[-1]
        analysis["indicators"]["ema_26"] = ema_26.iloc[-1]
        analysis["indicators"]["ema_short"] = ema_short.iloc[-1]
        analysis["indicators"]["ema_long"] = ema_long.iloc[-1]

        rsi_configs = {
            "15m": 13,  # Standart - hızlı sinyaller
            "30m": 13,  # Standart - hızlı sinyaller
            "1h": 13,  # Standart - genel kullanım
            "4h": 14,  # Daha yavaş - gürültü azaltma
            "6h": 14,  # Orta-uzun vadeli - dengeli
            "8h": 14,  # Uzun vadeli - güvenilir sinyaller
            "12h": 14,  # Uzun vadeli - güvenilir sinyaller
            "1d": 13,  # Standart - günlük analiz
            "1w": 10,  # Haftalık - daha reaktif makro trend
        }

        # Momentum indikatörleri
        rsi_values = self.rsi(df["close"], period=rsi_configs.get(interval, 14))

        analysis["indicators"]["rsi"] = rsi_values.iloc[-1]
        analysis["indicators"]["rsi_prev"] = rsi_values.iloc[-2]
        rsi_diff = rsi_values.iloc[-1] - rsi_values.iloc[-2]
        analysis["indicators"]["rsi_diff"] = rsi_diff
        # Önerilen RSI trend eşikleri
        if rsi_diff >= 5.0:
            rsi_trend = "strong_up"
        elif 2.0 <= rsi_diff < 5.0:
            rsi_trend = "mild_up"
        elif -2.0 < rsi_diff < 2.0:
            rsi_trend = "flat"
        elif -5.0 < rsi_diff <= -2.0:
            rsi_trend = "mild_down"
        else:  # rsi_diff <= -5.0
            rsi_trend = "strong_down"

        analysis["indicators"]["rsi_trend"] = rsi_trend

        macd_params = self.macd.configs.get(
            interval, {"fast": 12, "slow": 26, "signal": 9}
        )

        macd_data = self.macd.calculate(
            df["close"],
            fast=macd_params["fast"],
            slow=macd_params["slow"],
            signal=macd_params["signal"],
        )

        analysis["indicators"]["macd"] = {
            "macd": macd_data["macd"].iloc[-1],
            "signal": macd_data["signal"].iloc[-1],
            "histogram": macd_data["histogram"].iloc[-1],
        }

        cci_values = self.cci(df["high"], df["low"], df["close"])
        analysis["indicators"]["cci"] = cci_values.iloc[-1]

        williams_r_values = self.williams_r(df["high"], df["low"], df["close"])
        analysis["indicators"]["williams_r"] = williams_r_values.iloc[-1]

        # Volatilite indikatörleri

        bollinger_configs = {
            "15m": {"period": 19, "std_dev": 1.9},  # Kısa vadeli - hızlı reaksiyon
            "30m": {"period": 19, "std_dev": 1.9},  # Kısa vadeli - hızlı reaksiyon
            "1h": {"period": 19, "std_dev": 1.9},  # Standart - genel kullanım
            "4h": {"period": 19, "std_dev": 1.9},  # Daha geniş bantlar
            "6h": {"period": 19, "std_dev": 1.9},  # Orta-uzun vadeli
            "8h": {"period": 19, "std_dev": 1.9},  # Uzun vadeli - daha stabil
            "12h": {"period": 19, "std_dev": 1.9},  # Uzun vadeli - daha stabil
            "1d": {"period": 19, "std_dev": 1.9},  # Standart günlük
            "1w": {"period": 12, "std_dev": 2.0},  # Haftalık - daha reaktif
        }

        # Bollinger Bands hesaplamaları
        bb_config = bollinger_configs.get(interval, {"period": 20, "std_dev": 1.9})
        bb_data = self.bollinger_bands(
            df["close"], period=bb_config["period"], std_dev=bb_config["std_dev"]
        )

        analysis["indicators"]["bollinger"] = {
            "upper": bb_data["upper"].iloc[-1],
            "middle": bb_data["middle"].iloc[-1],
            "lower": bb_data["lower"].iloc[-1],
        }

        atr_value = self.atr(df["high"], df["low"], df["close"])
        analysis["indicators"]["atr"] = atr_value.iloc[-1]

        # Trend indikatörleri
        adx_data = self.adx(df["high"], df["low"], df["close"])
        analysis["indicators"]["adx"] = {
            "adx": adx_data["adx"].iloc[-1],
            "plus_di": adx_data["plus_di"].iloc[-1],
            "minus_di": adx_data["minus_di"].iloc[-1],
        }

        sar_values = self.parabolic_sar(df["high"], df["low"])
        analysis["indicators"]["parabolic_sar"] = sar_values.iloc[-1]

        # Hacim indikatörleri
        obv_values = self.obv(df["close"], df["volume"])
        analysis["indicators"]["obv"] = obv_values.iloc[-1]

        # # Pattern Recognition
        # doji_pattern = self.doji(df['open'], df['high'], df['low'], df['close'])
        # hammer_pattern = self.hammer(df['open'], df['high'], df['low'], df['close'])
        # engulfing_pattern = self.engulfing(df['open'], df['high'], df['low'], df['close'])

        # analysis['patterns'] = {
        #     'doji': bool(doji_pattern.iloc[-1]) if not pd.isna(doji_pattern.iloc[-1]) else False,
        #     'hammer': bool(hammer_pattern.iloc[-1]) if not pd.isna(hammer_pattern.iloc[-1]) else False,
        #     'engulfing': bool(engulfing_pattern.iloc[-1]) if not pd.isna(engulfing_pattern.iloc[-1]) else False
        # }

        self_patterns = self.get_all_patterns(
            df["open"], df["high"], df["low"], df["close"]
        )
        for pattern_name, pattern_series in self_patterns.items():
            analysis["patterns"][pattern_name] = (
                bool(pattern_series.iloc[-1])
                if not pd.isna(pattern_series.iloc[-1])
                else False
            )

        # Reason
        analysis["reason"] = ""  # Bu kısım daha sonra  doldurulacak
        try:
            # Sinyaller
            rsi_signals = self.generate_rsi_signals(rsi_values)
            macd_signals = self.macd.generate_signals(macd_data, price_data=df["close"])
            bb_signals = self.generate_bollinger_signals(df["close"], bb_data)

            golden_cross_signals = self.generate_golden_cross_signals(
                ema_short, ema_long
            )

            def get_latest_signals(signals_dict):
                """Her signal'in son değerini al"""
                return {key: value.iloc[-1] for key, value in signals_dict.items()}

            def get_latest_signals(signals_dict):
                """Her signal'in son değerini al"""
                return {
                    key: value.iloc[-1] if isinstance(value, pd.Series) else value
                    for key, value in signals_dict.items()
                }

            analysis["signals"] = {}
            analysis["signals"].update(get_latest_signals(rsi_signals))
            analysis["signals"].update(get_latest_signals(macd_signals))
            analysis["signals"].update(get_latest_signals(bb_signals))
            analysis["signals"].update(get_latest_signals(golden_cross_signals))
        except Exception as e:
            print(f"[Analysis Exception] : {e}")

        return analysis

    def get_all_patterns(
        self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series
    ) -> Dict[str, pd.Series]:
        """Tüm mum formasyonlarını döndürür"""
        patterns = {}

        # TA-Lib'deki tüm pattern fonksiyonları
        pattern_functions = [
            ("DOJI", talib.CDLDOJI),
            ("HAMMER", talib.CDLHAMMER),
            ("ENGULFING", talib.CDLENGULFING),
            ("MORNING_STAR", talib.CDLMORNINGSTAR),
            ("EVENING_STAR", talib.CDLEVENINGSTAR),
            ("SHOOTING_STAR", talib.CDLSHOOTINGSTAR),
            ("HANGING_MAN", talib.CDLHANGINGMAN),
            ("HARAMI", talib.CDLHARAMI),
            ("DARK_CLOUD_COVER", talib.CDLDARKCLOUDCOVER),
            ("PIERCING", talib.CDLPIERCING),
        ]

        for name, func in pattern_functions:
            try:
                patterns[name] = pd.Series(
                    func(open_.values, high.values, low.values, close.values),
                    index=close.index,
                )
            except:
                patterns[name] = pd.Series([0] * len(close), index=close.index)

        return patterns


class SupportResistanceAnalyzer:

    def __init__(self, data, tf="4h"):
        """
        Args:
            data (pd.DataFrame): OHLCV data with columns ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.data = data.copy()
        self.current_price = data["Close"].iloc[-1]
        self.tf = tf

        # Timeframe'e göre parametreleri ayarla
        timeframe_settings = {
            "4h": {
                "volume_period": 60,
                "lookback_period": 50,
                "min_touches": 3,
                "pivot_window": 8,
                "tolerance_percent": 3,
            },
            "1d": {
                "pivot_window": 5,
                "volume_period": 10,
                "lookback_period": 20,
                "min_touches": 2,
                "tolerance_percent": 0.5,
            },
        }

        settings = timeframe_settings.get(tf, timeframe_settings["4h"])
        self.pivot_window = settings["pivot_window"]
        self.volume_period = settings["volume_period"]
        self.lookback_period = settings["lookback_period"]
        self.min_touches = settings["min_touches"]
        self.tolerance_percent = settings["tolerance_percent"]

    def find_pivot_points(self, window=None):
        """

        # Grafikte yerel tepe ve dip noktalarını buluyor.

        Pivot noktalarını bul (Local maxima/minima)

        Args:
            window (int): Pivot nokta pencere boyutu

        Returns:
            dict: Pivot high/low noktaları
        """
        if window is None:
            window = self.pivot_window

        # Local maxima (resistance candidates)
        high_peaks = argrelextrema(self.data["High"].values, np.greater, order=window)[
            0
        ]  #  Bir tepe noktasının "tepe" sayılabilmesi" için, öncesindeki ve sonrasındaki window değerden daha büyük olması gerekiyor.

        # Local minima (support candidates)
        low_peaks = argrelextrema(self.data["Low"].values, np.less, order=window)[0]

        pivot_highs = []
        pivot_lows = []

        for peak in high_peaks:
            pivot_highs.append(
                {
                    "index": peak,
                    "price": self.data["High"].iloc[peak],
                    "volume": (
                        self.data["Volume"].iloc[peak]
                        if "Volume" in self.data.columns
                        else 0
                    ),
                }
            )

        for peak in low_peaks:
            pivot_lows.append(
                {
                    "index": peak,
                    "price": self.data["Low"].iloc[peak],
                    "volume": (
                        self.data["Volume"].iloc[peak]
                        if "Volume" in self.data.columns
                        else 0
                    ),
                }
            )

        return {"pivot_highs": pivot_highs, "pivot_lows": pivot_lows}

    def find_support_resistance_levels(self, min_touches=None, tolerance_percent=None):
        """
        Horizontal support/resistance seviyelerini bul

        Args:
            min_touches (int): Minimum dokunma sayısı
            tolerance_percent (float): Tolerans yüzdesi

        Returns:
            dict: Support ve resistance seviyeleri
        """
        if min_touches is None:
            min_touches = self.min_touches
        if tolerance_percent is None:
            tolerance_percent = self.tolerance_percent

        pivots = self.find_pivot_points()

        # Tüm pivot noktalarını birleştir
        all_levels = []

        # Resistance levels (pivot highs)
        for pivot in pivots["pivot_highs"]:
            all_levels.append(
                {
                    "price": pivot["price"],
                    "type": "resistance",
                    "strength": 1,
                    "last_touch": pivot["index"],
                    "volume": pivot["volume"],
                }
            )

        # Support levels (pivot lows)
        for pivot in pivots["pivot_lows"]:
            all_levels.append(
                {
                    "price": pivot["price"],
                    "type": "support",
                    "strength": 1,
                    "last_touch": pivot["index"],
                    "volume": pivot["volume"],
                }
            )

        # Yakın seviyeleri grupla
        tolerance = tolerance_percent / 100
        grouped_levels = []

        for level in all_levels:
            found_group = False

            for group in grouped_levels:
                price_diff = abs(level["price"] - group["price"]) / group["price"]

                if price_diff <= tolerance and level["type"] == group["type"]:
                    # Aynı gruba ekle
                    group["strength"] += 1
                    group["price"] = (
                        group["price"] + level["price"]
                    ) / 2  # Ortalama al
                    group["last_touch"] = max(group["last_touch"], level["last_touch"])
                    group["volume"] += level["volume"]
                    found_group = True
                    break

            if not found_group:
                grouped_levels.append(level.copy())

        # Minimum dokunma sayısını karşılayanları filtrele
        strong_levels = [
            level for level in grouped_levels if level["strength"] >= min_touches
        ]

        # Güçlü seviyeleri ayır
        support_levels = [
            level for level in strong_levels if level["type"] == "support"
        ]
        resistance_levels = [
            level for level in strong_levels if level["type"] == "resistance"
        ]

        # Güçlülüğe göre sırala
        support_levels.sort(key=lambda x: x["strength"], reverse=True)
        resistance_levels.sort(key=lambda x: x["strength"], reverse=True)

        return {
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
        }

    def generate_sr_signals(self, lookback_period=None):
        """
        Support/Resistance sinyalleri üret

        Args:
            lookback_period (int): Geriye bakış periyodu

        Returns:
            dict: S/R sinyalleri
        """

        if lookback_period is None:
            lookback_period = self.lookback_period

        current_high = self.data["High"].iloc[-1]
        current_low = self.data["Low"].iloc[-1]

        # S/R seviyelerini bul
        levels = self.find_support_resistance_levels()

        signals = {
            "support_bounce": False,
            "support_break": False,
            "resistance_rejection": False,
            "resistance_break": False,
            "near_support": False,
            "near_resistance": False,
            "support_level": None,
            "resistance_level": None,
            "signal_strength": 0,
        }

        # En yakın support/resistance seviyelerini bul
        nearest_support = self._find_nearest_support(levels["support_levels"])
        nearest_resistance = self._find_nearest_resistance(levels["resistance_levels"])

        # Support sinyalleri
        if nearest_support:
            signals = self._process_support_signals(
                signals, nearest_support, lookback_period
            )

        # Resistance sinyalleri
        if nearest_resistance:
            signals = self._process_resistance_signals(
                signals, nearest_resistance, lookback_period
            )

        return signals

    def _find_nearest_support(self, support_levels):
        """En yakın support seviyesini bul"""
        nearest_support = None

        for support in support_levels:
            if support["price"] < self.current_price:
                if (
                    nearest_support is None
                    or support["price"] > nearest_support["price"]
                ):
                    nearest_support = support

        return nearest_support

    def _find_nearest_resistance(self, resistance_levels):
        """En yakın resistance seviyesini bul"""
        nearest_resistance = None

        for resistance in resistance_levels:
            if resistance["price"] > self.current_price:
                if (
                    nearest_resistance is None
                    or resistance["price"] < nearest_resistance["price"]
                ):
                    nearest_resistance = resistance

        return nearest_resistance

    def _process_support_signals(self, signals, nearest_support, lookback_period):
        """Support sinyallerini işle"""
        support_distance = (
            (self.current_price - nearest_support["price"]) / self.current_price * 100
        )
        signals["support_level"] = nearest_support["price"]

        # Support yakınında mı?
        if support_distance <= 2:  # %2 tolerans
            signals["near_support"] = True

            # Son lookback_period mumda support test edildi mi?
            recent_lows = self.data["Low"].tail(lookback_period).min()
            if recent_lows <= nearest_support["price"] * 1.01:  # %1 tolerans

                current_low = self.data["Low"].iloc[-1]

                # Support bounce (test edildi ama kırılmadı)
                if current_low > nearest_support["price"] * 0.99:
                    signals["support_bounce"] = True
                    signals["signal_strength"] = nearest_support["strength"]

                # Support break (kırıldı)
                elif self.current_price < nearest_support["price"] * 0.99:
                    signals["support_break"] = True
                    signals["signal_strength"] = nearest_support["strength"]

        return signals

    def _process_resistance_signals(self, signals, nearest_resistance, lookback_period):
        """Resistance sinyallerini işle"""
        resistance_distance = (
            (nearest_resistance["price"] - self.current_price)
            / self.current_price
            * 100
        )
        signals["resistance_level"] = nearest_resistance["price"]

        # Resistance yakınında mı?
        if resistance_distance <= 2:  # %2 tolerans
            signals["near_resistance"] = True

            # Son lookback_period mumda resistance test edildi mi?
            recent_highs = self.data["High"].tail(lookback_period).max()
            if recent_highs >= nearest_resistance["price"] * 0.99:  # %1 tolerans

                current_high = self.data["High"].iloc[-1]

                # Resistance rejection (test edildi ama kırılamadı)
                if current_high < nearest_resistance["price"] * 1.01:
                    signals["resistance_rejection"] = True
                    signals["signal_strength"] = nearest_resistance["strength"]

                # Resistance break (kırıldı)
                elif self.current_price > nearest_resistance["price"] * 1.01:
                    signals["resistance_break"] = True
                    signals["signal_strength"] = nearest_resistance["strength"]

        return signals

    def get_volume_confirmation(self, signals):
        """
        Volume ile S/R sinyallerini doğrula

        Args:
            signals (dict): S/R sinyalleri

        Returns:
            dict: Volume doğrulamalı sinyaller
        """
        if "Volume" not in self.data.columns:
            signals["volume_confirmation"] = False
            signals["volume_ratio"] = 1.0
            return signals

        # Timeframe'e uygun hacim periyodu
        avg_volume = self.data["Volume"].tail(self.volume_period).mean()
        current_volume = self.data["Volume"].iloc[-1]

        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        # Volume confirmation ekle
        signals["volume_confirmation"] = volume_ratio > 1.5  # %50 fazla hacim
        signals["volume_ratio"] = volume_ratio

        # Yüksek hacimle kırılım/bounce daha güçlü
        if signals["volume_confirmation"]:
            if signals["support_bounce"] or signals["resistance_break"]:
                signals["signal_strength"] *= 1.5
            elif signals["support_break"] or signals["resistance_rejection"]:
                signals["signal_strength"] *= 1.3

        return signals

    def calculate_risk_reward(self, signals):
        """
        Risk/Reward oranını hesapla

        Args:
            signals (dict): S/R sinyalleri

        Returns:
            dict: Risk/reward bilgileri
        """
        risk_reward = {}

        # Support bounce için risk/reward
        if signals["support_bounce"]:
            entry_price = self.current_price
            stop_loss = signals["support_level"] * 0.98  # Support altında %2
            take_profit = signals.get(
                "resistance_level", self.current_price * 1.05
            )  # Resistance veya %5

            risk = entry_price - stop_loss
            reward = take_profit - entry_price

            risk_reward = {
                "trade_type": "LONG",
                "entry": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_amount": risk,
                "reward_amount": reward,
                "rr_ratio": reward / risk if risk > 0 else 0,
            }

        # Resistance break için risk/reward
        elif signals["resistance_break"]:
            entry_price = self.current_price
            stop_loss = (
                signals["resistance_level"] * 0.98
            )  # Eski resistance support oldu
            take_profit = self.current_price * 1.05  # %5 hedef

            risk = entry_price - stop_loss
            reward = take_profit - entry_price

            risk_reward = {
                "trade_type": "LONG",
                "entry": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_amount": risk,
                "reward_amount": reward,
                "rr_ratio": reward / risk if risk > 0 else 0,
            }

        # Support break için short pozisyon
        elif signals["support_break"]:
            entry_price = self.current_price
            stop_loss = signals["support_level"] * 1.02  # Eski support resistance oldu
            take_profit = self.current_price * 0.95  # %5 hedef aşağıda

            risk = stop_loss - entry_price
            reward = entry_price - take_profit

            risk_reward = {
                "trade_type": "SHORT",
                "entry": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_amount": risk,
                "reward_amount": reward,
                "rr_ratio": reward / risk if risk > 0 else 0,
            }

        return risk_reward

    def analyze(self):
        """
        Kapsamlı S/R analizi

        Returns:
            dict: Tüm S/R analiz sonuçları
        """
        # Temel sinyaller
        signals = self.generate_sr_signals()

        # Volume doğrulaması
        signals = self.get_volume_confirmation(signals)

        # Risk/Reward hesapla
        risk_reward = self.calculate_risk_reward(signals)

        # S/R seviyelerini bul
        levels = self.find_support_resistance_levels()

        return {
            "signals": signals,
            "risk_reward": risk_reward,
            "levels": levels,
            "current_price": self.current_price,
            "summary": self._generate_summary(signals, risk_reward),
        }

    def _generate_summary(self, signals, risk_reward):
        """Analiz özeti oluştur"""
        summary = {
            "action": "HOLD",
            "confidence": 0,
            "key_levels": {},
            "next_targets": {},
        }

        # Ana sinyal belirleme
        if signals["support_bounce"] and signals["volume_confirmation"]:
            summary["action"] = "BUY"
            summary["confidence"] = min(90, 60 + signals["signal_strength"] * 5)
        elif signals["resistance_break"] and signals["volume_confirmation"]:
            summary["action"] = "BUY"
            summary["confidence"] = min(95, 70 + signals["signal_strength"] * 5)
        elif signals["support_break"] and signals["volume_confirmation"]:
            summary["action"] = "SELL"
            summary["confidence"] = min(90, 60 + signals["signal_strength"] * 5)
        elif signals["resistance_rejection"]:
            summary["action"] = "SELL"
            summary["confidence"] = min(80, 50 + signals["signal_strength"] * 5)

        # Key levels
        if signals["support_level"]:
            summary["key_levels"]["support"] = signals["support_level"]
        if signals["resistance_level"]:
            summary["key_levels"]["resistance"] = signals["resistance_level"]

        # Targets
        if risk_reward:
            summary["next_targets"] = {
                "stop_loss": risk_reward.get("stop_loss"),
                "take_profit": risk_reward.get("take_profit"),
                "rr_ratio": risk_reward.get("rr_ratio", 0),
            }

        return summary


# market_data_client = BinanceMarketData()
# analyzer = TechnicalAnalyzer(market_data_client)
# btc_df = analyzer.analyze_symbol("BTCUSDT", interval="1h", limit=100)
# print(btc_df)
