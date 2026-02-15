# importing the libraries
import requests
import json
import datetime
import datetime
import redis
import configparser

config = configparser.ConfigParser({'debug': '', 'Redis_Server': '', 'Redis_Port': '', 'Redis_Instance':'', 'Latitude': '', 'Longitude':'', 'APIkey':'' , 'URL': '', 'Do_OW': '', 'Do_Tempest':''})
config.read('config.ini')
Debug=int(config.get('DEFAULT', 'debug'))
Redis_Server=(config.get('DEFAULT', 'Redis_Server'))
Redis_Port=(config.get('DEFAULT', 'Redis_Port'))
Redis_Instance=(config.get('DEFAULT', 'Redis_Instance'))
APIkey=(config.get('OPENWEATHER', 'APIkey'))
lat=(config.get('OPENWEATHER', 'Latitude'))
lon=(config.get('OPENWEATHER', 'Longitude'))
Do_OW=bool((config.getboolean('OPENWEATHER', 'Do_OW')))
Do_Tempest=bool((config.getboolean('TEMPEST', 'Do_Tempest')) )
Tempest_URL=(config.get('TEMPEST', 'URL'))
if Debug > 0:
    print ("Get OpenWeather: "+str(Do_OW))
    print ("Get Tempest: "+str(Do_Tempest))

rds = redis.Redis(host=Redis_Server, port=Redis_Port, db=Redis_Instance)

# Get start of this day
Day_Start = datetime.datetime.now().strftime('%Y%m%d')

#### OpenWeather #####
if Do_OW:
    if Debug >0:
        print("Getting OpenWeather:")
    # API Call
    api_URL = ("https://api.openweathermap.org/data/3.0/onecall?lat=" + str(lat) + "&lon="+ str(lon) +"&exclude=current,minutely,hourly&units=imperial&appid="+APIkey)
    if Debug >1:
        print (" api_URL is :"+str(api_URL))
    api_Request = requests.get(api_URL)
    if Debug >3:
        print (" api_Request is :"+str(api_Request))
    api_Data = json.loads(api_Request.content)
    if Debug >2:
        print (str(api_Data))
        for key in api_Data.keys(): print ("  key: "+key)
    if Debug>3:
        print (" Daily 0:"+str(api_Data['daily'][0]))

    #######################
    # Let's Parse the Data
    Day_Count=0
    while Day_Count < 3:
        ext_Data = {}
        ext_Data['Day']= format(datetime.datetime.fromtimestamp(api_Data['daily'][Day_Count]['dt']).strftime('%Y-%m-%d'))
        ext_Data['sunrise']=str(format(datetime.datetime.fromtimestamp(api_Data['daily'][Day_Count]['sunrise']) ))
        ext_Data['sunset']=str( format(datetime.datetime.fromtimestamp(api_Data['daily'][Day_Count]['sunset']) ))
        ext_Data['moonrise']=str(format(datetime.datetime.fromtimestamp(api_Data['daily'][Day_Count]['moonrise']) ))
        ext_Data['moonset']=str( format(datetime.datetime.fromtimestamp(api_Data['daily'][Day_Count]['moonset']) ))
        ext_Data['moonphase']=str( api_Data['daily'][Day_Count]['moon_phase']) 
        ext_Data['min']=str(int(round(api_Data['daily'][Day_Count]['temp']['min'],0)))
        ext_Data['max']=str(int(round(api_Data['daily'][Day_Count]['temp']['max'],0)))
        ext_Data['weather']=str(api_Data['daily'][Day_Count]['weather'][0]['description']) 
        ext_Data['icon']=str(api_Data['daily'][Day_Count]['weather'][0]['icon']) 
        if Day_Count == 0:
            rds.set('forecast_today', json.dumps(ext_Data))
            if Debug >0:
                print ("Forecast for Today /"+ext_Data['Day'])
        if Day_Count == 1:
            rds.set('forecast_tomorrow', json.dumps(ext_Data))
            if Debug >0:
                print ("Forecast for Tomorrow /"+ext_Data['Day'])
        if Day_Count == 2:
            rds.set('forecast_dayafter', json.dumps(ext_Data))
            if Debug >0:
                print ("Forecast for day after /"+ext_Data['Day'])
        if Debug >0:
            print ("  sunrise: "+ext_Data['sunrise'])
            print ("  sunset :  "+ext_Data['sunset'])
            print ("  moonrise: "+ext_Data['moonrise'])
            print ("  moonset :  "+ext_Data['moonset'])
            print ("  moonphase :  "+ext_Data['moonphase'])
            print ("  temps  :  "+ext_Data['min'] +"/"+ext_Data['max'])
            print ("  Weather:  "+ext_Data['weather'])
        Day_Count+=1

########  Tempest Forecast Data ########
if Do_Tempest:
    if Debug > 0:
        print("Getting Tempest Data:")
    # API Call
    if Debug >1:
        print ("api_URL is :"+str(Tempest_URL))
    api_Request = requests.get(Tempest_URL)
    if Debug >3:
        print ("api_Request is :"+str(api_Request))
    api_Data = json.loads(api_Request.content)
    rds.set('tempest_forecast', json.dumps(api_Data['forecast']));
    if Debug >1:
        print (" Length Daily Forecast "+ str(len(api_Data['forecast']['daily'])));
        print (" Length Hourly Forecast "+ str(len(api_Data['forecast']['hourly'])));
    if Debug >2:
        print( " Dumping keys:")
        print (str(api_Data))
        for key in api_Data.keys(): print ("  "+key)
    if Debug>3:
        print (" Daily 0:"+str(api_Data['forecast']['daily'][0]))


