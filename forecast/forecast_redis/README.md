## About this program
This utility should be scheduled in cron to run on your desired frequency. It will retrieve forecast data from OpenWeather and/or Tempest and insert it into the redis server specified.

## Configuration 
Edit the config.ini file provide a few key pieces of information based on the data in sample, test, and schedule in cron.

## Redis Configuration
The redis server you use does not have to be local to this system running the cron, but most commonly it is, or at least that is the easiest solution.

## OpenWeather
The OpenWeather has a free API program for home development use. Obtain a token, and determine the lat/long of your location and fill in appropriately.

Enable the OpenWeather gathering by setting Do_OW to 1 or true, or anything that evaluates as true.

This is currently the forecast data I am using, but am comparing to Tempest forecast and may switch in the future.

### Redis Data Added
The OpenWeather data is stored in three "forecast" tables in json structure format.
- forecast_today
- forecast_tomorrow
- forecast_dayafter

The  output from OpenWeather is heavily modified and it will resemble:
$ redis-cli get forecast_today
"{\"Day\": \"2026-02-14\", \"sunrise\": \"2026-02-14 07:07:21\", \"sunset\": \"2026-02-14 17:55:12\", \"moonrise\": \"2026-02-14 05:35:00\", \"moonset\": \"2026-02-14 15:04:00\", \"moonphase\": \"0.91\", \"min\": \"31\", \"max\": \"57\", \"weather\": \"clear sky\", \"icon\": \"01d\"}"



## Tempest API
Use the Tempest API site to configure and generate a sample API URL. The generated URL will have your station ID, API key, and data scale configuration.

Enable Tempest gathering by setting Do_Tempest to 1 or true.

The forecast object returned from Tempest endpoint is inserted in entirety in redis. This provides a 10 day outlook through the daily array and hourly array.

More information here: https://weatherflow.github.io/Tempest/api/swagger/#!/forecast/getBetterForecast

