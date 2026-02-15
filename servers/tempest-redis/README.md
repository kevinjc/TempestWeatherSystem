## Purpose

This program needs to run continually and have access to the network device of the system. It will monitor for UDP broadcasts from the Tempest base station that contain Tempest weather and station related data.

## Data processing
The UDP transmissions from the Tempest base station are processing into a JSON structured before storing into Redis.

### UDP Data Definitions
The Tempest Developer documentation describe the various UDP messages. https://weatherflow.github.io/Tempest/api/udp/v171/

All the messages described to do not apply to the Tempest system, see below for likely keys and data added.

### Storage Structure

#### "tempest_evt_strike"
This will present as an array with three elements of data:
- epoch time of the strike
- distance to strike
- energy of the strike


#### "tempest_evt_precip"
This contains epoch time of the precipitation. That is all that is sent with the event.


#### "tempest_last_precipitation"
This is added for clarity, it is a string of the value "rain" when there is evt_precip.


#### "tempest_obs_st"
#### "tempest_device_status"
#### "tempest_rapid_wind"
#### "tempest_hub_status"
#### "tempest_obs_last"


## Files
### config.ini
### redis_tempest.py
### tempest-redis.service
