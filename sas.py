import time
from math import floor
from urllib.parse import quote_plus
from hmac import HMAC
from hashlib import sha256
from base64 import b64encode


def sas(sbNamespace,sbEntityPath,sharedAccessKey,sharedAccessKeyName):
   uri = "http://" + sbNamespace + ".servicebus.windows.net/" + sbEntityPath

   encodedResourceUri = quote_plus(uri)
   expireInSeconds = floor( time.time() + 60 + .5 )
   plainSignature = encodedResourceUri + "\n" + str(expireInSeconds)

   plainSignature = plainSignature.encode('utf-8')
   signed_hmac_sha256 = HMAC(sharedAccessKey,plainSignature,sha256)
   digest = signed_hmac_sha256.digest()
   encoded_digest = b64encode(digest)
   return "SharedAccessSignature sig=%s&se=%s&skn=%s&sr=%s" % (quote_plus(encoded_digest),expireInSeconds, sharedAccessKeyName, encodedResourceUri)

