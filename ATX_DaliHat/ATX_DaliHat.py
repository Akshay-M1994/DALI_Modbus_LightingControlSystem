import serial
import sys
import RPi.GPIO as GPIO
from   enum import IntEnum
import time

#Serial Debug prints can be set to True OR False
DBG_ENABLED = False

#Time Delay Constants
DaliTxDelay = 0.125
DaliRxDelay = 0.200

#DALI Broadcast address
BROADCAST_ADDRESS = 0x7F

#DALI Short Address Range
MAX_SHORT_ADDRESS = 0x40
MIN_SHORT_ADDRESS = 0x00

#DALI Long/Random Address Range
MAX_RANDOM_ADDRESS = 0xFFFFFF
MIN_RANDOM_ADDRESS = 0x000000

#DALI Commands
#class DALI_Commands(IntEnum):

#enums used for configuring pins
class ATX_DaliHatPwrPins(IntEnum):
    SECONDARY_PWR_PIN = 5
    PRIMARY_PWR_PIN = 6
#enums used for describing error statuses
class ATX_DaliHat_ErrorStatus(IntEnum):
    INIT_OK = 0x00
    INIT_FAILED = 0x01
    PRIMARY_PWR_FAILURE = 0x02
    SECONDARY_PWR_FAILURE = 0x03
    PWR_OK = 0x04
    
