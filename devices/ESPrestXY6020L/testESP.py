from os import path, getcwd
from sys import path as PATH
PATH.append(path.join(getcwd(),"script"))
import logging
from logsetup import d2s, pretty
import ESPrest

logger = logging.getLogger()
pretty()
#logger.setLevel(logging.DEBUG)

def getds18b20():
  ESPmeter.focall('ds18b20', 'POST', {"unit": "C[elsius]"})
  if (ESPmeter.responce.status_code == 428) and not ESPmeter.responce.json()['GPIO2used']:
    ESPmeter.focall('ds18b20', 'PUT', {"enable": True})
    ESPmeter.focall('ds18b20', 'POST', {"unit": "C[elsius]"})
  elif (ESPmeter.responce.status_code > 201):
    logger.info("%s", d2s(ESPmeter.responce.json()))
  if ESPmeter.responce.status_code < 202:
    for key in ESPmeter.responce.json()['data']:
      if key != "msg":
        logger.info("%s %s von Device: %s", ESPmeter.responce.json()['data'][key], ESPmeter.responce.json()['unit'], key)

def mkreadyformeter(baudrate, loopback=False):
  Ser0set = {"baud": baudrate, "config": "8N1", "loopback": False, "debug": False, "outBufSize": 1000}
  Ser1set = {"useTxT1": True, "baud": baudrate, "config": "8N1", "loopback": loopback, "debug": False, "outBufSize": 1000}
  ESPmeter.focall('serial')
  if (ESPmeter.responce.json()["Serial0"]["TxTmoved"]):
    ESPmeter.focall('serial', 'PATCH', {"move": "TxT"})
  if (ESPmeter.responce.json()["Serial0"]["swaped"]):
    ESPmeter.focall('serial', 'PATCH', {"move": "swap"})    
  if not ESPmeter.responce.json()["Serial1"]["enabeled"] and not ESPmeter.responce.json()["GPIO2used"]:
    ESPmeter.focall('serial', 'PATCH', Ser1set)
    if ESPmeter.responce.status_code != 201:
      logger.error("Status: %s -> Msg: %s", ESPmeter.responce.status_code, ESPmeter.responce.json()["msg"])
      return False
  elif not ESPmeter.responce.json()["Serial1"]["enabeled"]:
    logger.error("GPIO2 is used by another component.")
    return False
  if (ESPmeter.responce.json()["Serial1"]["baud"] != baudrate) or (ESPmeter.responce.json()["Serial1"]["loopback"] != loopback):
    ESPmeter.focall('serial', 'PATCH', Ser1set)
    if ESPmeter.responce.status_code != 201:
      logger.error("Status: %s -> Msg: %s", ESPmeter.responce.status_code, ESPmeter.responce.json()["msg"])
      return False    
  if ((ESPmeter.responce.json()["Serial0"]["baud"] != baudrate) or
      ESPmeter.responce.json()["Serial0"]["loopback"] or
      (ESPmeter.responce.json()["outBufSize"] != 1000)):
    ESPmeter.focall('serial', 'PATCH', Ser0set)
    if ESPmeter.responce.status_code != 201:
      logger.error("Status: %s -> Msg: %s", ESPmeter.responce.status_code, ESPmeter.responce.json()["msg"])
      return False    
  if not ESPmeter.responce.json()["SSE"]:
    ESPmeter.focall('', 'PUT', {})
    if ESPmeter.responce.status_code != 201:
      logger.error("Status: %s -> Msg: %s", ESPmeter.responce.status_code, ESPmeter.responce.json()["msg"])
      return False
  return True

  logger.info("%s", d2s(ESPmeter.responce.json()))
    
ESPmeter = ESPrest.set('192.168.173.163', 'admin@admin')
ESPmeter.open()
mkreadyformeter(9600, False)
ESPmeter.close()