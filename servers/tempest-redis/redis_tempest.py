import socket
import select
import time
import struct
import json
import datetime
import redis
import configparser
import ast

import syslog
syslog.openlog('tempest')
#syslog.syslog(syslog.LOG_INFO, "Test message at INFO priority")

# https://weatherflow.github.io/Tempest/api/udp/v143/

# debug = 2
#Redis_Server = localhost
#Redis_Port = 6379
#Redis_Instance = 0

config = configparser.ConfigParser({'debug': '', 'Redis_Server': '', 'Redis_Port': '', 'Redis_Instance':''})
config.read('config.ini')
debug=int(config.get('DEFAULT', 'debug'))
Redis_Server=(config.get('DEFAULT', 'Redis_Server'))
Redis_Port=(config.get('DEFAULT', 'Redis_Port'))
Redis_Instance=(config.get('DEFAULT', 'Redis_Instance'))

rds = redis.Redis(host=Redis_Server, port=Redis_Port, db=Redis_Instance)

# Get some of the last entries in redis for comparison purposes
def get_dev_fwver():
    device_status=ast.literal_eval(rds.get('tempest_device_status').decode("utf-8"))
    dev_fwver = device_status['firmware_revision']
    return dev_fwver

def get_hub_fwver():
    hub_status=ast.literal_eval(rds.get('tempest_hub_status').decode("utf-8"))
    hub_fwver = hub_status['firmware_revision']
    return hub_fwver

def get_sensor_status():
    device_status=ast.literal_eval(rds.get('tempest_device_status').decode("utf-8"))
    sensor_status = device_status['sensor_status']
    return sensor_status


# create broadcast listener socket
def create_broadcast_listener_socket(broadcast_ip, broadcast_port):
    b_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    b_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    b_sock.bind(('', broadcast_port))
    mreq = struct.pack("4sl", socket.inet_aton(broadcast_ip), socket.INADDR_ANY)
    b_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return b_sock


# ip/port to listen to
BROADCAST_IP = '239.255.255.250'
BROADCAST_PORT = 50222

# create the listener socket
sock_list = [create_broadcast_listener_socket(BROADCAST_IP, BROADCAST_PORT)]
data_type = ""

