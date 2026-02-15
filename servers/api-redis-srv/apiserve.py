# Python 3 server example
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler, HTTPServer
import time
import json
import sys
import os

import logging
import time
import traceback
from time import localtime, strftime
import configparser
import pprint
import select
import urllib3
import redis
import ast
from urllib.parse import urlparse

#from time import localtime, strftime

config = configparser.ConfigParser({'debug': '', 'Redis_Server': '', 'Redis_Port': '', 
                                    'Redis_Instance': '', 'Historical_Minutes': '',
                                    'Web_ServerName': '', 'Web_Port': ''
                                    })
config.read('config.ini')
debug=int(config.get('DEFAULT', 'debug'))
Redis_Server=(config.get('DEFAULT', 'Redis_Server'))
Redis_Port=(config.get('DEFAULT', 'Redis_Port'))
Redis_Instance=(config.get('DEFAULT', 'Redis_Instance'))
Redis_Historical_Minutes=(config.get('DEFAULT', 'Historical_Minutes'))
hostName=(config.get('DEFAULT', 'Web_ServerName'))
serverPort=int(config.get('DEFAULT', 'Web_Port'))

rds = redis.Redis(host=Redis_Server, port=Redis_Port, db=Redis_Instance)
if debug >0:
    print("Debug logs enabled, level ",debug)

import time

global forecast_dayafter, forecast_today, forecast_tomorrow, tempest_forecast, fw_download, fw_ipaddr, fw_lastdate, fw_upload, tempest_device_status, tempest_evt_precip, tempest_evt_strike, tempest_hub_status, tempest_last_precipitation, tempest_obs_last, tempest_obs_st, tempest_rapid_wind

def GetBandwidth():
    global fw_lastdate, fw_ipaddr, fw_upload, fw_download
    fw_lastdate=rds.get('fw_lastdate').decode("utf-8")
    fw_ipaddr=rds.get('fw_ipaddr').decode("utf-8")
    fw_upload=float(rds.get('fw_upload').decode("utf-8"))
    fw_download=float(rds.get('fw_download').decode("utf-8"))
    if debug > 2:
        print("read fw_ipaddr value updated to ",fw_ipaddr)
        print("read fw_upload value updated to ",str(fw_upload))
        print("read fw_lastdate value updated to ",fw_lastdate)
        print("read fw_download value updated to ",str(fw_download))

def GetForecast():
    global forecast_dayafter, forecast_today,forecast_tomorrow, tempest_forecast
    forecast_dayafter = ast.literal_eval(rds.get('forecast_dayafter').decode("utf-8"))
    forecast_today = ast.literal_eval(rds.get('forecast_today').decode("utf-8"))
    forecast_tomorrow = ast.literal_eval(rds.get('forecast_tomorrow').decode("utf-8"))
    tempest_forecast = ast.literal_eval(rds.get('tempest_forecast').decode("utf-8"))
    if debug > 1:
        print("forecast for day after: ",forecast_dayafter)
        print("forecast for today: ",forecast_today)
        print("forecast for tomorrow: ",forecast_tomorrow)
        print(" today weather: ",forecast_today['weather'])

def GetTempest():
    global tempest_device_status, tempest_evt_precip, tempest_evt_strike, tempest_hub_status, tempest_last_precipitation, tempest_obs_last, tempest_obs_st, tempest_rapid_wind
    tempest_device_status = ast.literal_eval(rds.get('tempest_device_status').decode("utf-8"))
    tempest_evt_precip = rds.get('tempest_evt_precip').decode("utf-8")
    tempest_evt_strike = rds.get('tempest_evt_strike').decode("utf-8")
    tempest_hub_status = ast.literal_eval(rds.get('tempest_hub_status').decode("utf-8"))
    tempest_last_precipitation = rds.get('tempest_last_precipitation').decode("utf-8")
    tempest_obs_last = ast.literal_eval(rds.get('tempest_obs_last').decode("utf-8"))
    tempest_obs_st = ast.literal_eval(rds.get('tempest_obs_st').decode("utf-8"))
    tempest_rapid_wind = ast.literal_eval(rds.get('tempest_rapid_wind').decode("utf-8"))
    if debug > 2:
        print("tempest data device_status: ",tempest_device_status)
        print("tempest data evt_precip: ",tempest_evt_precip)
        print("tempest data evt_strike: ",tempest_evt_strike)
        print("tempest data hub_status: ",tempest_hub_status)
        print("tempest data last_precipitation: ",tempest_last_precipitation)
        print("tempest data obs_last: ",tempest_obs_last)
        print("tempest data obs_st: ",tempest_obs_st)
        print("tempest data rapid_wind: ",tempest_rapid_wind)

