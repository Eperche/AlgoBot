from flask import Flask, render_template, jsonify, request
from marketData import BinanceMarketData
from binance.client import Client
from concurrent.futures import ThreadPoolExecutor

# from webSocketData import BinanceWebSocket
import math
from talibAnalysis import TechnicalAnalyzer, SupportResistanceAnalyzer
import json, os

import pandas as pd
from datetime import datetime, timedelta
import threading
import time
import threading
from typing import Dict, Optional
from smartCache import SmartCacheManager
from handle_data import DataManager

from datetime import datetime, timedelta
import pygame
from notificationService import TelegramNotification

pygame.init()
pygame.mixer.init()
pygame.mixer.music.load("static/assets/sounds/cmon.mp3")

telegram_bot = TelegramNotification()

coin_sound_reset_times = {}

app = Flask(__name__)

market = BinanceMarketData()
analyzer = TechnicalAnalyzer(market)

 

# COINS = (market.get_top_amount_usdt_pairs(100))

# coins_list = []
# with open("binance_common_cryptos.json", "r", encoding="utf-8") as f:
#     #     Sadece kripto para isimlerini yazdır
#     data = json.load(f)
#     print(f"Toplam kripto para sayısı: {len(data['cryptos'])}")

#     for crypto in data["cryptos"]:

#         coins_list.append(f"{crypto['symbol']}USDT")

# COINS = coins_list[:100]  # İlk 100 kripto para sembolünü alır

COINS = ["BTCUSDT", "ETHUSDT", "XRPUSDT","BNBUSDT","SOLUSDT","TRXUSTD","ADAUSDT","XLMUSDT","LINKUSDT","AVAXUSDT","LTCUSDT"]

# ['BTCUSDT', 'ETHUSDT', 'USDCUSDT', 'SOLUSDT', 'PEPEUSDT'...


# Cache manager instance
cache_manager = SmartCacheManager(analyzer=analyzer, COINS=COINS)
data_manager = DataManager(cache_manager=cache_manager,COINS=COINS,analyzer=analyzer)

def fetch(symbol):
    return market.get_market_data(symbol)




@app.route("/")
def mainPage():
    # market_data_list = [market.get_market_data(symbol) for symbol in COINS]
    with ThreadPoolExecutor(max_workers=25) as executor:
        market_data_list = list(executor.map(fetch, COINS))

    return render_template("starter_table.html", market_data_list=market_data_list)


# @app.route('/websocket_klines')
# def mainPage():

#     binance_ws = BinanceWebSocket(on_data_callback=mainPage)
#     binance_ws.start_ticker_stream("btcusdt")


@app.route("/home")
def home():
    # market_data_list = [market.get_market_data(symbol) for symbol in COINS]
    with ThreadPoolExecutor(max_workers=50) as executor:
        market_data_list = list(executor.map(fetch, COINS))
    print("hazır")
    return render_template("starter.html", market_data_list=market_data_list)


@app.route("/api/market-data")
def api_market_data():

    with ThreadPoolExecutor(max_workers=15) as executor:
        data = list(executor.map(fetch, COINS))

    return jsonify(data)


@app.route("/tradable-coins")
def tradable_coins_page():
    return render_template("tradable_analysis.html")


@app.route("/api/tradable-coins")
def tradable_coins():
    timeframe = request.args.get("timeframe", "1h")
    include_trend = (
        request.args.get("include_trend", "true").lower() == "true"
    )  # Varsayılan true

    force_refresh = request.args.get("force", "false").lower() == "true"
    
    # Yeni parametre - 1d filtrelemesi uygulansın mı?
    apply_daily_filter = request.args.get("daily_filter", "true").lower() == "true"
    
    print(
        f"[API] İstek: {timeframe} || Trend: {include_trend} || Force: {force_refresh} || {datetime.now()}"
    )

    cache_response, should_continue = data_manager.check_and_handle_cache(
        timeframe=timeframe, include_trend=include_trend, force_refresh=force_refresh
    )

    # Eğer cache'den döndürülecek veri varsa, direkt döndür
    if not should_continue:
        current_timeframe_data = cache_response
    else:
        # Cache yoksa veya force refresh varsa - gerçek zamanlı analiz
        results = data_manager.real_time_analysis(timeframe=timeframe)
        current_timeframe_data = results
    
    # Eğer daily filter isteniyorsa
    if apply_daily_filter:
        # Dictionary döndürüyor artık
        filtered_coins = data_manager.get_filtered_symbols(timeframe)
        
        # Her timeframe için hazırlık
        timeframe_symbol_maps = {}  # tf -> {symbol: reason}
        timeframe_symbol_sets = {}  # tf -> {symbol1, symbol2, ...}
        
        for tf, response_filter in filtered_coins.items():
            filtered_symbols = [item["symbol"] for item in response_filter]
            process_filtered_symbols(filtered_symbols, tf)
            
            # Hızlı lookup için hazırla
            timeframe_symbol_maps[tf] = {item["symbol"]: item["reason"] for item in response_filter}
            timeframe_symbol_sets[tf] = set(filtered_symbols)
        
        # Öncelik sırası (istediğin gibi değiştir)
        priority_order = ["4h", "1h", "30m", "15m", "1d"]
        
        # Mevcut timeframe verisinden sadece filtrelenmiş sembolleri tut
        final_data = []
        processed_symbols = set()  # Duplicate kontrolü
        
        for coin_data in current_timeframe_data:
            symbol = coin_data.get("symbol")
            
            # Eğer bu symbol zaten işlendiyse skip et
            if symbol in processed_symbols:
                continue
                
            coin_data_copy = coin_data.copy()  # Orijinal veriyi korumak için
            added = False
            
            # Öncelik sırasına göre kontrol et
            for priority_tf in priority_order:
                if priority_tf in timeframe_symbol_sets and symbol in timeframe_symbol_sets[priority_tf]:
                    coin_data_copy["reason"] = timeframe_symbol_maps[priority_tf][symbol]
                    coin_data_copy["filter_source"] = priority_tf
                    final_data.append(coin_data_copy)
                    processed_symbols.add(symbol)
                    print(f"✅✅ {symbol} - Final data'ya eklendi ({priority_tf})")
                    added = True
                    break
            
            # Eğer öncelikli timeframe'lerde yoksa, diğerlerini kontrol et
            if not added:
                for tf in timeframe_symbol_sets:
                    if tf not in priority_order and symbol in timeframe_symbol_sets[tf]:
                        coin_data_copy["reason"] = timeframe_symbol_maps[tf][symbol]
                        coin_data_copy["filter_source"] = tf
                        final_data.append(coin_data_copy)
                        processed_symbols.add(symbol)
                        print(f"✅✅ {symbol} - Final data'ya eklendi ({tf})")
                        break
        
        print(
            f"[FILTER] {timeframe} timeframe: {len(current_timeframe_data)} coindan {len(final_data)} tanesi döndürüldü"
        )
        return jsonify(final_data)

    # Filtreleme istenmiyorsa tüm veriyi döndür
    return jsonify(current_timeframe_data)
