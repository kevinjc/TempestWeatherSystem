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

#picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), './pic')
#libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), './lib')
picdir = 'pic'
libdir = 'lib'
if os.path.exists(libdir):
    sys.path.append(libdir)
from waveshare_epd import epd7in5_V2

config = configparser.ConfigParser({'debug': '', 'Redis_Server': '', 'Redis_Port': '', 'Redis_Instance':'', 'Historical_Minutes':''})
config.read('config.ini')
debug=int(config.get('DEFAULT', 'debug'))
Redis_Server=(config.get('DEFAULT', 'Redis_Server'))
Redis_Port=(config.get('DEFAULT', 'Redis_Port'))
Redis_Instance=(config.get('DEFAULT', 'Redis_Instance'))
Historical_Minutes=int((config.get('DEFAULT', 'Historical_Minutes')))
if debug >0:
    print ("Debug is on (",debug,"). Connecting to Redis: ",Redis_Server,":",Redis_Port,",",Redis_Instance )
# Redis connection
rds = redis.Redis(host=Redis_Server, port=Redis_Port, db=Redis_Instance)


# thanks https://gist.github.com/RobertSudwarts/acf8df23a16afdb5837f
def degrees_to_cardinal(d):
    '''
    note: this is highly approximate...
    '''
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    ix = int((d + 11.25)/22.5)
    return dirs[ix % 16]


degree_sign= u'\N{DEGREE SIGN}'

if os.path.exists(libdir):
    sys.path.append(libdir)


# Do IP stuff
def get_ip_address():
    s =socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8",80))
    return s.getsockname()[0]

myip = get_ip_address()

past=(datetime.datetime.now() - datetime.timedelta(minutes=Historical_Minutes)).strftime('%s')

# Tempest Data from redis
import ast
conditions=ast.literal_eval(rds.get('obs_st').decode("utf-8"))
if debug > 2:
    print ("Raw observation data: ",str(conditions),"\nUpdated at: ",str(conditions[0]))

last_conditions=ast.literal_eval(rds.get('obs_last').decode("utf-8"))
if debug > 2:
    print ("Raw observation data: ",str(last_conditions),"\nUpdated at: ",str(last_conditions[0]))

rapid_wind=ast.literal_eval(rds.get('rapid_wind').decode("utf-8"))
if debug > 2:
    print ("Raw Rapid_Wind data: ",str(rapid_wind),"\nUpdated at: ",str(rapid_wind[0]))

hub_status=ast.literal_eval(rds.get('hub_status').decode("utf-8"))
if debug > 2:
    print ("Raw Hub_Status data: ",hub_status,"\nUpdated at: ",hub_status['timestamp'])

device_status=ast.literal_eval(rds.get('device_status').decode("utf-8"))
if debug > 2:
    print ("Raw observation data: ",device_status,"\nUpdated at: ",device_status['timestamp'])

precip=ast.literal_eval(rds.get('evt_precip').decode("utf-8"))
if debug > 2:
    print ("Raw precipation observation data: ",precip,"\nUpdated at: ",precip[0])
do_precip=False
if int(precip[0]) > int(past):
    do_precip=True

strike=ast.literal_eval(rds.get('evt_strike').decode("utf-8"))
if debug > 2:
    print ("Raw lightning strike observation data: ",strike,"\nUpdated at: ",strike[0])
    print ("Strike time",strike[0],"\nSixty minutes ago", past)
do_strike=False
if int(strike[0]) > int(past):
    do_strike=True

# https://weatherflow.github.io/Tempest/api/udp/v143/
# obs_st or conditions
time_update = format(datetime.datetime.fromtimestamp(conditions[0]))
windlull = round(conditions[1]*2.23694)
windavg = round(conditions[2]*2.23694)
windgust = round(conditions[3]*2.23694)
winddir = degrees_to_cardinal(conditions[4])
windint = conditions[5]
pressure = round(conditions[6],1)
last_pressure = round(last_conditions[6],1)
temp=round(((conditions[7] * 1.8)+32),1)
humid = round(conditions[8],1)
lux = conditions[9]
uv = round(conditions[10],1)
rad = conditions[11]
precipmm = conditions[12]
preciptype = conditions[13]
ltnavgdist = conditions[14] 
ltncnt = conditions[15]
batt = round(conditions [16],2)
reportint = conditions[17]

# Rapid_Wind
rw_epoch = format(datetime.datetime.fromtimestamp(rapid_wind[0]))
rw_speed = round(rapid_wind[1]*2.23694)
rw_dir = degrees_to_cardinal(rapid_wind[2])

#Hub_Status
hub_serial = hub_status['serial_number']
hub_fwver = hub_status['firmware_revision']

#Device_Status
dev_serial = device_status['serial_number']
dev_fwver = device_status['firmware_revision']
dev_sensorstatus = device_status['sensor_status']

logging.basicConfig(level=logging.DEBUG)

