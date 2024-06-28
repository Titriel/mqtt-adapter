from typing import Any
from json import dumps
import logging
from logging import StreamHandler
from logging.handlers import MemoryHandler
from sys import stderr
from copy import deepcopy

conf ={"pretty": False}

streamHandler = StreamHandler(stream=stderr)

LOGGING_FORMAT: str = "%(asctime)s.%(msecs)06d\t%(threadName)s\t%(levelname)s\n%(message)s"
LOGGING_DATEFMT: str = "%Y-%m-%dT%H:%M:%S"

formatter = logging.Formatter(
    fmt=LOGGING_FORMAT,
    datefmt=LOGGING_DATEFMT,
)    
streamHandler.setFormatter(formatter)

memoryHandler = MemoryHandler(
    capacity=100,
    flushLevel=logging.ERROR,
    target=streamHandler,
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(memoryHandler)

def pretty():
    conf["pretty"] = True

def d2s(data: Any, filter: list = []):
    if type(data) is not tuple and type(data) is not dict and type(data) is not list:
        sdata = data
        if type(sdata) is str:
            if len(sdata) > 160:
                sdata = "\n" + sdata[:78] + "..." + sdata[-78:]
        return sdata
    sdata = deepcopy(data)
    if len(filter) > 0:
        out = shortcutstr({k: sdata[k] for k in filter if k in sdata})
    else:
        out = shortcutstr(sdata)
    if conf["pretty"]:
        return "\n" + dumps(out, indent=2)
    else:
        return dumps(out)

def shortcutstr(data:dict):
    if type(data) is list:
        templist = []
        for item in data:
            if type(item) is str:
                if len(item) > 160:
                    templist.append(item[:78] + "..." + item[-78:])
                else:
                    templist.append(item)
            else:
                templist.append(shortcutstr(item))
        return templist
    if type(data) is dict:
        for item in data:
            if type(data[item]) is str:
                if len(data[item]) > 160:
                    data[item] = data[item][:78] + "..." + data[item][-78:]
            else:
                data[item] = shortcutstr(data[item])
        return data
    if type(data) is float or type(data) is int or type(data) is bool or type(data) is tuple or data is None:
        return data
    else:
        return {}