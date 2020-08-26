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
        print(f"Notification from {hex(cHandle)}: {data}")
        self.handle = cHandle
        self.data = data


class ScannerUI():
    _choiceWidth = 6
    _nameWidth = 16
    _macAddrWidth = 17
    _rssiWidth = 7

    def __init__(self):
        self.userInput = queue.Queue()
        self.reset()

    def reset(self):
        """Reset the UI. 
        
        For example, if the selected device failed to connect and the user must
        choose again.
        """
        self.devCount = 0
        self._userSelection = None
        self._errMsg = ''

    def update(self, devices):
        """Update the UI by including the supplied devices in the table"""
        if devices == []:
            return

        # If these are the first devices being displayed
        if self.devCount == 0:
            self._displayHeader()
            # For now, we only want input when there are devices to choose from
            threading.Thread(target=self._getUserInput).start()

        # Remove the prompt and move cursor to just below table
        self._moveCursorLeft(999) # Move cursor to beginning of line
        self._clearCursorToEnd() # Clear the line
        self._moveCursorUp()

        for device in devices:
            self.devCount += 1

            # Display the new device in the table
            self._displayDevice(device)

        # Re-display the prompt
        print()
        self._displayPrompt()

    @property
    def userSelection(self):
        """Get and cache the user's selection."""
        if self._userSelection == None: # If the user has not yet made a valid selection
            if not self.userInput.empty(): # If the user has provided some input
                selection = self.userInput.get() # Remove from queue
                
                # Validate the user's input
                try:
                    selection = int(selection)
                except:
                    self._errMsg = f"Choice \"{selection}\" not valid. "
                else:
                    if (selection < 1) or (selection > self.devCount):
                        self._errMsg = f"Device {selection} is not on the list. "
                    else:
                        self._userSelection = selection
                        return self._userSelection
                
                # Re-print the prompt (now with appropriate error message)
                self._moveCursorUp()
                self._moveCursorLeft(999)
                self._clearCursorToEnd()
                self._displayPrompt()
                threading.Thread(target=self._getUserInput).start()

        return self._userSelection 

    def _displayHeader(self):
        """Display the table header."""
        print(
            f" {'Choice':^{self._choiceWidth}} |"
            f" {'Device Name':^{self._nameWidth}} |"
            f" {'MAC ADDRESS':^{self._macAddrWidth}} |"
            f" {'RSSI':^{self._rssiWidth}} "
        )
        print('-' * (2 + self._choiceWidth)
            + '+' + '-' * (2 + self._nameWidth)
            + '+' + '-' * (2 + self._macAddrWidth)
            + '+' + '-' * (2 + self._rssiWidth)
        )
        print() 

    def _displayDevice(self, device):
        """Display device the info as a table row."""
        devName = device.getValueText(9)
        if devName == None:
            devName = "<No Name>"

        print(
            f" {self.devCount:^{self._choiceWidth}} |"
            f" {devName[:self._nameWidth]:<{self._nameWidth}} |"
            f" {device.addr:^{self._macAddrWidth}} |"
            f" {f'{device.rssi} dB':^{self._rssiWidth}} "
        )

    def _displayPrompt(self):
        print(self._errMsg, end='')
        print("Choose a device to update: ", end='', flush=True)

    def _getUserInput(self):
        self.userInput.put(input())

    def _moveCursorLeft(self, count=1):
        print(f"\x1B[{count}D", end='')

    def _moveCursorUp(self, count=1):
        print(f"\x1B[{count}A", end='')

    def _clearCursorToEnd(self):
        print("\x1B[K", end='')


if __name__ == '__main__':
    # Create a scanner object that sends BLE broadcast packets to the ScanDelegate
    scanner = btle.Scanner()

    # Create an object to manage the scanner user interface
    scannerUI = ScannerUI()

    # Start the scanner
    scanner.start()
    print("Scanning for devices...")
    print()

    # Continuously scan for devices while waiting for the user to choose one
    while scannerUI.userSelection == None:
        scannerUI.update(list(scanner.getDevices())[scannerUI.devCount:])
        scanner.process(1)

    # Stop the scanner
    try:
        scanner.stop()
    except:
        print("Error stopping scanner.")

    # Retrieve the selected device
    device = list(scanner.getDevices())[scannerUI.userSelection-1]

    # Connect to the user selected device
    try:
        target = btle.Peripheral(device.addr).withDelegate(Delegate())
    except btle.BTLEException:
        print(f"Could not connect to device \"{device.addr}\"")
        print("Exiting...")
        raise SystemExit
    except:
        print("Something went wrong.")
        print("Exiting...")
    print(f"Connected to device \"{target.addr}\"\n")

    crc32cFunc = crcmod.predefined.mkCrcFun('crc-32c')

    hostCmd = host.Host(target)

    fwImg = cyacd2.Application("mtb-example-psoc6-capsense-buttons-slider_crc.cyacd2")

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

    # TODO Make this better...
    try:
        target.disconnect()
    except:
        pass
    finally:
        print( "Disconnected from DFU Device." )
