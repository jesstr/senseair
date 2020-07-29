#!/usr/bin/python3
import serial
import time
import datetime
import getopt
import sys
import os
import json
import random
from influxdb import InfluxDBClient


ERROR = "<3>"
INFO = "<6>"

def usage():
    print("Usage:\r\n\
    --help \t\tprint usage info\r\n\
    --config=<path> \tuse specified config file\r\n\
    --emulate \t\temulate physical sensor readings with a randomly generated values")


def get_co2(s):
    s.flushInput()
    s.write("\xFE\x44\x00\x08\x02\x9F\x25")
    time.sleep(.5)
    resp = s.read(7)
    if len(resp) >= 4:
        high = ord(resp[3])
        low = ord(resp[4])
        co2 = (high*256) + low
        return co2
    else:
        return None


def store_co2(client, value):
    request_body = [{
        "measurement": 'co2',
        "tags": {"sensor": "senseair_s8"},
        "time": datetime.datetime.utcnow().isoformat(),
        "fields": {"value": value}
    }]
    try:
        client.write_points(request_body)
    except:
        return False
    return True


def main():
    config_file = os.path.dirname(os.path.realpath(__file__)) + "/config.json"
    emulate = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hc:e", \
            ["help", "config=", "emulate"])
    except getopt.GetoptError:
        usage()
        sys.exit(1)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        if opt in ("-c", "--config"):
            config_file = arg
        if opt in ("-e", "--emulate"):
            emulate = True
            random.seed()

    #Load configuration file
    try:
        cfg = json.load(open(config_file, "r"))
    except Exception as e:
        print(e)
        sys.exit(1)
    try:
        influx_user = cfg["influx_user"]
        influx_password = cfg["influx_password"]
        influx_database = cfg["influx_database"]
        serial_port = cfg["serial_port"]
        update_period = cfg["update_period"]
        serial_port = cfg["serial_port"]
        influx_server = cfg["influx_server"]
        influx_port = cfg["influx_port"]
    except KeyError:
        print("Configuration file missed mandatory parameters")
        sys.exit(1)

    #Check serial serial port
    if not emulate:
        try:
            ser = serial.Serial(serial_port, baudrate = 9600, timeout = .5)
            ser.flushInput()
        except Exception as e:
            print(e)
            sys.exit(1)

    client = InfluxDBClient(influx_server, influx_port, 
        influx_user, influx_password, influx_database)

    #Check C02 sensor presense
    if not emulate and not get_co2(ser):
        print(ERROR + "No CO2 sensor found")
        sys.exit(1)

    #Run sensor requests loop
    try:
        while True:
            if emulate:
                co2 = random.randint(400, 500)
            else:
                co2 = get_co2(ser)
            if not co2:
                print(ERROR + "Failed to read CO2 sensor")
                continue
            #print(INFO + ("Random " if emulate else "") + "CO2: " + str(co2))

            if not store_co2(client, co2):
                print(ERROR + "Failed to connect to the database")
            time.sleep(update_period)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()