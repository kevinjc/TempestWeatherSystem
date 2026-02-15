# Waveshare 2.15 in BWR Epaper Display
This project uses an ESP32 device soldered into pins of the Waveshare display board.

I first used an original ESP32 DevKit board but replaced it with an S2 Mini because it is more compact.

In cases you will see Blender files you can use on a 3D printer to print a little case assembly to perch it on top your monitor.
![2.15 inch display on monitor](/pictures/Tempest_EPD_2in15_monitor-topper.jpg)

In DEV_Config.h you can see two sections of the PIN definitions. The final, uncommented section lines 62 to 67 are for the S2 Mini. The commented out section was for the esp32 devkit board.

Most of the fonts are original from Waveshare. I did add font_64.c, I will try to find the source and add attribution.

The ImageData are icons I converted and manipulated to display with two colors. The original source for the icons is https://github.com/Bodmer/OpenWeather/

I used the site https://javl.github.io/image2cpp/ to obtain the CPP code after I had manipulated and separated the colors the way I wanted.


