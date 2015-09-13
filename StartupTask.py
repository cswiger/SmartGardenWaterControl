# for bgweb
import threading
import http.server
from cgi import parse_header, parse_multipart
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler
from time import sleep
# for sched
import sched, time
from datetime import datetime
# for Azure queue
import postazq
# for weather factor
import weather
# for gpio control
import _wingpio as gpio

valve_pin = 5
gpio.setup(valve_pin, gpio.OUT, gpio.PUD_OFF, gpio.HIGH)

# Globals for state
gPostVars = None

# Initialize an empty schedule with 10 (0 thru 9) events
schedule = {}
for key in range(10):
  schedule[key] = {"timeofday":"XX:XX","dayofweek":"X","duration":"X"}


# create the global table for the page
table = "<TABLE border=1><TR><TD>Event</TD><TD>Day of week</TD><TD>Time of day</TD><TD>Duration</TD></TR>"
for key in schedule:
  if(schedule[key]["dayofweek"] != 'X'):
    table += "<TR><TD>%s</TD><TD>%s</TD><TD>%s</TD><TD>%s</TD></TR>" % (key, schedule[key]["dayofweek"], schedule[key]["timeofday"],schedule[key]["duration"])
table += "</TABLE><BR>"

# helper page table to map days of the week to numeric since python datetime dayofweek is oddly unintuitive
dowTable = "<TABLE border=1><TR><TD>Day of week</TD><TD>Code</TD><TR><TR><TD>Monday</TD><TD>0</TD></TR><TR><TD>Tuesday</TD><TD>1</TD><TR><TD>Wednesday</TD><TD>2</TD></TR><TD>Thursday</TD><TD>3</TD></TR><TR><TD>Friday</TD><TD>4</TD></TR><TR><TD>Saturday</TD><TD>5</TD></TR><TD>Sunday</TD><TD>6</TD></TR></TABLE>"

# state of the gpio controlled water valve
gWateringStatus = False

# End globals

s = sched.scheduler(time.time, time.sleep)

# A request handler for the http server
class RequestHandler(BaseHTTPRequestHandler):
  def do_HEAD(self):
    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.end_headers()

  def parse_POST(self):
    global gPostVars
    ctype, pdict = parse_header(self.headers['content-type'])
    if ctype == 'multipart/form-data':
      postvars = parse_multipart(self.rfile, pdict)
      gPostVars = postvars
    elif ctype == 'application/x-www-form-urlencoded':
      length = int(self.headers['content-length'])
      postvars = parse_qs(self.rfile.read(length),keep_blank_values=1)
      gPostVars = postvars
    else:
      postvars = {}
    return postvars

  def do_POST(self):
    global gWateringStatus
    # check form action to see what was posted, update schedule or cancel any watering currently going on
    if (self.path == '/'):
      postvars = self.parse_POST()
      self.wfile.write("<HTML><HEAD><META http-equiv='refresh' content='1;URL=/'></HEAD><BODY><H1>Updating...</H1></BODY></HTML>".encode("utf-8"))
    elif (self.path == '/stop'):         # the STOP button was pressed
      gWateringStatus = "Canceled"
      self.wfile.write("<HTML><HEAD><META http-equiv='refresh' content='1;URL=/'></HEAD><BODY><H1>Updating...</H1></BODY></HTML>".encode("utf-8"))

  def do_GET(self):
    global table, gWateringStatus
    self.wfile.write(bytes("<html><head><title>Garden Water Controller</title></head><body>", "utf-8"))
    # display the watering status and a STOP button if it is on
    if ((gWateringStatus==True) and (gWateringStatus != "Canceled")):
       self.wfile.write(bytes("Watering: ON<BR>","utf-8"))
       self.wfile.write(bytes("<FORM action='/stop' method='POST'><input type='submit' value='Stop'></FORM><BR><BR>","utf-8"))
    else:
       self.wfile.write(bytes("Watering: OFF<BR><BR>","utf-8"))
    # print the current watering schedule
    self.wfile.write(bytes("Existing events<BR>","utf-8"))
    self.wfile.write(bytes(table,"utf-8"))
    # form to update the schedule
    self.wfile.write(bytes("<p>Enter new schedule details</p>", "utf-8"))
    self.wfile.write(bytes("<form action='/' method='POST'>", "utf-8"))
    self.wfile.write(bytes("<BR>Watering ID (0-9): ", "utf-8"))
    self.wfile.write(bytes("<input type='text' size='2' name='id' value='0'>", "utf-8"))
    self.wfile.write(bytes("<BR><BR>", "utf-8"))
    self.wfile.write(bytes(dowTable, "utf-8"))
    self.wfile.write(bytes("<BR>Day of week: ", "utf-8"))
    self.wfile.write(bytes("<input type='text' size='5' name='dow' value='0123456'>", "utf-8"))
    self.wfile.write(bytes("<BR>Time of day (24hr): ", "utf-8"))
    self.wfile.write(bytes("<input type='text' size='5' name='tod' value='5:30'>", "utf-8"))
    self.wfile.write(bytes("<BR>Duration (minutes): ", "utf-8"))
    self.wfile.write(bytes("<input type='text' size='5' name='dur' value='30'>", "utf-8"))
    self.wfile.write(bytes("<input type='submit' value='Submit'>", "utf-8"))
    self.wfile.write(bytes("</body></html>", "utf-8"))


