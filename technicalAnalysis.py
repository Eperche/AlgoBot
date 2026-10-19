from marketData import BinanceMarketData
import pandas as pd
import numpy as np
import ta

from typing import List, Dict, Tuple, Optional

class TechnicalAnalyzer:
    def __init__(self, market_data_client):
        self.market_data_client = market_data_client
    
    def _prepare_data(self, symbol: str = "LTCUSDT", interval: str = None, limit: int = 100) -> pd.DataFrame:
        """OHLCV verisini DataFrame formatına dönüştürür"""
        raw_data = self.market_data_client.get_ohlcv(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(raw_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    
    # Hareketli Ortalamalar (Manuel Hesaplama)
    def sma(self, data: pd.Series, period: int = 20) -> pd.Series:
        """Basit Hareketli Ortalama (Simple Moving Average)"""
        return data.rolling(window=period).mean()
    
    def ema(self, data: pd.Series, period: int = 12) -> pd.Series:
        """Üstel Hareketli Ortalama (Exponential Moving Average)"""
        return data.ewm(span=period, adjust=False).mean()
    
    def wma(self, data: pd.Series, period: int = 20) -> pd.Series:
        """Ağırlıklı Hareketli Ortalama (Weighted Moving Average)"""
        weights = np.arange(1, period + 1)
        return data.rolling(window=period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
    
    # Momentum İndikatörleri (Manuel Hesaplama)
    def rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """
        Göreceli Güç Endeksi (Relative Strength Index)
        
        Formül:
        1. Günlük değişimi hesapla: delta = close[i] - close[i-1]
        2. Pozitif değişimlerin ortalaması: gain = average(delta where delta > 0)
        3. Negatif değişimlerin ortalaması: loss = average(abs(delta) where delta < 0)
        4. RS = gain / loss
        5. RSI = 100 - (100 / (1 + RS))
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def macd(self, data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """
        MACD (Moving Average Convergence Divergence)
        
        Formül:
        1. MACD Line = EMA(12) - EMA(26)
        2. Signal Line = EMA(MACD Line, 9)
        3. Histogram = MACD Line - Signal Line
        """
        ema_fast = self.ema(data, fast)
        ema_slow = self.ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self.ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                   k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """
        Stokastik Osilatör
        
        Formül:
        1. %K = 100 * (Close - Lowest Low) / (Highest High - Lowest Low)
        2. %D = SMA(%K, 3)
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return {
            'k_percent': k_percent,
            'd_percent': d_percent
        }
    
    def williams_r(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Williams %R
        
        Formül:
        %R = -100 * (Highest High - Close) / (Highest High - Lowest Low)
        """
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        wr = -100 * ((highest_high - close) / (highest_high - lowest_low))
        return wr
    
    def cci(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """
        Commodity Channel Index
        
        Formül:
        1. Typical Price = (High + Low + Close) / 3
        2. SMA = SMA(Typical Price, period)
        3. Mean Deviation = SMA(|Typical Price - SMA|, period)
        4. CCI = (Typical Price - SMA) / (0.015 * Mean Deviation)
        """
        typical_price = (high + low + close) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mean_deviation = np.abs(typical_price - sma_tp).rolling(window=period).mean()
        cci = (typical_price - sma_tp) / (0.015 * mean_deviation)
        return cci
    
    # Volatilite İndikatörleri (Manuel Hesaplama)
    def bollinger_bands(self, data: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """
        Bollinger Bantları
        
        Formül:
        1. Middle Band = SMA(Close, 20)
        2. Upper Band = Middle Band + (2 * Standard Deviation)
        3. Lower Band = Middle Band - (2 * Standard Deviation)
        """
        sma = self.sma(data, period)
        std = data.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }
    
    def atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Ortalama Gerçek Aralık (Average True Range)
        
        Formül:
        1. TR1 = High - Low
        2. TR2 = |High - Previous Close|
        3. TR3 = |Low - Previous Close|
        4. True Range = MAX(TR1, TR2, TR3)
        5. ATR = SMA(True Range, period)
        """
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr
    
    # Trend İndikatörleri (Manuel Hesaplama)
    def adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Dict[str, pd.Series]:
        """
        Ortalama Yön Endeksi (Average Directional Index)
        
        Formül:
        1. +DM = High[i] - High[i-1] (eğer > 0 ve > -DM)
        2. -DM = Low[i-1] - Low[i] (eğer > 0 ve > +DM)  
        3. TR = True Range
        4. +DI = 100 * SMA(+DM, period) / SMA(TR, period)
        5. -DI = 100 * SMA(-DM, period) / SMA(TR, period)
        6. DX = 100 * |+DI - -DI| / (+DI + -DI)
        7. ADX = SMA(DX, period)
        """
        # True Range hesaplama
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movement hesaplama
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # Sadece biri diğerinden büyükse değer al
        plus_dm[(plus_dm - minus_dm) <= 0] = 0
        minus_dm[(minus_dm - plus_dm) <= 0] = 0
        
        # Directional Indicators
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean())
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean())
        
        # DX ve ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return {
            'adx': adx,
            'plus_di': plus_di,
            'minus_di': minus_di
        }
    
    def parabolic_sar(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                      af_start: float = 0.02, af_increment: float = 0.02, af_max: float = 0.2) -> pd.Series:
        """
        Parabolik SAR
        
        Formül:
        1. Başlangıç SAR = İlk Low (yükseliş trendi için)
        2. SAR = Önceki SAR + AF * (EP - Önceki SAR)
        3. AF (Acceleration Factor) = 0.02'den başlar, her yeni EP'de 0.02 artar, max 0.2
        4. EP (Extreme Point) = Trend süresince en yüksek High (yükseliş) veya en düşük Low (düşüş)
        """
        length = len(close)
        psar = close.copy()
        
        bull = True  # Başlangıç trendi (yükseliş)
        af = af_start
        ep = low.iloc[0]  # Extreme Point
        hp = high.iloc[0]  # Highest Point
        lp = low.iloc[0]   # Lowest Point
        
        for i in range(2, length):
            if bull:
                # Yükseliş trendi
                psar.iloc[i] = psar.iloc[i-1] + af * (hp - psar.iloc[i-1])
            else:
                # Düşüş trendi
                psar.iloc[i] = psar.iloc[i-1] + af * (lp - psar.iloc[i-1])
            
            reverse = False
            
            if bull:
                if low.iloc[i] <= psar.iloc[i]:
                    bull = False
                    reverse = True
                    psar.iloc[i] = hp
                    lp = low.iloc[i]
                    af = af_start
            else:
                if high.iloc[i] >= psar.iloc[i]:
                    bull = True
                    reverse = True
                    psar.iloc[i] = lp
                    hp = high.iloc[i]
                    af = af_start
            
            if not reverse:
                if bull:
                    if high.iloc[i] > hp:
                        hp = high.iloc[i]
                        af = min(af + af_increment, af_max)
                    # SAR önceki iki mumun en düşüğünden büyük olamaz
                    if low.iloc[i-1] < psar.iloc[i]:
                        psar.iloc[i] = low.iloc[i-1]
                    if low.iloc[i-2] < psar.iloc[i]:
                        psar.iloc[i] = low.iloc[i-2]
                else:
                    if low.iloc[i] < lp:
                        lp = low.iloc[i]
                        af = min(af + af_increment, af_max)
                    # SAR önceki iki mumun en yükseğinden küçük olamaz
                    if high.iloc[i-1] > psar.iloc[i]:
                        psar.iloc[i] = high.iloc[i-1]
                    if high.iloc[i-2] > psar.iloc[i]:
                        psar.iloc[i] = high.iloc[i-2]
        
        return psar
    
    # Hacim İndikatörleri (Manuel Hesaplama)
    def obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        On-Balance Volume
        
        Formül:
        - Eğer Close > Previous Close: OBV = Previous OBV + Volume
        - Eğer Close < Previous Close: OBV = Previous OBV - Volume
        - Eğer Close = Previous Close: OBV = Previous OBV
        """
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        return obv
    
    def vwap(self, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Volume Weighted Average Price
        
        Formül:
        1. Typical Price = (High + Low + Close) / 3
        2. VWAP = Σ(Typical Price * Volume) / Σ(Volume)
        """
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap
    
    def accumulation_distribution(self, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Accumulation/Distribution Line
        
        Formül:
        1. Money Flow Multiplier = [(Close - Low) - (High - Close)] / (High - Low)
        2. Money Flow Volume = Money Flow Multiplier * Volume
        3. A/D Line = Previous A/D + Money Flow Volume
        """
        mfm = ((close - low) - (high - close)) / (high - low)
        mfv = mfm * volume
        ad_line = mfv.cumsum()
        return ad_line
    
    # Sinyal Fonksiyonları
    def generate_rsi_signals(self, rsi: pd.Series, oversold: int = 30, overbought: int = 70) -> Dict[str, pd.Series]:
        """RSI tabanlı al/sat sinyalleri"""
        buy_signals = (rsi < oversold) & (rsi.shift(1) >= oversold)
        sell_signals = (rsi > overbought) & (rsi.shift(1) <= overbought)
        
        return {
            'buy': buy_signals,
            'sell': sell_signals
        }
    
    def generate_macd_signals(self, macd_data: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
        """MACD tabanlı al/sat sinyalleri"""
        macd_line = macd_data['macd']
        signal_line = macd_data['signal']
        
        buy_signals = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
        sell_signals = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))
        
        return {
            'buy': buy_signals,
            'sell': sell_signals
        }
    
    def generate_bollinger_signals(self, close: pd.Series, bollinger_data: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
        """Bollinger Bands tabanlı al/sat sinyalleri"""
        upper = bollinger_data['upper']
        lower = bollinger_data['lower']
        
        buy_signals = (close <= lower) & (close.shift(1) > lower.shift(1))
        sell_signals = (close >= upper) & (close.shift(1) < upper.shift(1))
        
        return {
            'buy': buy_signals,
            'sell': sell_signals
        }
    
    def generate_golden_cross_signals(self, short_ma: pd.Series, long_ma: pd.Series) -> Dict[str, pd.Series]:
        """Golden Cross/Death Cross sinyalleri"""
        buy_signals = (short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))  # Golden Cross
        sell_signals = (short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))  # Death Cross
        
        return {
            'buy': buy_signals,
            'sell': sell_signals
        }
    
    # Kapsamlı Analiz Fonksiyonu
    def analyze_symbol(self, symbol: str = "LTCUSDT", interval: str = None, limit: int = 100) -> Dict:
        """Sembol için kapsamlı teknik analiz"""
        df = self._prepare_data(symbol, interval, limit)
        
        analysis = {
            'symbol': symbol,
            'last_price': df['close'].iloc[-1],
            'indicators': {},
            'signals': {}
        }
        
        # Hareketli ortalamalar
        sma_20 = self.sma(df['close'], 20)
        ema_12 = self.ema(df['close'], 12)
        ema_26 = self.ema(df['close'], 26)
        
        analysis['indicators']['sma_20'] = sma_20.iloc[-1]
        analysis['indicators']['ema_12'] = ema_12.iloc[-1]
        analysis['indicators']['ema_26'] = ema_26.iloc[-1]
        
        # Momentum indikatörleri
        rsi_values = self.rsi(df['close'])
        analysis['indicators']['rsi'] = rsi_values.iloc[-1]
        
        macd_data = self.macd(df['close'])
        analysis['indicators']['macd'] = {
            'macd': macd_data['macd'].iloc[-1],
            'signal': macd_data['signal'].iloc[-1],
            'histogram': macd_data['histogram'].iloc[-1]
        }
        
        cci_values = self.cci(df['high'], df['low'], df['close'])
        analysis['indicators']['cci'] = cci_values.iloc[-1]
        
        williams_r_values = self.williams_r(df['high'], df['low'], df['close'])
        analysis['indicators']['williams_r'] = williams_r_values.iloc[-1]
        
        # Volatilite indikatörleri
        bb_data = self.bollinger_bands(df['close'])
        analysis['indicators']['bollinger'] = {
            'upper': bb_data['upper'].iloc[-1],
            'middle': bb_data['middle'].iloc[-1],
            'lower': bb_data['lower'].iloc[-1]
        }
        
        # ATR
        atr_value = self.atr(df['high'], df['low'], df['close'])
        analysis['indicators']['atr'] = atr_value.iloc[-1]
        
        # Trend indikatörleri
        adx_data = self.adx(df['high'], df['low'], df['close'])
        analysis['indicators']['adx'] = {
            'adx': adx_data['adx'].iloc[-1],
            'plus_di': adx_data['plus_di'].iloc[-1],
            'minus_di': adx_data['minus_di'].iloc[-1]
        }
        
        sar_values = self.parabolic_sar(df['high'], df['low'], df['close'])
        analysis['indicators']['parabolic_sar'] = sar_values.iloc[-1]
        
        # Hacim indikatörleri
        obv_values = self.obv(df['close'], df['volume'])
        analysis['indicators']['obv'] = obv_values.iloc[-1]
        
        ad_values = self.accumulation_distribution(df['high'], df['low'], df['close'], df['volume'])
        analysis['indicators']['ad_line'] = ad_values.iloc[-1]
        
        # Sinyaller
        rsi_signals = self.generate_rsi_signals(rsi_values)
        macd_signals = self.generate_macd_signals(macd_data)
        bb_signals = self.generate_bollinger_signals(df['close'], bb_data)
        golden_cross_signals = self.generate_golden_cross_signals(ema_12, ema_26)
        
        analysis['signals'] = {
            'rsi_buy': rsi_signals['buy'].iloc[-1] if len(rsi_signals['buy']) > 0 else False,
            'rsi_sell': rsi_signals['sell'].iloc[-1] if len(rsi_signals['sell']) > 0 else False,
            'macd_buy': macd_signals['buy'].iloc[-1] if len(macd_signals['buy']) > 0 else False,
            'macd_sell': macd_signals['sell'].iloc[-1] if len(macd_signals['sell']) > 0 else False,
            'bb_buy': bb_signals['buy'].iloc[-1] if len(bb_signals['buy']) > 0 else False,
            'bb_sell': bb_signals['sell'].iloc[-1] if len(bb_signals['sell']) > 0 else False,
            'golden_cross': golden_cross_signals['buy'].iloc[-1] if len(golden_cross_signals['buy']) > 0 else False,
            'death_cross': golden_cross_signals['sell'].iloc[-1] if len(golden_cross_signals['sell']) > 0 else False
        }
        
        # Genel öneri
        buy_count = sum([v for k, v in analysis['signals'].items() if 'buy' in k or 'golden' in k])
        sell_count = sum([v for k, v in analysis['signals'].items() if 'sell' in k or 'death' in k])
        
        if buy_count > sell_count:
            analysis['recommendation'] = 'BUY'
        elif sell_count > buy_count:
            analysis['recommendation'] = 'SELL'
        else:
            analysis['recommendation'] = 'HOLD'
        
        analysis['signal_strength'] = abs(buy_count - sell_count)
        
        return analysis
    
    
    # -------------------------------------------------------------
    
    def get_ohlcv_df(self, symbol, interval="1h", limit=100):
        """
        BinanceMarketData üzerinden OHLCV verilerini alır ve DataFrame'e çevirir.
        """
        ohlcv = self.market_data_client.get_ohlcv(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(ohlcv)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
        print(df)
        return df

    def calculate_rsi(self, df, window=14):
        rsi = ta.momentum.RSIIndicator(close=df["close"], window=window)
        df["rsi"] = rsi.rsi()
        return df

    def calculate_ema(self, df, window=21):
        ema = ta.trend.EMAIndicator(close=df["close"], window=window)
        df[f"ema{window}"] = ema.ema_indicator()
        return df

    def analyze(self, symbol="BTCUSDT", interval="1h", limit=100):
        """
        Veri çek -> RSI ve EMA hesapla -> Sonuçları döndür
        """
        df = self.get_ohlcv_df(symbol=symbol, interval=interval, limit=limit)
        df = self.calculate_rsi(df)
        df = self.calculate_ema(df)
        return df[["timestamp", "close", "rsi", "ema21"]]
    
    

market_data_client = BinanceMarketData()
analyzer = TechnicalAnalyzer(market_data_client)
btc_df = analyzer.analyze("BTCUSDT", interval="1h", limit=100)
print(btc_df.tail())