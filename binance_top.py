import requests
import json
from datetime import datetime
import time

def get_coin_info_comprehensive():
    """
    CoinGecko'dan kapsamlı market cap bilgilerini al
    """
    try:
        coin_map = {}
        
        # Birden fazla sayfa al
        for page in range(1, 11):  # İlk 10 sayfa (2500 coin)
            print(f"CoinGecko verisi alınıyor... Sayfa {page}/10")
            
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 250,
                'page': page,
                'sparkline': 'false'
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                coins = response.json()
                if not coins:  # Boş sayfa
                    break
                
                # Symbol bazlı map oluştur + özel eşleştirmeler
                for coin in coins:
                    symbol = coin['symbol'].upper()
                    coin_map[symbol] = {
                        'market_cap': coin.get('market_cap', 0),
                        'name': coin['name'],
                        'rank': coin.get('market_cap_rank', 999),
                        'id': coin.get('id', '')
                    }
                    
                    # Özel sembol eşleştirmeleri
                    coin_name_lower = coin['name'].lower()
                    coin_id = coin.get('id', '').lower()
                    
                    # Major coinler için özel eşleştirmeler
                    if coin_id == 'ethereum' or 'ethereum' in coin_name_lower:
                        coin_map['ETH'] = coin_map[symbol]
                    elif coin_id == 'bitcoin' or coin_name_lower == 'bitcoin':
                        coin_map['BTC'] = coin_map[symbol]
                    elif coin_id == 'binancecoin' or 'binance coin' in coin_name_lower:
                        coin_map['BNB'] = coin_map[symbol]
                    elif coin_id == 'avalanche-2' or 'avalanche' in coin_name_lower:
                        coin_map['AVAX'] = coin_map[symbol]
                    elif coin_id == 'solana' or coin_name_lower == 'solana':
                        coin_map['SOL'] = coin_map[symbol]
                    elif coin_id == 'cardano' or coin_name_lower == 'cardano':
                        coin_map['ADA'] = coin_map[symbol]
                    elif coin_id == 'polkadot' or coin_name_lower == 'polkadot':
                        coin_map['DOT'] = coin_map[symbol]
                    elif coin_id == 'matic-network' or 'polygon' in coin_name_lower:
                        coin_map['MATIC'] = coin_map[symbol]
                    elif coin_id == 'chainlink' or coin_name_lower == 'chainlink':
                        coin_map['LINK'] = coin_map[symbol]
                    elif coin_id == 'uniswap' or coin_name_lower == 'uniswap':
                        coin_map['UNI'] = coin_map[symbol]
                
                print(f"  Sayfa {page}: {len(coins)} coin eklendi")
                time.sleep(0.5)  # Rate limit için bekle
                
            except Exception as e:
                print(f"  Sayfa {page} hatası: {e}")
                continue
        
        print(f"Toplam {len(coin_map)} coin bilgisi alındı CoinGecko'dan")
        
        # Debug: Major coinlerin var olup olmadığını kontrol et
        major_coins = ['BTC', 'ETH', 'BNB', 'AVAX', 'SOL', 'ADA', 'DOT', 'MATIC', 'LINK', 'UNI']
        print("\nMajor coinlerin durumu:")
        for coin in major_coins:
            if coin in coin_map:
                print(f"✓ {coin}: {coin_map[coin]['name']} (Rank: {coin_map[coin]['rank']}) - Market Cap: ${coin_map[coin]['market_cap']/1e9:.1f}B")
            else:
                print(f"✗ {coin}: BULUNAMADI")
        
        # Ethereum'u özel olarak ara
        print(f"\nEthereum arama sonuçları:")
        eth_found = False
        for symbol, data in coin_map.items():
            if 'ethereum' in data['name'].lower() or symbol == 'ETH':
                print(f"  {symbol}: {data['name']} (Rank: {data['rank']})")
                eth_found = True
        if not eth_found:
            print("  Ethereum hiçbir formatta bulunamadı!")
        
        # Bitcoin'i özel olarak ara
        print(f"\nBitcoin arama sonuçları:")
        btc_found = False
        for symbol, data in coin_map.items():
            if 'bitcoin' in data['name'].lower() or symbol == 'BTC':
                print(f"  {symbol}: {data['name']} (Rank: {data['rank']})")
                btc_found = True
        if not btc_found:
            print("  Bitcoin hiçbir formatta bulunamadı!")
        
        return coin_map
        
    except Exception as e:
        print(f"CoinGecko verisi alınamadı: {e}")
        return {}

