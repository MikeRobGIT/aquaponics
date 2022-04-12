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
mqtt_auth = {'username': 'mqtt_user', 'password': '9EV8yw7qsPG%'}
mqtt_topic = "homeassistant/sensor/aquarium/state"
caltempC = 0
minimumDelay = 1.5
defaultDelay = 30.0


class AquariumSensor:
    def __init__(self, device):
        self.temp = self.resTemp(device)
        self.ph = self.resPH(device)
        self.ec = self.resEC(device)
        hasTemp = self.temp != None and self.temp > 0 and self.temp < 120
        hasPpm = self.ec != None and self.ec > 0 and self.ec < 20000
        hasPh = self.ph != None and self.ph > 0 and self.ph < 8.5
        self.json = {"temp": self.temp, "ph": self.ph, "ec": self.ec}
        self.clean = hasTemp and hasPpm and hasPh

    def tof(self, value):
        return value * 1.8 + 32

    def resTemp(self, device):
        global caltempC  # `Needed to modify global var
        print("-------------------Temp--------------------------")
        device.set_i2c_address(102)  # RTP
        device.query("S,c")
        caltempC = device.query("R").replace("\x00", "").strip()
        caltempF = self.tof(float(caltempC))
        caltempF = round(caltempF, 1)
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
            ph = float(device.query("RT,"+str(caltempC)
                                    ).replace("\x00", "").strip())
        else:
            ph = float(device.query("R").replace("\x00", "").strip())
        ph = round(ph, 2)
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

    def resEC(self, device):
        print("-------------------EC---------------------------")
        device.set_i2c_address(100)  # EC
        ec = float(device.query("R").replace("\x00", "").strip())
        print("Res EC: "+str(ec))
        ec = round(ec)
        if ec != None and ec > 0:
            try:
                return ec
            except Exception as e:
                print(e)
                print("*** ERROR *** Res EC Publish Failed")


def resInfo(device):
    res = AquariumSensor(device)

    if res.clean:
        packageStr = json.dumps(res.json)
        print(packageStr)
        publish.single(mqtt_topic, packageStr,
                       hostname=mqtt_hostname, auth=mqtt_auth)

    print("-------------------------------------------------")


def configure_ha_auto_discovery():
    # config HA auto discovery
    sleep(1)
    packageStr = json.dumps({
        "retain": True,
        "unit_of_measurement": "ec",
        "value_template": "{{ value_json.ec }}",
        "state_topic": "homeassistant/sensor/aquarium/state",
        "name": "Aquarium EC",
        "icon": "mdi:water-opacity",
        "unique_id": "aquarium_ec",
        "device": {
            "identifiers": [
                "aquarium_monitor"
            ],
            "name": "Aquarium Monitor",
            "model": "Aquarium Monitor",
            "manufacturer": "CRISIS"
        }
    })
    # print(packageStr)
    publish.single("homeassistant/sensor/aquariumEC/config", packageStr,
                   hostname=mqtt_hostname, auth=mqtt_auth, retain=True)

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
                "aquarium_monitor"
            ],
            "name": "Aquarium Monitor",
            "model": "Aquarium Monitor",
            "manufacturer": "CRISIS"
        }
    })
    # print(packageStr)
    publish.single("homeassistant/sensor/aquariumPh/config", packageStr,
                   hostname=mqtt_hostname, auth=mqtt_auth, retain=True)

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
                "aquarium_monitor"
            ],
            "name": "Aquarium Monitor",
            "model": "Aquarium Monitor",
            "manufacturer": "CRISIS"
        }
    })
    # print(packageStr)
    publish.single("homeassistant/sensor/aquariumT/config", packageStr,
                   hostname=mqtt_hostname, auth=mqtt_auth, retain=True)


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
            delaytime = 3.0
            pass
        time.sleep(delaytime - minimumDelay)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:  # catches the ctrl-c command, which breaks the loop above
        print(" - Polling stopped")
