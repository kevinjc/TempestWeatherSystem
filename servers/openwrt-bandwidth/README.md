# Test Bandwidth and get results in JSON
I have tried a couple of CLI speedtesters for OpenWRT and I have found this GoLang one the best lately. They seem to break a lot, or perhaps it was just what is available on this particular device? My first device was RPI4 and it was very stable running on that SD card, but after a couple of other systems failed (Flight Aware, another weather device) I got leery, plus Lumos/T-mobile's 1GB service was pushing the backplane limit of the RPI4, so I thought I'd try the Radxa dual 2.5GBE device.

This device is ok... I thought I'd be able to see a little bandwidth than the RPI4, but it wasn't the case. The upload speed dropped when it had been matching the download test speeds.

But here we are.

## CLI Speedtester
Make sure you get the GoLang version of the speedtest CLI utility. If not, you may have to adjust the api-redis-srv to handle the different format.

Use the shell script from this directory on the OpenWRT system to do the tests, and send the results to api-redis-srv. Included but commented out was sending it to Home Assistant via MQTT. It was working on the RPI4 router, but not on the Radxa. I never did build a dashboard in HA like I wanted.


