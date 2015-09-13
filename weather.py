from urllib.request import urlopen
from json import loads
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def weather():
   url = urlopen("https://api.forecast.io/forecast/<your forecast.io key here>/37.8267,-122.423", context=ctx)
   fc = url.read().decode('utf-8')
   url.close()
   jfc = loads(fc)

   return jfc
