'''
   TABLİB ANALİZ SONUCU VERİSİ ÖRNEĞİ
    Bu örnek, bir kripto para birimi (LTC/USDT) için yapılan teknik analiz sonuçlarını içermektedir.
   
   analysis_output = {
    # Temel Bilgiler
    'symbol': 'LTCUSDT',
    'last_price': 67.45,
    "OHLCV": > analysis["ohlcv"] = df olarak geliyordu 
    
    # Teknik İndikatörler
    'indicators': {
        # Hareketli Ortalamalar
        'sma_20': 67.12,
        'ema_12': 67.23,
        'ema_26': 66.89,
        
        # Momentum İndikatörleri
        'rsi': 65.4,
        'macd': {
            'macd': 0.34,
            'signal': 0.21,
            'histogram': 0.13
        },
        'cci': 45.6,
        'williams_r': -25.3,
        
        # Volatilite İndikatörleri
        'bollinger': {
            'upper': 68.45,
            'middle': 67.12,
            'lower': 65.79
        },
        'atr': 1.23,
        
        # Trend İndikatörleri
        'adx': {
            'adx': 35.6,
            'plus_di': 25.4,
            'minus_di': 18.9
        },
        'parabolic_sar': 66.78,
        
        # Hacim İndikatörleri
        'obv': 1234567.89
    },
    
    # Mum Formasyonları (Pattern Recognition)
    'patterns': {
        'doji': False,
        'hammer': True,
        'engulfing': False,
        'morning_star': False,
        'evening_star': False,
        # get_all_patterns() metodundan gelen diğer tüm pattern'ler
        'shooting_star': False,
        'hanging_man': False,
        'dark_cloud_cover': False,
        'piercing_pattern': False,
        'three_white_soldiers': False,
        'three_black_crows': False,
        'harami': False,
        'inverted_hammer': False
    },
    
    # Alım/Satım Sinyalleri
    'signals': {
        # RSI Sinyalleri
        'rsi_buy': False,           # RSI 30'dan yukarı çıkış
        'rsi_sell': False,          # RSI 70'den aşağı iniş
        
        # MACD Sinyalleri
        'macd_buy': True,           # MACD sinyal çizgisini yukarı kesti
        'macd_sell': False,         # MACD sinyal çizgisini aşağı kesti
        'momentum_strong': True,    # Güçlü yukarı momentum
        'momentum_weak': False,     # Zayıf momentum
        'zero_buy': False,          # MACD sıfır çizgisini yukarı kesti
        'zero_sell': False,         # MACD sıfır çizgisini aşağı kesti
        'buy_divergence': False,    # Pozitif divergence
        'sell_divergence': False,   # Negatif divergence
        
        # Bollinger Bands Sinyalleri
        'bb_buy': False,            # Alt banttan yukarı çıkış
        'bb_sell': False,           # Üst banttan aşağı iniş
        
        # Hareketli Ortalama Crossover Sinyalleri
        'golden_cross': True,       # Kısa EMA uzun EMA'yı yukarı kesti
        'death_cross': False        # Kısa EMA uzun EMA'yı aşağı kesti
    }
}
    '''



'''  enhanced_result >  SmartCacheManager.cache_storage['trend']['data'] = trend_data

            return {
                'trend': trend,
                'strength': abs(final_score),
                'confidence': confidence,
                'final_score': final_score,
                'breakdown': {
                    'base_score': base_score,
                    'sr_score': sr_score,
                    'ema_score': ema_score,
                    'h4_score': base_trend.get('h4_score', 0),
                    'h1_score': base_trend.get('h1_score', 0)
                },
                'context': {
                    'sr_context': sr_context.get('context', 'UNKNOWN'),
                    'ema_alignment': ema_trend.get('alignment', 'UNKNOWN'),
                    'key_levels': sr_context.get('key_levels', {}),
                    'volume_confirmation': sr_context.get('volume_confirmation', False)
                },
                'last_update': datetime.now().isoformat()
            }
'''



