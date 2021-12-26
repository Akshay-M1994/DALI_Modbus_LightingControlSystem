#!/usr/bin/env python 3
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import json
import time
import pyRTOS
from   LovatoD111 import LovatoD111
from   ATX_DaliHat import ATX_DaliHat

#Thingsboard Device Credentials
THINGSBOARD_HOST = 'demo.thingsboard.io'
ACCESS_TOKEN = 'DLS_01'

#Boolean used to track connection to backend
ClientConnected = 0

#Create instance of ATX DaliHAt
DaliHat = ATX_DaliHat('/dev/ttyS0')

#Create instance of D111 Power Meter
ME_D111 = LovatoD111(1,'/dev/ttyUSB0',0.5)
#----------------------------Application Variables-------------------------------/
#Frequency at which threads should run f=1/s
SERVER_DASHBOARD_UPDATE = 5
RECONNECTION_DELAY = 10
PUBLISH_DELAY = 0.1

#Addresses assigned to devices on the bus
DALI_DIMMER_ADD = 0x00
DALI_RELAY_ADD = 0x01
#/----------------------------JSON MESSAGES---------------------------------------/
#Json Message for Dali Relay Status
DaliRelayStatus = {'RelayStatus' : False}
#Json Message for Dali Dimmer
DaliDimmerLevel = {'BrightnessLevel' : 0}
#Json Message for current,voltage & power measurements
PowerMonitoring = {'Voltage': 0 , 'Current': 0 , 'kWh' : 0 , 'Alarm State' : False}
#/-----------------------Function Declarations-------------------------------------/
def GetRelayStatus():
    
    #First we read the value in the DTR register
    DTR0_Value  = DaliHat.QueryLevel(DALI_RELAY_ADD)
    
    #Next we determine discrete state i.e. either true(ON) or false(OFF) based on DTR value
    if(DTR0_Value == 0) :
        return False
    elif(DTR0_Value == 254):
        return True

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, rc, *extra_params):
    
    #Print result code
    print('Connection result code ' + str(rc))     
    
    # Subscribing to receive RPC requests
    client.subscribe('v1/devices/me/rpc/request/+')
    
    #Update Relay Status and brightness level on connection
    DaliRelayStatus['RelayStatus'] = GetRelayStatus()
    client.publish('v1/devices/me/attributes',json.dumps(DaliRelayStatus),1)
    
    DaliDimmerLevel['BrightnessLevel'] = DaliHat.QueryLevel(DALI_DIMMER_ADD)
    client.publish('v1/devices/me/attributes',json.dumps(DaliDimmerLevel),1)
    
    global ClientConnected
    ClientConnected = 1
  
#The callback for when the client disconnects from the server
def on_disconnect(client, userdata,rc):
    
    #Print error code
    print('Connection result code ' + str(rc))  
    print('MQTT Client Disconnected.Attempting Reconnection...')
    
    #Set client connected to '0' or false
    global ClientConnected
    ClientConnected = 0

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print('Topic: ' + msg.topic + '\nMessage: ' + str(msg.payload))
    
    #Extract request ID
    requestId = msg.topic[len('v1/devices/me/rpc/request/'):len(msg.topic)]
    
    # Decode JSON request
    data = json.loads(msg.payload)
    
    #execute rpc's based on method in payload
    if data['method'] == 'SetDaliRelayState':
        print('Set Relay State Command Received')
        DaliHat.SetDeviceState(DALI_RELAY_ADD,data['params'])
    
    #RPC used to set brightness level of dimmer switch
    if data['method'] == 'setBrightnessLevel':
        print('Set brightness level command received')
        DaliHat.SetTargetLevel(DALI_DIMMER_ADD,data['params'])
    
    #RPC request used to get relay status from device
    if data['method'] == 'checkRelayStatus':
        print('Relay Status Query Received')
        DaliRelayStatus['RelayStatus'] = GetRelayStatus()
        client.publish('v1/devices/me/attributes',json.dumps(DaliRelayStatus),1)
        client.publish('v1/devices/me/rpc/response/'+requestId,json.dumps(DaliRelayStatus['RelayStatus']),1)

    
    #RPC request used to get brightness level
    if data['method'] == 'checkBrightnessLevel':
        print('Dimmer Level Query Received')
        DaliDimmerLevel['BrightnessLevel'] = DaliHat.QueryLevel(DALI_DIMMER_ADD)
        client.publish('v1/devices/me/attributes',json.dumps(DaliDimmerLevel),1)
    
    #RPC request received from the server when dashboard is opened in an new window,ensures control knob starts from the correct position
    if data['method'] == 'getStartingBrightnessLevel':
        print('Dimmer Level First Query')
        DaliDimmerLevel['BrightnessLevel'] = DaliHat.QueryLevel(DALI_DIMMER_ADD)
        client.publish('v1/devices/me/rpc/response/'+requestId,json.dumps(DaliDimmerLevel['BrightnessLevel']),1)

