import paho.mqtt.client as mqtt
from time import sleep
from config import config

internal = {"command": ""}
CONFIG = config()

def on_connect(client, userdata, flags, return_code):
  if return_code == 0:
    print("connected")
    client.subscribe(internal["subscribe"])
    if "subscribe" in CONFIG:
      client.subscribe(CONFIG["subscribe"])
  else:
    print("could not connect, return code:", return_code)
    client.failed_connect = True

def on_command(client, userdata, message):
  internal["command"] = str(message.payload.decode("utf-8"))

def on_message(client, userdata, message):
  print("Received message from", message.topic, ":", str(message.payload.decode("utf-8")))
  if message.retain==1:
    print("This is a retained message")

if "clientname" in CONFIG:
  internal["clientname"] = CONFIG["clientname"]
else:
  internal["clientname"] = "default"
client = mqtt.Client(internal["clientname"])
if "broker" in CONFIG:
  if ("username" in CONFIG["broker"]) and ("password" in CONFIG["broker"]):
    client.username_pw_set(username=CONFIG["broker"]["username"], password=CONFIG["broker"]["password"])
  if "hostname" in CONFIG["broker"]:
    client.connect(CONFIG["broker"]["hostname"])
  else:
    print("Es wurde kein Hostname für den Broker angegeben")
    exit
  internal["subscribe"] = ("/adapter/" + internal["clientname"] + "/command/", 0)
  print("Own commandchannel: " + internal["subscribe"][0])
  client.on_connect = on_connect
  client.on_message = on_message
  client.message_callback_add(internal["subscribe"][0], on_command)
  client.failed_connect = False

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
  client.disconnect()
  client.loop_stop()