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
import urllib3

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
if debug > 1:
    print (" Past time for precip comparison ",past)

################################
# Tempest Data from redis
import ast
conditions=ast.literal_eval(rds.get('obs_st').decode("utf-8"))
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

last_conditions=ast.literal_eval(rds.get('obs_last').decode("utf-8"))
last_update = format(datetime.datetime.fromtimestamp(last_conditions[0]))
last_pressure = round(last_conditions[6],1)
if debug > 2:
    print ("Raw observation data: ",str(last_conditions),"\nUpdated at: ",str(last_update))

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
precip_time=format(datetime.datetime.fromtimestamp(precip[0]))

if debug > 2:
    print ("Raw precipation observation data: ",precip,"\nUpdated at: ",str(precip_time),"/",precip[0])
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


####################################################
logging.basicConfig(level=logging.DEBUG)

try:
    logging.info("Writing Tempest Weather Data")
    epd = epd7in5_V2.EPD()
    
    logging.info("init and Clear")
    epd.init()
    epd.Clear()

    font100 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 100)
    font65 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 65)
    font40 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 40)
    font32 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 32)
    font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
    font20 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 20)
    font18 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 18)

    # Drawing on the Horizontal image
    logging.info("1.Drawing on the Horizontal image...")
    Himage = Image.new('1', (epd.width, epd.height), 255)  # 255: clear the frame
    draw = ImageDraw.Draw(Himage)
    draw.text((10, 0), 'hello world, I am ' + myip, font = font18, fill = 0)
    draw.text((400, 0), 'Conditions updated at ' + time_update, font = font18, fill = 0)

    ####### the RECTANGLES of DATA
    #### top left: air/temp
    draw.rectangle((3, 22, 399, 210), outline = 0)
    #draw.rectangle((264, 22, 532, 210), outline = 0)
    draw.rectangle((401, 22, 797, 210), outline = 0)

    
    ### ### Left Rectangle
    # Temp in big letters left box
    # Main
    draw.text ((11,15), str(temp) + degree_sign +'f', font =font100, fill = 0)
    # small left first column
    draw.text ((12,120), str(humid) + '% RH', font =font32, fill = 0)
    if last_pressure < pressure:
        draw.text ((12,155), '\u2191'+" "+str(pressure) + 'mb', font =font32, fill = 0)
    elif last_pressure > pressure:
        draw.text ((12,155), '\u2193'+" "+str(pressure) + 'mb', font =font32, fill = 0)
    #draw.text ((24,155), " "+str(pressure) + 'mb', font =font32, fill = 0)

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

    #### bottom left: today forecast
    draw.rectangle((2, 213, 261, 475), outline = 0)
    if "snow" in fc_today['weather']:
        jpg = Image.open(os.path.join(picdir, 'snow_light100.jpg'))
        Himage.paste(jpg, (145,225))
    elif "rain" in fc_today['weather']:
        jpg = Image.open(os.path.join(picdir, 'rain100.jpg'))
        Himage.paste(jpg, (145,225))
    elif "hail" in fc_today['weather']:
        jpg = Image.open(os.path.join(picdir, 'hail150.jpg'))
        Himage.paste(jpg, (145,225))
    elif "lightning" in fc_today['weather']:
        jpg = Image.open(os.path.join(picdir, 'lightning75.jpg'))
        Himage.paste(jpg, (145,225))
    draw.text ((7,219),"Forecast Today: ", font =font24, fill = 0)
    # watch length of fc_today-weather
    if len(fc_today['weather']) > 14:
        draw.text ((15,258),str(fc_today['weather']), font =font24, fill = 0)
    elif len(fc_today['weather']) > 12:
        draw.text ((15,258),str(fc_today['weather']), font =font32, fill = 0)
    else: 
        draw.text ((15,258),str(fc_today['weather']), font =font40, fill = 0)

    draw.text ((25,310),str(fc_today['min'])+"-"+str(fc_today['max'])+degree_sign+"f", font =font40, fill = 0)
    draw.text ((60,406), "Sunrise @ "+str( datetime.datetime.strptime(fc_today['sunrise'],"%Y-%m-%d %H:%M:%S").strftime('%I:%M')), font =font18, fill = 0)
    draw.text ((60,428), "Sunset  @ "+str( datetime.datetime.strptime(fc_today['sunset'], "%Y-%m-%d %H:%M:%S").strftime('%I:%M')), font =font18, fill = 0)

    draw.text ((60,450), str( datetime.datetime.strptime(fc_today['Day'], '%Y-%m-%d').strftime('%A'))+", "+ str(fc_today['Day'] ), font =font18, fill = 0)



    #### bottom middle: tomorrow forecast
    draw.rectangle((264, 213, 532, 475), outline = 0)
    if "snow" in fc_tomorrow['weather']:
        jpg = Image.open(os.path.join(picdir, 'snow_light100.jpg'))
        Himage.paste(jpg, (430,225))
    elif "rain" in fc_tomorrow['weather']:
        jpg = Image.open(os.path.join(picdir, 'rain100.jpg'))
        Himage.paste(jpg, (438,250))
    elif "hail" in fc_tomorrow['weather']:
        jpg = Image.open(os.path.join(picdir, 'hail150.jpg'))
        Himage.paste(jpg, (438,250))
    elif "lightning" in fc_tomorrow['weather']:
        jpg = Image.open(os.path.join(picdir, 'lightning75.jpg'))
        Himage.paste(jpg, (438,280))
    draw.text ((272,219),(str(datetime.datetime.strptime(fc_tomorrow['Day'], '%Y-%m-%d').strftime('%A')))+" expect", font =font24, fill = 0)
    if len(fc_tomorrow['weather']) > 14:
        draw.text ((290,258),str(fc_tomorrow['weather']), font =font24, fill = 0)
    elif len(fc_tomorrow['weather']) > 12:
        draw.text ((290,258),str(fc_tomorrow['weather']), font =font32, fill = 0)
    else:
        draw.text ((290,258),str(fc_tomorrow['weather']), font =font40, fill = 0)

    draw.text ((290,310),str(fc_tomorrow['min'])+"-"+str(fc_tomorrow['max'])+degree_sign+"f", font =font40, fill = 0)

    draw.text ((330,406), "Sunrise @ "+str( datetime.datetime.strptime(fc_tomorrow['sunrise'],"%Y-%m-%d %H:%M:%S").strftime('%I:%M')), font =font18, fill = 0)
    draw.text ((330,428), "Sunset  @ "+str( datetime.datetime.strptime(fc_tomorrow['sunset'], "%Y-%m-%d %H:%M:%S").strftime('%I:%M')), font =font18, fill = 0)
    draw.text ((330,450), str( datetime.datetime.strptime(fc_tomorrow['Day'], '%Y-%m-%d').strftime('%A'))+", "+ str(fc_tomorrow['Day'] ), font =font18, fill = 0)



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