def debug_binance_symbols():
    """
    Binance sembollerini debug et
    """
    try:
        usdt_symbols = get_active_usdt_pairs()
        print(f"\nBinance'de {len(usdt_symbols)} USDT paritesi bulundu")
        
        # Major coinlerin Binance'de var olup olmadığını kontrol et
        major_pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'AVAXUSDT', 'SOLUSDT', 'ADAUSDT']
        print("\nMajor paritelerinin Binance durumu:")
        for pair in major_pairs:
            if pair in usdt_symbols:
                print(f"✓ {pair}: VAR")
            else:
                print(f"✗ {pair}: YOK")
        
        return usdt_symbols
        
    except Exception as e:
        print(f"Binance sembol debug hatası: {e}")
        return []

def get_binance_market_cap_ranking_debug(limit=200):
    """
    Debug bilgileri ile Binance'deki coinleri market cap'e göre sırala
    """
    try:
        # Debug modda sembol kontrolleri
        usdt_symbols = debug_binance_symbols()
        if not usdt_symbols:
            print("Aktif USDT pariteleri bulunamadı.")
            return None
        
        # Binance fiyat verilerini al
        print("\nBinance ticker verileri alınıyor...")
        ticker_data = requests.get("https://api.binance.com/api/v3/ticker/24hr").json()
        ticker_map = {item['symbol']: item for item in ticker_data}
        print(f"Binance'den {len(ticker_map)} ticker verisi alındı")
        
        # CoinGecko'dan market cap verilerini al
        print("\nMarket cap verileri CoinGecko'dan alınıyor...")
        coin_info = get_coin_info_comprehensive()
        
        crypto_data = []
        found_symbols = []
        not_found_symbols = []
        processed = 0
        
        for symbol in usdt_symbols:
            pair_data = ticker_map.get(symbol)
            if not pair_data:
                continue
            
            # Symbol'dan USDT'yi çıkar
            coin_symbol = symbol.replace('USDT', '')
            
            # Market cap bilgisini al
            market_cap_info = coin_info.get(coin_symbol, {})
            market_cap = market_cap_info.get('market_cap', 0)
            
            if market_cap > 0:  # Market cap'i olan coinleri al
                crypto_data.append({
                    'symbol': coin_symbol,
                    'name': market_cap_info.get('name', coin_symbol),
                    'price': float(pair_data['lastPrice']),
                    'market_cap': market_cap,
                    'market_cap_rank': market_cap_info.get('rank', 999),
                    'volume_24h': float(pair_data['quoteVolume']),
                    'price_change_24h': float(pair_data['priceChangePercent'])
                })
                found_symbols.append(coin_symbol)
            else:
                not_found_symbols.append(coin_symbol)
            
            processed += 1
            if processed % 100 == 0:
                print(f"İşlenen: {processed}/{len(usdt_symbols)}")
        
        # Market cap'e göre sırala
        sorted_cryptos = sorted(crypto_data, key=lambda x: x['market_cap'], reverse=True)
        
        # Debug raporu
        print(f"\n=== DEBUG RAPORU ===")
        print(f"Total Binance USDT pairs: {len(usdt_symbols)}")
        print(f"Market cap bulunan coinler: {len(found_symbols)}")
        print(f"Market cap bulunamayan coinler: {len(not_found_symbols)}")
        
        print(f"\nBulunan major coinler:")
        major_coins = ['BTC', 'ETH', 'BNB', 'AVAX', 'SOL', 'ADA']
        for coin in major_coins:
            if coin in found_symbols:
                crypto = next((c for c in sorted_cryptos if c['symbol'] == coin), None)
                if crypto:
                    rank = sorted_cryptos.index(crypto) + 1
                    print(f"✓ {coin}: Rank #{rank}, Market Cap: ${crypto['market_cap']/1e9:.1f}B")
            else:
                print(f"✗ {coin}: BULUNAMADI")
        
        print(f"\nBulunamayan bazı semboller (ilk 20):")
        print(", ".join(not_found_symbols[:20]))
        
        return sorted_cryptos[:limit]
        
    except Exception as e:
        print(f"Hata oluştu: {e}")
        return None

