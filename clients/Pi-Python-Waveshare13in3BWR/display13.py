#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
import socket
import logging
import math
import fcntl
import struct
import time
from PIL import Image,ImageDraw,ImageFont 
import traceback
import select
import pprint
import requests
from io import BytesIO
import json
import datetime
import redis
import configparser
import urllib3

libdir = 'lib'
picdir = 'pic'

if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd13in3b

logging.basicConfig(level=logging.DEBUG)


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

fw_upload=round(float(rds.get('fw_upload').decode("utf-8"))/125000)
fw_download=round(float(rds.get('fw_download').decode("utf-8"))/125000)

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


past=(datetime.datetime.now() - datetime.timedelta(minutes=Historical_Minutes)).strftime('%s')
if debug > 1:
    print (" Past time for precip comparison ",past)

################################
# Tempest Data from redis
import ast
conditions=ast.literal_eval(rds.get('tempest_obs_st').decode("utf-8"))
# https://weatherflow.github.io/Tempest/api/udp/v143/
# obs_st or conditions
time_update = format(datetime.datetime.fromtimestamp(conditions[0]))
windlull = round(conditions[1]*2.23694)
windavg = round(conditions[2]*2.23694)
windgust = round(conditions[3]*2.23694)
winddir = degrees_to_cardinal(conditions[4])
windint = conditions[5]
pressure = round(conditions[6],1)
temp=round(((conditions[7] * 1.8)+32),1)
humid = round(conditions[8],1)
lux = conditions[9]
uv = round(conditions[10],1)
rad = conditions[11]
precipmm = round(conditions[12],2)
preciptype = conditions[13]
ltnavgdist = conditions[14] 
ltncnt = conditions[15]
batt = round(conditions [16],2)
reportint = conditions[17]


if debug > 2:
    print ("Raw observation data: ",str(conditions),"\nUpdated at: ",str(time_update))

last_conditions=ast.literal_eval(rds.get('tempest_obs_last').decode("utf-8"))
last_update = format(datetime.datetime.fromtimestamp(last_conditions[0]))
last_pressure = round(last_conditions[6],1)
if debug > 2:
    print ("Raw observation data: ",str(last_conditions),"\nUpdated at: ",str(last_update))

rapid_wind=ast.literal_eval(rds.get('tempest_rapid_wind').decode("utf-8"))
if debug > 2:
    print ("Raw Rapid_Wind data: ",str(rapid_wind),"\nUpdated at: ",str(rapid_wind[0]))

hub_status=ast.literal_eval(rds.get('tempest_hub_status').decode("utf-8"))
if debug > 2:
    print ("Raw Hub_Status data: ",hub_status,"\nUpdated at: ",hub_status['timestamp'])

device_status=ast.literal_eval(rds.get('tempest_device_status').decode("utf-8"))
if debug > 2:
    print ("Raw observation data: ",device_status,"\nUpdated at: ",device_status['timestamp'])

precip=ast.literal_eval(rds.get('tempest_evt_precip').decode("utf-8"))
precip_time=format(datetime.datetime.fromtimestamp(precip[0]))

if debug > 2:
    print ("Raw precipation observation data: ",precip,"\nUpdated at: ",str(precip_time),"/",precip[0])
do_precip=False
if int(precip[0]) > int(past):
    do_precip=True

strike=ast.literal_eval(rds.get('tempest_evt_strike').decode("utf-8"))
if debug > 2:
    print ("Raw lightning strike observation data: ",strike,"\nUpdated at: ",strike[0])
    print ("Strike time",strike[0],"\nSixty minutes ago", past)
do_strike=False
if int(strike[0]) > int(past):
    do_strike=True


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
####################################################
# Forecast Data

#######################
# Get the Forecast Data
fc_today=ast.literal_eval(rds.get('forecast_today').decode("utf-8"))
fc_tomorrow=ast.literal_eval(rds.get('forecast_tomorrow').decode("utf-8"))
fc_dayafter=ast.literal_eval(rds.get('forecast_dayafter').decode("utf-8"))
day_of_week_test=str( datetime.datetime.strptime(fc_today['Day'], '%Y-%m-%d').strftime('%A'))
if debug >2:
    print (fc_today)
    print (" Day "+day_of_week_test+", " + fc_today['Day'])
    print ("   Sunrise : "+fc_today['sunrise'])
    print ("   Sunset  : "+fc_today['sunset'])
    print ("   Temps   : "+fc_today['min']+"/"+fc_today['max'])
    print (" Conditions: "+fc_today['weather'])
    print ("   Icon today: "+fc_today['icon'])


