
import json
import requests
import asyncio
import telebot

# class pushbulletNotification:
    
#     def __init__(self,name) -> None:
#         with open("data.json") as file:
#             my_data = json.load(file)
#             self.api_key = my_data["pb_api_key"]
#             print(f"pb api key : {self.api_key}")
#         self.baslik = "Knight Online Pazar"
#         self.icerik = f"Lütfen {name}'den gelen PMlerinizi Kontrol ediniz"
    
#     def sendNotification(self):
        
#         pb = pushbullet.Pushbullet(self.api_key)
#         pb.push_note(self.baslik, self.icerik)
        
        

class TelegramNotification:
    def __init__(self):
        # Telegram bot token'ını başlatma
        # DİKKAT: Token'ı güvenli bir şekilde saklayın!
        TOKEN = "7496350035:AAHpflAN7NsFaZ_M5mttB_5rHXVIDfIHVRc"
        self.bot = telebot.TeleBot(TOKEN)
        
        # İzin verilen kullanıcı kimliklerini tutan liste
        self.user_ids = [7596065675]

    def start_handler(self, message):
        # Yeni bir kullanıcı /start komutunu çalıştırdığında
        user_id = message.from_user.id
        
        # Eğer kullanıcı daha önce listede değilse ekle
        if user_id not in self.user_ids:
            self.user_ids.append(user_id)
        
        # Kullanıcıya hoş geldin mesajı gönder
        self.bot.reply_to(message, "Merhaba! Bildirim botuna hoş geldiniz. Düzenli bildirimler alacaksınız.")

    def set_up_handlers(self):
        # Telegram bot için mesaj işleyicileri ayarlama
        @self.bot.message_handler(commands=['start'])
        def start(message):
            # /start komutu için handler'ı çağır
            self.start_handler(message)

    def send_notification(self, msg):
        # Kayıtlı tüm kullanıcılara bildirim gönderme
        for user_id in self.user_ids:
            try:
                # Her kullanıcıya mesaj gönder
                self.bot.send_message(user_id, msg)
            except Exception as e:
                # Herhangi bir hata durumunda hatayı yazdır
                print(f"Bildirim gönderilirken hata: {e}")

        




# Örnek kullanım (async olmayan senaryolar için)
# telegram_bot = telegramNotification()
# telegram_bot.send_message("Merhaba babuş, mesaj test ediliyor!")