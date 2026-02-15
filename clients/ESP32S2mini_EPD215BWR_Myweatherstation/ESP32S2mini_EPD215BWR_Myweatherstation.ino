/*
	This uses the Waveshare libraries, install them before validating and compiling.

	In addition, ArduinoJson, StreamUtils, HTTPClient as noted below

	Icons were adapted from https://github.com/Bodmer/OpenWeather/, thanks those were wonderful starting points

	This client is a small screen, so minimal information in as clear a manner as possible.

	The case allows it to sit on top of a monitor.

*/
#include "DEV_Config.h"
#include "EPD_2in15b.h"
#include "GUI_Paint.h"
#include "ImageData.h"
#include <stdlib.h>
#include <ArduinoJson.h>
#include <ArduinoJson.hpp>
#include <StreamUtils.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <TimeLib.h>     // For time functions
#include <Timezone.h>    // For timezone and DST handling


/**********************************************  WIFI Client *********************************
   configure items here
*/
const char* ssid = "xxxxxxx"; //replace "xxxxxx" with your WIFI's ssid
const char* password = "xxxxxxx"; //replace "xxxxxx" with your WIFI's password
const char* dataUrl = "http://xxxxxxx:8080/weather/"; // replace "xxxxxx" with your server ip or hostname


// Example: Eastern Time (USA)
TimeChangeRule myDST = {"EDT", Second, Sun, Mar, 2, -240}; // UTC -4 hours
TimeChangeRule mySTD = {"EST", First, Sun, Nov, 2, -300};  // UTC -5 hours

/*
 * END configuration variables
 */
 
// Global Variables
String ipString;
const char* myIP;
Timezone myTZ(myDST, mySTD);
String Last_Temp = "N/C";
String Last_Weather = "N/C";
bool Last_Daylight = true;
String Last_IconCode = "---";


/*********************************************************************
   setup wifi
*/
void setupWIFI()
{
  printf("start WiFi");
  WiFi.disconnect(true);
  delay(1500);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(ssid, password);

  //Wait for 5000ms, if not connected, continue
  byte count = 0;
  while (WiFi.status() != WL_CONNECTED && count < 10)
  {
    count ++;
    delay(500);
    printf(".");
  }
  printf("WiFi complete\r\n");
  ipString = WiFi.localIP().toString();
  Serial.println("IP Address as String: " + ipString);
} /* End Wifi Init */


void setup() {
  printf("Setup stage - DEV_Module_Init initialize\r\n");
  DEV_Module_Init();

  Serial.begin(115200);
  while (!Serial) {
    ; // wait for serial port to connect. Needed for native USB port only
  }

  Serial.println("Initialize WiFi...");
  setupWIFI();
}