@app.route("/technical-analysis")
def technical_analysis_page():
    return render_template("technical_analysis.html")


# Flask route ekle


@app.route("/api/technical-analysis")
def technical_analysis():
    timeframe = request.args.get("timeframe", "1h")
    include_trend = (
        request.args.get("include_trend", "true").lower() == "true"
    )  # Varsayılan true

    force_refresh = request.args.get("force", "false").lower() == "true"
    print(
        f"[API] İstek: {timeframe} || Trend: {include_trend} || Force: {force_refresh} || {datetime.now()}"
    )

    cache_response, should_continue = data_manager.check_and_handle_cache(
        timeframe=timeframe, include_trend=include_trend, force_refresh=force_refresh
    )

    # Eğer cache'den döndürülecek veri varsa, direkt döndür
    if not should_continue:
        return jsonify(cache_response)

    # Cache yoksa veya force refresh varsa - gerçek zamanlı analiz

    results = data_manager.real_time_analysis(timeframe=timeframe)

    return jsonify(results)


@app.route("/api/technical-analysis/<symbol>")
def technical_analysis_symbol(symbol, timeframe="1h", limit=200):
    """Tek bir sembol için teknik analiz yapar."""
    try:
        analysis = analyzer.analyze_symbol(symbol, interval=timeframe, limit=limit)
        return data_manager.convert_to_json_serializable(analysis)
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None


@app.route("/api/cache-status")
def cache_status():
    """Cache durumunu görüntüle"""
    status = {}

    for timeframe in SmartCacheManager.CACHE_CONFIG.keys():
        with SmartCacheManager.cache_locks[timeframe]:
            cache_data = SmartCacheManager.cache_storage[timeframe]
            config = SmartCacheManager.CACHE_CONFIG[timeframe]

            status[timeframe] = {
                "last_update": (
                    cache_data["last_update"].isoformat()
                    if cache_data["last_update"]
                    else None
                ),
                "symbols_count": len(cache_data["data"]),
                "is_updating": cache_data["is_updating"],
                "is_fresh": cache_manager.is_cache_fresh(timeframe),
                "needs_update": cache_manager.should_update_cache(timeframe),
                "config": config,
            }

    return jsonify(status)


@app.route("/api/force-update/<timeframe>")
def force_update(timeframe):
    """Manuel cache güncelleme"""
    if timeframe not in SmartCacheManager.CACHE_CONFIG:
        return jsonify({"error": f"Timeframe {timeframe} desteklenmiyor"}), 400

    print(f"[FORCE] Manuel güncelleme: {timeframe}")
    cache_manager.update_cache_async(timeframe)

    return jsonify(
        {
            "message": f"{timeframe} cache güncellemesi başlatıldı",
            "timestamp": datetime.now().isoformat(),
        }
    )

def process_filtered_symbols(filtered_symbols,tf):
    current_time = datetime.now()
    
    if len(filtered_symbols) > 0:
        for symbol in filtered_symbols:
            # Bu coin için daha önce bir reset zamanı var mı kontrol et
            if symbol not in coin_sound_reset_times:
                coin_sound_reset_times[symbol] = datetime.min  # İlk seferinde hemen çalsın
            
            # Bu coin için bekleme süresi doldu mu kontrol et
            if coin_sound_reset_times[symbol] < current_time:
                # Ses çal ve bildirim gönder
                pygame.mixer.music.play()
                telegram_bot.send_notification(f"Yeni {tf} filtrelenmiş sembol bulundu: {symbol}")
                
                print(f"[SOUND] Yeni  {tf} > filtrelenmiş sembol: {symbol}")
                
                # Bu coin için 5 dakika bekleme süresi ayarla
                coin_sound_reset_times[symbol] = current_time + timedelta(minutes=60)
                
  
if __name__ == "__main__":
    # Sadece ana process'te initialize et (çift başlatmayı önler)
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        cache_manager.initialize_cache()

    try:
        app.run(debug=True, threaded=True)
    finally:
        cache_manager.is_running = False