#This thread is used to reconnect to the server in the event of disconnection.If client disconnects from server,we attempt a reconnection
#every 5s
        
def MQTT_ConnectionManager(self):
    
    while True:
        if(ClientConnected == 0):
            try:
                #Connect to ThingsBoard using default MQTT port and 60 seconds keepalive interval
                client.connect(THINGSBOARD_HOST, 1883, 20)
            except:
                #Notify User that we are attempting reconnection
                print("MQTT Connection Attempt Failed.Attempting reconnection in 5s")
        
        yield [pyRTOS.timeout(RECONNECTION_DELAY)]



#Thread responsible for monitoring & publishing system voltage,current,power consumption + state of all DALI devices on the bus
def DALI_SysMonitor(self):

    while True:
        
        try:
            #Only monitor if mqtt connection is established
            if(ClientConnected == 1):
                
                 print("[...System Status...]")
                 #Read System Power Consumption
                 PowerMonitoring['Voltage'] = ME_D111.GetVoltage()
                 PowerMonitoring['Current'] = ME_D111.GetCurrent()
                 PowerMonitoring['kWh'] = ME_D111.GetActiveEnergy()
                 PowerMonitoring['Alarm State'] = ME_D111.GetProgThresholdStatus()
                
                 #Get Relay Status & Brightness Level
                 DaliDimmerLevel['BrightnessLevel'] = DaliHat.QueryLevel(DALI_DIMMER_ADD)
                 DaliRelayStatus['RelayStatus'] = GetRelayStatus()
             
                 #Convert python objects to JSON strings before publishing
                 PowerMonitoringJSON = json.dumps(PowerMonitoring)
                 DaliDimmerLevelJSON  = json.dumps(DaliDimmerLevel)
                 DaliRelayStatusJSON  = json.dumps(DaliRelayStatus)
                 
                 #print latest values
                 print(PowerMonitoringJSON)
                 print(DaliDimmerLevelJSON)
                 print(DaliRelayStatusJSON)
                
                 #Publish updated attributes
                 client.publish('v1/devices/me/attributes',PowerMonitoringJSON,1)
                 client.publish('v1/devices/me/attributes',DaliDimmerLevelJSON,1)
                 client.publish('v1/devices/me/attributes',DaliRelayStatusJSON,1)
                 
            yield [pyRTOS.timeout(SERVER_DASHBOARD_UPDATE)]
        
        except Exception as e:
            raise e
#/-----------------------------------THINGSBOARD Setup & Configuration-----------------/
#Create instance of MQTT client
client = mqtt.Client()
#Register connect callback
client.on_connect = on_connect
#Register on_disconnect callback
client.on_disconnect = on_disconnect
# Registed publish message callback
client.on_message = on_message
# Set access token
client.username_pw_set(ACCESS_TOKEN)
#Perform disconnection in case system powers up from scratch 
client.disconnect()
#---------------------------------Creating & Starting Tasks---------------------------/
#Print ATX DaliHat information to serial shell monitor
DaliHat.Print_DaliHatInfo()

#Add threads to scheduler
pyRTOS.add_task(pyRTOS.Task(MQTT_ConnectionManager,6, name="MQTT_ConnManager", mailbox=False))
pyRTOS.add_task(pyRTOS.Task(DALI_SysMonitor,4, name="DALI_SysMonitor", mailbox=False))

# Startx Client Loop
client.loop_start()

#Start the RTOS
pyRTOS.start()