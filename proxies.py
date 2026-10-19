class Proxy:
    proxy_index = 0  # Statik değişken (tüm nesneler için ortak)

    def __init__(self):
        
        proxies_block4 = [
                          None,
            "socks5h://scxorka:dac626@isp.livaproxy.com:21236",
            "socks5h://scxorka:dac626@isp.livaproxy.com:21069",
            "socks5h://scxorka:dac626@isp.livaproxy.com:21190",
            
            "socks5h://scxorka:dac626@isp.livaproxy.com:13040",
            "socks5h://scxorka:dac626@isp.livaproxy.com:13055",
            "socks5h://scxorka:dac626@isp.livaproxy.com:13177",
            "socks5h://scxorka:dac626@isp.livaproxy.com:15104",
            "socks5h://scxorka:dac626@isp.livaproxy.com:15007",
            "socks5h://scxorka:dac626@isp.livaproxy.com:15111",
                          
                          ]
        self.proxies = proxies_block4
        
        
 
 
    @classmethod
    def increment_proxy_index(cls):
        cls.proxy_index += 1  # Statik değişkeni artır

    def proxy_generator(self):
        if self.__class__.proxy_index >= len(self.proxies):
            self.__class__.proxy_index = 0  # Liste sonuna geldiyse başa sar

        print(f"Denenen proxy index: {self.__class__.proxy_index}")
        
        prxy = self.proxies[self.__class__.proxy_index]   
        self.increment_proxy_index()

        proxy_dict = {
            "http": prxy,
            "https": prxy
        }

        return proxy_dict