''' 
SupportResistanceAnalyzer için örnek çıktı formatı:
 # Örnek sonuç:sr_result    
    
   sr_context = 
   {
    # 1️⃣ SİNYALLER BÖLÜMÜ
    'signals': {
        'support_bounce': True,               # Destekten sekme sinyali
        'support_break': False,               # Destek kırılması
        'resistance_rejection': False,        # Dirençten red
        'resistance_break': False,            # Direnç kırılması
        'near_support': True,                 # Destek yakınında
        'near_resistance': False,             # Direnç yakınında
        'support_level': 43250.5,            # Aktif destek fiyatı
        'resistance_level': 44800.2,         # Aktif direnç fiyatı
        'signal_strength': 4,                # Ham sinyal gücü (dokunma sayısı)
        'volume_confirmation': True,          # Hacim onayı var mı?
        'volume_ratio': 2.3                  # Hacim oranı (ortalamaya göre)
    },
    
    # 2️⃣ RİSK/ÖDÜL HESABI
    'risk_reward': {
        'trade_type': 'LONG',                # İşlem türü
        'entry': 43285.0,                   # Giriş fiyatı (mevcut fiyat)
        'stop_loss': 42385.49,              # Zarar kes seviyesi
        'take_profit': 44800.2,             # Kar al seviyesi
        'risk_amount': 899.51,              # Risk miktarı
        'reward_amount': 1515.2,            # Ödül miktarı
        'rr_ratio': 1.68                    # Risk/Ödül oranı (1:1.68)
    },
    
    # 3️⃣ TÜM S/R SEVİYELERİ
    'levels': {
        'support_levels': [
            {
                'price': 43250.5,
                'type': 'support',
                'strength': 4,               # 4 kez test edilmiş
                'last_touch': 145,           # Son dokunma index'i
                'volume': 1250000            # Toplam hacim
            },
            {
                'price': 42800.8,
                'type': 'support', 
                'strength': 3,
                'last_touch': 120,
                'volume': 980000
            }
        ],
        'resistance_levels': [
            {
                'price': 44800.2,
                'type': 'resistance',
                'strength': 3,
                'last_touch': 140,
                'volume': 1100000
            },
            {
                'price': 45200.1,
                'type': 'resistance',
                'strength': 2,
                'last_touch': 130,
                'volume': 750000
            }
        ]
    },
    
    # 4️⃣ MEVCUT FİYAT
    'current_price': 43285.0,               # Analizdeki mevcut fiyat
    
    # 5️⃣ ÖZET TAVSİYE
    'summary': {
        'action': 'BUY',                     # Ana tavsiye
        'confidence': 80,                    # Güven seviyesi (0-100)
        'key_levels': {
            'support': 43250.5,             # Anahtar destek
            'resistance': 44800.2           # Anahtar direnç
        },
        'next_targets': {
            'stop_loss': 42385.49,          # Önerilen stop
            'take_profit': 44800.2,         # Önerilen hedef
            'rr_ratio': 1.68                # Risk/ödül oranı
        }
    }
}

'''


'''
final_result > 

{
    # Temel Bilgiler
    'symbol': 'LTCUSDT',
    'last_price': 67.45,
    "OHLCV": {
        'open': 67.00,
        'high': 68.00,
        'low': 66.50,
        'close': 67.45,
        'volume': 123456.78
    },
    # Teknik İndikatörler
    'indicators': {
        # Hareketli Ortalamalar
        'sma_20': 67.12,
        'ema_12': 67.23,
        'ema_26': 66.89,
        
        # Momentum İndikatörleri
        'rsi': 65.4,
        'macd': {
            'macd': 0.34,
            'signal': 0.21,
            'histogram': 0.13
        },
        'cci': 45.6,
        'williams_r': -25.3,
        
        # Volatilite İndikatörleri
        'bollinger': {
            'upper': 68.45,
            'middle': 67.12,
            'lower': 65.79
        },
        'atr': 1.23,
        
        # Trend İndikatörleri
        'adx': {
            'adx': 35.6,
            'plus_di': 25.4,
            'minus_di': 18.9
        },
        'parabolic_sar': 66.78,
        
        # Hacim İndikatörleri
        'obv': 1234567.89
    },
    
    # Mum Formasyonları (Pattern Recognition)
    'patterns': {
        'doji': False,
        'hammer': True,
        'engulfing': False,
        'morning_star': False,
        'evening_star': False,
        # get_all_patterns() metodundan gelen diğer tüm pattern'ler
        'shooting_star': False,
        'hanging_man': False,
        'dark_cloud_cover': False,
        'piercing_pattern': False,
        'three_white_soldiers': False,
        'three_black_crows': False,
        'harami': False,
        'inverted_hammer': False
    },
    
    # Alım/Satım Sinyalleri
    'signals': {
        # RSI Sinyalleri
        'rsi_buy': False,           # RSI 30'dan yukarı çıkış
        'rsi_sell': False,          # RSI 70'den aşağı iniş
        
        # MACD Sinyalleri
        'macd_buy': True,           # MACD sinyal çizgisini yukarı kesti
        'macd_sell': False,         # MACD sinyal çizgisini aşağı kesti
        'momentum_strong': True,    # Güçlü yukarı momentum
        'momentum_weak': False,     # Zayıf momentum
        'zero_buy': False,          # MACD sıfır çizgisini yukarı kesti
        'zero_sell': False,         # MACD sıfır çizgisini aşağı kesti
        'buy_divergence': False,    # Pozitif divergence
        'sell_divergence': False,   # Negatif divergence
        
        # Bollinger Bands Sinyalleri
        'bb_buy': False,            # Alt banttan yukarı çıkış
        'bb_sell': False,           # Üst banttan aşağı iniş
        
        # Hareketli Ortalama Crossover Sinyalleri
        'golden_cross': True,       # Kısa EMA uzun EMA'yı yukarı kesti
        'death_cross': False        # Kısa EMA uzun EMA'yı aşağı kesti
    }
    'trend_analysis':{
                'trend': trend,
                'strength': abs(final_score),
                'confidence': confidence,
                'final_score': final_score,
                'breakdown': {
                    'base_score': base_score,
                    'sr_score': sr_score,
                    'ema_score': ema_score,
                    'h4_score': base_trend.get('h4_score', 0),
                    'h1_score': base_trend.get('h1_score', 0)
                },
                'context': {
                    'sr_context': sr_context.get('context', 'UNKNOWN'),
                    'ema_alignment': ema_trend.get('alignment', 'UNKNOWN'),
                    'key_levels': sr_context.get('key_levels', {}),
                    'volume_confirmation': sr_context.get('volume_confirmation', False)
                },
                'last_update': datetime.now().isoformat()
            }
'''