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

#picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), './pic')
#libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), './lib')
picdir = 'pic'
libdir = 'lib'

degree_sign= u'\N{DEGREE SIGN}'

if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd7in5_V2

# Do IP stuff
def get_ip_address():
    s =socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8",80))
    return s.getsockname()[0]


myip = get_ip_address()



# create broadcast listener socket
def create_broadcast_listener_socket(broadcast_ip, broadcast_port):

    b_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    b_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    b_sock.bind(('', broadcast_port))

    mreq = struct.pack("4sl", socket.inet_aton(broadcast_ip), socket.INADDR_ANY)
    b_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    return b_sock

# Tempest Vars
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


# ip/port to listen to
BROADCAST_IP = '239.255.255.250'
BROADCAST_PORT = 50222

# create the listener socket
sock_list = [create_broadcast_listener_socket(BROADCAST_IP, BROADCAST_PORT)]

data_type = ""

while data_type != 'obs_st':
    # small sleep otherwise this will loop too fast between messages and eat a lot of CPU
    time.sleep(0.01)

    # wait until there is a message to read
    readable, writable, exceptional = select.select(sock_list, [], sock_list, 0)

    # for each socket with a message
    for s in readable:
        data, addr = s.recvfrom(4096)

        # convert data to json
        data_json = json.loads(data)

        if data_json['type'] == 'obs_st':
            data_type = "obs_st"
            # 0 Time Epoch  Seconds
            #1   Wind Lull (minimum 3 second sample) m/s
            #2   Wind Avg (average over report interval) m/s
            #3   Wind Gust (maximum 3 second sample) m/s
            #4   Wind Direction  Degrees
            #5   Wind Sample Interval    seconds
            #6   Station Pressure    MB
            #7   Air Temperature C
            #8   Relative Humidity   %
            #9   Illuminance Lux
            #10  UV  Index
            #11  Solar Radiation W/m^2
            #12  Precip Accumulated  mm
            #13  Precipitation Type  0 = none, 1 = rain, 2 = hail
            #14  Lightning Strike Avg Distance   km
            #15  Lightning Strike Count  
            #16  Battery Volts
            #17  Report Interval Minutes
            time_epoch = data_json['obs'][0][0]
            windlull = data_json['obs'][0][1]
            windavg = data_json['obs'][0][2]
            windgust = data_json['obs'][0][3]
            winddir = data_json['obs'][0][4]
            pressure = data_json['obs'][0][6]
            temp = round(((data_json['obs'][0][7] * 1.8)+32),1)
            humid = data_json['obs'][0][8]
            lux = data_json['obs'][0][9]
            uv = data_json['obs'][0][10]
            rad = data_json['obs'][0][11]
            precipmm = data_json['obs'][0][12]
            preciptp = data_json['obs'][0][13]
            ltndist = data_json['obs'][0][14]
            ltncnt = data_json['obs'][0][15]
            batt = data_json['obs'][0][16]
            print ( "temp: ", temp )
            print ( "humidity: ", humid )


logging.basicConfig(level=logging.DEBUG)

try:
    logging.info("epd7in5_V2 Demo")
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
    #draw.text((10, 20), '7.5inch e-Paper', font = font24, fill = 0)
    #draw.text((150, 0), u'微雪电子', font = font24, fill = 0)    
    #draw.line((20, 50, 70, 100), fill = 0)
    #draw.line((70, 50, 20, 100), fill = 0)
    # top left
    draw.rectangle((2, 22, 261, 249), outline = 0)
    #draw.text ((6,26), 'Temperature: ' + str(temp), font =font24, fill = 0)
    #draw.text ((6,55), 'Humidity: ' + str(humid), font =font24, fill = 0)
    draw.text ((100,70), str(temp) + degree_sign +'f', font =font65, fill = 0)
    draw.text ((6,210), str(humid) + '% RH', font =font24, fill = 0)
    draw.text ((160,210), str(pressure) + 'mb', font =font24, fill = 0)

    # top middle
    draw.rectangle((264, 22, 532, 249), outline = 0)
    # top right
    draw.rectangle((535, 22, 798, 249), outline = 0)
    # bottom left
    draw.rectangle((2, 253, 261, 475), outline = 0)
    # bottom middle
    draw.rectangle((264, 253, 532, 475), outline = 0)
    # bottom right
    draw.rectangle((535, 253, 798, 475), outline = 0)
    #draw.line((165, 50, 165, 100), fill = 0)
    #draw.line((140, 75, 190, 75), fill = 0)
    #draw.arc((140, 50, 190, 100), 0, 360, fill = 0)
    #draw.rectangle((80, 50, 130, 100), fill = 0)
    #draw.chord((200, 50, 250, 100), 0, 360, fill = 0)
    epd.display(epd.getbuffer(Himage))
    #time.sleep(2)

    # Drawing on the Vertical image
    #logging.info("2.Drawing on the Vertical image...")
    #Limage = Image.new('1', (epd.height, epd.width), 255)  # 255: clear the frame
    #draw = ImageDraw.Draw(Limage)
    #draw.text((2, 0), 'hello world', font = font18, fill = 0)
    #draw.text((2, 20), '7.5inch epd', font = font18, fill = 0)
    #draw.text((20, 50), u'微雪电子', font = font18, fill = 0)
    #draw.line((10, 90, 60, 140), fill = 0)
    #draw.line((60, 90, 10, 140), fill = 0)
    #draw.rectangle((10, 90, 60, 140), outline = 0)
    #draw.line((95, 90, 95, 140), fill = 0)
    #draw.line((70, 115, 120, 115), fill = 0)
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

    #logging.info("Goto Sleep...")
    #epd.sleep()
    
except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd7in5_V2.epdconfig.module_exit()
    exit()
