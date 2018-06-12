import threading
import serial
from PyCRC.CRC16 import CRC16
import paho.mqtt.client as mqtt
import json, time
import random

#setup Serial 
ser = serial.Serial(
port='/dev/ttyS0',
baudrate=115200,
parity=serial.PARITY_NONE,
stopbits=serial.STOPBITS_ONE,
bytesize= serial.EIGHTBITS,
timeout=0.5)
# timer led
    
def node_crc(arg1, arg2, arg3):
    data = serial.to_bytes([arg1 ,arg2, arg3])
    crc_result = CRC16().calculate(data)
    status = crc_result 
    lowbyte = status & 0xff
    highbyte = (status & 0xff00) >> 8
    data = serial.to_bytes([arg1 , arg2, arg3, lowbyte, highbyte,0x0A])
    ser.write(data)


#MQTT on_connect and subscribe, disconnect
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.connected_flag=True #set flag
        print("MQTT connect to Thingsboard success")
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed
    #subscribe to RPC commands from the server ------------ Server side
        client.subscribe('v1/devices/me/rpc/request/+') 
    #subcribe the RPC response from server     ------------  Client side
        #publish device attributes
        client.publish('v1/devices/me/attributes', json.dumps({"Device 1":"Not Connect", "Device 2":"Not Connect"}))
        client.publish('v1/devices/me/attributes', json.dumps({"Area1/Bulb1":"OFF"}), 1) 
        client.publish('v1/devices/me/attributes', json.dumps({"Area1/Bulb2":"OFF"}), 1)
        client.publish('v1/devices/me/attributes', json.dumps({"Area2/Light1":"OFF"}), 1)
        client.publish('v1/devices/me/attributes', json.dumps({"Area2/Light2":"OFF"}), 1)
    else:
        print("MQTT Bad connection Returned code=",rc)


# led state
bulb1  = False
bulb2  = False
light1 = False
light2 = False
#control time on/off led
realValueLight1 = 0
controlValueLight1 = None
light1Alarm = False

realValueLight2 = 0
controlValueLight2 = None
light2Alarm = False
########################
realValueBulb1 = 0
controlValueBulb1 = None
bulb1Alarm = False

realValueBulb2 = 0
controlValueBulb2 = None
bulb2Alarm = False

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global bulb1
    global bulb2
    
    global light1
    global light2
    
    global controlValueLight1
    global controlValueLight2
    global controlValueBulb1
    global controlValueBulb2
    
    global bulb1Alarm
    global bulb2Alarm 
    global light1Alarm
    global light2Alarm
    
    print 'Topic: ' + msg.topic + '\nMessage: ' + str(msg.payload)
   #print (str(msg.payload))
    if msg.topic.startswith( 'v1/devices/me/rpc/request/'):
       # Decode JSON request
       data = json.loads(msg.payload)
       requestId = msg.topic[len('v1/devices/me/rpc/request/'):len(msg.topic)]
       print 'This is a RPC call. RequestID: ' + requestId + '. Going to reply now!'

       # Check request method
       # Node 1  ------------------     BULB 1
       if data['method'] == 'setArea1Bulb1':
           if data['params'] == True:
               print ("Area 1 Bulb 1 ON")
               #send uart alarm on led     
               node_crc(0x10,0x21,0x11) # on led
               bulb1 = True
               client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(bulb1), 1)
           elif data['params'] == False:
               print ("Area 1 Bulb 1 OFF")
               #send uart off led  1
               bulb1 = False
               #ser.write('\x10'+'\x21'+'\x00'+'\x19'+'\x95'+'\x0A')
               node_crc(0x10,0x21,0x00)
               client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(bulb1), 1)
       elif data['method'] == 'getArea1Bulb1':
               client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(bulb1), 1)
                       
       if data['method'] == 'setTimerBulb1':
           controlValueBulb1  = data['params']
           if controlValueBulb1 != 0:
               node_crc(0x10,0x29, int(controlValueBulb1)) # send alarm time
               print('Going to set new control value BULB 1: ' + controlValueBulb1)
           
       elif data['method'] == 'getTimerBulb1':
           if controlValueBulb1 is None:
                client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(realValueBulb1))
           else: 
                client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(controlValueBulb1))
               
       # Node 1 -------------------------- BULB 2
       if data['method'] == 'setArea1Bulb2':
           if data['params'] == True:
               print ("Area 1 Bulb 2 ON")
               bulb2 = True
               node_crc(0x10, 0x22, 0x11)
               #ser.write('\x10'+'\x22'+'\x11'+'\xD9'+'\x69'+'\x0A')
               client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(bulb2), 1)
           elif data['params'] == False:
               print ("Area 1 Bulb 2 OFF")
               bulb2 = False
               node_crc(0x10, 0x22, 0x00)
               client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(bulb2), 1)
       elif data['method'] == 'getArea1Bulb2':
               client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(bulb2), 1)