class MyServer(ThreadingHTTPServer):
    def __init__(self, address, handler): 
        super().__init__(address, handler)


class myHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global forecast_dayafter, forecast_today, forecast_tomorrow, fw_download, fw_ipaddr, fw_lastdate, fw_upload, tempest_device_status, tempest_evt_precip, tempest_evt_strike, tempest_hub_status, tempest_last_precipitation, tempest_obs_last, tempest_obs_st, tempest_rapid_wind
        #print("agent was ", self.headers['User-Agent'])
        if 'application/json' in self.headers['Accept']: 
            if debug > 0:
                print(" responding in json")
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            if 'bandwidth' in self.path:
                GetBandwidth()
                query = urlparse(self.path).query or "format=kb"
                query_components = dict(qc.split("=") for qc in query.split("&"))
                if 'bytes' == query_components['format']:
                    print(" seeing query string for format of bytes: "+query)
                format = self.headers.get('Format') or query_components["format"] or "kb"
                if debug > 0:
                    print("the format header value " +format)
                if 'bytes' == format:
                    upload = fw_upload 
                    download = fw_download
                else:
                    upload  = f"{ (fw_upload/125000):.2f}"
                    download= f"{ (fw_download/125000):.2f}"

                body = { 'upload': upload, 'download': download, 'ipaddress': fw_ipaddr, 'lastdate': fw_lastdate}
                self.wfile.write(json.dumps(body, indent=4).encode("utf-8"))
            if 'weather' in self.path:
                GetTempest()
                GetForecast()
                body = { 'tempest': { 'device_status': tempest_device_status, 'evt_precip': tempest_evt_precip, 
                        'evt_strike': tempest_evt_strike, 'hub_status': tempest_hub_status,
                        'last_precipitation': tempest_last_precipitation, 'rapid_wind': tempest_rapid_wind,
                        'obs_st': tempest_obs_st , 'obs_last': tempest_obs_last },
                        'forecast': {'today': forecast_today, 'tomorrow': forecast_tomorrow, 
                                     'dayafter': forecast_dayafter,
                                     'tempest': tempest_forecast }
                        }
                self.wfile.write(json.dumps(body, indent=4).encode("utf-8"))
            if 'tempest' in self.path:
                GetTempest()
                body = { 'device_status': tempest_device_status, 'evt_precip': tempest_evt_precip, 
                        'evt_strike': tempest_evt_strike, 'hub_status': tempest_hub_status,
                        'last_precipitation': tempest_last_precipitation, 'rapid_wind': tempest_rapid_wind,
                        'obs_st': tempest_obs_st , 'obs_last': tempest_obs_last
                        }
                self.wfile.write(json.dumps(body, indent=4).encode("utf-8"))
            if 'forecast' in self.path:
                GetForecast()
                body = { 'today': forecast_today, 'tomorrow': forecast_tomorrow, 
                        'dayafter': forecast_dayafter, 'tempest': tempest_forecast }
                self.wfile.write(json.dumps(body, indent=4).encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            if debug > 0:
                print(" responding in html")
            self.end_headers()
            if '/forecast' in self.path:
                GetForecast()
                self.wfile.write(bytes("<html><head><title>Redis Forecast Data here</title></head>", "utf-8"))
                self.wfile.write(bytes("<body><h3> | <a href='/'>Home</a> | <a href='/bandwidth'>Bandwidth</a> "+
                    " | <a href='/tempest'>Tempest Weather Data</a> | <i>Forecast</i> "+
                    " | <a href='/help'>Help</a> |</h3>","utf-8"))
                # {'Day': '2025-03-24', 'sunrise': '2025-03-24 07:14:07', 
                #'sunset': '2025-03-24 19:32:05', 'min': '51', 'max': '63', 'weather': 'light rain'}.
                self.wfile.write(bytes("<p><b>Today</b>, expect %s. The low about %s, high around %s. The sun will shine from %s to %s.</p>"
                                       %( forecast_today['weather'], forecast_today['min'], forecast_today['max'], 
                                       str(forecast_today['sunrise']).split()[1],
                                       str(forecast_today['sunset']).split()[1] ),"utf-8"))
                self.wfile.write(bytes("<p>Tomorrow, it <i>might</i> be %s.</p>" % forecast_tomorrow['weather'],"utf-8"))
                self.wfile.write(bytes("<p>On the day after, <u>look for</U> %s.</p>" % forecast_dayafter['weather'],"utf-8"))
            elif '/tempest' in self.path:
                #GetBandwidth()
                self.wfile.write(bytes("<html><head><title>Redis Tempest Data here</title></head>", "utf-8"))
                self.wfile.write(bytes("<body><h3> | <a href='/'>Home</a> | <a href='/bandwidth'>Bandwidth</a> "+
                    " | <i>Tempest Weather Data</i> | <a href='/forecast'>Forecast</a> "+
                    " | <a href='/help'>Help</a> |</h3>","utf-8"))
            elif '/bandwidth' in self.path:
                GetBandwidth()
                query = urlparse(self.path).query or "format=kb"
                query_components = dict(qc.split("=") for qc in query.split("&"))
                if 'bytes' == query_components['format']:
                    print(" seeing query string for format of bytes: "+query)
                format = self.headers.get('Format') or query_components["format"] or "kb"
                if debug > 0:
                    print("the format header value " +format)
                if 'bytes' == format:
                    upload = fw_upload 
                    download = fw_download
                else:
                    upload  = f"{ (fw_upload/125000):.2f}"
                    download= f"{ (fw_download/125000):.2f}"
                self.wfile.write(bytes("<html><head><title>Redis SpeedTest Data here</title></head>", "utf-8"))
                self.wfile.write(bytes("<body><h3> | <a href='/'>Home</a> | <i>Bandwidth</i> "+
                    " | <a href='/tempest'>Tempest Weather Data</a> | <a href='/forecast'>Forecast</a> "+
                    " | <a href='/help'>Help</a> |</h3>","utf-8"))
                self.wfile.write(bytes("<p>Last Request: ","utf-8"))
                self.wfile.write(bytes("<ul><li>Upload: %s" % upload, "utf-8"))
                self.wfile.write(bytes("</li><li>Download: %s" % download, "utf-8"))
                self.wfile.write(bytes("</li><li>Date: %s" % fw_lastdate, "utf-8"))
                self.wfile.write(bytes("</li><li>IP Address: %s" % fw_ipaddr, "utf-8"))
                self.wfile.write(bytes("</li><li>Your user-agent : %s" % self.headers['user-agent'] , "utf-8")) 
                self.wfile.write(bytes("</li></ul></p>" , "utf-8"))
            elif '/help' in self.path:
                self.wfile.write(bytes("<html><head><title>Redis Data Helper</title></head>", "utf-8"))
                self.wfile.write(bytes("<body><h3> | <a href='/'>Home</a> | <a href='/bandwidth'>Bandwidth</a> "+
                    " | <a href='/tempest'>Tempest Weather Data</a> | <a href='/forecast'>Forecast</a> "+
                    " | <i>Help</i> |</h3>","utf-8"))
                self.wfile.write(bytes("<body>Post the following:", "utf-8"))
                self.wfile.write(bytes("<pre>{\"type\":\"result\",\"timestamp\":\"2025-02-19T22:30:15Z\",\"ping\":{\"jitter\":0.193,\"latency\":3.194},\"download\":{\"bandwidth\":116231842,\"bytes\":419550760,\"elapsed\":3606},\"upload\":{\"bandwidth\":117566361,\"bytes\":447455104,\"elapsed\":3810},\"packetLoss\":0,\"isp\":\"LUMOS Networks, Inc.\",\"interface\":{\"internalIp\":\"216.98.83.236\",\"name\":\"eth1\",\"macAddr\":\"00:E0:4C:B5:6E:B1\",\"isVpn\":false,\"externalIp\":\"216.98.83.236\"},\"server\":{\"id\":7085,\"name\":\"Lumos Fiber\",\"location\":\"Waynesboro, VA\",\"country\":\"United States\",\"host\":\"speedtest.lumos.net\",\"port\":8080,\"ip\":\"64.4.117.62\"},\"result\":{\"id\":\"c03131c1-3533-4766-a3a2-a3b5b3994a85\",\"url\":\"https://www.speedtest.net/result/c/c03131c1-3533-4766-a3a2-a3b5b3994a85\"}}</pre>", "utf-8"))
                self.wfile.write(bytes("<p>That is all.</p>", "utf-8"))
            else:
                self.wfile.write(bytes("<html><head><title>Redis Data Server</title></head>", "utf-8"))
                self.wfile.write(bytes("<body><h3> | <a href='/'>Home</a> | <a href='/bandwidth'>Bandwidth</a> "+
                    " | <a href='/tempest'>Tempest Weather Data</a> | <a href='/forecast'>Forecast</a> "+
                    " | <a href='/help'>Help</a> |</h3>","utf-8"))
            self.wfile.write(bytes("<p>Request: %s</p>" % self.path, "utf-8"))
            self.wfile.write(bytes("</body></html>", "utf-8"))
            if debug > 0:
                print("was GET request")
    def do_POST(self): 
        body = {}
        if debug > 0:
            print("starting POST request")
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        length = int(self.headers.get('content-length'))
        if debug > 1:
            print("Content type is: ",self.headers['Content-Type'])
        if 'application/json' in self.headers['Content-Type']:
            #Load the JSON data
            jsondata = json.loads(self.rfile.read(length))
            # Check the data
            if 'servers' in jsondata and 'user_info' in jsondata:
                if debug > 1:
                    print("processing bandwidth data")
                if 'dl_speed' in jsondata['servers'][0] and 'ul_speed' in jsondata['servers'][0] and 'IP' in jsondata['user_info']:
                    fw_ipaddr= jsondata['user_info']['IP']
                    rds.set('fw_ipaddr', fw_ipaddr)
                    #fw_upload= f"{ (jsondata['upload']['bandwidth']/125000):.2f}"
                    fw_upload= jsondata['servers'][0]['ul_speed']
                    rds.set('fw_upload', fw_upload)
                    #fw_download= f"{ (jsondata['download']['bandwidth']/125000):.2f}"
                    fw_download= jsondata['servers'][0]['dl_speed']
                    rds.set('fw_download', fw_download)
                    clocktime=strftime("%H:%M:%S %Z", localtime())
                    clockday=strftime("%a %B %d", localtime())
                    fw_lastdate = clockday+"-"+clocktime
                    rds.set('fw_lastdate', fw_lastdate)
                    if debug > 2:
                        print("External IP is "+ fw_ipaddr)
                        print("UpLoad speed is "+ str(fw_upload))
                        print("DownLoad speed is "+ str(fw_download))
                    message = json.dumps({ 'success': True },indent=4).encode("utf-8")
                else:
                    message = json.dumps({'error':"Missing bandwidth value for upload or download"},
                                         indent=4).encode("utf-8")
            elif 'weather' in jsondata:
                if debug > 1:
                    print("processing weather data...")
                if 'forecast' in jsondata['weather']:
                    if debug >2:
                        print("forecast data in payload:",jsondata['weather']['forecast'])
                    if 'today' in jsondata['weather']['forecast']:
                        if debug >2:
                            print("  forecast today", jsondata['weather']['forecast']['today'])
                        rds.set('forecast_today', jsondata['weather']['forecast']['today'])
                    #5) "forecast_tomorrow"
                    if 'tomorrow' in jsondata['weather']['forecast']: 
                        if debug >2:
                            print ("  forecast tomorrow: ",jsondata['weather']['forecast']['tomorrow'])
                        rds.set('forecast_tomorrow', jsondata['weather']['forecast']['tomorrow'])
                    #10) "forecast_dayafter"
                    if 'dayafter' in jsondata['weather']['forecast']:
                        if debug >2:
                            print("  forecast dayafter: ",jsondata['weather']['forecast']['dayafter'])
                        rds.set('forecast_dayafter', jsondata['weather']['forecast']['dayafter'])
                    message = json.dumps({ 'success': True },indent=4).encode("utf-8")

                if 'tempest' in jsondata['weather']:
                    if debug > 2:
                        print("tempest data in payload:",jsondata['weather']['tempest'])
                    #2) "hub_status"
                    if 'hub_status' in jsondata['weather']['tempest']:
                        if debug > 2:
                            print ("  tempest hub status: ",jsondata['weather']['tempest']['hub_status'])
                        rds.set('tempest_hub_status', jsondata['weather']['tempest']['hub_status'])
                    #3) "device_status"
                    if 'device_status' in jsondata['weather']['tempest']:
                        if debug >2:
                            print ("  tempest device status: ",jsondata['weather']['tempest']['device_status'])
                        rds.set('tempest_device_status', jsondata['weather']['tempest']['device_status'])
                    #4) "last_precipitation"
                    if 'last_precipitation' in jsondata['weather']['tempest']:
                        if debug >2:
                            print ("  tempest last_precipitation status: ",jsondata['weather']['tempest']['last_precipitation'])
                        rds.set('tempest_last_precipitation', jsondata['weather']['tempest']['last_precipitation'])
                    # 6) "evt_strike"
                    if 'evt_strike' in jsondata['weather']['tempest']:
                        if debug >2:
                            print ("  tempest evt_strike status: ",jsondata['weather']['tempest']['evt_strike'])
                        rds.set('tempest_evt_strike', jsondata['weather']['tempest']['evt_strike'])
                    #7) "rapid_wind"
                    if 'rapid_wind' in jsondata['weather']['tempest']:
                        if debug >2:
                            print ("  tempest rapid_wind status: ",jsondata['weather']['tempest']['rapid_wind'])
                        rds.set('tempest_rapid_wind', jsondata['weather']['tempest']['rapid_wind'])
                    #8) "evt_precip"
                    if 'evt_precip' in jsondata['weather']['tempest']:
                        if debug >2:
                            print ("  tempest evt_precip status: ",jsondata['weather']['tempest']['evt_precip'])
                        rds.set('tempest_evt_precip', jsondata['weather']['tempest']['evt_precip'])
                    #9) "obs_st"
                    if 'obs_st' in jsondata['weather']['tempest']:
                        if debug >2:
                            print ("  tempest obs_st status: ",jsondata['weather']['tempest']['obs_st'])
                        rds.set('tempest_obs_st', jsondata['weather']['tempest']['obs_st'])
                    #11) "obs_last"
                    if 'obs_last' in jsondata['weather']['tempest']:
                        if debug >2:
                            print ("  tempest obs_last status: ",jsondata['weather']['tempest']['obs_last'])
                        rds.set('tempest_obs_last', jsondata['weather']['tempest']['obs_last'])
                    message = json.dumps({ 'success': True },indent=4).encode("utf-8")

            self.wfile.write(message)
        else:
            print("please send json and set content-type")
            message = "Missing proper json data"
            self.wfile.write(message, "utf8")

httpd = MyServer((hostName,serverPort),myHandler)
print(time.asctime(), "Start Server - %s:%s\n"%(hostName,serverPort))
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    pass
httpd.server_close()
print(time.asctime(),'Stop Server - %s:%s' %(hostName,serverPort))
