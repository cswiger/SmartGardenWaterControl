import urllib.request
import json
from urllib.parse import urljoin
from urllib.error import URLError
from urllib.error import HTTPError
import sas
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def postazq(postdata):
   # put your azure sb queue details here
   sbNamespace = 'nameSpace'
   sbEntityPath = 'EntityPath'
   sharedAccessKey = b'<your Azure key here>'
   sharedAccessKeyName = 'your Azure key name here'

   environment = 'https://yourname.servicebus.Windows.net'
   sessionUrl = urljoin(environment,'/yourname/messages')

   data = json.dumps(postdata).encode('utf-8')

   headers = {}
   headers['Content-type'] = "application/atom+xml;type=entry;charset=utf-8"
   headers['Authorization'] = sas.sas(sbNamespace,sbEntityPath,sharedAccessKey,sharedAccessKeyName)
   req = urllib.request.Request(sessionUrl, data, headers)
   try:
      response = urllib.request.urlopen(req, context=ctx)
      return response.status
   except HTTPError as httperror:
      return httperror.reason
   except URLError as urlerror:
      return urlerror.reason