try:
    logging.info("Writing Tempest Weather Data")
    epd = epd7in5_V2.EPD()
    
    logging.info("init and Clear")
    epd.init()
    epd.Clear()

    font65 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 65)
    font40 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 40)
    font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
    font20 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 20)
    font18 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 18)

    # Drawing on the Horizontal image
    logging.info("1.Drawing on the Horizontal image...")
    Himage = Image.new('1', (epd.width, epd.height), 255)  # 255: clear the frame
    draw = ImageDraw.Draw(Himage)
    draw.text((10, 0), 'hello world, I am ' + myip, font = font20, fill = 0)
    draw.text((400, 0), 'Conditions updated at ' + time_update, font = font20, fill = 0)

    ####### the RECTANGLES of DATA
    #### top left: air/temp
    draw.rectangle((2, 22, 261, 249), outline = 0)
    draw.text ((10,30), str(humid) + '% RH', font =font24, fill = 0)

    draw.text ((45,75), str(temp) + degree_sign +'f', font =font65, fill = 0)
    if last_pressure < pressure:
        draw.text ((10,210), '\u2191', font =font24, fill = 0)
    elif last_pressure > pressure:
        draw.text ((10,210), '\u2193', font =font24, fill = 0)
    draw.text ((24,210), str(pressure) + 'mb', font =font24, fill = 0)

    #### top middle: wind stuff
    draw.rectangle((264, 22, 532, 249), outline = 0)

    draw.text ((274,30),'Gusts: '+ str(windgust)+'mph' , font =font24, fill = 0)

    draw.text ((310,75), str(rw_speed)+'mph' , font =font65, fill = 0)
    draw.text ((430,150), str(rw_dir) , font =font24, fill = 0)


    draw.text ((274,210), 'Avg: '+str(windavg)+'mph' , font =font24, fill = 0)


    #### top right: light stuff
    draw.rectangle((535, 22, 798, 249), outline = 0)

    draw.text ((550,30), str(lux)+' lux' , font =font24, fill = 0)
    draw.text ((570,75), str(uv)+' uv' , font =font65, fill = 0)
    draw.text ((550,210), str(rad)+' rad' , font =font24, fill = 0)

    #### bottom left
    draw.rectangle((2, 253, 261, 475), outline = 0)



    #### bottom middle
    draw.rectangle((264, 253, 532, 475), outline = 0)



    #### bottom right
    # precipitation and lightning
    draw.rectangle((535, 253, 798, 475), outline = 0)

    if do_strike == True:
        print ("Lightning strike in last 60 minutes ",(format(datetime.datetime.fromtimestamp(strike[0]).strftime("%H:%M"))),"; distance ",strike[1])
        draw.text ((562,260),"dist: "+ str(strike[1])+' km' , font =font24, fill = 0)
        draw.line((550, 264, 540, 285), fill = 0,width=3)
        draw.line((540, 285, 550, 285), fill = 0,width=3)
        draw.line((550, 285, 540, 310), fill = 0,width=3)
        draw.text ((562,290), "At "+(format(datetime.datetime.fromtimestamp(strike[0]).strftime("%H:%M"))), font =font24, fill = 0)
        draw.line((565, 325, 772, 325), fill = 0,width=3)


    if do_precip == True:
        print("Precipitation in last 60 minutes ",format(datetime.datetime.fromtimestamp(precip[0])))
        # Get last precipitation type
        if preciptype == 1:
            preciptype="rain"
        elif preciptype ==2:
            preciptype="hail"
        elif preciptype == 0:
            #Not currently registering, get last
            #preciptype=str(rds.get('last_precipitation'))
            preciptype=rds.get('last_precipitation').decode("utf-8")
        print ("Last precipitation is ",str(preciptype))
        draw.text ((565,335), str(preciptype)+" at "+
                (format(datetime.datetime.fromtimestamp(strike[0]).strftime("%H:%M"))), font =font24, fill = 0)
        draw.text ((565,365), "Totals "+str(precipmm), font =font24, fill = 0)
        draw.line((565, 398, 772, 398), fill = 0,width=3)

    draw.text ((560,440), str(batt)+"v", font =font24, fill = 0)

    epd.display(epd.getbuffer(Himage))
    logging.info("Goto Sleep...")
    epd.sleep()

    #draw.arc((140, 50, 190, 100), 0, 360, fill = 0)
    #draw.rectangle((80, 50, 130, 100), fill = 0)
    #draw.chord((200, 50, 250, 100), 0, 360, fill = 0)
    #logging.info("2.Drawing on the Vertical image...")
    #Limage = Image.new('1', (epd.height, epd.width), 255)  # 255: clear the frame
    #draw = ImageDraw.Draw(Limage)
    #draw.rectangle((10, 90, 60, 140), outline = 0)
    #draw.arc((70, 90, 120, 140), 0, 360, fill = 0)
    #draw.rectangle((10, 150, 60, 200), fill = 0)
    #draw.chord((70, 150, 120, 200), 0, 360, fill = 0)
    #epd.display(epd.getbuffer(Limage))
    #time.sleep(2)

    #logging.info("3.read bmp file")
    #Himage = Image.open(os.path.join(picdir, '7in5_V2.bmp'))
    #epd.display(epd.getbuffer(Himage))
    #time.sleep(2)

    #logging.info("4.read bmp file on window")
    #Himage2 = Image.new('1', (epd.height, epd.width), 255)  # 255: clear the frame
    #bmp = Image.open(os.path.join(picdir, '100x100.bmp'))
    #Himage2.paste(bmp, (50,10))
    #epd.display(epd.getbuffer(Himage2))
    #time.sleep(2)

    #logging.info("Clear...")
    #epd.init()
    #epd.Clear()

    
except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd7in5_V2.epdconfig.module_exit()
    exit()
