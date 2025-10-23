from sseclient import SSEClient
from json import loads
from base64 import b64decode
from time import time as now 
from math import floor
from os import path, getcwd
from sys import path as PATH
PATH.append(path.join(getcwd(),"script"))
import logging
from logsetup import d2s, pretty as logpretty
from XY6020L import XY6020L

logger = logging.getLogger()
logpretty()

myXY6020L = XY6020L(1,0,20)
myXY6020L.want()
print (myXY6020L.readcode())
print (myXY6020L.todict(b'\x01\x03(\x05P\x00#\x04\xe7\x00\x0b\x00\r\x051\x08\'\x00\x00\\\xe4\x00\x00\x00\x05\x00)\x00\x17\x00\xf7"\xb8\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00;O'))
print (myXY6020L.set({"I_SET": 0.10}))
print (myXY6020L.wants)