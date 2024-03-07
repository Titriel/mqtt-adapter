from time import sleep, time as now 
from json import loads
from base64 import b64decode
from math import floor
from sseclient import SSEClient
from SML import check, set_time_offset, getTelegramm, pretty

class device:
  def __init__(self, config, topic, publisher):
    self.topic = topic
    self.publisher = publisher
    self.workerrunning = False
    self.syncmetertime = False
    self.sseworkerready = False
    self.c = config
    print("do init the device", config)

  def on_massage(self, topic, payload, retain):
    print("This is my worker", self.topic)
    sleep(2)
    print("Received message for topic", topic, ":", payload)
    if retain==1:
      print("This is a retained message")

  def worker(self):
    print("This is my worker", self.topic)
    while (self.workerrunning):
      self.publisher(self.topic, '{"Plug1":"OFF", "Plug2":"ON"}')
      sleep(2)
      self.publisher(self.topic, '{"Plug1":"ON", "Plug2":"OFF"}')
      sleep(2)
      #self.workerrunning = False   
    print("Stopping worker", self.topic)
    return True
  
  def sse_worker(self):
    self.sseworkerready = True
    try:
      messages = SSEClient('http://' + self.c.ip+ '/events', auth=(self.c.sseUser, self.c.ssePass))
      for msg in messages:
        if msg.event == "Serial0":
          jetzt = floor(now() + 0.5)
          Serial0data = loads(msg.data)
          Meterdata = b64decode(Serial0data["RxT"].encode('utf-8'))
          print(Meterdata)
          Telegramms = check(Meterdata)
          for Telegramm in Telegramms:
            print('**********Telegramm***********')
            print(Telegramm)
            print('**********Pretty***********')
            last_Telegramm = getTelegramm(Telegramm['Start'], Meterdata)
            pretty(last_Telegramm)
          if self.syncmetertime:
            print (jetzt)

        print(msg.id, msg.event, msg.data)
    except:
      self.sseworkerready = False