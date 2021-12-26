import minimalmodbus
from   enum import IntEnum

#Serial Configuration Parameters 
D111_DEFAULT_BAUDRATE   = 9600                #Baudrate of serial port connected to USB-to-RS485 converter 
MODBUS_MODE             = 'rtu'               #Modbus mode can be either 'rtu' OR 'ascii'
DBG_ENABLED             = False                #Modbus debug prints can be set to True OR False

#Register Sizes
Word = 1
DoubleWord = 2

#D111 Register Names
class D111_Registers(IntEnum):
    Voltage = 1
    Current = 7
    ActivePwr = 19
    ReactivePwr = 25
    PwrFactor = 37
    Hz = 49
    AvgKW_Pwr = 2065
    MaxAvgKW_Pwr = 2577
    TotActEnergy = 6687
    TotReactEnergy = 6691
    PartialActEnergy = 6697
    PartialReactEnergy = 6702
    HrCounter = 7679
    PartialHrCounter = 7681
    ProgThresholdStatus = 8719

class LovatoD111():

        def __init__(self,D111_ModBusAdd,USB_SerialPortName,SerialTimeout):
         
            #Configure serial comms with D111
            self.Lovato_D111 = minimalmodbus.Instrument(USB_SerialPortName,D111_ModBusAdd,'rtu',False,DBG_ENABLED)
            self.Lovato_D111.serial.baudrate = D111_DEFAULT_BAUDRATE
            self.Lovato_D111.serial.timeout = SerialTimeout
            

        def GetActiveEnergy(self):
            
            #Read out contents of 2-byte register containing total active energy measurement
            PowerArr = self.Lovato_D111.read_registers(D111_Registers.TotActEnergy,DoubleWord)
            
            #Bitwise logic for combining two bytes to form 16-bit integer
            Power = PowerArr[0]
            Power = (Power << 8) | PowerArr[1]
         
            #Divide by 1000 to convert to kWh
            return Power/1000
            

        def GetVoltage(self):
         
            #Read out contents of 2-byte(Double Word) register containing most recent voltage measurement
            VoltageArr = self.Lovato_D111.read_registers(D111_Registers.Voltage,DoubleWord)
            
            #Bitwise logic for combining two bytes to form 16-bit integer
            Voltage = VoltageArr[0]
            Voltage = (Voltage << 8) | VoltageArr[1]
         
            #Dividing by 100 as spec'd in datasheet
            return Voltage/100

        def GetCurrent(self):

            #Read out contents of 2-byte(Double Word) register containing most recent current measurement
            CurrentArr = self.Lovato_D111.read_registers(D111_Registers.Current,DoubleWord)
         
            #Divide result by 1000 to convert to amperes
            Current = CurrentArr[1]/1000
         
            return Current

        def GetActivePwr(self):

            #Divide by 100 to convert to KW
            ActivePwr = self.Lovato_D111.read_registers(D111_Registers.ActivePwr,DoubleWord)/100
         
            return ActivePwr

        def GetReactivePwr(self):
         
            #Divide by 100 to convert to KVar
            ReactivePwr = self.Lovato_D111.read_registers(D111_Registers.ReactivePwr,DoubleWord)/100
         
            return ReactivePwr

        def GetPwrFactor(self):
         
            #Divide by 100 to get power factor
            PwrFactor = self.Lovato_D111.read_registers(D111_Registers.PwrFactor,DoubleWord)/100
         
            return PwrFactor

        def GetFrequency(self):
            
            #Divide by 10 to get frequency
            Hz = self.Lovato_D111.read_registers(D111_Registers.Hz,DoubleWord)/10
            
            return Hz

        def GetHourCounter(self):
            
            HourCounter = self.Lovato_D111.read_registers(D111_Registers.HrCounter,DoubleWord)
            
            return HourCounter

        def GetPartialHourCounter(self):
            
            PartialHourCounter = self.Lovato_D111.read_registers(D111_Registers.PartialHrCounter,DoubleWord)
            
            return PartialHourCounter

        def GetAvgKW_Pwr(self):
            
            #Divide by 10000 to convert to kW
            AvgKW_Pwr = self.Lovato_D111.read_registers(D111_Registers.AvgKW_Pwr,DoubleWord)/10000
            
            return AvgKW_Pwr

        def GetMaxAvgKW_Pwr(self):
            
            #Divide by 10000 to convert to kW
            MaxAvgKW_Pwr = self.Lovato_D111.read_registers(D111_Registers.MaxAvgKW_Pwr,DoubleWord)/10000
            
            return MaxAvgKW_Pwr

        def GetProgThresholdStatus(self):

            ThresholdExceeded = self.Lovato_D111.read_registers(D111_Registers.ProgThresholdStatus,Word)
            
            #Any value greater than 0 indicatest that an alarm has been raised
            if(ThresholdExceeded[0] > 0):
                return True
            
            return False
