import paho.mqtt.client as mqtt
from os import path, getcwd
from sys import modules as devlib
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader, module_from_spec
from types import ModuleType
from typing import Any, Union
from json import load
from threading import Thread
from time import sleep
from config import config

internal = {"command": "", "worker": {}}
CONFIG = config()

def import_device(name: str) -> ModuleType:
  """
  Imports or get the divice module by the name.
  - The module must be in ./devices/<name>/main.py.
  - The name is also taken for register the module by this name.
  - The divice module will be also executed by loading the first time.

  Args:
    name (str): Divice module name and the folder name where the main.py of the divice module is placed.

  Returns:
    ModuleType: The requested device module
  """
  try:
    return devlib[name]
  except KeyError:
    pass
  print(path.join(getcwd(),"devices", name, "main.py"))
  loader = SourceFileLoader(name, path.join(getcwd(),"devices", name, "main.py"))
  spec = spec_from_loader(name, loader)
  try:
    module = module_from_spec(spec)
    devlib[name] = module
    spec.loader.exec_module(module)
    return module
  finally:
    pass

def formatsc(subcribtion: Union[str, list]) -> list:
  """
  Normalize a subcribtion.

  Args:
    subcribtion (str, list): e.g. "/home/myitem/, 0" or ["/home/myitem/", 0] or [[...], [...]]

  Returns:
    list: A list of lists of subcribtions e.g. [["/home/myitem/", 0], [...]]
  """
  if type(subcribtion) is list:
    if type(subcribtion[0]) is list:
      return subcribtion
    if len(subcribtion) == 2:
      return [subcribtion]
  elif type(subcribtion) is str:
    parts = subcribtion.replace(' ','').split(',')
    if len(parts) == 1:
      parts.append(0)
    if len(parts) == 2:
      parts[1] = int(parts[1])
      return [parts]
  print("Unabel to interpret subscription.")
  return []

def on_connect(client, userdata, flags, return_code):
  if return_code == 0:
    print("connected")
    client.subscribe(internal["subscribe"])        
  else:
    print("could not connect, return code:", return_code)
    client.failed_connect = True

def on_command(client, userdata, message):
  internal["command"] = str(message.payload.decode("utf-8"))

def on_message(client, userdata, message):
  if message.topic in internal["subscribtions"]:
    for name in internal["subscribtions"][message.topic]:
      temp = Thread(target=internal["items"][name].on_massage, args=(message.topic, str(message.payload.decode("utf-8")), message.retain))
      temp.start()

if "clientname" in CONFIG:
  internal["clientname"] = CONFIG["clientname"]
else:
  internal["clientname"] = "clientadapter"
client = mqtt.Client(internal["clientname"])
if "broker" in CONFIG:
  if ("username" in CONFIG["broker"]) and ("password" in CONFIG["broker"]):
    client.username_pw_set(username=CONFIG["broker"]["username"], password=CONFIG["broker"]["password"])

  if "items" in CONFIG:
    internal["subscribe"] = [["/adapter/" + internal["clientname"] + "/command/", 0]]
    internal["items"] = {}
    internal["subscribtions"] = {}
    for item in CONFIG["items"]:
      if "config" not in item:
          tempfile = path.join(getcwd(),"config", item["name"] + ".json")
          if path.exists(tempfile):
            with open(tempfile,'r') as file:
              item = load(file)
      internal["items"][item["name"]] = import_device(item["device"]).device(item["config"], item["topic"], client.publish)
      subscribe = formatsc(item["subscribe"])
      internal["subscribe"] += [v for v in subscribe if v not in internal["subscribe"]]
      #internal["subscribe"] = dict.fromkeys(internal["subscribe"] + subscribe)
      for subscribtion in subscribe:
        if subscribtion[0] in internal["subscribtions"]:
          if item["name"] not in internal["subscribtions"][subscribtion[0]]:
            internal["subscribtions"][subscribtion[0]].append(item["name"])
        else:
          internal["subscribtions"][subscribtion[0]] = [item["name"]]
  else:
    print("Es sind keine Items configuriert")
    exit    

  if "hostname" in CONFIG["broker"]:
    client.connect(CONFIG["broker"]["hostname"])
  else:
    print("Es wurde kein Hostname für den Broker angegeben")
    exit

  client.on_connect = on_connect
  client.on_message = on_message
  client.message_callback_add(internal["subscribe"][0][0], on_command)
  client.failed_connect = False

  for item in CONFIG["items"]:
    if not internal["items"][item["name"]].workerrunning:
      internal["worker"][item["name"]] = Thread(target=internal["items"][item["name"]].worker)
      internal["items"][item["name"]].workerrunning = True
      internal["worker"][item["name"]].start()

  client.loop_start()
else:
  print("Es wurde kein Broker angegeben")
  exit

try:
  while (internal["command"] != "stop") and client.failed_connect == False:
    if internal["command"] == "ON":
      result = client.publish("/home/steckerleiste/", '{"Plug1":"ON", "Plug2":"ON"}')
      internal["command"] = ""
    if internal["command"] == "OFF":
      result = client.publish("/home/steckerleiste/", '{"Plug1":"OFF", "Plug2":"OFF"}')
      internal["command"] = ""      
    sleep(1)
  if client.failed_connect == True:
    print('Connection failed, exiting...')
  elif internal["command"] == "stop":
    print('Connection disconect by stop command')    
finally:
  for item in internal["worker"]:
    internal["items"][item].workerrunning = False   
  client.disconnect()
  client.loop_stop() 
  for item in internal["worker"]:
    internal["worker"][item].join()