# run the webserver in a background thread with access to global variables
httpd = http.server.HTTPServer(("", 8800), RequestHandler)
httpd_thread = threading.Thread(target=httpd.serve_forever)
httpd_thread.setDaemon(True)
httpd_thread.start()

# called with duration argument when a scheduled watering event is due
# This is where we can also check the weather and adjust the duration down or off depending on the 
# weather probability of precip forecast
def waterCycle(t):
    global gWateringStatus
    now = time.time()
    print("watering, gpio on at " + str(now))
    gpio.output(valve_pin, gpio.LOW)
    # post ON time to Azure Queue
    postdata = {'ON':''}
    postdata['ON'] = now
    print(postazq.postazq(postdata))
    gWateringStatus = True
    # get weather forecast 
    jfc = weather.weather()
    # adjust duration down by prediction of rain
    duration = t * (1. - jfc["hourly"]["data"][0]["precipProbability"])
    print("watering for " + str(duration) + " seconds")
    then = time.time() + duration
    while ( (gWateringStatus == True) and (time.time() < then ) ):      # in case watering is canceled by the STOP button
      updateSched()
      sleep(1)
    now = time.time()
    print("Done watering, gpio off " + str(now))
    gpio.output(valve_pin, gpio.HIGH)
    # post OFF time to Azure Queue
    postdata = {'OFF':''}
    postdata['OFF'] = now
    print(postazq.postazq(postdata))
    if ( gWateringStatus == "Canceled" ):	# if canceled, wait a minute before resuming normal so another cycle doesn't kick off 
        then = time.time() + 60
        while ( time.time() < then ):
           updateSched()
           sleep(1)
    gWateringStatus = False

# datetime weekday()    Return the day of the week as an integer, where Monday is 0 and Sunday is 6.
def checkSched():
  global schedule
  now = time.time()
  # loop over the entire schedule
  for i in range(len(schedule)):
    # loop over dayofweek entries
    for j in range(len(schedule[i]["dayofweek"])):
      # if any dayofweek entry is NOT a blank schedule
      if ( schedule[i]["dayofweek"][j] != 'X' ):
        # and the dayofweek entry matches today
        if ( int( schedule[i]["dayofweek"][j] ) == datetime.fromtimestamp(now).weekday() ):
          # and the hour part of timeofday matches now
          if ( int( schedule[i]["timeofday"].split(':')[0] ) == datetime.fromtimestamp(now).hour ):
            # and the minute part of timeofday matches now
            if ( int( schedule[i]["timeofday"].split(':')[1] ) == datetime.fromtimestamp(now).minute ):
              print("it's time to water!")
              # call waterCycle function with duration from schedule
              waterCycle(int(schedule[i]["duration"])*60)  # duration in minutes


def updateSched():
  global schedule, gPostVars, table
  if (gPostVars != None):
    # all form elements must be filled in 
    if ( (gPostVars[b'id'][0] != b'') and (gPostVars[b'tod'][0] != b'') and (gPostVars[b'dow'][0] != b'')):
      # make sure the id is in range
      if ( ( int(gPostVars[b'id'][0].decode("utf-8")) < 10 ) and ( int(gPostVars[b'id'][0].decode("utf-8")) >= 0) ):
        id = int(gPostVars[b'id'][0].decode("utf-8"))
        # prolly should sanitize these too but for now - if not in format no water!  As it is they are
        # free format strings and bytes that just happen to be interpreted as day of week with 0 = Monday
	      # and time of day - if there is the ':' missing there it'll cause an error of not trapped
        tod = gPostVars[b'tod'][0].decode("utf-8")
        if ( tod.find(':') != -1 ):      # tod must have a colon ':' or it breaks the script
           dow = gPostVars[b'dow'][0].decode("utf-8")
           dur = gPostVars[b'dur'][0].decode("utf-8")
           schedule[id]['timeofday'] = tod
           schedule[id]['dayofweek'] = dow
           schedule[id]['duration'] = dur
           table = "<TABLE border=1><TR><TD>Event</TD><TD>Day of week</TD><TD>Time of day</TD><TD>Duration</TD></TR>"
           for key in schedule:
             if(schedule[key]["dayofweek"] != 'X'):
               table += "<TR><TD>%s</TD><TD>%s</TD><TD>%s</TD><TD>%s</TD></TR>" % (key, schedule[key]["dayofweek"], schedule[key]["timeofday"],schedule[key]["duration"])
           table += "</TABLE><BR>"
        gPostVars = None

def loop():
  global schedule,table,gPostVars
  while True:
    updateSched()
    s.enter(1,1,checkSched,())
    s.run()

loop()

