#include <Wire.h>  
#include "HT_SSD1306Wire.h"

#ifdef WIRELESS_STICK_V3
static SSD1306Wire  display(0x3c, 500000, SDA_OLED, SCL_OLED, GEOMETRY_64_32, RST_OLED); // addr , freq , i2c group , resolution , rst
#else
static SSD1306Wire  display(0x3c, 500000, SDA_OLED, SCL_OLED, GEOMETRY_128_64, RST_OLED); // addr , freq , i2c group , resolution , rst
#endif

#include <HTTPClient.h>
#include <Timezone.h>
#include <WeatherIcons_50pix.h>

#include <ArduinoJson.h>
#include <ArduinoJson.hpp>
#include <StreamUtils.h>

#include <WiFi.h>
#include <Wire.h>

#include <iostream>
#include <sstream>
/*
#include <iomanip>
#include <ctime>
*/

/**********************************************  WIFI Client *********************************

 * wifi client
 */
const char* ssid = "xxxxx";               //replace "xxxxxx" with your WIFI's ssid
const char* password = "xxxxx";  //replace "xxxxxx" with your WIFI's password

const char* dataUrl = "http://xxxxxx:8080/weather/";// replace "xxxxxx" with your server ip or hostname

TimeChangeRule myDST = { "EDT", Second, Sun, Mar, 2, -240 };  //Daylight time = UTC - 4 hours
TimeChangeRule mySTD = { "EST", First, Sun, Nov, 2, -300 };   //Standard time = UTC - 5 hours
Timezone myTZ(myDST, mySTD);

/************************************************  *********************************
 * Whether to use static IP
 */

#define USE_STATIC_IP false
#if USE_STATIC_IP
IPAddress staticIP(192, 168, 1, 22);
IPAddress gateway(192, 168, 1, 9);
IPAddress subnet(255, 255, 255, 0);
IPAddress dns1(8, 8, 8, 8);
IPAddress dns2(114, 114, 114, 114);
#endif

String LastTemp = "N/C";
String LastWifiStat = "--";
String LastTime = "--";
String LastDate = "--";
String LastWeatherForecast = "N/C";
String LastIconCode = "--";
bool LastDaylight = false;


/********************************************************************
* Images
*/
#define WiFi_width 15
#define WiFi_height 9
static unsigned char WiFi_bits[] = {
  0x00, 0x80, 0xe0, 0x83, 0xf8, 0x8f, 0xbc, 0x80, 0x84, 0xaa, 0xa4, 0xaa,
  0xfc, 0x80, 0xf8, 0x8f, 0xc0, 0x83
};


/*********************************************************************
 * setup wifi
 */
void setupWIFI() {
  display.clear();
  display.setFont(ArialMT_Plain_10);
  display.drawString(0, 0, "Connecting...");
  display.drawString(0, 10, String(ssid));
  display.display();

  //Connect to WiFi, delete old configuration, turn off WiFi, prepare to reconfigure

  WiFi.disconnect(true);
  delay(1500);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);

  WiFi.setAutoReconnect(true);  //Automatically reconnect after disconnecting WiFi ESP32 is not available

  //WiFi.setHostname(HOSTNAME);
  WiFi.begin(ssid, password);
#if USE_STATIC_IP
  WiFi.config(staticIP, gateway, subnet);
#endif

  //Wait for 5000ms, if not connected, continue

  byte count = 0;
  while (WiFi.status() != WL_CONNECTED && count < 10) {
    count++;
    delay(500);
    Serial.print(".");
  }

  display.clear();
//  display.setColor(WHITE);
//  display.setFont(ArialMT_Plain_10);
//  if (WiFi.status() == WL_CONNECTED) {
//    display.drawXbm(0, 0, WiFi_width, WiFi_height, WiFi_bits);
//  } else {
//    display.drawString(0, 0, "w:False");
//  }
//  display.display();
}

/******************************************************
 * arduino setup
 */
void setup() {

  display.init();
  display.clear();
  display.display();

  display.setContrast(255);
  Serial.begin(115200);
  // pinMode(36, OUTPUT);
  // digitalWrite(36,HIGH);

  while (!Serial) {
    ;  // wait for serial port to connect. Needed for native USB port only
  }

  Serial.println("Initialize...");

  setupWIFI();
}

/******************************************************
 * arduino loop
 */
