#!/usr/local/bin/python3
import urllib.request
from urllib.parse import urljoin
from urllib.error import URLError
from urllib.error import HTTPError
from datetime import datetime
import sas

sbNamespace = 'nameSpace'
sbEntityPath = 'EntityPath'
sharedAccessKey = b'<your Azure key here>'
sharedAccessKeyName = 'your Azure key name here'

environment = 'https://yourname.servicebus.Windows.net'
sessionUrl = urljoin(environment,'/yourname/messages/head')

headers = {}
headers['Authorization'] = sas.sas(sbNamespace,sbEntityPath,sharedAccessKey,sharedAccessKeyName)

req = urllib.request.Request(sessionUrl,headers=headers,method='DELETE')
response = urllib.request.urlopen(req)

if (response.status == 200):
  data = response.read()
  event = eval(data.decode('utf-8'))
  for key, value in event.items():
    print(key, datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S'))
else:
  print("Got status " + str(response.status))


