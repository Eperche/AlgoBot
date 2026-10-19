import requests
import json
from datetime import datetime
import time

def get_x_day_volume(symbol, x_day=90, min_age_days=30):
    """
    Belirli bir sembol için ortalama hacmi hesapla ve yeni coinleri ele
    """
    try:
        # Klines verisi al
        url = f"https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': '1d',
            'limit': x_day
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        klines = response.json()
        
        # Yeni coin kontrolü - gerçek veri sayısına bak
        actual_days = len(klines)
        
        # Eğer yeterli veri yoksa coin yeni demektir
        if actual_days < min_age_days:
            print(f"❌ {symbol} elendi: Sadece {actual_days} günlük veri var (minimum {min_age_days} gün)")
            return 0, 0  # Sıfır döndür = coin elendi
        
        # Hacim verisini topla (index 7 = quote asset volume)
        total_volume = sum(float(kline[7]) for kline in klines)
        avg_daily_volume = total_volume / len(klines)
        
        return total_volume, avg_daily_volume
        
    except Exception as e:
        print(f"{symbol} için hacim hesaplanamadı: {e}")
        return 0, 0

# Kullanım:
# get_x_day_volume("BTCUSDT", 90, 7)  # 7 günden yeni coinleri ele
# get_x_day_volume("ETHUSDT", 90, 14) # 14 günden yeni coinleri ele



def get_binance_top_cryptos(limit=200,x_day=180):
    try:
        usdt_symbols = get_active_usdt_pairs()
        if not usdt_symbols:
            print("Aktif USDT pariteleri bulunamadı.")
            return None

        print(f"{len(usdt_symbols)} aktif USDT paritesi bulundu. {x_day} günlük hacim hesaplanıyor...")

        ticker_data = requests.get("https://api.binance.com/api/v3/ticker/24hr").json()
        ticker_map = {item['symbol']: item for item in ticker_data}

        crypto_data = []
        processed = 0

        for symbol in usdt_symbols:
            pair_data = ticker_map.get(symbol)
            if not pair_data:
                continue

            total_volume_x_day, avg_daily_volume = get_x_day_volume(symbol, x_day=x_day)
            if total_volume_x_day > 0:
                crypto_data.append({
                    'symbol': symbol.replace('USDT', ''),
                    'price': float(pair_data['lastPrice']),
                    'volume_x_day': total_volume_x_day,
                    'avg_daily_volume': avg_daily_volume,
                    'price_change_24h': float(pair_data['priceChangePercent'])
                })

            processed += 1
            if processed % 50 == 0:
                print(f"İşlenen: {processed}/{len(usdt_symbols)}")
                time.sleep(1)

        sorted_cryptos = sorted(crypto_data, key=lambda x: x['volume_x_day'], reverse=True)
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



def save_to_file(crypto_list, filename="binance_top_200_cryptos.json", x_day=180):
    """
    Kripto para listesini dosyaya kaydet
    """
    filename = filename.replace(".json", f"_{x_day}d.json")
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_count': len(crypto_list),
                'period': f"{x_day} Günlük Hacim",
                'cryptos': crypto_list
            }, f, indent=2, ensure_ascii=False)
        print(f"Veriler {filename} dosyasına kaydedildi.")
    except Exception as e:
        print(f"Dosya kaydetme hatası: {e}")

def print_crypto_names_only(crypto_list):
    """
    Sadece kripto para isimlerini yazdır
    """
    print("30 Günlük Hacim Bazında En Popüler 200 Kripto Para:")
    print("-" * 50)
    for i, crypto in enumerate(crypto_list, 1):
        volume_millions = crypto['volume_x_day'] / 1_000_000
        print(f"{i:3d}. {crypto['symbol']:8s} (x_Gün Hacim: ${volume_millions:,.0f}M)")

# Ana fonksiyon
if __name__ == "__main__":
    print("Binance'den 30 günlük hacim bazında en popüler 200 kripto para çekiliyor...")
    print("Bu işlem biraz zaman alabilir (rate limit nedeniyle)...\n")
    
    x_day = 90
    # Kripto para listesini al
    top_cryptos = get_binance_top_cryptos(200,x_day)
    
    if top_cryptos:
        print(f"\nToplam {len(top_cryptos)} kripto para alındı.\n")
        
        # Sadece isimleri yazdır
        print_crypto_names_only(top_cryptos)
        
        # Dosyaya kaydet
        save_to_file(top_cryptos,x_day=x_day)
        
        # Sadece isimleri text dosyasına kaydet
        with open(f"crypto_names_{x_day}d.txt", "w", encoding="utf-8") as f:
            for crypto in top_cryptos:
                f.write(crypto['symbol'] + "\n")
        print(f"\nSadece kripto para isimleri 'crypto_names_{x_day}d.txt' dosyasına kaydedildi.")
        
        # En üst 20'yi özel olarak göster
        print(f"\n🏆 En Yüksek x Günlük Hacimli İlk 20 Kripto Para:")
        print("-" * 60)
        for i, crypto in enumerate(top_cryptos[:20], 1):
            volume_millions = crypto['volume_x_day'] / 1_000_000
            avg_daily_millions = crypto['avg_daily_volume'] / 1_000_000
            print(f"{i:2d}. {crypto['symbol']:8s} | 30G: ${volume_millions:8,.0f}M | Günlük Ort: ${avg_daily_millions:6,.0f}M")
        
    else:
        print("Veri alınamadı. Lütfen internet bağlantınızı kontrol edin.")