void loop() {
  String ipString = WiFi.localIP().toString();
  Serial.println("Loop start: IP = "+ ipString );
  if (ipString == "0.0.0.0") {
    //
    Serial.println("reset WiFi");
    setupWIFI();
    ipString = WiFi.localIP().toString();
   }
  bool Daylight = LastDaylight;
  String WeatherForecast = LastWeatherForecast;
  String NowTemp = LastTemp;
  String IconCode = LastIconCode;
  DynamicJsonDocument jdoc(2048);

  Serial.println("Begin fetch weather data");
  const char * headerkeys[] = {"Server","Date","Content-Type"} ;
  const size_t headerkeyssize = sizeof(headerkeys) / sizeof(headerkeys[0]);
  Serial.println("loop processing");
  HTTPClient connect;
  connect.begin(dataUrl);
  connect.addHeader("accept", "application/json");
  connect.collectHeaders( headerkeys, headerkeyssize);
  int respcode = connect.GET();
  if (respcode > 0) {
    // some http connection
    Serial.println(" response code " +(String(respcode)));
    /* String Date is  difficult */
    if (connect.header("Date")) {
      //
      String respDate = connect.header("Date");
      Serial.println(" date from HTTP response header: " +respDate);
      // Convert from String and to local time
      int length = respDate.length() + 1;
      char datearray[length];
      respDate.toCharArray(datearray, length);
      struct tm ts;
      strptime(datearray, "%a, %d %b %Y %H:%M:%S %Z", &ts);
      long int epoch = mktime(&ts);
      long int eastern = myTZ.toLocal(epoch);
      String l_time = (String(hour(eastern)) + ":" + String(minute(eastern)) + ":" + String(second(eastern)));
      Serial.println("   Time breakout from response date: " + String(l_time));
      String l_date = (String(year(eastern)) + "." + String(month(eastern)) + "." + String(day(eastern)));
      Serial.println("   Date breakout from response date: " + String(l_date));
      DisplayTime(l_time, l_date);
     }
    if (respcode == 200) {
      //
      Serial.println("  Parsing JSON weather data");
      deserializeJson(jdoc, connect.getStream(), DeserializationOption::NestingLimit(20));
      // probably should validate JSON ?
      //String obsv = jdoc["tempest"]["obs_st"];
      //Serial.println("  The current observation: "+obsv);
      // Time Data -- Sunrise/Sunset and Daylight
      // -- tempest time (GMT epoch)
      long int TempestEpoch = jdoc["tempest"]["obs_st"][0];
      String Sunset = String(jdoc["forecast"]["today"]["sunset"]);
      time_t SunsetEpoch = parseDateTimeToUTC(Sunset.c_str());
      String Sunrise = String(jdoc["forecast"]["today"]["sunrise"]);
      time_t SunriseEpoch = parseDateTimeToUTC(Sunrise.c_str());
      Serial.println("   Parsing forecast times");
      if (SunriseEpoch < TempestEpoch) {
        //
        Serial.println("    It is after sunrise.");
        if (SunsetEpoch < TempestEpoch) {
          //
          Serial.println("    It is after sunset.");
          Daylight = false;
         } 
        else {
          //
          Serial.println("    It is daylight.");
          Daylight = true;
         }
        } 
       else {
        //
        Serial.println("    It is not yet daylight");
        Daylight = false;
       }
      // Forecast
      IconCode = String(jdoc["forecast"]["today"]["icon"]);
      Serial.println("    Forecast icon code: " + IconCode);
      WeatherForecast = String(jdoc["forecast"]["today"]["weather"]);
      Serial.println("    Forecast conditions: " +WeatherForecast);
 
      // Tempest Obvservation Data
      Serial.println("   Parsing Observation data from Tempest");
      Serial.printf("    The last observation time is: %ld. \n", TempestEpoch);
      time_t utcEpoch = TempestEpoch;
      //convert to local time
      time_t localTime = myTZ.toLocal(utcEpoch);
      // Temperature
      float tempc = jdoc["tempest"]["obs_st"][7];
      Serial.println("    tempest obs temp cel: " + String(tempc));
      //float tempf = (( tempc  * 9) + 3) / 5 + 32;
      int tempf = int((tempc * 1.8) + 32);
      Serial.println("    tempest obs temp fahr: " + String(tempf));
      NowTemp = String(tempf) + "°f";

      // END JSON Parsing and Response 200
     }     
    }
    else {
      Serial.printf(" HTTP GET failed, error: %s\n", connect.errorToString(respcode).c_str());
      NowTemp = "N/C";
    }
  connect.end();
  Serial.printf(" Evaluating for Changed Temp: %ld:%ld", NowTemp,LastTemp); 
  if (NowTemp != LastTemp) {
    display.setColor(BLACK);
    display.setFont(ArialMT_Plain_24);
    display.drawString(0, 25, LastTemp);
    display.display();
    display.setColor(WHITE);
    display.setFont(ArialMT_Plain_24);
    display.drawString(0, 25, NowTemp);
    display.display();
    LastTemp = NowTemp;
   }
  Serial.printf(" Evaluating forecast data %s:%s, and %s:%s\r\n", WeatherForecast,LastWeatherForecast,IconCode, LastIconCode);
  if ((IconCode != LastIconCode) || (!WeatherForecast.equals(LastWeatherForecast))) {
    //Serial.printf("   Changing icon from %s to %s...\n", LastIconCode, IconCode);
    DisplayIcon(IconCode, WeatherForecast, Daylight);
  } 
  //else {    Serial.printf("   Not changing from lasticon to new icon: %s,%s\n", LastIconCode, IconCode);  }
  
  delay(9500);
}

