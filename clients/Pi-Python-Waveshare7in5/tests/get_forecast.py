# https://www.geeksforgeeks.org/create-a-gui-for-weather-forecast-using-openweathermap-api-in-python/
# importing the libraries
import requests
import json
import datetime

APIkey="xxxxxxx"
lat=38.9189
lon=-104.7045
Debug=3

# API Call
api_URL = ("https://api.openweathermap.org/data/2.5/onecall?lat=" + str(lat) + "&lon="+ str(lon) +"&exclude=current,minutely,hourly&units=imperial&appid="+APIkey)
if Debug >2:
    print ("api_URL is :"+str(api_URL))
api_Request = requests.get(api_URL)
if Debug >2:
    print ("api_Request is :"+str(api_Request))
api_Data = json.loads(api_Request.content)
print (str(api_Data))
for key in api_Data.keys(): print (key)
print ("Daily 0:"+str(api_Data['daily'][0]))
Day_0= format(datetime.datetime.fromtimestamp(api_Data['daily'][0]['dt']))
print ("Forecast for "+Day_0)
print ("  sunrise: "+str( format(datetime.datetime.fromtimestamp(api_Data['daily'][0]['sunrise']) )))
print ("  sunset:  "+str( format(datetime.datetime.fromtimestamp(api_Data['daily'][0]['sunset']) )))
print ("  temps :  "+str(api_Data['daily'][0]['temp']['min']) +"/"+str(api_Data['daily'][0]['temp']['max']))
print (" Weather:  "+str(api_Data['daily'][0]['weather'][0]['main']) )

Day_1= format(datetime.datetime.fromtimestamp(api_Data['daily'][1]['dt']))
print ("Forecast for "+Day_1)
print ("Daily 1:"+str(api_Data['daily'][1]))
print ("Daily 1-sunrise:"+str(api_Data['daily'][1]['sunrise']))