def get_active_usdt_pairs():
    """
    Sadece aktif USDT işlem çiftlerini getirir.
    """
    try:
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        usdt_pairs = [
            s['symbol'] for s in data['symbols']
            if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING'
        ]
        return usdt_pairs
    except Exception as e:
        print(f"USDT pariteleri alınamadı: {e}")
        return []

def save_to_file(crypto_list, filename="binance_top_by_marketcap_debug.json"):
    """
    Kripto para listesini dosyaya kaydet
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_count': len(crypto_list),
                'sorting_method': 'Market Capitalization',
                'data_source': 'Binance Trading Pairs + CoinGecko Market Cap (Debug)',
                'cryptos': crypto_list
            }, f, indent=2, ensure_ascii=False)
        print(f"Veriler {filename} dosyasına kaydedildi.")
    except Exception as e:
        print(f"Dosya kaydetme hatası: {e}")

def print_crypto_ranking(crypto_list):
    """
    Market cap bazlı kripto para sıralamasını yazdır
    """
    print(f"\nMarket Kapitalizasyonu Bazında İlk {len(crypto_list)} Kripto Para (Binance'de İşlem Gören):")
    print("-" * 85)
    print(f"{'#':<4} {'Symbol':<8} {'Name':<25} {'Market Cap':<15} {'Price':<12} {'24h %':<8}")
    print("-" * 85)
    
    for i, crypto in enumerate(crypto_list, 1):
        market_cap_b = crypto['market_cap'] / 1_000_000_000  # Milyar cinsinden
        price_str = f"${crypto['price']:.4f}" if crypto['price'] < 1 else f"${crypto['price']:.2f}"
        change_str = f"{crypto['price_change_24h']:+.2f}%"
        name_short = crypto['name'][:23] if len(crypto['name']) > 23 else crypto['name']
        
        print(f"{i:<4} {crypto['symbol']:<8} {name_short:<25} ${market_cap_b:>10.2f}B {price_str:<12} {change_str:<8}")

def format_market_cap(market_cap):
    """Market cap'i okunabilir formatta döndür"""
    if market_cap >= 1_000_000_000:
        return f"${market_cap/1_000_000_000:.2f}B"
    elif market_cap >= 1_000_000:
        return f"${market_cap/1_000_000:.2f}M"
    else:
        return f"${market_cap:,.0f}"

# Ana fonksiyon
if __name__ == "__main__":
    print("=== DEBUG MODDA MARKET CAP SIRALAMA ===")
    print("Bu işlem detaylı debug bilgileri verecek...\n")
    
    # Market cap bazlı kripto para listesini al (debug mode)
    top_cryptos = get_binance_market_cap_ranking_debug(500)
    
    if top_cryptos:
        print(f"\n=== SONUÇLAR ===")
        print(f"Toplam {len(top_cryptos)} kripto para alındı (market cap verileri olan).")
        
        # İlk 50'yi yazdır
        print_crypto_ranking(top_cryptos[:50])
        
        # Dosyaya kaydet
        save_to_file(top_cryptos)
        
        # Sadece isimleri text dosyasına kaydet
        with open("crypto_names_by_marketcap_debug.txt", "w", encoding="utf-8") as f:
            for crypto in top_cryptos:
                f.write(crypto['symbol'] + "\n")
        print(f"\nSadece kripto para isimleri 'crypto_names_by_marketcap_debug.txt' dosyasına kaydedildi.")
        
        # En üst 30'u özel olarak göster
        print(f"\n🏆 En Yüksek Market Cap'li İlk 30 Kripto Para:")
        print("-" * 80)
        for i, crypto in enumerate(top_cryptos[:30], 1):
            market_cap_formatted = format_market_cap(crypto['market_cap'])
            price_str = f"${crypto['price']:.4f}" if crypto['price'] < 1 else f"${crypto['price']:.2f}"
            print(f"{i:2d}. {crypto['symbol']:8s} | {market_cap_formatted:>12s} | {price_str:>10s} | {crypto['price_change_24h']:+6.2f}%")
        
    else:
        print("Veri alınamadı. Lütfen internet bağlantınızı kontrol edin.")