/****************************************************

 * [Universal Function] ESP32 WiFi Kit 32 Event Handling

 */



void DisplayTime(String timeString, String dateString) {
  if (LastTime != timeString) {
    // Time
    display.setFont(ArialMT_Plain_10);
    display.setColor(BLACK);
    display.drawString(70, 0, LastTime);
    display.display();
    display.setColor(WHITE);
    display.drawString(70, 0, timeString);
    display.display();
    LastTime = timeString;
  }
  if (LastDate != dateString) {
    // Date
    display.setFont(ArialMT_Plain_10);
    display.setColor(BLACK);
    display.drawString(65, 54, LastDate);
    display.display();
    display.setColor(WHITE);
    display.drawString(65, 54, dateString);
    display.display();
    LastDate = dateString;
  }
}

void DisplayIcon(String Icon, String Weather, bool daynight) {
  // Clear Forecast
  display.setColor(BLACK);
  display.setFont(ArialMT_Plain_10);
  display.drawString(0, 0, LastWeatherForecast);
  // Set Current Forecast
  display.setColor(WHITE);
  display.setFont(ArialMT_Plain_10);
  display.drawString(0, 0, Weather);
  //  .... Clear Image
  if (LastWeatherForecast == "clear sky") {
    if (LastDaylight = true) {
      display.setColor(BLACK);
      display.drawXbm(70, 11, 50, 50, weather_bitmap_clear_day);
      display.display();
    } 
    else {
      display.setColor(BLACK);
      display.drawXbm(70, 11, 50, 50, weather_bitmap_clear_night);
      display.display();
    }
  } 
  else if (LastWeatherForecast == "few clouds" || LastWeatherForecast == "scattered clouds") {
    if (LastDaylight = true) {
      //
      display.setColor(BLACK);
      display.drawXbm(70, 11, 50, 50, weather_bitmap_partly_cloudy_day);
      display.display();
    } 
    else {
      //
      display.setColor(BLACK);
      display.drawXbm(70, 11, 50, 50, weather_bitmap_partly_cloudy_night);
      display.display();
    }
  } 
  else if ((LastWeatherForecast == "broken clouds") || (LastWeatherForecast == "overcast clouds")) {
    //
    display.setColor(BLACK);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_cloudy);
    display.display();
  } 
  else if (LastWeatherForecast.indexOf("drizzle") != -1) {
    display.setColor(BLACK);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_drizzle);
    display.display();
  } 
  else if ((LastWeatherForecast.indexOf("sleet") != -1) || (LastWeatherForecast.indexOf("freezing rain") != -1)) {
    display.setColor(BLACK);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_sleet);
    display.display();
  } 
  else if ((LastWeatherForecast == "light rain") || (LastWeatherForecast == "moderate rain")) {
    display.setColor(BLACK);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_lightRain);
    display.display();
  } 
  else if ((LastWeatherForecast == "heavy intensity rain") || (LastWeatherForecast == "very heavy rain") || (LastWeatherForecast == "extreme rain") || (LastWeatherForecast.indexOf("shower rain") != -1)) {
    display.setColor(BLACK);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_rain);
    display.display();
  } 
  else if (LastIconCode == "11d" || LastIconCode == "11n") {
    display.setColor(BLACK);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_thunderstorm);
    display.display();
  } 
  else if (LastIconCode == "13d" || LastIconCode == "13n") {
    display.setColor(BLACK);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_snow);
    display.display();
  } 
  else if (LastIconCode == "50d" || LastIconCode == "50n") {
    display.setColor(BLACK);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_fog);
    display.display();
  } 
  else {
    display.setColor(BLACK);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_unknown);
    display.display();
  }
  // .... Set New Image 'Icon'
  if (Weather == "clear sky") {
    if (daynight = true) {
      display.setColor(WHITE);
      display.drawXbm(70, 11, 50, 50, weather_bitmap_clear_day);
      display.display();
      Serial.println("   printing clear day icon");
    } 
    else {
      display.setColor(WHITE);
      display.drawXbm(70, 11, 50, 50, weather_bitmap_clear_night);
      display.display();
      Serial.println("   printing clear night icon");
    }
  } 
  else if (Weather == "few clouds" || Weather == "scattered clouds") {
    if (daynight = true) {
      //
      display.setColor(WHITE);
      display.drawXbm(70, 11, 50, 50, weather_bitmap_partly_cloudy_day);
      display.display();
      Serial.println("   printing day partly cloudy icon");

    } 
    else {
      //
      display.setColor(WHITE);
      display.drawXbm(70, 11, 50, 50, weather_bitmap_partly_cloudy_night);
      display.display();
      Serial.println("   printing night partly cloudy icon");
    }
  } 
  else if ((Weather == "broken clouds") || (Weather == "overcast clouds")) {
    //
    display.setColor(WHITE);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_cloudy);
    display.display();
    Serial.println("   printing cloudy icon");
  } 
  else if (Weather.indexOf("drizzle") != -1) {
    display.setColor(WHITE);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_drizzle);
    display.display();
    Serial.println("   printing drizzle icon");
  } 
  else if ((Weather.indexOf("sleet") != -1) || (Weather.indexOf("freezing rain") != -1)) {
    display.setColor(WHITE);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_sleet);
    display.display();
    Serial.println("   printing sleet icon");
  } 
  else if ((Weather == "light rain") || (Weather == "moderate rain")) {
    display.setColor(WHITE);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_lightRain);
    display.display();
    Serial.println("   printing light rain icon");
  } 
  else if ((Weather == "heavy intensity rain") || (Weather == "very heavy rain") || (Weather == "extreme rain") || (Weather.indexOf("shower rain") != -1)) {
    display.setColor(WHITE);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_rain);
    display.display();
    Serial.println("   printing rain icon");
  } 
  else if (Icon == "11d" || Icon == "11n") {
    display.setColor(WHITE);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_thunderstorm);
    display.display();
    Serial.println("   printing thunderstorm icon");
  } 
  else if (Icon == "13d" || Icon == "13n") {
    display.setColor(WHITE);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_snow);
    display.display();
    Serial.println("   printing snow icon");
  } 
  else if (Icon == "50d" || Icon == "50n") {
    display.setColor(WHITE);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_fog);
    display.display();
    Serial.println("   printing fog icon");
  } 
  else {
    display.setColor(WHITE);
    display.drawXbm(70, 11, 50, 50, weather_bitmap_unknown);
    display.display();
    Serial.println("   printing unknown icon");
  }

  // Set Value
  LastIconCode = Icon;
  LastWeatherForecast = Weather;
  LastDaylight = daynight;
}

