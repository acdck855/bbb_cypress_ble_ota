#!env/bin/python

from bluepy import btle
import crcmod
import time
import cyacd2
import host

class Delegate( btle.DefaultDelegate ):
    def __init__( self ):
        btle.DefaultDelegate.__init__( self )
        self.handle = 0
        self.data = 0

    def handleNotification( self, cHandle, data ):
        print( "cHandle: {}\tdata: {}".format( cHandle, data ) )
        self.handle = cHandle
        self.data = data


target_mac = "00:a0:50:f4:64:be"
dfu_uuid = "00060000-F8CE-11E4-ABF4-0002A5D5C51B"
delegate = Delegate()

crc32c_func = crcmod.predefined.mkCrcFun( 'crc-32c' )

target = btle.Peripheral( target_mac )
target.setDelegate( delegate )

dfu_service = target.getServiceByUUID( dfu_uuid )

# Enable Notifications on the DFU Device
target.writeCharacteristic( 0x0C, bytes.fromhex( "0100" ), withResponse=True )
resp = target.readCharacteristic( 0x0C ) 

# check response
if resp != bytes.fromhex( "0100" ):
    print( "Failed to enable notifications on target " + target_mac + '.' )
    raise SystemExit

# Open the CYACD2 file and program the target
fwImg = cyacd2.Application("mtb-example-psoc6-capsense-buttons-slider_crc.cyacd2")

hostCmd = Host()

# Begin a DFU operation
packet = hostCmd.enterDFU()
target.writeCharacteristic(0x0B, packet)

# check response
if not target.waitForNotifications(2):
    print("No response from target! Enter DFU unsuccessful.")
    raise SystemExit
if delegate.handle != 0x0B:
    print("Expected response from handle 0x0B. Enter DFU unsuccessful.")
    raise SystemExit
statusCode, data = hostCmd.getResponse(delegate.data)
if statusCode != 0:
    print(f"Status code {statusCode} returned. Enter DFU unsuccessful.")
    raise SystemExit
jtagID, deviceRev, dfuSdkVer = struct.unpack("<4sc3s", data)
print("Enter DFU successful")
print("> JTAG ID:", jtagID)
print("> Device Revision", deviceRev)
print("> DFU SDK Version", dfuSdkVer)

# Create Set Application Metadata packet and send it
packet = hostCmd.setApplicationMetadata(fwImg.appID, fwImg.appStartAddr, fwImg.appLength)
target.writeCharacteristic(0x0B, packet)

# check response
if not target.waitForNotifications( 2 ):
    print( "No response from target! Set Application Metadata unsuccessful." )
    raise SystemExit
if delegate.handle != 0x0B:
    print("Expected response from handle 0x0B. Set Application Metadata unsuccessful.")
    raise SystemExit
statusCode, data = hostCmd.getResponse(delegate.data)
if statusCode != 0:
    print(f"Status code {statusCode} returned. Set Application Metadata unsuccessful.")
    raise SystemExit
print("Set Application Metadata successful")

# Iterate through the remaining rows of program data and send them to the target
while True:
    try:
        rowAddr, rowData = fwImg.getNextRow()
    except:
        break
    
    # Calculate the CRC-32C checksum of the row data
    crc = crc32c_func(rowData)

    # Break the row data into smaller chucks of size payloadSize
    payloadLength = 137
    rowData = [rowData[i:i+payloadLength] for i in range(0, len(rowData), payloadLength)]

    # Send all but the last chunk using the Send Data command
    for chunk in rowData[:-1]:
        packet = hostCmd.sendData(chuck)

        # Slice the packet and send the slices
        sliceLength = 20
        packet = [packet[i:i+sliceLength] for i in range(0, len(packet), sliceLength)]

        for p in packet:
            print(p, target.writeCharacteristic(0x0B, p))
        
        # Check response
        if not target.waitForNotification(2):
            print("No response from target! Send Data unsuccessful.")
            raise SystemExit
        if delegate.handle != 0x0B:
            print("Expected response from handle 0x0B. Send Data unsuccessful.")
            rasie SystemExit
        statusCode, data = hostCmd.getResponse(delegate.data)
        if statusCode != 0:
            print(f"Status code {statusCode} returned. Send Data unsuccessful.")
            raise SystemExit
        print("Send Data successful.")

    # Send the last chuck using the Program Data command
    packet = hostCmd.programData(rowAddr, crc, rowData[-1])

    # Slice the packet and send the slices
    sliceLength = 20
    packet = [packet[i:i+sliceLength] for i in range(0, len(packet), sliceLength)]

    for p in packet:
        print(p, target.writeCharacteristic(0x0B, p))
    
    # Check response
    if not target.waitForNotification(2):
        print("No response from target! Program Data unsuccessful.")
        raise SystemExit
    if delegate.handle != 0x0B:
        print("Expected response from handle 0x0B. Program Data unsuccessful.")
        rasie SystemExit
    statusCode, data = hostCmd.getResponse(delegate.data)
    if statusCode != 0:
        print(f"Status code {statusCode} returned. Program Data unsuccessful.")
        raise SystemExit
    print("Program Data successful.")

fwImg.close()

# Send Verify Application command
packet = hostCmd.verifyApplication(fwImg.appNum)
target.writeCharacteristic(0x0B, packet)

# check response
if not target.waitForNotifications(2):
    print("No response from target! Verify Application unsuccessful.")
    raise SystemExit
if delegate.handle != 0x0B:
    print("Expected response from handle 0x0B. Verify Application unsuccessful.")
    raise SystemExit
statusCode, data = hostCmd.getResponse(delegate.data)
if statusCode != 0:
    print(f"Status code {statusCode} returned. Verify Application unsuccessful.")
    raise SystemExit
appValid = struct.unpack("<B", data)
print("Verify Application successful")
print("> Application Valid:", appValid)

# Send the Exit DFU command
packet = hostCmd.exitDFU()
target.writeCharacteristic(0xB, packet)

try:
    target.disconnect()
except:
    pass
finally:
    print( "Disconnected from DFU Device." )
