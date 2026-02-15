# Kevin's Tempest Weather System
My modest system uses  few components that I personally like. It may not agree with everyone, but I do welcome constructive criticism and improvements. All clients use HTTP to fetch data in JSON format.

It uses a Redis database to store data. The only services that interact directly with the Redis data is the two Data Acquisition services and one data client server service.

The first Data Acquisition service will parse the Tempest UDP broadcasts and format into JSON before storing in Redis. The second Data Acquisition service will retrieve forecast data from the Internet, and with minimal parsing of the JSON data add it to the Redis database. This runs on schedule in cron on my RPI server.

The only Redis client is another server service, the api-redis server. This is an HTTP Server that retrieves the requested data from Redis and presents it in JSON payload to the client. It also accepts JSON formatted bandwidth data from your router if desired, and has an modest HTML front end.

## Hardware

### Weather System Hardware
The Tempest Weather System by WeatherFlow is required. This could be adapted to other WeatherFlow systems, at least as far as the API documentation demonstrates there are other systems that also provide UDP broadcasts for weather data.


### Client Display Hardware
I love Epaper displays. I think they are the bomb for a weather display, but do have a client that is an ESP32 with OLED display. After a year of running the OLED is seriously damaged, so not a great client.


### Client Hardware
The client hardware is a variety and can easily adapt to additional varieties. I love Raspberry Pis, but worry about failed SD cards and corrupt filesystems after an unexpected power outage so have begun moving to ESP32s as the computing system to drive the Epaper displays.


### Server Hardware
I use an Raspberry Pi 4 for my server. Any linux system will work, the only requirement is a stable network connection into the same network as the Tempest Base station so that it can hear the UDP broadcasts.


### Other Hardware
I use OpenWRT for my router, which has been a RPI4, but is currently another platform with dual 2.5GBE interfaces. I love OpenWRT for the ability to customize and run custom bits.

I have installed the GoLang speedtest libraries and have it send back bandwidth test results to the Redis API server. A client or two will refer to this data even if it is not technically part of the Tempest Weather System.
 

## servers
There are two server services running in my Tempest Weather System. These can run on the same system, I am using an RPI4 but a 3B is sufficient computing power. A Pi0 may even be enough, but I prefer an ethernet device instead of relying on WiFi here.


### Tempest UDP to Redis server
This python app needs to run as a service on the system that relies on the Redis and network layer being online. It listens for the UDP broadcasts from the Tempest base station, formats the data into JSON and stores it in Redis. It can log events to system logging if desired.


### Redis API Server Service
This python app runs as a service on the system and requires Redis and network layer being online. It handles client HTTP requests for data and interacts with Redis to return the data to the client in JSON format. There is also a basic HTML front end.


### forecast
This python app does not run as a service. Instead it is scheduled on the system to run at the desired intervals using cron. It retrieves forecast data from the internet and stores it in Redis for the clients, doing minimal processing of the forecast JSON data.


## clients
I have a clients available and it may not be simple but it is easy to adapt for new clients. They are in the majority different Epaper screens from Waveshare or Seeed. The first client display was to use a Waveshare 7.5 single color Epaper directly on the RPI server using Python. This has been superseded by ESP32 devices so that clients and server can be separated where the server is in network closet with a UPS and clients don't have a filesystem that can be corrupted on power outages.


### Pi Python Epaper 7.5 inch
The original display, a Pi0w ran this display for six years or so until I cracked the screen putting it another case I printed.
![picture of 7.5 inch Waveshare epaper](/pictures/Tempest_Pi_Python_weatherdisplay.jpg)

### Epaper 2.15 Black-White-Red
A new addition that I am no longer tweaking. This is an ESP32-s2mini running a Waveshare 2.15inch three color.
![mini epaper on top of a monitor](/pictures/Tempest_EPD_2in15_monitor topper.jpg)

### Heltek OLED mini 1inch
Using an OLED display given to me, but now damaged after about a year of continuous use and some serious burn-in/burn-out.
![oled mini display on top of a monitor](/pictures/Tempest_HeltekOLED.jpg)

### Pi Python 13.3 inch in Imac G4
New addition not yet finished, screen stopped working so a replacement must be acquired.
![large epaper in an Imac G4](/pictures/Tempest_Pi_13-3_imacg4.jpg)

### Seeed TRMNL DIY 7.5in Epaper
New addition, work in progress. I'm using the GFX libraries from demos, not happy with the blocky/pixelated text. Might try the Waveshare methods, should work, looks smoother.
![seeeed diy trmnl epaper display, incomplete](/pictures/Tempest_SeeedTRMNL-DIY.jpg)
