import json
from datetime import datetime
from typing import Dict, List, Any

def load_json_file(file_path: str) -> Dict:
    """JSON dosyasını yükle"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Hata: {file_path} dosyası bulunamadı")
        return {}
    except json.JSONDecodeError:
        print(f"Hata: {file_path} dosyasında JSON formatı hatası")
        return {}

def find_common_cryptos(json_1day: Dict, json_90day: Dict) -> List[Dict]:
    """İki JSON dosyasındaki ortak coinleri bul"""
    if not json_1day.get('cryptos') or not json_90day.get('cryptos'):
        return []
    
    # 1 günlük verilerden symbol listesi
    symbols_1day = {crypto['symbol'] for crypto in json_1day['cryptos']}
    
    # 90 günlük verilerden symbol listesi
    symbols_90day = {crypto['symbol'] for crypto in json_90day['cryptos']}
    
    # Ortak symboller
    common_symbols = symbols_1day.intersection(symbols_90day)
    
    # Ortak coinlerin 1 günlük verilerini al (daha güncel olduğu için)
    common_cryptos = [crypto for crypto in json_1day['cryptos'] if crypto['symbol'] in common_symbols]
    
    return common_cryptos

def create_common_cryptos_json(json_1day: Dict, json_90day: Dict) -> Dict:
    """Ortak coinleri içeren yeni JSON formatı oluştur"""
    common_cryptos = find_common_cryptos(json_1day, json_90day)
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "total_count": len(common_cryptos),
        "period": "Ortak Coinler (1 Günlük & 90 Günlük)",
        "comparison_info": {
            "1day_total": json_1day.get('total_count', 0),
            "90day_total": json_90day.get('total_count', 0),
            "common_count": len(common_cryptos)
        },
        "cryptos": common_cryptos
    }
    
    return result

def save_json_file(data: Dict, file_path: str):
    """JSON dosyasını kaydet"""
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        print(f"Dosya başarıyla kaydedildi: {file_path}")
    except Exception as e:
        print(f"Dosya kaydetme hatası: {e}")

def print_common_cryptos(common_data: Dict):
    """Ortak coinleri konsola yazdır"""
    print("=" * 80)
    print(f"ORTAK KRİPTO PARALAR")
    print("=" * 80)
    print(f"Zaman: {common_data['timestamp']}")
    print(f"Toplam Ortak Coin: {common_data['total_count']}")
    print(f"Periyot: {common_data['period']}")
    
    if 'comparison_info' in common_data:
        info = common_data['comparison_info']
        print(f"1 Günlük Toplam: {info['1day_total']}")
        print(f"90 Günlük Toplam: {info['90day_total']}")
        print(f"Ortak Sayı: {info['common_count']}")
    
    print("-" * 80)
    
    for i, crypto in enumerate(common_data['cryptos'], 1):
        print(f"{i:3d}. {crypto['symbol']:8s} - "
              f"Fiyat: ${crypto['price']:>12,.2f} - "
              f"Hacim: ${crypto.get('volume_x_day', 0):>15,.0f} - "
              f"Değişim: %{crypto.get('price_change_24h', 0):>6.2f}")

# Ana kullanım fonksiyonu
def main():
    # Dosya yolları
    file_1day = "crypto_1day.json"
    file_90day = "crypto_90day.json"
    output_file = "crypto_common.json"
    
    # JSON dosyalarını yükle
    print("JSON dosyaları yükleniyor...")
    json_1day = load_json_file(file_1day)
    json_90day = load_json_file(file_90day)
    
    if not json_1day or not json_90day:
        print("Dosyalar yüklenemedi!")
        return
    
    # Ortak coinleri bul ve JSON formatında oluştur
    common_data = create_common_cryptos_json(json_1day, json_90day)
    
    # Konsola yazdır
    print_common_cryptos(common_data)
    
    # Dosyaya kaydet
    save_json_file(common_data, output_file)
    
    return common_data

# Flask route örneği
def get_common_cryptos_route():
    """Flask route için kullanılabilir"""
    try:
        json_1day = load_json_file("crypto_1day.json")
        json_90day = load_json_file("crypto_90day.json")
        
        if not json_1day or not json_90day:
            return {"error": "Dosyalar yüklenemedi"}, 500
        
        common_data = create_common_cryptos_json(json_1day, json_90day)
        return common_data
    
    except Exception as e:
        return {"error": str(e)}, 500

# Sadece symbol listesi almak için
def get_common_symbols_only(json_1day: Dict, json_90day: Dict) -> List[str]:
    """Sadece ortak symbol listesini döndür"""
    common_cryptos = find_common_cryptos(json_1day, json_90day)
    return [crypto['symbol'] for crypto in common_cryptos]

# Test için örnek kullanım
if __name__ == "__main__":
    # Gerçek JSON dosyalarını yükle
    with open("binance_top_200_cryptos_90d.json", "r", encoding="utf-8") as f:
        test_90day = json.load(f)
    
    with open("binance_top_200_cryptos_1d.json", "r", encoding="utf-8") as f:
        test_1day = json.load(f)
        
    # Ortak coinleri bul ve formatla
    common_data = create_common_cryptos_json(test_1day, test_90day)
    
    # Konsola yazdır
    print_common_cryptos(common_data)
    
    # JSON dosyasına kaydet
    output_filename = "binance_common_cryptos.json"
    save_json_file(common_data, output_filename)
    
    print(f"\n✅ Ortak coinler '{output_filename}' dosyasına kaydedildi!")
    print(f"📊 Toplam {common_data['total_count']} adet ortak coin bulundu.")