############BULB2 TIMER
       if data['method'] == 'setTimerBulb2':
           controlValueBulb2  = data['params']
           if controlValueBulb2 != 0:
               node_crc(0x10,0x30, int(controlValueBulb2)) # send alarm time
               print('Going to set new control value BULB 2: ' + controlValueBulb2)
               #client.publish('v1/devices/me/attributes', json.dumps({"Bulb 2 Count":controlValueBulb2}), 1)
       elif data['method'] == 'getTimerBulb2':
           if controlValueBulb2 is None:
                client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(realValueBulb2))
           else: 
                client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(controlValueBulb2)) 
        ##########      
       # Node 2 ____ Light 1
       
       if data['method'] == 'setArea2Light1':
           if data['params'] == True:
               print ("Area 2 Light 1 ON")
               light1 = True
               node_crc(0x30, 0x21, 0x11)
               #ser.write('\x30'+'\x21'+'\x11'+'\xD8'+'\x53'+'\x0A')
               client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(light1), 1)
           elif data['params'] == False:
               print ("Area 2 Light 1 OFF")
               #ser.write('\x30'+'\x21'+'\x00'+'\x18'+'\x5F'+'\x0A')
               node_crc(0x30, 0x21, 0x00)
               light1 = False
               client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(light1), 1)               
       elif data['method'] == 'getArea2Light1':
               client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(light1), 1)
               
       if data['method'] == 'setTimerLight1':
           controlValueLight1  = data['params']
           if controlValueLight1 != 0:
               node_crc (0x30, 0x29, int(controlValueLight1))
               print('Going to set new control value LIGHT 1: ' + controlValueLight1)
           
       elif data['method'] == 'getTimerLight1':
           if controlValueBulb2 is None:
                client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(realValueLight1))
           else: 
                client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(controlValueLight1)) 
       
# light 2222----------------------------------------------------------------------------       
       if data['method'] == 'setArea2Light2':
           if data['params'] == True:
               print ("Area 2 Light 2 ON")
               if light2Alarm == True:
                   light2Alarm = False
                   time.sleep(0.1)
               light2 = True
               node_crc(0x30, 0x22, 0x11)
               client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(light2), 1)
           elif data['params'] == False:
               print ("Area 2 Ligh 2 OFF")
               light2 = False
               node_crc(0x30, 0x22, 0x00)
               client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(light2), 1)
       
       elif data['method'] == 'getArea2Light2':
               client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(light2), 1)
#### Loght2 ------- alarm
       if data['method'] == 'setTimerLight2':
           controlValueLight2  = data['params']
           if controlValueLight2 != 0:
               node_crc (0x30, 0x30, int(controlValueLight2)) 
               print('Going to set new control value LIGHT 2: ' + controlValueLight2)
               #client.publish('v1/devices/me/attributes', json.dumps({"Light 2 Count":controlValueLight2}), 1)
       elif data['method'] == 'getTimerLight2':
           if controlValueBulb2 is None:
                client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(realValueLight2))
           else: 
                client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(controlValueLight2)) 
                  
