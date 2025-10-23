from time import sleep, time as now
from datetime import date
from datetime import timedelta
from json import dumps
from math import floor
from requests import get, exceptions
from requests.auth import HTTPBasicAuth
from os import path, getcwd
from sys import path as PATH
PATH.append(path.join(getcwd(), "script"))
PATH.append(path.join(getcwd(), "devices", "TibberLocal"))
import logging
from logsetup import d2s, pretty as logpretty
from SML import check, set_time_offset, getTelegramm, pretty
import traceback

logger = logging.getLogger()
logpretty()

class device:
  def __init__(self, config, topic, publisher):
    self.topic = topic
    self.publisher = publisher
    self.buffer = []
    self.workerrunning = False
    self.syncmetertime = False
    self.c = config
    self.day = date.today() - timedelta(days = 2)
    self.metrics = 'http://' + self.c['ip'] + '/metrics.json?node_id=' + self.c['node_id']
    self.data = 'http://' + self.c['ip'] + '/data.json?node_id=' + self.c['node_id']
    self.auth = HTTPBasicAuth(self.c['User'], self.c['Pass'])
    logger.info("do init the device %s", d2s(config))

  def on_busy(self, topic, payload, retain):
    self.buffer.append({"topic": topic, "payload": payload, "retain": retain})

  def on_massage(self, topic, payload, retain):
    if len(self.buffer) > 0:
      self.buffer.append({"topic": topic, "payload": payload, "retain": retain})    
    while True:
      if len(self.buffer) > 0:
        temp = self.buffer.pop(0)
        topic = temp["topic"]
        payload = temp["payload"]
        retain = temp["retain"]

      logger.info("Received message for topic %s: %s", topic, payload)
      if retain==1:
        logger.info("This is a retained message")
      if len(self.buffer) == 0:
        return
      
  def worker(self):
    logger.info("This is my worker %s", self.topic)

    hadtried = False
    lastmsg = b''
    lastdecoded = {}
    loops = 30
    while (self.workerrunning):
      loops += 1
      if loops > 30:
        loops = 0
        try:
          r = get(self.metrics, auth=self.auth, timeout=60)
          self.publisher(self.topic + 'status/', dumps(r.json()['node_status']))
        except Exception as error:
          logger.warning("Unexpected error %s ocures.", type(error).__name__)
          traceback.print_exc()          
      try:
        message = get(self.data, auth=self.auth, timeout=60)
        if message.content == lastmsg:
          state = None
          logger.info("Old massage.")
          sleep(0.5)
        else:
          lastmsg = message.content
          state = True
      except Exception as error:
        logger.warning("Unexpected error %s ocures.", type(error).__name__)
        traceback.print_exc()
        state = False
        sleep(5)
        logger.warning("No responce from Bridge.")

      if state == hadtried:
        logger.warning("No Stream from meter.")
        lastdecoded['online'] = False
        self.publisher(self.topic, dumps(lastdecoded))
      elif state:
        try:
          if not self.workerrunning:
            break
          if message.content:
            jetzt = floor(now() + 0.5)
            Meterdata = message.content
            #print(Meterdata)
            Telegramms = check(Meterdata)
            for Telegramm in Telegramms:
              logger.info("Telegram: %s", d2s(Telegramm))
              last_Telegramm = getTelegramm(Telegramm['Start'], Meterdata)
              #print(last_Telegramm)
              lastdecoded = last_Telegramm['decoded']
            if self.day != date.today():
              set_time_offset(lastdecoded['Server_ID']['bytes'], now() - lastdecoded['actSensorTime']['raw'])
              self.day = date.today()
            del lastdecoded['Server_ID']['bytes']
            lastdecoded['actSensorTime']['hr'] = str(lastdecoded['actSensorTime']['hr']).split('.')[0]
            lastdecoded['online'] = True
            self.publisher(self.topic, dumps(lastdecoded))
          else:
            logger.info(message.text)
        except TimeoutError:
          logger.warning("No Data from meter while the last %s seconds.", self.c["ssetimeout"])
        except exceptions.HTTPError:
          logger.warning("HTTP Error by establishing the SSE connect.")        
        except Exception as error:
          logger.warning("Unexpected error %s ocures.", type(error).__name__)
          traceback.print_exc()
        hadtried = False

    logger.info("Stopping worker %s", self.topic)
    return True