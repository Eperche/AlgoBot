from binance.client import Client
import os
from dotenv import load_dotenv
import requests
from datetime import datetime, date
from proxies import Proxy
import time


load_dotenv()  # .env dosyasını yükler

 
 
class BinanceMarketData:
    
    def __init__(self,max_retries=3):
        self.API_KEY = os.getenv("BINANCE_API_KEY")
        self.API_SECRET = os.getenv("BINANCE_SECRET_KEY")
        self.client = Client(self.API_KEY, self.API_SECRET)
        self.proxy_manager = Proxy()
        self.max_retries = max_retries
        self.current_client = None
        self._create_client()

    def _create_client(self):
        """Yeni proxy ile client oluştur"""
        current_proxy = self.proxy_manager.proxy_generator()
        print(f"Yeni proxy ile client oluşturuluyor: {current_proxy['http']}")
        
        try:
            self.current_client = Client(
                self.API_KEY, 
                self.API_SECRET,
                requests_params={
                    'proxies': current_proxy,
                    'timeout': 30
                }
            )
            return True
        except Exception as e:
            print(f"Client oluşturma hatası: {e}")
            return False
        
    def _retry_with_new_proxy(self, func, *args, **kwargs):
        """Proxy rotasyonu ile tekrar deneme"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            
            except Exception as e:
                if "APIError" in str(e):
                    return
                print(f"Deneme {attempt + 1} başarısız: {e}")
                if attempt < self.max_retries - 1:
                    print("Yeni proxy ile tekrar deneniyor...")
                    self._create_client()
                    # time.sleep(1)  # Kısa bekleme
                else:
                    print("Tüm denemeler başarısız!")
                    raise e

    def get_latest_price(self, symbol="LTCUSDT"):
        """Son fiyat"""
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    
    def split_symbol(self, symbol):
        """
        Sembol çiftini base ve quote asset'e ayırır
        LTCUSDT -> BTC, USDT
        ETHBTC -> ETH, BTC
        """
        symbol = symbol.upper()
        
        # Yaygın quote asset'ler (parite)
        quote_assets = ['USDT', 'BUSD', 'USDC', 'BTC', 'ETH', 'BNB', 'EUR', 'GBP', 'TRY']
        
        for quote in quote_assets:
            if symbol.endswith(quote):
                base_asset = symbol[:-len(quote)]
                return base_asset, quote
        
        # Eğer hiçbiri bulunamazsa (nadir durum)
        # Son 4 karakteri quote olarak al
        if len(symbol) > 4:
            return symbol[:-4], symbol[-4:]
        else:
            return symbol, ""
        
        
    def get_24h_stats(self, symbol="LTCUSDT"):
        def _get_price():
            try:
                stats = self.client.get_ticker(symbol=symbol)
                # Sembol çiftini ayır
                base_asset, quote_asset = self.split_symbol(symbol)
                
                return {
                "symbol": symbol,
                "base_asset": base_asset,  # BTC
                "quote_asset": quote_asset,  # USDT
                "price_change_percent": float(stats['priceChangePercent']),
                "high_price": float(stats['highPrice']),
                "low_price": float(stats['lowPrice']),
                "volume": float(stats['volume']),
                "quote_volume": float(stats['quoteVolume']),
                "last_price": float(stats['lastPrice']),
                "status": "success"
            }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"{symbol} verisi çekilemedi: {str(e)}"
                }
                
        return self._retry_with_new_proxy(_get_price)
            
    def get_change_percent(self,symbol="LTCUSDT", interval=Client.KLINE_INTERVAL_1HOUR, lookback=1):
        def _get_change_percent():
            klines = self.client.get_klines(symbol=symbol, interval=interval, limit=lookback+1)
            
            if len(klines) < 2:
                return None

            old_price = float(klines[0][4])  # kapanış fiyatı
            new_price = float(klines[-1][4])

            change_percent = ((new_price - old_price) / old_price) * 100
            return round(change_percent, 2)

        return self._retry_with_new_proxy(_get_change_percent)
        
    def get_ohlcv(self, symbol="LTCUSDT", interval=Client.KLINE_INTERVAL_1MINUTE, limit=10):
        """Proxy rotasyonu ile mum verisi çekme"""
        def _get_data():
            klines = self.current_client.get_klines(
                symbol=symbol, 
                interval=interval, 
                limit=limit
            )
            return [
                {
                    "timestamp": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5])
                }
                for k in klines
            ]
        
        return self._retry_with_new_proxy(_get_data)

    def get_top_amount_usdt_pairs(self,amount):
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url)
        data = response.json()
        
        # Sadece USDT ile bitenleri al
        usdt_pairs = [item for item in data if item['symbol'].endswith('USDT') and float(item['quoteVolume']) > 0]

        # Hacme göre sırala (quoteVolume en yüksekten düşüğe)
        sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)

        # İlk 200 tanesini al
        top_symbols = [item['symbol'] for item in sorted_pairs[:amount]]

        return top_symbols
    
        #market_data >>  {
        #                   'symbol': 'LTCUSDT',
        #                   'base_asset': 'LTC', 
        #                   'quote_asset': 'USDT',
        #                   'price_change_percent': 0.372,
        #                   'high_price': 99.69, 
        #                   'low_price': 94.29, 
        #                   'volume': 545650.626, 
        #                   'quote_volume': 52807793.0429,
        #                   'last_price': 97.13,
        #                   'status': 'success'
        #                   }
   
   
    def get_market_data(self, symbol):
        def get_direction(val):
            if val is None:
                return "none"
            return "down" if val < 0 else "up"

        market_data = self.get_24h_stats(symbol)
        market_data["symbol"] = symbol

        market_data["price_change_percent_1H"] = self.get_change_percent(symbol, Client.KLINE_INTERVAL_1HOUR, 1)
        market_data["price_change_percent_1W"] = self.get_change_percent(symbol, Client.KLINE_INTERVAL_1DAY, 7)
        market_data["price_change_percent_1M"] = self.get_change_percent(symbol, Client.KLINE_INTERVAL_1DAY, 30)
        market_data["price_change_percent_3M"] = self.get_change_percent(symbol, Client.KLINE_INTERVAL_1DAY, 90)
        market_data["price_change_percent_6M"] = self.get_change_percent(symbol, Client.KLINE_INTERVAL_1DAY, 180)

        try:
            price_change_24h = float(market_data.get("price_change_percent", 0))
        except ValueError:
            price_change_24h = 0.0

        market_data["direction_1H"] = get_direction(market_data["price_change_percent_1H"])
        market_data["direction_1D"] = get_direction(price_change_24h)
        market_data["direction_1W"] = get_direction(market_data["price_change_percent_1W"])
        market_data["direction_1M"] = get_direction(market_data["price_change_percent_1M"])
        market_data["direction_3M"] = get_direction(market_data["price_change_percent_3M"])
        market_data["direction_6M"] = get_direction(market_data["price_change_percent_6M"])

        return market_data
    
    
    
    # def get_ohlcv(self, symbol="LTCUSDT", interval=Client.KLINE_INTERVAL_1MINUTE, limit=10):
    #     """Mum verisi: Açılış, Yüksek, Düşük, Kapanış, Hacim"""
    #     klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
       
    #     return [
    #         {
    #             "timestamp": k[0],
    #             "open": float(k[1]),
    #             "high": float(k[2]),
    #             "low": float(k[3]),
    #             "close": float(k[4]),
    #             "volume": float(k[5])
    #         }
    #         for k in klines
    #     ] 

    # def get_order_book(self, symbol="LTCUSDT", limit=5):
    #     """Order book verisi (en iyi alış/satış)"""
    #     order_book = self.client.get_order_book(symbol=symbol, limit=limit)
    #     return {
    #         "bids": order_book['bids'],  # [["fiyat", "miktar"]]
    #         "asks": order_book['asks'],
    #     }

    # def print_order_book(self,order_book):
    #     print("🔹 ORDER BOOK (Top 5):\n")
    #     print("BIDS (Alışlar):")
    #     for price, qty in order_book['bids']:
    #         print(f"  Fiyat: {price:>10}  Miktar: {qty}")

    #     print("\nASKS (Satışlar):")
    #     for price, qty in order_book['asks']:
    #         print(f"  Fiyat: {price:>10}  Miktar: {qty}")
                

# if __name__ == "__main__":
    



#     market = BinanceMarketData()

    # print("🔹 Son Fiyat:", market.get_latest_price("ETHUSDT"))
    # print("🔹 24h Bilgi:", market.get_24h_stats("ETHUSDT"))
    # print("🔹 Order Book:", market.get_order_book("ETHUSDT"))
    # print("🔹 24h Bilgi:", market.get_24h_stats('LTCUSDT'))
    ##--------------------------------------------------------------------------------------------------------
    # candle_sticks = market.get_ohlcv('LTCUSDT', interval=Client.KLINE_INTERVAL_15MINUTE, limit=7)
    # for mum in candle_sticks:
    #     # print(mum)
    #     print (datetime.fromtimestamp(mum["timestamp"] / 1000))
    #     print (f"open : {mum['open']}")
    #     print (f"high : {mum['high']}")
    #     print (f"low : {mum['low']}")
    #     print (f"close : {mum['close']}")
    #     print (f"volume : {mum['volume']}")
    #     print(10 * "--")
    ##--------------------------------------------------------------------------------------------------------
    # print(f"1h: {market.get_change_percent(symbol='LTCUSDT', interval=Client.KLINE_INTERVAL_1HOUR)}")  # 1 saatlik
    # print(f"1d: {market.get_change_percent(symbol='LTCUSDT', interval=Client.KLINE_INTERVAL_1DAY)}")  # 1 günlük
    # print(f"7d: {market.get_change_percent(symbol='LTCUSDT', interval=Client.KLINE_INTERVAL_1DAY, lookback=7)}") # 7 günlük
    # print(f"1mo: {market.get_change_percent(symbol='LTCUSDT', interval=Client.KLINE_INTERVAL_1DAY, lookback=30)}")  # 1 aylık
    
    # print("1 Saat:", market.get_change_percent("LTCUSDT", Client.KLINE_INTERVAL_1HOUR, 1))
    # print("1 Gün :", market.get_change_percent("LTCUSDT", Client.KLINE_INTERVAL_1DAY, 1))
    # print("1 Hafta:", market.get_change_percent("LTCUSDT", Client.KLINE_INTERVAL_1DAY, 7))
    # print("1 Ay:", market.get_change_percent("LTCUSDT", Client.KLINE_INTERVAL_1DAY, 30))
    # print("3 Ay:", market.get_change_percent("LTCUSDT", Client.KLINE_INTERVAL_1DAY, 90))
    # print("6 Ay:", market.get_change_percent("LTCUSDT", Client.KLINE_INTERVAL_1DAY, 180))
    
    # tarih = date.today()
    # yil_basi = date(tarih.year, 1, 1)
    # gecen_gun = (tarih - yil_basi).days + 1
    # input(gecen_gun)
    # print("Yıl Başından:", market.get_change_percent("LTCUSDT", Client.KLINE_INTERVAL_1DAY, gecen_gun))
    
    ##--------------------------------------------------------------------------------------------------------
    # print(market.get_price_changes_gecko(coin_id ="litecoin"))
    ##--------------------------------------------------------------------------------------------------------
      
    


     
 