class ATX_DaliHat():
    
    def __init__(self,SerialPortName):
    
        #Create Serial Port Name
        self.ATX_DaliHatSerial = serial.Serial(SerialPortName,baudrate = 19200,parity=serial.PARITY_NONE,stopbits=serial.STOPBITS_ONE,bytesize=serial.EIGHTBITS, timeout=1,)

        #Configure GPIOs used to check power status
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(ATX_DaliHatPwrPins.PRIMARY_PWR_PIN,GPIO.IN)
        GPIO.setup(ATX_DaliHatPwrPins.SECONDARY_PWR_PIN,GPIO.IN)
        
        self.CheckPwrStatus()
    
    def PrintDALI_HatVersionInfo(self):
        
        #Query DALI Hat version status
        self.ATX_DaliHatSerial.write("v\n".encode())
        
        #Time to allow for transmission & response
        time.sleep(DaliTxDelay/2)
        
        #Read response
        bytesAvailable = self.ATX_DaliHatSerial.inWaiting()
        Response = self.ATX_DaliHatSerial.read(bytesAvailable).decode("utf-8")
                
        #Print DALI Hat version
        print("ATX DALI HAT: V" + Response[1:7])
        print("HW Version: " + Response[1:3])
        print("FW Version: " + Response[3:5])
        print("Hardware Type:" + Response[5:7])
        
    def GetDALI_BusStatus(self):

        #Query DALI Bus state
        self.ATX_DaliHatSerial.write("d\n".encode())
        
        #Time to allow for transmission & response
        time.sleep(DaliTxDelay)
        
        #Read response
        bytesAvailable = self.ATX_DaliHatSerial.inWaiting()
        Response = self.ATX_DaliHatSerial.read(bytesAvailable).decode("utf-8")
        
        #Strip newline characters from response
        Response = Response.replace("\n","")
                
        #Print DALI Bus state
        if (Response.find("D01") != -1):
            print("No power on DALI bus")
        elif (Response.find("D11") != -1):
            print("Bus Current too high - Cannot drive to zero")
        elif (Response.find("D21") != -1):
            print("DALI bus OK")
        elif (Response.find("D41") != -1):
            print("Bus Voltage > 24V")
        else:
            print("Invalid Response Received!")
        

    def CheckPwrStatus(self):

        #Read GPIO Inputs to determine power status
        if GPIO.input(ATX_DaliHatPwrPins.PRIMARY_PWR_PIN) == 0 :
            print("Primary Power Failure")
            return ATX_DaliHat_ErrorStatus.PRIMARY_PWR_FAILURE
        
        if GPIO.input(ATX_DaliHatPwrPins.SECONDARY_PWR_PIN) == 0 :
            print("Secondary Power Failure")
            return ATX_DaliHat_ErrorStatus.SECONDARY_PWR_FAILURE
        
        print("Power Sources OK")
        
        return ATX_DaliHat_ErrorStatus.PWR_OK
    
    def SetTargetLevel(self,DevAddress,TargetLevel):
        
        #Set target level
        self.ATX_DaliHatSerial.write("h%02X%02X\n".encode()%(2*DevAddress,TargetLevel))
    
    def SetDeviceState(self,DevAddress,DeviceState):
    
        #Device state is either '1' or '0',we translate to either 0 or 254 before writing to bus
        On_Off_State =  254 * DeviceState
    
        #Set device either on or off
        self.ATX_DaliHatSerial.write("h%02X%02X\n".encode()%(2*DevAddress,On_Off_State))
        
    def ClearInputSerialBuffer(self):
        
        #Get number of bytes in input buffer
        bytesAvailable = self.ATX_DaliHatSerial.inWaiting()
        self.ATX_DaliHatSerial.read(bytesAvailable)
        
    def Reset(self,DevAddress):
    
        #Reset all variables for specified device on bus
        self.ATX_DaliHatSerial.write("t%02X20\n".encode()%(2*DevAddress + 1))
        
        time.sleep(4*DaliTxDelay)
    
    def QueryReset(self,DevAddress):
            
        #Send Query Reset command
        self.ATX_DaliHatSerial.write("h%02X95\n".encode()%(2*DevAddress + 1))
        
        #Atleast 200ms is require for response
        time.sleep(DaliRxDelay)
        
        #Determine number bytes in input buffer
        bytesAvailable = self.ATX_DaliHatSerial.inWaiting()
        
        #Read Response
        Response = self.ATX_DaliHatSerial.read(bytesAvailable).decode("utf-8")
        
        #Strip newline characters from response
        Response = Response.replace("\n","")
        
        print(Response)
        
        #Search buffer for "JFF or Yes" response
        if(Response.find("JFF") != -1):
            return True
        
        return False;
        
        
    def QueryLevel(self,DevAddress):
        
        for RetryCount in range(5):
            
            #Clear input serial buffer
            self.ClearInputSerialBuffer()
            
            #Query target Level
            self.ATX_DaliHatSerial.write("h%02XA0\n".encode()%(2*DevAddress + 1))
            
            #Read Response
            Response = self.ATX_DaliHatSerial.read(4).decode("utf-8")
            
            #strip newline characters from response
            Response = Response.strip()
        
            TargetLevel = 0
            
            #Confirm that response begins with a 'J' as per documentation
            if Response[0] == 'J':
                
                #Combine 2nd & 3rd character of response to form a single string represent target level in hex format and then convert to integer
                TargetLevel = int(Response[1] + Response[2], base = 16)
                #print("Current Target Level Of Device " + str(DevAddress)+ " is " + str(TargetLevel))
        
                return TargetLevel
            else:
                print("Failed to obtain Current Target Level.Retrying....")
                
        
        return TargetLevel
    
    def QueryStatus(self,DevAddress):
     
        #Clear input serial buffer
        self.ClearInputSerialBuffer()
 
        #Query Device Status
        self.ATX_DaliHatSerial.write("h%02X90\n".encode()%(2*DevAddress + 1))

        #Transmission Delay
        time.sleep(DaliTxDelay)

        #Read number of bytes available
        bytesAvailable = self.ATX_DaliHatSerial.inWaiting()

        #Read Response
        Response = self.ATX_DaliHatSerial.read(bytesAvailable).decode("utf-8")
        
        #Strip newline characters from response
        Response = Response.replace("\n","")

        #Response must contain 'J' for it to be valid , refer to documentation
        if(Response.find("J") == -1):
            print("Invalid Response Received")
        else:
            print("Status of Device [%02X] is [%s]"%(DevAddress,Response))
                
    def Initialize(self):
        
        #Broadcast Initialize command
        self.ATX_DaliHatSerial.write("tA500\n".encode())
        
    def Randomize(self):
      
        #Broadcast randomize command
        self.ATX_DaliHatSerial.write("tA700\n".encode())
        
    def AssignSingleAddress(self,DeviceAddress):
                
        #Load the DTR into a single device
        self.ATX_DaliHatSerial.write('hA3%02X\n'.encode()%(2*DeviceAddress + 1))
        
        #Allow delay for DTR write to be written
        time.sleep(DaliTxDelay)
        
        #Save DTR as short address
        self.ATX_DaliHatSerial.write('tFF80\n'.encode())
        
        #Allow time for DTR to be written to short address
        time.sleep(DaliTxDelay)
        
    def CommissionDevices(self):
        
        #Variable to track search boundaries during binary search
        Low_LongAdd  = MIN_RANDOM_ADDRESS
        High_LongAdd = MAX_RANDOM_ADDRESS
        
        #Variable to track 'guess' address during binary search
        Random_24_BitAdd = (int)((Low_LongAdd + High_LongAdd)/2)
        
        #Variables to split 24-bit address into high,middle & low bytes
        HighByte = 0x00
        MiddleByte = 0x00
        LowByte = 0x00
        
        #Assigned short addresses as devices are enumerated
        ShortAddress = MIN_SHORT_ADDRESS
                
        #Switch all devices off
        self.SetTargetLevel(BROADCAST_ADDRESS,0)
        
        #Allow devices to switch off before issuing reset command
        time.sleep(DaliTxDelay)
        
        #Broadcast Reset command
        self.Reset(BROADCAST_ADDRESS)
        
        #Broadcast initialize command
        self.Initialize()
        
        #Allow time for initialization to occur
        time.sleep(DaliTxDelay)
        
        #Send Randomize command
        self.Randomize()
        
        #Allow time for start of 15 minute timer
        time.sleep(DaliTxDelay)
        
        print("Dali Master Now Searching For Long Addresses")
        
        while ((Random_24_BitAdd <= (MAX_RANDOM_ADDRESS - 2)) and (ShortAddress <= MAX_SHORT_ADDRESS)):
            while((High_LongAdd - Low_LongAdd) > 1):
                   
                #Split 24-bit address into high,middle & low bytes
                HighByte = (Random_24_BitAdd >> 16)
                MiddleByte = (Random_24_BitAdd >> 8) & 0x0000FF
                LowByte = (Random_24_BitAdd & 0x0000FF)
                                             
                #Write Search high byte
                self.ATX_DaliHatSerial.write("hB1%02X\n".encode()%HighByte)
                time.sleep(DaliTxDelay)
                
                #Write Search middle byte
                self.ATX_DaliHatSerial.write("hB3%02X\n".encode()%MiddleByte)
                time.sleep(DaliTxDelay)
                
                #Write Search low byte
                self.ATX_DaliHatSerial.write("hB5%02X\n".encode()%LowByte)
                time.sleep(DaliTxDelay)
                
                #Transmit compare command
                self.ATX_DaliHatSerial.write("hA900\n".encode())
                time.sleep(DaliTxDelay)
                                
                bytesAvailable = self.ATX_DaliHatSerial.inWaiting()
                                
                #Read response of compare query
                Response  = self.ATX_DaliHatSerial.read(bytesAvailable).decode("utf-8")
                time.sleep(DaliTxDelay)
                
                #Strip newline characters from response
                Response = Response.replace("\n","")
                
                #If adjust bounds based on response
                if(Response.find("JFF") != -1):
                    High_LongAdd = Random_24_BitAdd
                else:
                    Low_LongAdd = Random_24_BitAdd
                
                #Update midpoint
                Random_24_BitAdd = (int)((Low_LongAdd + High_LongAdd)/2)
                
                print("Curent Random/Long Address : ",hex(Random_24_BitAdd + 1))
            
            if(High_LongAdd != MAX_RANDOM_ADDRESS):
                    
                #Split new 24-bit address
                HighByte = ((Random_24_BitAdd + 1) >> 16)
                MiddleByte = ((Random_24_BitAdd + 1) >> 8) & 0x0000FF
                LowByte = ((Random_24_BitAdd + 1) & 0x0000FF)
              
                print("Assigning short address.....")
              
                #Write Search high byte
                self.ATX_DaliHatSerial.write("hB1%02X\n".encode()%HighByte)
                time.sleep(DaliTxDelay)
                
                #Write Search middle byte
                self.ATX_DaliHatSerial.write("hB3%02X\n".encode()%MiddleByte)
                time.sleep(DaliTxDelay)
                
                #Write Search low byte
                self.ATX_DaliHatSerial.write("hB5%02X\n".encode()%LowByte)
                time.sleep(DaliTxDelay)
                
                #Program short address
                self.ATX_DaliHatSerial.write("hB7%02X\n".encode()%(1 + (ShortAddress << 1)))
                time.sleep(DaliTxDelay)
                
                #Send terminate command
                self.ATX_DaliHatSerial.write("hAB00\n".encode())
                time.sleep(DaliTxDelay)
                
                #Print short-address assigned
                print("Short-Assigned : [%02X]"%ShortAddress)
                
                #Switch newly assigned device on and off
                self.SetTargetLevel(ShortAddress,0)
                
                #Leave off for 1 second
                time.sleep(1)
                
                #Switch newly assigned device on
                self.SetTargetLevel(ShortAddress,254)
                
                #Leave on for 1 second
                time.sleep(1)
                
                #Switch off again
                self.SetTargetLevel(ShortAddress,0)
                
                #Increment short address
                ShortAddress = ShortAddress + 1
                
                #Reset high part of long address in preparation for next iteration
                High_LongAdd = MAX_RANDOM_ADDRESS
        
                #Variable to track 'guess' address during binary search
                Random_24_BitAdd = (int)((Low_LongAdd + High_LongAdd)/2)
                
        else:
            print("Commissioning Process Has Completed.Terminating Process...")
        
        #Send command to terminate commissioning process
        self.ATX_DaliHatSerial.write("hA100\n".encode())
        