####################################################
logging.basicConfig(level=logging.DEBUG)

try:
    logging.info("epd13in3b Demo")
    epd = epd13in3b.EPD()
    logging.info(f"Screen Width: {epd.width}")
    logging.info(f"Screen Height: {epd.height}")
    
    logging.info("init ...")
    epd.init()
    time.sleep(5)
    #logging.info("... and Clear")
    #epd.Clear()
    #time.sleep(25)

    WeatherFont = ImageFont.truetype(os.path.join(libdir, 'WeatherIcons.ttf'),40)
    font12 = ImageFont.truetype(os.path.join(libdir, 'Font.ttc'), 12)
    font15 = ImageFont.truetype(os.path.join(libdir, 'Font.ttc'), 15)
    font18 = ImageFont.truetype(os.path.join(libdir, 'Font.ttc'), 18)
    font20 = ImageFont.truetype(os.path.join(libdir, 'Font.ttc'), 20)
    font24 = ImageFont.truetype(os.path.join(libdir, 'Font.ttc'), 24)
    font32 = ImageFont.truetype(os.path.join(libdir, 'Font.ttc'), 32)
    font35 = ImageFont.truetype(os.path.join(libdir, 'Font.ttc'), 35)
    font40 = ImageFont.truetype(os.path.join(libdir, 'Font.ttc'), 40)
    font45 = ImageFont.truetype(os.path.join(libdir, 'Font.ttc'), 45)
    font55 = ImageFont.truetype(os.path.join(libdir, 'Font.ttc'), 55)
    font65 = ImageFont.truetype(os.path.join(libdir, 'Font.ttc'), 65)
    font100 = ImageFont.truetype(os.path.join(libdir, 'Font.ttc'), 100)


    # Drawing on the Horizontal image
    logging.info("3.Drawing on the Horizontal image...")
    HBlackimage = Image.new('1', (epd.width, epd.height), 255)  
    HRedimage = Image.new('1', (epd.width, epd.height), 255) 
    drawblack = ImageDraw.Draw(HBlackimage)
    drawred = ImageDraw.Draw(HRedimage)

    ##########################
    # Look! a Moon!
    png = Image.open(os.path.join(picdir, "Look-A-Moon-bw_295.png")).convert("RGBA")
    Moon_HStart = 250
    Moon_VStart = 375
    Moon_Diameter = 295
    logging.info(f"---- Placing Moon image, Horiz start {Moon_HStart}, Vert start {Moon_VStart}, diameter {Moon_Diameter} ----")
    HBlackimage.paste(png, (Moon_HStart,Moon_VStart), png)
    #Calculate the location of white overlay on moon
    moonphase = float(fc_today['moonphase'])
    if moonphase > .5 and moonphase < 1:
        # Waning Moon Phase
        MoonPixelsToDrop = (2*Moon_Diameter) * moonphase
        logging.info(f"  Waning moon offset pixel amount is {MoonPixelsToDrop}")
        WhiteMoonStart = (Moon_HStart + 2*Moon_Diameter) - MoonPixelsToDrop
        logging.info(f"  Waning Moon start position is {WhiteMoonStart}")
        drawblack.text((330, 650), "Waning Moon", font = font18, fill = 0)
    if moonphase > 0 and moonphase < .5:
        # Waxing Moon Phase
        WhiteMoonStart = Moon_HStart - (Moon_Diameter * moonphase) 
        logging.info(f"  Waxing Moon start position is {WhiteMoonStart}")
    if moonphase != .5:
        drawblack.chord((WhiteMoonStart, Moon_VStart, (WhiteMoonStart+Moon_Diameter), (Moon_VStart+Moon_Diameter) ), 0, 360, fill = 1)
    ##########################
    # Left SIDE 
    LTOP_HL = 1
    LTOP_HR = 230
    BOX_DEPTH = 250
    TEXT_HSPACE = 10
    TEXT_VSPACE = 5
    PIXEL = 1
    DROP = 1
    #
    # title rectangle
    box_startH = TEXT_HSPACE+LTOP_HL
    box_startV = 2*TEXT_VSPACE + DROP
    box_endH = LTOP_HR - 2*TEXT_HSPACE
    box_endV = DROP + 8*TEXT_VSPACE 
    logging.info(f"title rectangle from {box_startH},{box_startV} to {box_endH},{box_endV}")
    drawblack.rectangle((box_startH, box_startV, box_endH, box_endV), outline = 0, fill = 0)
    drawblack.text(((5*TEXT_HSPACE), (DROP+(2*TEXT_VSPACE))), "Upload", font = font24, fill = 1)
    drawblack.text(((4*TEXT_HSPACE), (DROP+(8*TEXT_VSPACE))), str(fw_upload) +" Mbps", font = font18, fill = 0)
    #drawblack.arc((20, 73, 150, 200), 115, 65, fill = 0)
    #####################################################
    # Speedometer Globals
    # 66 initially
    MeterRAD = 100
    max_speed=1000
    #####################################################
    # Speedometer Uploads
    #UpCenterH = 86
    #UpCenterV = 136
    CenterH = PIXEL + MeterRAD
    UpCenterV = DROP + MeterRAD + (12*TEXT_VSPACE)
    logging.info(f"Setting center of gauge to {CenterH} and {UpCenterV}")
    # Draw Meter face
    drawblack.ellipse(
            (CenterH - MeterRAD, UpCenterV - MeterRAD, CenterH + MeterRAD, UpCenterV + MeterRAD),
            outline=0, width=3)
    # draw needle center
    drawblack.chord(((CenterH - 3), (UpCenterV -3), (CenterH + 3), (UpCenterV +3)), 0, 360, fill = 0)
    # Draw speed ticks
    for i in range(0, max_speed + 1, 100):
        angle = math.radians(270 - (i / max_speed) * 270)
        x1 = CenterH + (MeterRAD - 10) * math.cos(angle)
        y1 = UpCenterV - (MeterRAD - 10) * math.sin(angle)
        x2 = CenterH + MeterRAD * math.cos(angle)
        y2 = UpCenterV - MeterRAD * math.sin(angle)
        drawblack.line((x1, y1, x2, y2), fill=0, width=2)

    # Add speed labels
    label_x = CenterH + (MeterRAD - 30) * math.cos(angle)
    label_y = UpCenterV - (MeterRAD - 30) * math.sin(angle)
    drawblack.text((label_x - 10, label_y - 10), str(i), fill=0)

    # Draw the needle
    needle_angle = math.radians(270 - (fw_upload / max_speed) * 270)
    needle_x = CenterH + (MeterRAD ) * math.cos(needle_angle)
    needle_y = UpCenterV - (MeterRAD ) * math.sin(needle_angle)
    drawred.line((CenterH, UpCenterV, needle_x, needle_y), fill=0, width=4)

    ######
    # New DROP
    DROP = DROP + BOX_DEPTH + TEXT_VSPACE
    # title rectangle
    box_startH = TEXT_HSPACE+LTOP_HL
    box_startV = 2*TEXT_VSPACE + DROP
    box_endH = LTOP_HR - 2*TEXT_HSPACE
    box_endV = DROP + 8*TEXT_VSPACE 
    logging.info(f"title rectangle from {box_startH},{box_startV} to {box_endH},{box_endV}")
    drawblack.rectangle((box_startH, box_startV, box_endH, box_endV), outline = 0, fill = 0)
    drawblack.text(((4*TEXT_HSPACE), (DROP+(2*TEXT_VSPACE))), "Download", font = font24, fill = 1)
    drawblack.text(((4*TEXT_HSPACE), (DROP+(8*TEXT_VSPACE))), str(fw_download) +" Mbps", font = font18, fill = 0)

    ## Left Down 1 Rectangle
    ###########################################################
    # Speedometer Downloads
    #DnCenterV = 336
    DnCenterV = DROP + MeterRAD + (12*TEXT_VSPACE)
    ## Draw Meter Face
    drawblack.ellipse(
            (CenterH - MeterRAD, DnCenterV - MeterRAD, CenterH + MeterRAD, DnCenterV + MeterRAD),
            outline=0, width=3)
    # draw needle center
    drawblack.chord(((CenterH - 3), (DnCenterV -3), (CenterH + 3), (DnCenterV +3)), 0, 360, fill = 0)
    # Draw speed ticks
    for i in range(0, max_speed + 1, 100):
        angle = math.radians(270 - (i / max_speed) * 270)
        x1 = CenterH + (MeterRAD - 10) * math.cos(angle)
        y1 = DnCenterV - (MeterRAD - 10) * math.sin(angle)
        x2 = CenterH + MeterRAD * math.cos(angle)
        y2 = DnCenterV - MeterRAD * math.sin(angle)
        drawblack.line((x1, y1, x2, y2), fill=0, width=2)
    
    # Add speed labels
    label_x = CenterH + (MeterRAD - 30) * math.cos(angle)
    label_y = DnCenterV - (MeterRAD - 30) * math.sin(angle)
    drawblack.text((label_x - 10, label_y - 10), str(i), fill=0)

    # Draw the needle
    needle_angle = math.radians(270 - (fw_download / max_speed) * 270)
    needle_x = CenterH + (MeterRAD ) * math.cos(needle_angle)
    needle_y = DnCenterV - (MeterRAD ) * math.sin(needle_angle)
    drawred.line((CenterH, DnCenterV, needle_x, needle_y), fill=0, width=4)


    #########################
    # middle LARGE BOX
    #
    # Top Middle Rectangle
    # Temp in big letters left box : TEXT IS OVER AND thEN DoWN
    # Main
    drawblack.text ((250,30), str(temp) + degree_sign +'f', font =font100, fill = 0)
    # small left first column
    drawblack.text ((300,130), str(humid) + '% RH', font =font32, fill = 0)
    if last_pressure < pressure:
        logging.info(" pressure rising")
        drawred.text ((475,130), '\u2193'+" "+str(pressure) + ' millibars', font =font32, fill = 0)
    elif last_pressure > pressure:
        logging.info(" pressure dropping")
        drawblack.text ((475,130), '\u2191'+" "+str(pressure) + ' millibars', font =font32, fill = 0)
    else:
        logging.info(" static pressure ")
        drawblack.text ((475,130), str(pressure) + ' millibars', font =font32, fill = 0)

    drawblack.rectangle((240, 180, 740, 310), outline = 0)
    drawred.rectangle((243, 183, 737, 307), outline = 0)
    drawred.text((300, 190), "Kevin's e-Paper", font = font45, fill = 0)
    drawred.text((300, 250), "Apple Core", font = font45, fill = 0)



    # Middle Down 1 Artsy Fartsy Rectangle
    #drawblack.rectangle((177, 82, 760, 130), outline = 0)
    #drawred.rectangle((180, 85, 757, 127), outline = 0)
    #drawblack.rectangle((183, 88, 754, 124), outline = 0)
    #drawred.rectangle((186, 91, 751, 121), outline = 0)
    #drawblack.rectangle((189, 94, 748, 118), outline = 0)
    #drawred.rectangle((192, 97, 745, 115), outline = 0)
    #drawblack.rectangle((195, 100, 741, 112), outline = 0)
    #drawblack.text((240, 98), 'Conditions updated at ' + time_update, font = font12, fill = 0)



    


    

    # Bottom Box full width
    #drawblack.rectangle((0, 640, 959, 679), outline = 0)



    ########################
    # RIGHT SIDE
    RTOP_HL = 762
    RTOP_HR = 959
    BOX_DEPTH = 205
    TEXT_HSPACE = 11
    TEXT_VSPACE = 5
    PIXEL = 1
    DROP = 4
    # Right Top  Rectangle
    #drawblack.rectangle((RTOP_HL, DROP, RTOP_HR, (DROP + BOX_DEPTH)), outline = 0)
    #### TOP Right: today forecast
    # Day Description
    drawblack.rectangle(((RTOP_HL+2*PIXEL), DROP+PIXEL, (RTOP_HR - 2*TEXT_HSPACE), (DROP + PIXEL+ 5*TEXT_VSPACE)), outline = 0,fill=0)
    drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP+TEXT_VSPACE-PIXEL-PIXEL)),"Forecast Today: ", font =font20, fill = 1)
    # Forecast description
    if len(fc_today['weather']) > 14:
        drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP+ (5*TEXT_VSPACE))),str(fc_today['weather']), font =font20, fill = 0)
    elif len(fc_today['weather']) > 12:
        drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP+(5*TEXT_VSPACE))),str(fc_today['weather']), font =font24, fill = 0)
    else: 
        drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP+(5*TEXT_VSPACE))),str(fc_today['weather']), font =font32, fill = 0)
    # Icon
    #print ("   Icon today: "+fc_today['icon'])
    #drawblack.text ((800,55), '\uea01', font = WeatherFont, fill = 0)
    #drawblack.text (((RTOP_HL + TEXT_HSPACE),40), fc_today['icon'], font = WeatherFont, fill = 0)
    #response = requests.get("https://openweathermap.org/img/wn/"+fc_today['icon']+"@2x.png")
    #image_from_url = Image.open(BytesIO(response.content)).convert("RGBA")
    png = Image.open(os.path.join(picdir, fc_today['icon']+"@2x.png")).convert("RGBA")
    HBlackimage.paste(png, ((RTOP_HL + (3*TEXT_HSPACE)),(DROP+(6*TEXT_VSPACE))), png)
    # Big Temp 
    drawblack.text (((RTOP_HL + TEXT_HSPACE+TEXT_VSPACE),(DROP+(20*TEXT_VSPACE))),str(fc_today['min'])+"-"+str(fc_today['max'])+degree_sign+"f", font =font40, fill = 0)
    # small text
    drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP+(30*TEXT_VSPACE))), "Sunrise @ "+str( datetime.datetime.strptime(fc_today['sunrise'],"%Y-%m-%d %H:%M:%S").strftime('%I:%M')), font =font18, fill = 0)
    drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP+(33*TEXT_VSPACE)+PIXEL)), "Sunset  @ "+str( datetime.datetime.strptime(fc_today['sunset'], "%Y-%m-%d %H:%M:%S").strftime('%I:%M')), font =font18, fill = 0)
    drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP +(37*TEXT_VSPACE))), str( datetime.datetime.strptime(fc_today['Day'], '%Y-%m-%d').strftime('%A'))+", "+ str(fc_today['Day'] ), font =font12, fill = 0)

    # Right Middle  Rectangle
    DROP = DROP + PIXEL + BOX_DEPTH
    # Tomorrow forecast
    #drawblack.rectangle((RTOP_HL, DROP, RTOP_HR, (DROP + BOX_DEPTH)), outline = 0)
    # Day Description
    drawblack.rectangle(((RTOP_HL+2*PIXEL), DROP+PIXEL, (RTOP_HR - 2*TEXT_HSPACE), (DROP + PIXEL+ 5*TEXT_VSPACE)), outline = 0,fill=0)
    drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP+TEXT_VSPACE-PIXEL-PIXEL)),(str(datetime.datetime.strptime(fc_tomorrow['Day'], '%Y-%m-%d').strftime('%A')))+" expect", font =font20, fill = 1)
    # forecast description
    if len(fc_tomorrow['weather']) > 14:
        drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP + (5*TEXT_VSPACE))),str(fc_tomorrow['weather']), font =font20, fill = 0)
    elif len(fc_tomorrow['weather']) > 12:
        drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP + (5*TEXT_VSPACE))),str(fc_tomorrow['weather']), font =font24, fill = 0)
    else:
        drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP + (5*TEXT_VSPACE))),str(fc_tomorrow['weather']), font =font32, fill = 0)
    # Icon
    #response = requests.get("https://openweathermap.org/img/wn/"+fc_tomorrow['icon']+"@2x.png")
    #image_from_url = Image.open(BytesIO(response.content)).convert("RGBA")
    #HBlackimage.paste(image_from_url, ((RTOP_HL + (3*TEXT_HSPACE)),(DROP+ (7*TEXT_VSPACE))), image_from_url)
    png = Image.open(os.path.join(picdir, fc_tomorrow['icon']+"@2x.png")).convert("RGBA")
    HBlackimage.paste(png, ((RTOP_HL + (3*TEXT_HSPACE)),(DROP+(6*TEXT_VSPACE))), png)
    # big temp
    drawblack.text (((RTOP_HL + TEXT_HSPACE+TEXT_VSPACE),(DROP +(20*TEXT_VSPACE))),str(fc_tomorrow['min'])+"-"+str(fc_tomorrow['max'])+degree_sign+"f", font =font40, fill = 0)
    # small details
    drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP+ (30*TEXT_VSPACE))), "Sunrise @ "+str( datetime.datetime.strptime(fc_tomorrow['sunrise'],"%Y-%m-%d %H:%M:%S").strftime('%I:%M')), font =font18, fill = 0)
    drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP+ (33*TEXT_VSPACE)+PIXEL)), "Sunset  @ "+str( datetime.datetime.strptime(fc_tomorrow['sunset'], "%Y-%m-%d %H:%M:%S").strftime('%I:%M')), font =font18, fill = 0)
    drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP+ (37*TEXT_VSPACE))), str( datetime.datetime.strptime(fc_tomorrow['Day'], '%Y-%m-%d').strftime('%A'))+", "+ str(fc_tomorrow['Day'] ), font =font12, fill = 0)

    # Right Bottom  Rectangle
    DROP = DROP + PIXEL + BOX_DEPTH
    # Day-After forecast
    #drawblack.rectangle((RTOP_HL, DROP, RTOP_HR, (DROP + BOX_DEPTH)), outline = 0)
    # Day Description
    drawblack.rectangle(((RTOP_HL+2*PIXEL), DROP+PIXEL, (RTOP_HR - 2*TEXT_HSPACE), (DROP + PIXEL+ 5*TEXT_VSPACE)), outline = 0,fill=0)
    drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP+TEXT_VSPACE-PIXEL-PIXEL)),(str(datetime.datetime.strptime(fc_dayafter['Day'], '%Y-%m-%d').strftime('%A')))+" expect", font =font20, fill = 1)
    # Forecast description
    if len(fc_dayafter['weather']) > 14:
        drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP + (5*TEXT_VSPACE))),str(fc_dayafter['weather']), font =font20, fill = 0)
    elif len(fc_dayafter['weather']) > 12:
        drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP + (5*TEXT_VSPACE))),str(fc_dayafter['weather']), font =font24, fill = 0)
    else:
        drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP + (5*TEXT_VSPACE))),str(fc_dayafter['weather']), font =font32, fill = 0)
    # Icon
    #response = requests.get("https://openweathermap.org/img/wn/"+fc_dayafter['icon']+"@2x.png")
    #image_from_url = Image.open(BytesIO(response.content)).convert("RGBA")
    #HBlackimage.paste(image_from_url, ((RTOP_HL + (3*TEXT_HSPACE)),(DROP+ (7*TEXT_VSPACE))), image_from_url)
    png = Image.open(os.path.join(picdir, fc_dayafter['icon']+"@2x.png")).convert("RGBA")
    HBlackimage.paste(png, ((RTOP_HL + (3*TEXT_HSPACE)),(DROP+(6*TEXT_VSPACE))), png)
    # Big temps
    drawblack.text (((RTOP_HL + TEXT_HSPACE+TEXT_VSPACE),(DROP +(20*TEXT_VSPACE))),str(fc_tomorrow['min'])+"-"+str(fc_dayafter['max'])+degree_sign+"f", font =font40, fill = 0)
    # small details
    drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP+ (30*TEXT_VSPACE))), "Sunrise @ "+str( datetime.datetime.strptime(fc_dayafter['sunrise'],"%Y-%m-%d %H:%M:%S").strftime('%I:%M')), font =font18, fill = 0)
    drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP+ (33*TEXT_VSPACE)+PIXEL)), "Sunset  @ "+str( datetime.datetime.strptime(fc_dayafter['sunset'], "%Y-%m-%d %H:%M:%S").strftime('%I:%M')), font =font18, fill = 0)
    drawblack.text (((RTOP_HL + TEXT_HSPACE),(DROP+ (37*TEXT_VSPACE))), str( datetime.datetime.strptime(fc_dayafter['Day'], '%Y-%m-%d').strftime('%A'))+", "+ str(fc_dayafter['Day'] ), font =font12, fill = 0)

    #drawblack.text((10, 0), 'hello world', font = font24, fill = 0)
    #drawblack.text((150, 200), 'How do I look?', font = font35, fill = 0)
    #drawred.line((20, 50, 70, 100), fill = 0)
    #drawblack.line((70, 50, 20, 100), fill = 0)
    #drawblack.rectangle((1, 252, 352, 452), outline = 0)
    #drawblack.line((165, 50, 165, 100), fill = 0)
    #drawred.line((140, 75, 190, 75), fill = 0)
    #drawblack.arc((140, 50, 190, 100), 0, 360, fill = 0)
    #drawred.rectangle((80, 50, 130, 100), fill = 0)
    #drawblack.chord((200, 50, 250, 100), 0, 360, fill = 0)
    logging.info(" image prepared...")
    epd.display_Base(epd.getbuffer(HBlackimage), epd.getbuffer(HRedimage))
    time.sleep(30)
    epd.sleep()

    
