import socket
import select
import time
import struct
import pprint
import json
import datetime

# create broadcast listener socket
def create_broadcast_listener_socket(broadcast_ip, broadcast_port):

    b_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    b_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    b_sock.bind(('', broadcast_port))

    mreq = struct.pack("4sl", socket.inet_aton(broadcast_ip), socket.INADDR_ANY)
    b_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    return b_sock

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
            temp = data_json['obs'][0][7]
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
