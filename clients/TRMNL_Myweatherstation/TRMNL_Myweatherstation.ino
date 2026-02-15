#include "ImageData.h"
#include <stdlib.h>
#include <ArduinoJson.h>
#include <ArduinoJson.hpp>
#include <StreamUtils.h>
#include <HTTPClient.h>
#include <TimeLib.h>     // For time functions
#include <Timezone.h>    // For timezone and DST handling

#include <SPI.h>
#include <TFT_eSPI.h>
#include <WiFi.h>
#include <esp_sntp.h>

const char* SSID     = "xxxxxx"; // replace "xxxxxx" with your wifi sid
const char* PWD      = "xxxxxx"; // replace "xxxxxx" with your wifi password

const int W = 800;
const int H = 480;

EPaper epd = EPaper();

const char* WeatherURL = "http://xxxxxx:8080/weather/"; /// replace "xxxxxx" with your server ip or hostname
const char* BandwidtURL = "http://xxxxxx:8080/bandwidth/"; /// replace "xxxxxx" with your server ip or hostname

// Example: Eastern Time (USA)
TimeChangeRule myDST = {"EDT", Second, Sun, Mar, 2, -240}; // UTC -4 hours
TimeChangeRule mySTD = {"EST", First, Sun, Nov, 2, -300};  // UTC -5 hours
const char* TIMEZONE = "EST5EDT,M3.2.0,M11.1.0";

/*
 * END configuration variables
 */
 
// Global Variables
String ipString;
const char* myIP;
Timezone myTZ(myDST, mySTD);
String Last_Temp = "N/C";
String Last_Forecast = "N/C";
bool Last_Daylight = true;
String Last_IconCode = "---";
int Last_Humidity;
int Last_Pressure;
int Last_Lux;
float Last_UV;
int Last_Rads;
String Last_Batt = "boot";
float Last_TBatt = 0.0;

// Define button pins
const int BUTTON_D1 = D1;  // First user button
const int BUTTON_D2 = D2;  // Second user button
const int BUTTON_D4 = D4;  // Third user button

// TRMNL DIY Kit - Battery Voltage Monitoring Example
#define BATTERY_PIN 1       // GPIO1 (A0) - BAT_ADC
#define ADC_EN_PIN 6        // GPIO6 (A5) - ADC_EN
const float CALIBRATION_FACTOR = 0.968;


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
  WiFi.begin(SSID, PWD);

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
  initDisplay();
  
  // Configure button pins as inputs with internal pull-up resistors
  pinMode(BUTTON_D1, INPUT_PULLUP);
  pinMode(BUTTON_D2, INPUT_PULLUP);
  pinMode(BUTTON_D4, INPUT_PULLUP);

  // Configure Battery stuff, ADC_EN
  pinMode(ADC_EN_PIN, OUTPUT);
  digitalWrite(ADC_EN_PIN, LOW);  // Start with ADC disabled to save power
  // Configure ADC
  analogReadResolution(12);
  analogSetPinAttenuation(BATTERY_PIN, ADC_11db);
  
  Serial.begin(115200);
  while (!Serial) {
    ; // wait for serial port to connect. Needed for native USB port only
  }

  Serial.println("Initialize WiFi...");
  setupWIFI();
}

void initDisplay() {
  epd.begin();
  epd.setRotation(0);
  epd.fillScreen(TFT_WHITE);
  epd.setTextColor(TFT_BLACK);
  epd.setTextSize(2);
}

float readBatteryVoltage() {
  // Enable ADC
  digitalWrite(ADC_EN_PIN, HIGH);
  delay(10);  // Short delay to stabilize
  
  // Read 30 times and average for more stable readings
  long sum = 0;
  for(int i = 0; i < 30; i++) {
    sum += analogRead(BATTERY_PIN);
    delayMicroseconds(100);
  }
  
  // Disable ADC to save power
  digitalWrite(ADC_EN_PIN, LOW);
  
  // Calculate voltage
  float adc_avg = sum / 30.0;
  float voltage = (adc_avg / 4095.0) * 3.6 * 2.0 * CALIBRATION_FACTOR;
  
  return voltage;
}

