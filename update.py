#!env/bin/python

from bluepy import btle
import cydfu
import crcmod
import sys
import time
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

    # TODO: Make scaleable. Add options for abort, refresh, etc. 
    @property
    def userSelection(self):
        """Get and cache the user's selection."""
        if self._userSelection == None: # If the user has not yet made a valid selection
            if not self.userInput.empty(): # If the user has provided some input
                selection = self.userInput.get() # Remove from queue
                
                # Validate the user's input
                try:
                    selection = int(selection)
                except Exception:
                    self._errMsg = f"Choice \"{selection}\" not valid. "
                else:
                    if (selection < 1) or (selection > self.devCount):
                        self._errMsg = f"Device {selection} is not on the list. "
                        
                        # Re-print the prompt (now with appropriate error message)
                        self._moveCursorUp()
                        self._moveCursorLeft(999)
                        self._clearCursorToEnd()
                        self._displayPrompt()

                        # Re-start the getUserInput thread
                        threading.Thread(target=self._getUserInput).start()
                    else:
                        self._userSelection = selection

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


class Target(btle.Peripheral):

    def updateFirmware(self, app):
        crc32cFunc = crcmod.predefined.mkCrcFun('crc-32c')
        dfuCmd = cydfu.CyDFUProtocol(self)

        dfuCmd.enterDFU(app.productID)
        # TODO change appID to id, appStartAddr to startAddr, etc.
        dfuCmd.setApplicationMetadata(app.appID, app.appStartAddr, app.appLength)

        while True:
            try:
                rowAddr, rowData = app.getNextRow()
            except Exception:
                break

            # Calculate the CRC-32C checksum of the row data
            crc = crc32cFunc(rowData)

            # Break the row data into smaller chunks of size payloadLength
            # TODO don't hardcode this
            payloadLength = 256
            rowData = [rowData[i:i+payloadLength] for i in range(0, len(rowData), payloadLength)]

            # Send all but the last chunk using the Send Data command
            for chunk in rowData[:-1]:
                dfuCmd.sendData(chunk)

            # Send the last chunk using the Program Data command
            dfuCmd.programData(rowAddr, crc, rowData[-1])

        # Send Verify Application command
        dfuCmd.verifyApplication(fwImg.appID)

        # Send the Exit DFU command
        dfuCmd.exitDFU()


    def eraseFirmware(self, appNum):
        # TODO Implement
        pass


if __name__ == '__main__':
    usageStatement = "Usage: update.py <applicaion file> [target MAC address]"
    
    # Check the command line arguments
    if (len(sys.argv[1:]) == 0) or (len(sys.argv[1:]) > 2):
        print(usageStatement)
        raise SystemExit

    # If 1 or 2 command line arguments were provided, process the first one
    try:
        fwImg = cydfu.Application(sys.argv[1])    
    except FileNotFoundError:
        print(f"{sys.argv[1]} does not exist.")
        raise SystemExit
    except cydfu.InvalidFileType:
        print(usageStatement + '\n')
        raise
    except cydfu.InvaildApplicationFile:
        raise
    except Exception:
        print(usageStatement + '\n')
        raise 
    
    print()
    
    # If the optional second cmd line argument was provided, try to connect
    target = None
    if len(sys.argv[1:]) == 2:
        try:
            target = Target(sys.argv[2]).withDelegate(Delegate())
        except ValueError:
            print(usageStatement + '\n')
            raise
        except Exception as e:
            print(e.args[0])

    if (target == None):
        # Create scanner and scanner user interface objects
        scanner = btle.Scanner()
        scannerUI = ScannerUI()

        while (target == None):
            # Forget preveously discovered devices
            scanner.clear()
            scannerUI.reset()

            # Start the scanner
            scanner.start()
            print("Scanning for devices...\n")
            # TODO scannerUI.printHeader() 

            # Continuously scan for devices while waiting for the user to choose one
            while scannerUI.userSelection == None:
                scannerUI.update(list(scanner.getDevices())[scannerUI.devCount:])
                scanner.process(1)

            # Stop the scanner
            try:
                scanner.stop()
            except Exception:
                print("Error stopping scanner.")

            # Retrieve the selected device
            device = list(scanner.getDevices())[scannerUI.userSelection-1]

            # Try to connect to the device
            try:
                target = Target(device).withDelegate(Delegate())
            except Exception:
                print(f"Could not connect to device {device.addr}.")


    target.updateFirmware(fwImg)
    fwImg.close()

    # TODO Make this better...
    try:
        target.disconnect()
    except Exception:
        pass
    finally:
        print( "Disconnected from DFU Device." )