def on_disconnect(client, userdata, rc):
    print (" Disconnect Broker")

#setup Thingsboard and MQTT client
THINGSBOARD_HOST = '192.168.43.184'
ACCESS_TOKEN = 'QJdEzwK3hEkru7YRicak'

client = mqtt.Client()
client.on_connect=on_connect  #bind callback function
client.on_disconnect = on_disconnect
client.on_message = on_message

# Set access token
client.username_pw_set(ACCESS_TOKEN)
# Connect to ThingsBoard using default MQTT port and 60 seconds keepalive interval
client.connect(THINGSBOARD_HOST, 1883, 60)
print('hello from Raspberry')
# ARRAY[0] = mASTER ADDRESS
# ARRAY[1] = NODE ADDRESS
# ARRAY[2] = FUNCTION
# ARRAY[3] && ARRAY[4] == DATA
#connect node1 & node 2
on_connect_1 = False
on_connect_2 = False

array = [0,0,0,0,0,0,0]
#function for thread 1, data from node 1
def node1(arg1,arg2,arg3):
    global on_connect_1
    global keep_alive_node_1
    
    #print threading.currentThread().getName(), 'Starting'
    if (arg1 == 0x23):
        #print "Area 1 light current: ",arg3 + random.randrange(0, 10)
        data_out = json.dumps ({'currentA1':arg3 + random.randrange(0, 10)})
        client.publish('v1/devices/me/telemetry', data_out, 1)
        
    elif (arg1 == 0x24):
        #print "Area 1 temperature: ",arg3 + random.randrange(0, 10)
        data_out = json.dumps({'temperatureA1': arg3 + random.randrange(0, 10)})
        client.publish('v1/devices/me/telemetry', data_out, 1)
        
    elif (arg1 == 0x25): # humidity
        #print "Area 1 humidity: ",arg3 + random.randrange(0, 10)
        data_out = json.dumps({'humidityA1':arg3 + random.randrange(0, 10)})
        client.publish('v1/devices/me/telemetry', data_out, 1)
        
    elif (arg1 == 0x27): #keep_alive message every 60s
        if (arg2 ==0xFF and arg3 == 0xFF):
            keep_alive_node_1 = True
            
    elif (arg1 == 0x28): #on_connect message
        if (arg2== 0xFF and arg3 == 0xFF):
            ##cpnnect
            on_connect_1 = True
            print ("Connect to slave 0x10")
            client.publish('v1/devices/me/attributes', json.dumps({"Device 1":"Connected"}), 1)
            ser.write('\x10'+'\x28'+'\xFF'+'\x5F'+'\x85' + '\x0A')
            
    elif (arg1 == 0x29):
        print "Bulb 1 Off Count down: ", arg3
        client.publish('v1/devices/me/attributes', json.dumps({"Bulb 1 Count":arg3}), 1)     
    elif (arg1 == 0x30):
        print "Bulb 2 Off Count down: ", arg3
        client.publish('v1/devices/me/attributes', json.dumps({"Bulb 2 Count":arg3}), 1)
    
    elif (arg1 == 0x21):
        if (arg2==0 and arg3==0x11 ):
            print("led 1 Area 1 ON")
            client.publish('v1/devices/me/attributes', json.dumps({"Area1/Bulb1":"ON"}), 1)
        elif (arg2== 0 and arg3== 0):
            client.publish('v1/devices/me/attributes', json.dumps({"Area1/Bulb1":"OFF"}), 1)
            print ("led 1 Area 1 OFF")
            
    elif (arg1 == 0x22):
        if (arg2==0 and arg3==0x11 ):
            print("led 2 Area 1 ON")
            client.publish('v1/devices/me/attributes', json.dumps({"Area1/Bulb2":"ON"}), 1)       
        elif (arg2== 0 and arg3 == 0):
            print ("led 2 Area 1 OFF")
            client.publish('v1/devices/me/attributes', json.dumps({"Area1/Bulb2":"OFF"}), 1)               
    return        
        
