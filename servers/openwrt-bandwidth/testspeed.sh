#!/bin/sh

cd /root/speedtest
speedtest-go --json > data.json

curl -H "content-type: application/json" -s http://10.76.75.8:8080/ -d @data.json >/dev/null
curl -H "content-type: application/json" -s http://10.76.76.8:8080/ -d @data.json >/dev/null
# sending mqtt data to home assistant
#mosquito_pub -h 10.10.10.49 -t bandwidth -f data.json -u router -P "Slartibartfast"

