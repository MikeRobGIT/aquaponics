#!/usr/bin/python
import io         # used to create file streams
from io import open
from pickletools import int4
from time import sleep
import fcntl      # used to access I2C parameters like addresses
import time       # used for sleep delay and timestamps
import copy
import string     # helps parse strings
import json
import paho.mqtt.publish as publish

from AtlasI2C import (
	 AtlasI2C
)
mqtt_hostname = "homeassistant"
mqtt_auth = { 'username': 'mqtt_user', 'password': '9EV8yw7qsPG%' }
mqtt_topic = "homeassistant/sensor/aquarium/state"
caltempC = 0
minimumDelay = 1.5
defaultDelay = 300.0


class AquariumSensor:
    def __init__(self, device):
        self.temp = self.resTemp(device)
        self.ph = self.resPH(device)
        self.ppm = self.resPPM(device)
        hasTemp = self.temp != None and self.temp > 0 and self.temp < 120
        hasPpm = self.ppm != None and self.ppm > 0 and self.ppm < 20000
        hasPh = self.ph != None and self.ph > 0 and self.ph < 8.5
        self.json = { "temp": self.temp, "ph": self.ph, "ppm": self.ppm }
        self.clean = hasTemp and hasPpm and hasPh

    def tof(self, value):
        return value * 1.8 + 32

    def resTemp(self, device):
        global caltempC    # Needed to modify global var
        print("-------------------Temp--------------------------")
        device.set_i2c_address(102)  # RTP
        device.query("S,c")
        caltempC = device.query("R").replace("\x00","").strip()
        caltempF = self.tof(float(caltempC))
        caltempF = round(caltempF,1)
        print("Res Temp: "+str(caltempF))
        if caltempF != None and caltempF > 0:
            try:
                return caltempF
            except Exception as e:
                print(e)
                print("*** ERROR *** Res Temp Publish Failed")

    def resPH(self, device):
        print("-------------------pH----------------------------")
        device.set_i2c_address(99)  # pH
        print("Compensate pH Temp: "+str(caltempC))
        ph = 0
        if caltempC != 0:
            ph = float(device.query("RT,"+str(caltempC)).replace("\x00","").strip())
        else:
            ph = float(device.query("R").replace("\x00","").strip())
        ph = round(ph,2)
        print("Res pH: "+str(ph))

        if isinstance(ph, str) is True and "Error" in ph:
            print("*** ERROR *** Problem reading sensor value")
        elif ph != None and 4 <= ph <= 9:
            try:
                return ph
            except Exception as e:
                print(e)
                print("*** ERROR *** Res pH Publish Failed")
        else:
            print("*** ERROR *** Problem reading sensor value")

    def resPPM(self, device):
        print("-------------------PPM---------------------------")
        device.set_i2c_address(100)  # EC
        ppm = float(device.query("R").replace("\x00","").strip())
        print("Res PPM: "+str(ppm))
        ppm = round(ppm)
        if ppm != None and ppm > 0:
            try:
                return ppm
            except Exception as e:
                print(e)
                print("*** ERROR *** Res PPM Publish Failed")

def resInfo(device):
    res = AquariumSensor(device)

    if res.clean:
        packageStr = json.dumps(res.json)
        print(packageStr)
        publish.single(mqtt_topic, packageStr, hostname=mqtt_hostname, auth=mqtt_auth)

    print("-------------------------------------------------")

def configure_ha_auto_discovery():
    # config HA auto discovery
    sleep(1)
    packageStr = json.dumps({
        "retain": True,
        "unit_of_measurement": "ppm",
        "value_template": "{{ value_json.ppm }}",
        "state_topic": "homeassistant/sensor/aquarium/state",
        "name": "Aquarium PPM",
        "icon": "mdi:water-opacity",
        "unique_id": "aquarium_ppm",
        "device": {
            "identifiers": [
                "aquarium_monitor_pi_3"
            ],
            "name": "Aquarium Monitor",
            "model": "Aquarium Monitor",
            "manufacturer": "CRISIS"
        }
    })
    #print(packageStr)
    publish.single("homeassistant/sensor/aquariumPPM/config",packageStr,hostname=mqtt_hostname, auth=mqtt_auth, retain=True)

    sleep(1)
    packageStr = json.dumps({
        "retain": True,
        "unit_of_measurement": "pH",
        "value_template": "{{ value_json.ph }}",
        "state_topic": "homeassistant/sensor/aquarium/state",
        "name": "Aquarium pH",
        "icon": "mdi:ph",
        "unique_id": "aquarium_ph",
        "device": {
            "identifiers": [
                "aquarium_monitor_pi_3"
            ],
            "name": "Aquarium Monitor",
            "model": "Aquarium Monitor",
            "manufacturer": "CRISIS"
        }
    })
    #print(packageStr)
    publish.single("homeassistant/sensor/aquariumPh/config",packageStr,hostname=mqtt_hostname, auth=mqtt_auth, retain=True)

    sleep(1)
    packageStr = json.dumps({
        "retain": True,
        "unit_of_measurement": "°F",
        "device_class": "temperature",
        "value_template": "{{ value_json.temp }}",
        "state_topic": "homeassistant/sensor/aquarium/state",
        "name": "Aquarium Temperature",
        "icon": "mdi:coolant-temperature",
        "unique_id": "aquarium_temperature",
        "device": {
            "identifiers": [
                "aquarium_monitor_pi_3"
            ],
            "name": "Aquarium Monitor",
            "model": "Aquarium Monitor",
            "manufacturer": "CRISIS"
        }
    })
    #print(packageStr)
    publish.single("homeassistant/sensor/aquariumT/config",packageStr,hostname=mqtt_hostname, auth=mqtt_auth, retain=True)


def main():
    configure_ha_auto_discovery()
    device = AtlasI2C()
    delaytime = defaultDelay
    if(delaytime < minimumDelay):
        delaytime = minimumDelay
    while True:
        try:
            resInfo(device)
        except Exception as e:
            print(e)
            print("*** ERROR *** Res Update Failed")
            pass
        time.sleep(delaytime - minimumDelay)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:  # catches the ctrl-c command, which breaks the loop above
        print(" - Polling stopped")