except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd.sleep()
    epd13in3b.epdconfig.module_exit(cleanup=True)
    exit()

############################################################################

'''
try:
    logging.info("Writing Tempest Weather Data")

    # Drawing on the Horizontal image
    logging.info("1.Drawing on the Horizontal image...")
    Himage = Image.new('1', (epd.width, epd.height), 255)  # 255: clear the frame
    draw = ImageDraw.Draw(Himage)
    #draw.text((10, 0), 'hello world, I am ' + myip, font = font18, fill = 0)

    ####### the RECTANGLES of DATA
    #### top left: air/temp
    draw.rectangle((3, 22, 399, 210), outline = 0)
    #draw.rectangle((264, 22, 532, 210), outline = 0)
    draw.rectangle((401, 22, 797, 210), outline = 0)

    
    ### ### Left Rectangle

    # small left second column
    draw.text ((250,120),'Gusts: '+ str(windgust)+'mph' , font =font18, fill = 0)
    draw.text ((250,140), str(rw_speed)+'mph' , font =font18, fill = 0)
    draw.text ((250,160), str(rw_dir) , font =font18, fill = 0)

    draw.text ((250,180), 'Avg: '+str(windavg)+'mph' , font =font18, fill = 0)


    ### ### Right Rectangle
    #Main
    draw.text ((410,15), str(uv)+' uv' , font =font100, fill = 0)
    if len(str(lux)) > 5:
        draw.text ((410,120), str(lux)+' lux' , font =font40, fill = 0)
    else:
        draw.text ((410,120), str(lux)+' lux' , font =font65, fill = 0)

    #small right column
    #draw.text ((697,120), str(batt)+"v", font =font18, fill = 0)
    draw.text ((697,140), str(batt)+' v' , font =font18, fill = 0)
    draw.text ((697,160), str(rad)+' rad' , font =font18, fill = 0)

    #########################################################






    #### bottom right
    # precipitation and lightning
    draw.rectangle((535, 213, 798, 475), outline = 0)

    # Uncomment these to test this module
    #do_precip=True
    #do_strike=True

    ## Top section of the lower rectangle:  precipation or forecast
    if (do_precip == False) and (do_strike == False):
        # Do the dayafter forecast pt 1
        if "snow" in fc_dayafter['weather']:
            jpg = Image.open(os.path.join(picdir, 'snow_light100.jpg'))
            Himage.paste(jpg, (693,218))
        elif "rain" in fc_dayafter['weather']:
            jpg = Image.open(os.path.join(picdir, 'rain100.jpg'))
            Himage.paste(jpg, (438,250))
        elif "hail" in fc_dayafter['weather']:
            jpg = Image.open(os.path.join(picdir, 'hail150.jpg'))
            Himage.paste(jpg, (438,250))
        elif "lightning" in fc_dayafter['weather']:
            jpg = Image.open(os.path.join(picdir, 'lightning75.jpg'))
            Himage.paste(jpg, (438,280))
        draw.text ((545,219),(str(datetime.datetime.strptime(fc_dayafter['Day'], '%Y-%m-%d').strftime('%A')))+" expect", font =font24, fill = 0)
        draw.text ((555,260),str(fc_dayafter['weather']), font =font32, fill = 0)
        draw.text ((555,310),str(fc_dayafter['min'])+"-"+str(fc_dayafter['max'])+degree_sign+"f", font =font32, fill = 0)
        draw.text ((598,406), "Sunrise @ "+str( datetime.datetime.strptime(fc_dayafter['sunrise'],"%Y-%m-%d %H:%M:%S").strftime('%I:%M')), font =font18, fill = 0)
        draw.text ((598,428), "Sunset  @ "+str( datetime.datetime.strptime(fc_dayafter['sunset'], "%Y-%m-%d %H:%M:%S").strftime('%I:%M')), font =font18, fill = 0)
        draw.text ((598,450), str( datetime.datetime.strptime(fc_dayafter['Day'], '%Y-%m-%d').strftime('%A'))+", "+ str(fc_dayafter['Day'] ), font =font18, fill = 0)
    else:
        draw.text ((545,219),"Recent events", font =font24, fill = 0)


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
        
        #preciptype ="snow"

        if preciptype == "hail":
            jpg = Image.open(os.path.join(picdir, 'hail150.jpg'))
            Himage.paste(jpg, (685,220))
        if preciptype == "rain":
            jpg = Image.open(os.path.join(picdir, 'rain100.jpg'))
            Himage.paste(jpg, (685,220))
        if preciptype == "snow":
            jpg = Image.open(os.path.join(picdir, 'snow_light100.jpg'))
            Himage.paste(jpg, (693,218))
        draw.text ((555,275), str(preciptype)+" at "+
                (format(datetime.datetime.fromtimestamp(strike[0]).strftime("%H:%M"))), font =font24, fill = 0)
        draw.text ((555,300), "Totals "+str(precipmm), font =font20, fill = 0)
        draw.line((555,340, 655, 340), fill = 0,width=3)

    # Bottom Half 565x365
    if do_strike == True:
        jpg = Image.open(os.path.join(picdir, 'lightning75.jpg'))
        Himage.paste(jpg, (700,340))
        miles=round(strike[1] * 0.621371,1)
        print ("Lightning strike in last 60 minutes ",(format(datetime.datetime.fromtimestamp(strike[0]).strftime("%H:%M"))),"; distance ",miles)
        draw.text ((555,350),"dist: "+ str(miles)+' miles' , font =font24, fill = 0)
        draw.text ((555,385), "At "+(format(datetime.datetime.fromtimestamp(strike[0]).strftime("%H:%M"))), font =font24, fill = 0)


    epd.display(epd.getbuffer(Himage))
    logging.info("Goto Sleep...")
    epd.sleep()

        #draw.line((552, 360, 542, 380), fill = 0,width=3)
        #draw.line((542, 380, 552, 380), fill = 0,width=3)
        #draw.line((552, 380, 542, 400), fill = 0,width=3)
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
global forecast_dayafter, forecast_today, forecast_tomorrow, fw_download, fw_ipaddr, fw_lastdate, fw_upload, tempest_device_status, tempest_evt_precip, tempest_evt_strike, tempest_hub_status, tempest_last_precipitation, tempest_obs_last, tempest_obs_st, tempest_rapid_wind
    global fw_lastdate, fw_ipaddr, fw_upload, fw_download
        print("read fw_upload value updated to ",str(fw_upload))
        global forecast_dayafter, forecast_today, forecast_tomorrow, fw_download, fw_ipaddr, fw_lastdate, fw_upload, tempest_device_status, tempest_evt_precip, tempest_evt_strike, tempest_hub_status, tempest_last_precipitation, tempest_obs_last, tempest_obs_st, tempest_rapid_wind
                    upload = fw_upload 
                    upload  = f"{ (fw_upload/125000):.2f}"
                    upload = fw_upload 
                    upload  = f"{ (fw_upload/125000):.2f}"
                    #fw_upload= f"{ (jsondata['upload']['bandwidth']/125000):.2f}"
                    fw_upload= jsondata['servers'][0]['ul_speed']
                    rds.set('fw_upload', fw_upload)
                        print("UpLoad speed is "+ str(fw_upload))
'''