# Perma-loop, enable while True
while True:
# Temp-loop, enable while data_type and comment while True
#while data_type != 'obs_st':
    # small sleep otherwise this will loop too fast between messages and eat a lot of CPU
    time.sleep(0.01)

    # wait until there is a message to read
    readable, writable, exceptional = select.select(sock_list, [], sock_list, 0)

    # for each socket with a message
    for s in readable:
        data, addr = s.recvfrom(4096)

        # the obs_st data has double square brackets`
        # this makes it easier to deal with
        data=data.replace(b'[[', b'[')
        data=data.replace(b']]', b']')
        
        # convert data to json
        data_json = json.loads(data)
        if debug > 0:
            print ( "Data type observed: ", data_json['type']  )
        if debug > 2:
            print(">>RAW DATA: ", data)

        if data_json['type'] == 'obs_st':
            data_type = "obs_st"
            if debug ==0:
                syslog.syslog(syslog.LOG_INFO, "Tempest Weather Observation, "+str((datetime.datetime.fromtimestamp(data_json['obs'][0]).strftime('%Y-%m-%d_%H:%M:%S') ) ))
            if debug >2:
                print ( str(datetime.datetime.fromtimestamp(data_json['obs'][0]).strftime('%Y-%m-%d_%H:%M:%S') ) )
            last=rds.get('tempest_obs_st')
            rds.set('tempest_obs_last', str(last))
            rds.set('tempest_obs_st', str(data_json['obs']))
            if data_json['obs'][13] == 0:
                rds.set('tempest_last_precipitation', str("none"))
            if data_json['obs'][13] == 1:
                rds.set('tempest_last_precipitation', str("rain"))
            if data_json['obs'][13] == 2:
                rds.set('tempest_last_precipitation', str("hail"))
            # Event time/epoch is data_json['obs'][0]
            # pressure = data_json['obs'][6]
            # temp = data_json['obs'][7]
            # humid = data_json['obs'][8]
            # lux = data_json['obs'][9]
            # uv = data_json['obs'][10]
            # rad = data_json['obs'][11]
            # batt = data_json['obs'][16]
            # interval = data_json['obs'][17]
            if debug > 0:
                print ("  Conditions at ", str(data_json['obs'][0]), " the weather readings are, temp: ", str(data_json['obs'][7]),  "  humidity: ", str(data_json['obs'][8]) )

            if debug > 1:
                print ( "  the observation: ", data_json['obs'] )


        elif data_json['type'] == 'rapid_wind':
            data_type = "ob"
            if debug >2:
                print ( str(datetime.datetime.fromtimestamp(data_json['ob'][0]).strftime('%Y-%m-%d_%H:%M:%S') ) )
            rds.set('tempest_rapid_wind', str(data_json['ob']))
            event_time=data_json['ob'][0]
            windspd =  data_json['ob'][1]
            winddir =  data_json['ob'][2] 
            if debug >0:
                print ("  Wind at time ", str(data_json['ob'][0]), ", speed is: ", str(data_json['ob'][1]),  "  from direction: ", str(data_json['ob'][2]) )

            if debug > 1:
                print ( "  the observation: ", data_json['ob'] )

        elif data_json['type'] == 'evt_strike':
            if debug ==0:
                syslog.syslog(syslog.LOG_INFO, "Tempest Event Strike, "+str((datetime.datetime.fromtimestamp(data_json['evt'][0]).strftime('%Y-%m-%d_%H:%M:%S') ) ))
            if debug >2:
                print ("Strike event detected!")
                print ("  ",str(datetime.datetime.fromtimestamp(data_json['evt'][0]).strftime('%Y-%m-%d_%H:%M:%S') ) )
            rds.set('tempest_evt_strike', str(data_json['evt']))
            if debug >1:
                print ( "  the observation: ", data_json['evt'] )

        elif data_json['type'] == 'evt_precip':
            if debug ==0:
                syslog.syslog(syslog.LOG_INFO, "Tempest Precipitation Event, "+str((datetime.datetime.fromtimestamp(data_json['evt'][0]).strftime('%Y-%m-%d_%H:%M:%S') ) ))
            if debug >2:
                print ( str(datetime.datetime.fromtimestamp(data_json['evt'][0]).strftime('%Y-%m-%d_%H:%M:%S') ) )
            rds.set('tempest_evt_precip', str(data_json['evt']))
            rds.set('tempest_last_precipitation', str("rain"))
            if debug > 1:
                print ( "  the observation: ", data_json['evt'] )

        elif data_json['type'] ==  'hub_status':
            if debug ==0:
                cur_fwver=get_hub_fwver()
                if cur_fwver != data_json['firmware_revision']:
                    syslog.syslog(syslog.LOG_INFO, "Tempest Hub Status, fwver "+str(data_json['firmware_revision']+", was ")+str(cur_fwver) )
            if debug >2:
                print ( str(datetime.datetime.fromtimestamp(data_json['timestamp']).strftime('%Y-%m-%d_%H:%M:%S') ) )
            rds.set('tempest_hub_status', str(data_json))
            if debug > 1:
                print ("  the observation: ", data_json['uptime'])

        elif data_json['type'] ==  'device_status':
            if debug ==0:
                cur_fwver=get_dev_fwver()
                if cur_fwver != data_json['firmware_revision']:
                    syslog.syslog(syslog.LOG_INFO, "Tempest Device FW version "+str(data_json['firmware_revision'])+", was "+str(cur_fwver) )
                sensor_status=get_sensor_status()
                if sensor_status != data_json['sensor_status']:
                    syslog.syslog(syslog.LOG_INFO, "Tempest Device Sensor Status "+str(data_json['sensor_status'])+", was "+str(sensor_status) )
            if debug >2:
                print ( str(datetime.datetime.fromtimestamp(data_json['timestamp']).strftime('%Y-%m-%d_%H:%M:%S') ) )
            rds.set('tempest_device_status', str(data_json))
            if debug > 1:
                print ("  the observation: ", data_json['uptime'])

        else:
            if debug ==0:
                syslog.syslog(syslog.LOG_INFO, "Unknown Tempest observation: "+str(data_json))
            if debug > 1:
                print ( "unknown observation keys: ", data_json.keys() )
                print(" "+data_json)


