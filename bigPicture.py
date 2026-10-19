from smartCache import SmartCacheManager

class  BigPictureTrend:
    def __init__(self, symbol: str, timeframe: str, trend: str):
        self.symbol = symbol
        self.timeframe = timeframe
        self.trend = trend
    
        
    def analyze_big_picture_trend(self,symbol):
        """
        1H ve 4H verilerini kullanarak genel trend yönünü belirler
        """
        try:
            # Cache'den verileri al
            h1_data = SmartCacheManager.cache_storage.get('1h', {}).get('data', {})
            h4_data = SmartCacheManager.cache_storage.get('4h', {}).get('data', {})
            
            if not h1_data or not h4_data:
                return {
                    'trend': 'UNKNOWN',
                    'strength': 0,
                    'confidence': 'LOW',
                    'details': 'Insufficient data'
                }
            
            # 4H - Ana trend yönü (daha önemli)
            h4_trend_score = 0
            h4_signals = h4_data.get('signals', {})
            h4_indicators = h4_data.get('indicators', {})
            
            # Golden/Death Cross (en güçlü sinyal)
            if h4_signals.get('golden_cross', False):
                h4_trend_score += 3
            elif h4_signals.get('death_cross', False):
                h4_trend_score -= 3
                
            # MACD trend
            if h4_signals.get('macd_buy', False):
                h4_trend_score += 2
            elif h4_signals.get('macd_sell', False):
                h4_trend_score -= 2
                
            # RSI trend bias
            rsi_4h = h4_indicators.get('rsi', 50)
            if rsi_4h > 55:
                h4_trend_score += 1
            elif rsi_4h < 45:
                h4_trend_score -= 1
                
            # 1H - Momentum doğrulaması
            h1_trend_score = 0
            h1_signals = h1_data.get('signals', {})
            h1_indicators = h1_data.get('indicators', {})
            
            # MACD momentum
            macd_1h = h1_indicators.get('macd', {})
            if isinstance(macd_1h, dict):
                histogram = macd_1h.get('histogram', 0)
                if histogram > 0:
                    h1_trend_score += 1
                elif histogram < 0:
                    h1_trend_score -= 1
                    
            # BB momentum
            if h1_signals.get('bb_buy', False):
                h1_trend_score += 1
            elif h1_signals.get('bb_sell', False):
                h1_trend_score -= 1
                
            # RSI momentum
            if h1_signals.get('rsi_buy', False):
                h1_trend_score += 1
            elif h1_signals.get('rsi_sell', False):
                h1_trend_score -= 1
                
            # Toplam trend skoru (4H daha ağırlıklı)
            total_score = (h4_trend_score * 0.7) + (h1_trend_score * 0.3)
            
            # Trend yönünü belirle
            if total_score >= 2:
                trend = 'BULLISH'
                confidence = 'HIGH' if total_score >= 3 else 'MEDIUM'
            elif total_score <= -2:
                trend = 'BEARISH'  
                confidence = 'HIGH' if total_score <= -3 else 'MEDIUM'
            elif total_score > 0:
                trend = 'WEAK_BULLISH'
                confidence = 'LOW'
            elif total_score < 0:
                trend = 'WEAK_BEARISH'
                confidence = 'LOW'
            else:
                trend = 'NEUTRAL'
                confidence = 'LOW'
                
            return {
                'trend': trend,
                'strength': abs(total_score),
                'confidence': confidence,
                'h4_score': h4_trend_score,
                'h1_score': h1_trend_score,
                'total_score': total_score,
                'details': {
                    '4h_golden_cross': h4_signals.get('golden_cross', False),
                    '4h_death_cross': h4_signals.get('death_cross', False),
                    '4h_rsi': rsi_4h,
                    '1h_macd_histogram': macd_1h.get('histogram', 0) if isinstance(macd_1h, dict) else 0
                }
            }
            
        except Exception as e:
            return {
                'trend': 'ERROR',
                'strength': 0,
                'confidence': 'LOW',
                'details': f'Error: {str(e)}'
            }

    def should_trade_based_on_trend(trend_analysis, m15_signals):
        """
        Büyük resim trendi ile 15M sinyalleri uyumlu mu kontrol et
        """
        trend = trend_analysis['trend']
        confidence = trend_analysis['confidence']
        
        # Düşük güven = trade yapma
        if confidence == 'LOW':
            return False, "Low confidence in trend direction"
            
        # Bullish trend - sadece long pozisyonlar
        if trend in ['BULLISH', 'WEAK_BULLISH']:
            if m15_signals.get('rsi_buy', False) or m15_signals.get('bb_buy', False):
                return True, f"Long signal confirmed by {trend} trend"
            elif m15_signals.get('rsi_sell', False) or m15_signals.get('bb_sell', False):
                return False, f"Short signal rejected - against {trend} trend"
                
        # Bearish trend - sadece short pozisyonlar  
        elif trend in ['BEARISH', 'WEAK_BEARISH']:
            if m15_signals.get('rsi_sell', False) or m15_signals.get('bb_sell', False):
                return True, f"Short signal confirmed by {trend} trend"
            elif m15_signals.get('rsi_buy', False) or m15_signals.get('bb_buy', False):
                return False, f"Long signal rejected - against {trend} trend"
                
        # Neutral trend - her iki yön de geçerli ama dikkatli
        else:
            strong_signals = sum([
                m15_signals.get('rsi_buy', False),
                m15_signals.get('bb_buy', False),
                m15_signals.get('rsi_sell', False),
                m15_signals.get('bb_sell', False)
            ])
            
            if strong_signals >= 2:
                return True, "Multiple signals in neutral trend"
            else:
                return False, "Insufficient signals in neutral trend"
        
        return False, "No clear signal"

    # Kullanım örneği:
    """
    # Büyük resmi analiz et
    trend_analysis = analyze_big_picture_trend('BTCUSDT')
    print(f"Trend: {trend_analysis['trend']}")
    print(f"Strength: {trend_analysis['strength']}")
    print(f"Confidence: {trend_analysis['confidence']}")

    # 15M sinyalleri ile uyumlu mu kontrol et
    m15_data = SmartCacheManager.cache_storage.get('15m', {}).get('data', {})
    m15_signals = m15_data.get('signals', {})

    should_trade, reason = should_trade_based_on_trend(trend_analysis, m15_signals)
    print(f"Should trade: {should_trade}, Reason: {reason}")
    """