/* The main loop -------------------------------------------------------------*/
void loop()
{
  Serial.println("\r\nbegin loop");
  DynamicJsonDocument jdoc(2048);
  String respTime;
  Serial.println("  Read Last_Temp: " + Last_Temp );
  Serial.println("  Read Last_Weather: " + Last_Weather );
  String NowTemp = Last_Temp;
  String WeatherForecast = Last_Weather;
  String TempestTime;
  bool Daylight = Last_Daylight;
  String IconCode = Last_IconCode;

  // Get IP Address
  ipString = WiFi.localIP().toString();
  Serial.println(" IP Address as String: " + ipString );
  myIP = ipString.c_str(); // Pointer valid as long as ipString exists
  if (ipString == "0.0.0.0" ) {
    Serial.println("reset WiFi");
    setupWIFI();
    myIP = ipString.c_str(); // Pointer valid as long as ipString exists
  }

  //Begin weather data
  Serial.println(" begin fetch weather");

  const char * headerkeys[] = {"Server", "Date", "Content-Type"} ;
  const size_t headerkeyssize = sizeof(headerkeys) / sizeof(headerkeys[0]);
  HTTPClient connect;

  connect.begin(dataUrl);
  connect.addHeader("accept", "application/json");
  connect.collectHeaders( headerkeys, headerkeyssize);
  int respcode = connect.GET();
  Serial.println("  http response code: " + String(respcode));

  if (connect.header("Date")) {
    respTime = connect.header("Date");
    Serial.println("   date from response:  " + respTime );
  }

  if (respcode == 200) {
    deserializeJson(jdoc, connect.getStream(), DeserializationOption::NestingLimit(20));

    // --------------------
    // Get the Temp reading
    float tempc = jdoc["tempest"]["obs_st"][7];
    Serial.println("   tempest temp in Celcius:  " + String(tempc) );
    int tempf = int(( tempc  * 1.8) + 32);
    Serial.println("   tempest temp in Fahrenheit:  " + String(tempf) );
    NowTemp = String(tempf)+"F";
    
    // --------------------
    // Get the Forecast Weather value
    Serial.println("   reading forecast value from response: " + String(jdoc["forecast"]["today"]["weather"]) );
    WeatherForecast = String(jdoc["forecast"]["today"]["weather"]);
    
    // --------------------
    // Get the Forecast Icon code
    Serial.println("   reading forecast icon code from response: " + String(jdoc["forecast"]["today"]["icon"]) );
    IconCode = String(jdoc["forecast"]["today"]["icon"]);
    
    // --------------------
    //Get tempest time - it is in GMT epoch
    int TempestEpoch = jdoc["tempest"]["obs_st"][0];
    Serial.println("   tempest epoch time: " + String(TempestEpoch) );
    time_t utcEpoch = TempestEpoch;
    // Convert to local time
    time_t localTime = myTZ.toLocal(utcEpoch);
    // Store formatted time in const char*
    TempestTime = epochToString12H(localTime);
    // Print results
    Serial.println("     Formatted Local Time: " + TempestTime ); 

    // -------------------- Sunset is in local human readable time
    String Sunset = String(jdoc["forecast"]["today"]["sunset"]);
    Serial.println("    Today's sunset is: " + Sunset);
    // need to convert to GMT before convert to epoch
    time_t SunsetEpoch = parseDateTimeToUTC(Sunset.c_str());
    if (SunsetEpoch != -1) {
        Serial.println("     Sunset Epoch time: " + String(SunsetEpoch));
    }
    // -------------------- Sunrise is in local human readable time
    String Sunrise = String(jdoc["forecast"]["today"]["sunrise"]);
    Serial.println("    Today's sunrise is: " + Sunrise);
    // need to convert to GMT before convert to epoch
    time_t SunriseEpoch = parseDateTimeToUTC(Sunrise.c_str());
    if (SunriseEpoch != -1) {
        Serial.println("     Sunrise Epoch time: " + String(SunriseEpoch));
    }
    if (SunriseEpoch < TempestEpoch) {
      Serial.println("    It is after sunrise.");
      if (SunsetEpoch < TempestEpoch) {
        Serial.println("    It is after sunset.");
        Daylight = false;
      }
      else {
        Serial.println("    It is daylight.");
        Daylight = true;
      }
     }
     else {
      Serial.println("    It is not yet sunrise.");
     }
  }
  else {
    Serial.println(" HTTP connect issue ");
    TempestTime = "--";
    respTime = "--";
  }
  Serial.println("  NowTemp:  " + NowTemp + ", Last_Temp: " + Last_Temp );
  Serial.println("  Forecast Code:  " + WeatherForecast + ", Last code: " + Last_Weather );
  Serial.println("  Tempest event time:  " + TempestTime );
  Serial.println("  Daylight is " + String(Daylight ? "on":"off") );
  
  //End HTTP connection
  connect.end();

  if ( !NowTemp.equals(Last_Temp) || !WeatherForecast.equals(Last_Weather) || 
    Daylight != Last_Daylight  || !IconCode.equals(Last_IconCode) ) {
    //Create a new image cache
    Serial.println(" Last Values did not match, create image canvas and populate");
    UBYTE *BlackImage, *RedImage;
    /* you have to edit the startup_stm32fxxx.s file and set a big enough heap size */
    UWORD Imagesize = ((EPD_2IN15B_WIDTH % 8 == 0) ? (EPD_2IN15B_WIDTH / 8 ) : (EPD_2IN15B_WIDTH / 8 + 1)) * EPD_2IN15B_HEIGHT;
    if ((BlackImage = (UBYTE *)malloc(Imagesize)) == NULL) {
      Serial.println("Failed to apply for black memory...\r\n");
      while (1);
    }
    if ((RedImage = (UBYTE *)malloc(Imagesize)) == NULL) {
      Serial.println("Failed to apply for red memory...\r\n");
      while (1);
    }

    Serial.println("Drawing main screen\r\n");
    EPD_2IN15B_Init();
    //EPD_2IN15B_Clear();
    DEV_Delay_ms(500);
    //1.Draw black image
    Paint_NewImage(BlackImage, EPD_2IN15B_WIDTH, EPD_2IN15B_HEIGHT, 270, WHITE);
    Paint_Clear(WHITE);
    Paint_NewImage(RedImage, EPD_2IN15B_WIDTH, EPD_2IN15B_HEIGHT, 270, WHITE);
    Paint_Clear(WHITE);

    // Do the Icon Codes - switching colors as needed
    if (WeatherForecast == "clear sky" ) {
      if (Daylight == true) {
        Paint_SelectImage(BlackImage);
        Paint_DrawBitMap_Paste(icon_clear_day_black, 175, 20, 100, 100, 0 );
      }
      else {
        Paint_SelectImage(BlackImage);
        Paint_DrawBitMap_Paste(icon_clear_night_black, 175, 20, 100, 100, 0 );
      }  
    }
    else if ((WeatherForecast == "few clouds" )||(WeatherForecast == "scattered clouds")) {
      if (Daylight == true){
        Paint_SelectImage(BlackImage);
        Paint_DrawBitMap_Paste(icon_partly_cloudy_day_black, 175, 20, 100, 100, 0 );
        Paint_SelectImage(RedImage);
        Paint_DrawBitMap_Paste(icon_partly_cloudy_day_red, 175, 20, 100, 100, 0 );
      }
      else {
        Paint_SelectImage(BlackImage);
        Paint_DrawBitMap_Paste(icon_partly_cloudy_night_black, 175, 20, 100, 100, 0 );
        Paint_SelectImage(RedImage);
      Paint_DrawBitMap_Paste(icon_partly_cloudy_night_red, 175, 20, 100, 100, 0 );
      }
    }
    else if ((WeatherForecast == "broken clouds" )||(WeatherForecast == "overcast clouds")) {
      Paint_SelectImage(BlackImage);
      Paint_DrawBitMap_Paste(icon_cloudy_black, 175, 20, 100, 100, 0 );
    } 
    else if (WeatherForecast.indexOf("drizzle") != -1) {
      Paint_SelectImage(BlackImage);
      Paint_DrawBitMap_Paste(icon_drizzle_black, 175, 20, 100, 100, 0 ); 
    }
    else if ((WeatherForecast.indexOf("sleet") != -1 )|| (WeatherForecast.indexOf("freezing rain") != -1)) {
      Paint_SelectImage(BlackImage);
      Paint_DrawBitMap_Paste(icon_sleet_black, 175, 20, 100, 100, 0 ); 
      Paint_SelectImage(RedImage);
      Paint_DrawBitMap_Paste(icon_sleet_red, 175, 20, 100, 100, 0 );
      }
    else if ((WeatherForecast == "light rain" )||(WeatherForecast == "moderate rain" )) {
      Paint_SelectImage(BlackImage);
      Paint_DrawBitMap_Paste(icon_lightRain_black, 175, 20, 100, 100, 0 );
    } 
    else if ((WeatherForecast == "heavy intensity rain" )||(WeatherForecast == "very heavy rain" )||
      (WeatherForecast == "extreme rain" ) || (WeatherForecast.indexOf("shower rain") != -1) ) {
      Paint_SelectImage(BlackImage);
      Paint_DrawBitMap_Paste(icon_rain_black, 175, 20, 100, 100, 0 );
    }  
    else if ((IconCode == "11d" )||(IconCode == "11n" )) {
      Paint_SelectImage(BlackImage);
      Paint_DrawBitMap_Paste(icon_thunderstorm_black, 175, 20, 100, 100, 0 );
      Paint_SelectImage(RedImage);
      Paint_DrawBitMap_Paste(icon_thunderstorm_red, 175, 20, 100, 100, 0 );
    } 
    else if ((IconCode == "13d" )||(IconCode == "13n" ) ||
        (WeatherForecast.indexOf("snow") != -1 ) ) {
      Paint_SelectImage(BlackImage);
      Paint_DrawBitMap_Paste(icon_snow_black, 175, 20, 100, 100, 0 );
    } 
    else if ((IconCode == "50d" )||(IconCode == "50n" )) {
      Paint_SelectImage(BlackImage);
      Paint_DrawBitMap_Paste(icon_fog_black, 175, 20, 100, 100, 0 );
      Paint_SelectImage(RedImage);
      Paint_DrawBitMap_Paste(icon_fog_red, 175, 20, 100, 100, 0 );
    } 
    else {
      Paint_SelectImage(BlackImage);
      Paint_DrawBitMap_Paste(icon_unknown_black, 160, 20, 100, 100, 0 );
      Paint_SelectImage(RedImage);
      Paint_DrawBitMap_Paste(icon_unknown_red, 160, 20, 100, 100, 0 );
      //Paint_DrawString_EN(240, 45, WeatherForecast.c_str(), &Font16, WHITE, BLACK);
    }

    // #1 - 
    // Paint It Black
    Paint_SelectImage(BlackImage);
    Paint_DrawString_EN(25, 40, NowTemp.c_str(), &Font64, BLACK, WHITE);
    const char* displayTime = respTime.c_str();
    Paint_DrawString_EN(90, 0, displayTime, &Font12, WHITE, BLACK);
    Paint_DrawString_EN(0, 138, TempestTime.c_str(), &Font20, WHITE, BLACK);

    //2.Draw red image
    Paint_SelectImage(RedImage);
    Paint_DrawString_EN(0, 0, myIP, &Font12, WHITE, BLACK);
    Paint_DrawString_EN(40, 110, WeatherForecast.c_str(), &Font20, WHITE, BLACK);

    //Send the Image
    EPD_2IN15B_Display(BlackImage, RedImage);
    //delay before sleep
    DEV_Delay_ms(2000);
    printf("Goto Sleep...\r\n");
    EPD_2IN15B_Sleep();
    free(BlackImage);
    BlackImage = NULL;
    free(RedImage);
    RedImage = NULL;
    DEV_Delay_ms(2000);//important, at least 2s
    // close 5V
    printf("close 5V, Module enters 0 power consumption ...\r\n");
    Serial.println("completed screen draw, copy values to Last");
    Last_Temp = NowTemp;
    Last_Weather = WeatherForecast;
    Last_Daylight = Daylight;
    Last_IconCode = IconCode;
  }
  else {
    Serial.println(" Last Values matched, sleeping until next time.");
  }

  DEV_Delay_ms(180000);

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
        hr = 12; // Midnight
    } else if (hr == 12) {
        ampm = "PM"; // Noon
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
               &year, &month, &day, &hour, &minute, &second) != 6) {
        Serial.println(F("Invalid date-time format!"));
        return 0;
    }

    // Convert to time_t assuming LOCAL time
    tmElements_t tm;
    tm.Year   = year - 1970; // tmElements_t counts years since 1970
    tm.Month  = month;
    tm.Day    = day;
    tm.Hour   = hour;
    tm.Minute = minute;
    tm.Second = second;

    time_t localTime = makeTime(tm); // Local time epoch
    time_t utcTime   = myTZ.toUTC(localTime); // Convert to UTC epoch

    return utcTime;
}
