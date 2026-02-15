#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
import socket
import logging
import fcntl
import struct
import time
from PIL import Image,ImageDraw,ImageFont 
import traceback
import select
import pprint
import json
import datetime
import redis
import configparser


config = configparser.ConfigParser({'debug': '', 'Redis_Server': '', 'Redis_Port': '', 'Redis_Instance':''})
config.read('config.ini')
debug=int(config.get('DEFAULT', 'debug'))
Redis_Server=(config.get('DEFAULT', 'Redis_Server'))
Redis_Port=(config.get('DEFAULT', 'Redis_Port'))
Redis_Instance=(config.get('DEFAULT', 'Redis_Instance'))

# Redis connection
rds = redis.Redis(host=Redis_Server, port=Redis_Port, db=Redis_Instance)

#picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), './pic')
#libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), './lib')
picdir = 'pic'
libdir = 'lib'

degree_sign= u'\N{DEGREE SIGN}'

if os.path.exists(libdir):
    sys.path.append(libdir)


# Do IP stuff
def get_ip_address():
    s =socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8",80))
    return s.getsockname()[0]

myip = get_ip_address()

# Tempest Vars
# https://weatherflow.github.io/Tempest/api/udp/v143/
time_epoch = ""
temp = ""
batt = ""
lux = ""
ltndist = ""
ltncnt = ""
precipmm = ""
preciptp = ""
humid = ""
rad = ""
pressure = ""
uv = ""
windavg = ""
winddir = ""
windgust = ""
windlull = ""
windspd = ""

conditions=rds.get('obs_st')

print("conditions: ",conditions)