#function for thread 2, data from node 2
def node2(arg1,arg2,arg3):
    #print threading.currentThread().getName(), 'Starting'
    global on_connect_2
    global keep_alive_node_2
    
    if (arg1 == 0x23):
        #print "Area 2 bulb current: ",arg3 + random.randrange(0, 10)
        data_out = json.dumps ({'currentA2':arg3 + random.randrange(0, 10)})
        client.publish('v1/devices/me/telemetry', data_out, 1)
        
    elif (arg1 == 0x24): #temperature
        #print "Area 2 temperature: ",arg3 + random.randrange(0, 10)
        data_out = json.dumps ({'temperatureA2':arg3 + random.randrange(0, 10)})
        client.publish('v1/devices/me/telemetry', data_out, 1)
    
    elif (arg1 == 0x25): # humidity
        #print"Area 2 humidity: ",arg3 + random.randrange(0, 10)
        data_out = json.dumps ({'humidityA2':arg3 + random.randrange(0, 10)})
        client.publish('v1/devices/me/telemetry', data_out, 1)
        
    elif (arg1 == 0x27):
        if (arg2 == 0xFF and arg3 ==0xFF):
            keep_alive_node_2 = True

    elif (arg1 == 0x28): #on_connect message
        if (arg2== 0xFF and arg3 == 0xFF):
            ##cpnnect
            on_connect_2 = True
            print ("Connect to slave 0x30")
            client.publish('v1/devices/me/attributes', json.dumps({"Device 2":"Connected"}), 1)
            ser.write('\x30'+'\x28'+'\xFF'+'\x5E'+'\x4F'+'\x0A')
            #timeout_2.start() #start keep_alive, timeout 60s
    
    elif (arg1 == 0x29):
        print "Light 1 Off Count down: ", arg3
        client.publish('v1/devices/me/attributes', json.dumps({"Light 1 Count":arg3}), 1)     

    elif (arg1 == 0x30):
        print "Light 2 Off Count down: ", arg3
        client.publish('v1/devices/me/attributes', json.dumps({"Light 2 Count":arg3}), 1)
        
    elif (arg1 == 0x21):
        if (arg2==0 and arg3==0x11 ):
            print("led 1 Area 2 ON")
            client.publish('v1/devices/me/attributes', json.dumps({"Area2/Light1":"ON"}), 1)
        elif (arg2== 0 and arg3== 0):
            print ("led 1 Area 2 OFF")
            client.publish('v1/devices/me/attributes', json.dumps({"Area2/Light1":"OFF"}), 1)
            
    elif (arg1 == 0x22):
        if (arg2==0 and arg3==0x11 ):
            print("led 2 Area 2 ON")
            client.publish('v1/devices/me/attributes', json.dumps({"Area2/Light2":"ON"}), 1)               
        elif (arg2== 0 and arg3 == 0):
            print ("led 2 Area 2 OFF")
            client.publish('v1/devices/me/attributes', json.dumps({"Area2/Light2":"OFF"}), 1)
    return
############    MAIN #####################
        
        
client.loop_start()
while True:
    #print ("In while loop")
    read = ser.read(7)
    if(read): 
        data_crc = CRC16().calculate(read)
        if (data_crc != 0):
            print("Error because crc")
        else:#data_crc =0
            #print ("receive success and process")
            for n in range(len(read)):
                array[n] = int(ord(read[n]))
                
            if (array[0] != 0xFF):
                print ("not in netwrok")
            elif (array[1] == 0x10):
                #call thread 1
                w1 = threading.Thread(name='Thread-1 - process Node 1', target=node1,
                                         args=(array[2],array[3],array[4],))
                w1.start()
                #w1.join()
            elif (array[1] == 0x30):
                #call thread
                w2= threading.Thread(name='Thread-2 - process Node 2', target=node2,
                                         args=(array[2],array[3],array[4],))                                                       
                w2.start()
                #w2.join()
      
       
       
    