// Function to convert epoch to formatted string
String epochToString12H(time_t epoch) {
  // Month abbreviations
  const char* months[] = {
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
  };
  // Extract components
  int hr = hour(epoch);
  int minVal = minute(epoch);
  int secVal = second(epoch);
  int dayVal = day(epoch);
  int monthVal = month(epoch);
  int yearVal = year(epoch);

  // Determine AM/PM and convert to 12-hour format
  String ampm = "AM";
  if (hr == 0) {
    hr = 12;  // Midnight
  } else if (hr == 12) {
    ampm = "PM";  // Noon
  } else if (hr > 12) {
    hr -= 12;
    ampm = "PM";
  }
  // Format string with leading zeros for minutes/seconds
  char buffer[30];
  snprintf(buffer, sizeof(buffer), "%02d:%02d%s, %s %02d %04d",
           hr, minVal, ampm.c_str(), months[monthVal - 1], dayVal, yearVal);
  return String(buffer);
}

// Function to parse "YYYY-MM-DD HH:MM:SS" into epoch (UTC)
time_t parseDateTimeToUTC(const char* dateTimeStr) {
  int year, month, day, hour, minute, second;
  // Parse the string safely
  if (sscanf(dateTimeStr, "%d-%d-%d %d:%d:%d",
             &year, &month, &day, &hour, &minute, &second)
      != 6) {
    Serial.println(F("Invalid date-time format!"));
    return 0;
  }
  // Convert to time_t assuming LOCAL time
  tmElements_t tm;
  tm.Year = year - 1970;  // tmElements_t counts years since 1970
  tm.Month = month;
  tm.Day = day;
  tm.Hour = hour;
  tm.Minute = minute;
  tm.Second = second;
  time_t localTime = makeTime(tm);         // Local time epoch
  time_t utcTime = myTZ.toUTC(localTime);  // Convert to UTC epoch
  return utcTime;
}
