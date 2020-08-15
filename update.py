#!env/bin/python

from bluepy import btle
import crcmod
import time
import cyacd2
import host
import struct

class Delegate(btle.DefaultDelegate):
    def __init__(self):
        super().__init__()
        self.handle = 0
        self.data = 0

    def handleNotification(self, cHandle, data):
        self.handle = cHandle
        self.data = data


target_mac = "00:a0:50:f4:64:be"
dfu_uuid = "00060000-F8CE-11E4-ABF4-0002A5D5C51B"
charHandle = 0x009
propHandle = 0x00A

crc32cFunc = crcmod.predefined.mkCrcFun('crc-32c')

target = btle.Peripheral(target_mac).withDelegate(Delegate())

# Enable Notifications on the DFU Device
target.writeCharacteristic(propHandle, bytes.fromhex("0100"), withResponse=True)
resp = target.readCharacteristic(propHandle) 

# check response
if resp != bytes.fromhex("0100"):
    print("Failed to enable notifications on target " + target_mac + '.')
    raise SystemExit

# Open the CYACD2 file and program the target
fwImg = cyacd2.Application("mtb-example-psoc6-capsense-buttons-slider_crc.cyacd2")

hostCmd = host.Host(target, charHandle)

# Begin a DFU operation
hostCmd.enterDFU(fwImg.productID)

# Set the application metadata
hostCmd.setApplicationMetadata(fwImg.appID, fwImg.appStartAddr, fwImg.appLength)

# Iterate through the remaining rows of program data and send them to the target
while True:
    try:
        rowAddr, rowData = fwImg.getNextRow()
    except:
        break
    
    # Calculate the CRC-32C checksum of the row data
    crc = crc32cFunc(rowData)

    # Break the row data into smaller chunks of size payloadSize
    payloadLength = 256
    rowData = [rowData[i:i+payloadLength] for i in range(0, len(rowData), payloadLength)]

    # Send all but the last chunk using the Send Data command
    for chunk in rowData[:-1]:
        hostCmd.sendData(chunk)

    # Send the last chunk using the Program Data command
    hostCmd.programData(rowAddr, crc, rowData[-1])

fwImg.close()

# Send Verify Application command
hostCmd.verifyApplication(fwImg.appID)

# Send the Exit DFU command
hostCmd.exitDFU()

try:
    target.disconnect()
except:
    pass
finally:
    print( "Disconnected from DFU Device." )
