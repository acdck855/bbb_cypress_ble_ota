#!env/bin/python

from bluepy import btle
import crcmod
import time
import cyacd2
import host
import struct
import threading
import queue


class Delegate(btle.DefaultDelegate):
    def __init__(self):
        super().__init__()
        self.handle = 0
        self.data = 0

    def handleNotification(self, cHandle, data):
        self.handle = cHandle
        self.data = data


class ScanDelegate(btle.DefaultDelegate):
    _nameWidth = 16

    def __init__(self):
        super().__init__()
        self.devDict = {}
        self.devCount = 0
        print("Scanning for devices...")
        print()
        print(f" Choice | {'Device Name':^{self._nameWidth}} |    MAC Address    |  RSSI ")
        print('-' * (41 + self._nameWidth))
        print()
        print("Choose a device to update: ", end='')

    def handleDiscovery(self, scanEntry, isNewDev, isNewData):
        # Add to list
        if isNewDev:
            self.devDict[scanEntry.addr] = scanEntry
            self.devCount = self.devCount + 1
            self._printDevInfo(scanEntry)
        # Update list TODO Do I really need this?
        elif isNewData:
            self.devDict[scanEntry.addr] = scanEntry

    def _printDevInfo(self, dev):
        devName = dev.getValueText(9)
        if devName == None:
            devName = "<No Name>"

        print("\x1B[99D\x1B[K\x1B[1A", end='')
        print(f"{self.devCount:^8}| {devName[:self._nameWidth]:<{self._nameWidth}} | {dev.addr} | {f'{dev.rssi} dB':^7} ")
        print()
        print("Choose a device to update: ", end='', flush=True)

q = queue.Queue()

def getSelection():
    q.put(input())


if __name__ == '__main__':
    # Create a scanner object that sends BLE broadcast packets to the ScanDelegate
    scanner = btle.Scanner().withDelegate(ScanDelegate())

    # Start the scanner
    scanner.start()

    while True:
        # Create and start a thread to get the user's device selection
        threading.Thread(target=getSelection).start()

        # Continuously scan for devices until the user makes a selection
        while q.empty():
            scanner.process(1)

        choice = q.get()
        try:
            choice = int(choice)
        except:
            print(f"\x1B[99D\x1B[K\x1B[1AChoice \"{choice}\" not valid. Choose a device to update: ", end='', flush=True)
            continue

        # Validate the users selection
        if (choice < 1) or (choice > scanner.delegate.devCount):
            print(f"\x1B[99D\x1B[K\x1B[1ADevice {choice} is not on the list. Choose a device to update: ", end='', flush=True)
        else:
            device = list(scanner.delegate.devDict.values())[choice-1]
            print(f"You chose the device with MAC Address \"{device.addr}\"")
            break

    scanner.stop()

    target = btle.Peripheral(device.addr).withDelegate(Delegate())

    dfu_uuid = "00060000-F8CE-11E4-ABF4-0002A5D5C51B"
    charHandle = 0x009
    propHandle = 0x00A

    crc32cFunc = crcmod.predefined.mkCrcFun('crc-32c')

    target = btle.Peripheral(target_mac).withDelegate(Delegate())

    print(target.getState())
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
