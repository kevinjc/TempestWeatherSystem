#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
import socket
import logging
import fcntl
import struct
import time
from PIL import Image,ImageDraw,ImageFont 
import traceback

picdir = 'pic'
libdir = 'lib'

if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd7in5_V2

logging.basicConfig(level=logging.DEBUG)

try:
    logging.info("epd7in5_V2 Demo")
    epd = epd7in5_V2.EPD()
    epd.init () 

    font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
    font20 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 20)
    font18 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 18)

    # Drawing on the Horizontal image
    logging.info("1.Drawing on the Horizontal image...")
    Himage = Image.new('1', (epd.width, epd.height))
    draw = ImageDraw.Draw(Himage)
    draw.text((10, 50), 'Testing ... ', font = font20, fill = 0)
    epd.display(epd.getbuffer(Himage))

    
except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd7in5_V2.epdconfig.module_exit()
    exit()