/* The main loop -------------------------------------------------------------*/
void loop()
{
  Serial.println("\r\nbegin loop");
  
  // Read battery voltage
  float voltage = readBatteryVoltage();
  // Print the results
  Serial.println("Battery Voltage: " + String (voltage, 2) + "V");
  // Determine battery level
  String Now_Batt;
  if (voltage >= 4.0) {
    Now_Batt = "Full";
  } else if (voltage >= 3.7) {
    Now_Batt = "Good";
  } else if (voltage >= 3.5) {
    Now_Batt = "Medium";
  } else if (voltage >= 3.2) {
    Now_Batt = "Low";
  } else {
    Now_Batt = "Critical";
  }
  
  DynamicJsonDocument jdoc(2048);
  Serial.println("  Read Last_Temp: " + Last_Temp );
  Serial.println("  Read Last_Forecast: " + Last_Forecast );
  String Now_Temp = Last_Temp;
  int Now_Humidity = Last_Humidity;
  int Now_Pressure = Last_Pressure;
  int Now_Lux = Last_Lux;
  float Now_UV = Last_UV;
  int Now_Rads = Last_Rads;
  String Now_Forecast = Last_Forecast;
  String Now_Time;
  bool Now_Daylight = Last_Daylight;
  String Now_IconCode = Last_IconCode;
  float Now_TBatt = Last_TBatt;

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

  connect.begin(WeatherURL);
  connect.addHeader("accept", "application/json");
  connect.collectHeaders( headerkeys, headerkeyssize);
  int respcode = connect.GET();
  Serial.println("  http response code: " + String(respcode));

  if (respcode == 200) {
    deserializeJson(jdoc, connect.getStream(), DeserializationOption::NestingLimit(20));

    // Pressure
    Now_Pressure = jdoc["tempest"]["obs_st"][6];
    
    // Get the Temp reading
    float tempc = jdoc["tempest"]["obs_st"][7];
    Serial.println("   tempest temp in Celcius:  " + String(tempc) );
    int tempf = int(( tempc  * 1.8) + 32);
    Serial.println("   tempest temp in Fahrenheit:  " + String(tempf) );
    Now_Temp = String(tempf)+"F";

    // Humidity 
    Now_Humidity = jdoc["tempest"]["obs_st"][8];

    // Lux
    Now_Lux = jdoc["tempest"]["obs_st"][9];
    // UV
    Now_UV = jdoc["tempest"]["obs_st"][10];
    // Rads
    Now_Rads = jdoc["tempest"]["obs_st"][11];
    // Tempest Battery
    Now_TBatt = jdoc["tempest"]["obs_st"][16];
    
    // --------------------
    // Get the Forecast Weather value
    Serial.println("   reading forecast value from response: " + String(jdoc["forecast"]["today"]["weather"]) );
    Now_Forecast = String(jdoc["forecast"]["today"]["weather"]);
    
    // --------------------
    // Get the Forecast Icon code
    Serial.println("   reading forecast icon code from response: " + String(jdoc["forecast"]["today"]["icon"]) );
    Now_IconCode = String(jdoc["forecast"]["today"]["icon"]);
    
    // --------------------
    //Get tempest time - it is in GMT epoch
    int TempestEpoch = jdoc["tempest"]["obs_st"][0];
    Serial.println("   tempest epoch time: " + String(TempestEpoch) );
    time_t utcEpoch = TempestEpoch;
    // Convert to local time
    time_t localTime = myTZ.toLocal(utcEpoch);
    // Store formatted time in const char*
    Now_Time = epochToString12H(localTime);
    // Print results
    Serial.println("     Formatted Local Time: " + Now_Time ); 

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
        Now_Daylight = false;
      }
      else {
        Serial.println("    It is daylight.");
        Now_Daylight = true;
      }
     }
     else {
      Serial.println("    It is not yet sunrise.");
     }
  }
  else {
    Serial.println(" HTTP connect issue ");
    Now_Time = "--";
  }
  Serial.println("  NowTemp:  " + Now_Temp + ", Last_Temp: " + Last_Temp );
  Serial.println("  Forecast Code:  " + Now_Forecast + ", Last code: " + Last_Forecast );
  Serial.println("  Tempest event time:  " + Now_Time );
  Serial.println("  Daylight is " + String(Now_Daylight ? "on":"off") );
  
  //End HTTP connection
  connect.end();

  if ( !Now_Temp.equals(Last_Temp) || !Now_Forecast.equals(Last_Forecast) || 
    Now_Daylight != Last_Daylight  || !Now_IconCode.equals(Last_IconCode) ||
    Now_Humidity != Last_Humidity || Now_Pressure != Last_Pressure ||
    Now_Lux != Last_Lux || Now_UV != Last_UV || Now_Rads != Last_Rads ||
    Now_Batt != Last_Batt
    ) {

    Serial.println(" Last Values did not match, create image canvas and populate");


    Serial.println("Drawing main screen\r\n");
    initDisplay();
    //DEV_Delay_ms(500);
    
    //1.Draw black image
    //Paint_NewImage(BlackImage, W, H, 270, WHITE);
    //Paint_Clear(WHITE);
/*
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
*/
    // #1 - 
    // Paint It Black
    
    epd.drawString(Now_Time.c_str(), 5, 5, 2);
    //Temp,F
    Serial.println("Printing Temp: " + Now_Temp);
    epd.drawString(Now_Temp, 10, 50, 8);
    //Forecast text
    epd.drawString(Now_Forecast, 5, 220, 4);
    // Humidity
    epd.drawString( (String (Now_Humidity) + "%rh"),5, 290, 4);
    // Pressure
    epd.drawString( (String (Now_Pressure) + "MB"),220, 290, 2);
    if (Now_Pressure > Last_Pressure) {
      epd.drawString( "rising",220, 325, 2);
    }
    else if (Last_Pressure > Now_Pressure) {
      epd.drawString( "falling",220, 325, 2);
    }

    // Middle Column
    epd.drawString(("Lux: " +String(Now_Lux)), 280, 55, 2); 
    epd.drawString((" UV: " +String(Now_UV)), 280, 100, 2);
    epd.drawString(("Rad: " +String(Now_Rads)), 280, 145, 2);  
    epd.drawString(("Display Battery " +Now_Batt), 550,2, 1);
    epd.drawString(("Tempest Batt " +String(Now_TBatt) +"v"), 550,35, 1);

    //Send the Image
    epd.update();
    
    //delay before sleep
    sys_delay_ms(2000);
    printf("Goto Sleep...\r\n");
    //EPD_2IN15B_Sleep();
    //free(BlackImage);
    //BlackImage = NULL;

    esp_sleep_enable_timer_wakeup(30 * 1000 * 1000ULL);  // 30 sec
    //esp_deep_sleep_start();
    

    Serial.println("completed screen draw, copy values to Last");
    Last_Temp = Now_Temp;
    Last_Forecast = Now_Forecast;
    Last_Daylight = Now_Daylight;
    Last_IconCode = Now_IconCode;
    Last_Humidity = Now_Humidity;
    Last_Pressure = Now_Pressure;
    Last_UV = Now_UV;
    Last_Lux = Now_Lux;
    Last_Rads = Now_Rads;
    Last_Batt = Now_Batt;
    Last_TBatt = Now_TBatt;
  }
  else {
    Serial.println(" Last Values matched, sleeping until next time.");
  }
  sys_delay_ms(180000);
} // End LOOP

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
