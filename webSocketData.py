import websocket
import json
import threading
from datetime import datetime

class BinanceWebSocket:
    def __init__(self, on_data_callback=None):
        self.ws = None
        self.base_url = "wss://stream.binance.com:9443/ws/"
        self.on_data_callback = on_data_callback  # Callback fonksiyon
        
    def on_message(self, ws, message):
        """WebSocket'ten gelen mesajları işle"""
        try:
            data = json.loads(message)
            self.process_data(data)
            # if self.on_data_callback:
            #     self.on_data_callback(data)
            
        except json.JSONDecodeError as e:
            print(f"JSON decode hatası: {e}")
    
    def on_error(self, ws, error):
        """Hata durumunda çalışır"""
        print(f"WebSocket hatası: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Bağlantı kapandığında çalışır"""
        print("WebSocket bağlantısı kapandı")
    
    def on_open(self, ws):
        """Bağlantı açıldığında çalışır"""
        print("WebSocket bağlantısı açıldı")
    
    def process_data(self, data):
        """Gelen verileri işle ve ekrana yazdır"""
        if 'e' in data:
            event_type = data['e']
            timestamp = datetime.fromtimestamp(data['E'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            
            if event_type == '24hrTicker':
                # 24 saat ticker verisi
                print(f"\n=== 24 Saat Ticker - {timestamp} ===")
                print(f"Sembol: {data['s']}")
                print(f"Fiyat Değişimi: {data['p']} ({data['P']}%)")
                print(f"Son Fiyat: {data['c']}")
                print(f"Yüksek: {data['h']}")
                print(f"Düşük: {data['l']}")
                print(f"Hacim: {data['v']}")
                
            elif event_type == 'trade':
                # Gerçek zamanlı işlem verisi
                print(f"\n=== Yeni İşlem - {timestamp} ===")
                print(f"Sembol: {data['s']}")
                print(f"Fiyat: {data['p']}")
                print(f"Miktar: {data['q']}")
                print(f"Alıcı Market Maker: {'Evet' if data['m'] else 'Hayır'}")
                
            elif event_type == 'kline':
                # Mum (candlestick) verisi
                kline = data['k']
                print(f"\n=== Mum Verisi - {timestamp} ===")
                print(f"Sembol: {kline['s']}")
                print(f"Açılış: {kline['o']}")
                print(f"Yüksek: {kline['h']}")
                print(f"Düşük: {kline['l']}")
                print(f"Kapanış: {kline['c']}")
                print(f"Hacim: {kline['v']}")
                print(f"Mum Tamamlandı: {'Evet' if kline['x'] else 'Hayır'}")
    
    def start_ticker_stream(self, symbol="btcusdt"):
        """24 saat ticker stream başlat"""
        stream_name = f"{symbol.lower()}@ticker"
        url = self.base_url + stream_name
        
        print(f"{symbol.upper()} için 24 saat ticker stream başlatılıyor...")
        
        self.ws = websocket.WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        self.ws.run_forever()
    
    def start_trade_stream(self, symbol="btcusdt"):
        """Gerçek zamanlı işlem stream başlat"""
        stream_name = f"{symbol.lower()}@trade"
        url = self.base_url + stream_name
        
        print(f"{symbol.upper()} için gerçek zamanlı işlem stream başlatılıyor...")
        
        self.ws = websocket.WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        self.ws.run_forever()
        
    def start_multiple_kline_streams(self, symbol="btcusdt", intervals=["1m", "1h"]):
        """Birden fazla kline (mum) interval'ini aynı anda dinle"""
        stream_names = [f"{symbol.lower()}@kline_{interval}" for interval in intervals]
        url = self.base_url.replace("ws/", "stream?streams=") + "/".join(stream_names)
        
        print(f"{symbol.upper()} için çoklu mum stream başlatılıyor: {intervals}")
        
        self.ws = websocket.WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
    
        self.ws.run_forever()
        
        
    def start_kline_stream(self, symbol="btcusdt", interval="1m"):
        """Mum (candlestick) stream başlat"""
        stream_name = f"{symbol.lower()}@kline_{interval}"
        url = self.base_url + stream_name
        
        print(f"{symbol.upper()} için {interval} mum stream başlatılıyor...")
        
        self.ws = websocket.WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        self.ws.run_forever()
    
    def start_multiple_streams(self, streams):
        """Birden fazla stream'i aynı anda başlat"""
        stream_names = "/".join(streams)
        url = self.base_url + stream_names
        
        print(f"Çoklu stream başlatılıyor: {streams}")
        
        self.ws = websocket.WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        self.ws.run_forever()

def main():
    # WebSocket client oluştur
    binance_ws = BinanceWebSocket()
    
    print("Binance WebSocket Market Verileri")
    print("=================================")
    print("1. 24 Saat Ticker")
    print("2. Gerçek Zamanlı İşlemler")
    print("3. Mum Verileri (1m)")
    print("4. Çoklu Stream (Ticker + Trade + Kline)")
    
    choice = input("\nSeçiminizi yapın (1-4): ")
    symbol = input("Sembol girin (varsayılan: BTCUSDT): ").upper() or "BTCUSDT"
    
    try:
        if choice == "1":
            binance_ws.start_ticker_stream(symbol)
        elif choice == "2":
            binance_ws.start_trade_stream(symbol)
        elif choice == "3":
            binance_ws.start_kline_stream(symbol, "1m")
            
        elif choice == "4":
            streams = [
                f"{symbol.lower()}@ticker",
                f"{symbol.lower()}@trade",
                f"{symbol.lower()}@kline_1m"
            ]
            binance_ws.start_multiple_streams(streams)
            
        elif choice == "5":
            intervals_input = input("Intervalleri virgülle girin (örnek: 1m,1h,4h): ")
            intervals = [i.strip() for i in intervals_input.split(",")]
            binance_ws.start_multiple_kline_streams(symbol, intervals)
        else:
            print("Geçersiz seçim!")
            
    except KeyboardInterrupt:
        print("\nProgram kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"Bir hata oluştu: {e}")

# Alternatif: Sadece basit ticker için hızlı başlatma
def quick_start():
    """Hızlı başlatma - sadece BTC/USDT ticker"""
    binance_ws = BinanceWebSocket()
    print("BTC/USDT ticker stream başlatılıyor...")
    print("Durdurmak için Ctrl+C basın\n")
    
    try:
        binance_ws.start_ticker_stream("BTCUSDT")
    except KeyboardInterrupt:
        print("\nStream durduruldu.")

if __name__ == "__main__":
    # Ana menü için main() fonksiyonunu çalıştır
    # main()
    
    # Veya hızlı başlatma için quick_start() fonksiyonunu çalıştır
    quick_start()