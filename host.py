import struct

class Host:

    # TODO Use dictionaries? e.g. {0x00: "Success"}
    _START_OF_PACKET                 = b'\x01'
    _END_OF_PACKET                   = b'\x17'

    _CMD_ENTER_DFU                   = b'\x38'
    _CMD_SYNC_DFU                    = b'\x35'
    _CMD_EXIT_DFU                    = b'\x3B'

    _CMD_SEND_DATA                   = b'\x37'
    _CMD_SEND_DATA_WITHOUT_RESPONSE  = b'\x47'
    _CMD_PROGRAM_DATA                = b'\x49'
    _CMD_VERIFY_DATA                 = b'\x4A'
    _CMD_ERASE_DATA                  = b'\x44'

    _CMD_VERIFY_APPLICATION          = b'\x31'
    _CMD_SET_APPLICATION_METADATA    = b'\x4C'
    _CMD_GET_METADATA                = b'\x3C'
    _CMD_SET_EIVECTOR                = b'\x4D'

    _CODE_DFU_SUCCESS                = b'\x00'
    _CODE_DFU_ERROR_VERIFY           = b'\x02'
    _CODE_DFU_ERROR_LENGTH           = b'\x03'
    _CODE_DFU_ERROR_DATA             = b'\x04'
    _CODE_DFU_ERROR_CMD              = b'\x05'
    _CODE_DFU_ERROR_CHECKSUM         = b'\x08'
    _CODE_DFU_ERROR_ROW              = b'\x0A'
    _CODE_DFU_ERROR_ROW_ACCESS       = b'\x0B'
    _CODE_DFU_ERROR_UNKNOWN          = b'\x0F'

    _CYPRESS_BOOTLOADER_SERVICE_UUID = "00060000-F8CE-11E4-ABF4-0002A5D5C51B"


    def __init__(self, dfuTarget):
        # TODO Check input parameters

        # TODO Enusre a connection has been established with the target

        # TODO Error checking
        # Get the bootloader service object
        dfuService = dfuTarget.getServiceByUUID(self._CYPRESS_BOOTLOADER_SERVICE_UUID)

        # Get the bootloader command characteristic (should be the only one...)
        self._dfuCmdChar = dfuService.getCharacteristics()[0]

        # Get the Client Characteristic Configuration Descriptor (CCCD)
        self._dfuCCCD = self._dfuCmdChar.getDescriptors(forUUID=0x2902)[0]
        
        # Enable notifications from the Bootloader service
        self._enableNotifications(self._dfuCCCD)


    def enterDFU(self, productID = 0):
        # Check input parameters
        if not isinstance(productID, int):
            print("productID must be an int object")
            raise SystemExit

        # Create the packet payload
        payload = struct.pack("<I", productID)
        
        # Send the Enter DFU command and get the response
        statusCode, respData = self._sendCommandGetResponse(self._CMD_ENTER_DFU, payload, 2)

        # Check status code
        if statusCode != self._CODE_DFU_SUCCESS:
            print(f"ERROR: Enter DFU: Status code {statusCode} returned.")  
            raise SystemExit

        # Parse reponse packet payload and print data fields
        jtagID, deviceRev, dfuSdkVer = struct.unpack("<IBI", respData[:5] + b'\x00' + respData[5:])
        print("Enter DFU successful.")
        print(f"> JTAG ID: 0x{jtagID:08x}")
        print(f"> Device Revision 0x{deviceRev:02x}")
        print(f"> DFU SDK Version 0x{dfuSdkVer:08x}")

        return statusCode
    
    def syncDFU(self):
        # Create the Sync DFU command packet
        packet = self._createCmdPacket(self._CMD_SYNC_DFU)
        return self._sendPacket(packet)


    def exitDFU(self):
        # Send the Exit DFU command (no response)
        # Create the Exit DFU command packet
        packet = self._createCmdPacket(self._CMD_EXIT_DFU)

        # Send the packet to the target
        self._sendPacket(packet)
        
        # No need to wait for and get response
        return 


    def sendData(self, data):
        # Check input parameters
        if not isinstance(data, bytes):
            print("data must be a bytes object")
            raise SystemExit

        # Send the Send Command command and get the response from the target
        statusCode, respData = self._sendCommandGetResponse(self._CMD_SEND_DATA, data, 2)

        # Check status code
        if statusCode != self._CODE_DFU_SUCCESS:
            print(f"ERROR: Send Data: Status code {statusCode} returned.")  
            raise SystemExit
        print("Send Data successful.")

        return statusCode


    def sendDataWithoutResponse(self, data):
        # Check input parameters
        if not isinstance(data, bytes):
            print("data must be a bytes object")
            raise SystemExit

        # Create the Send Data Without Response command packet
        packet = self._createCmdPacket(self._CMD_SEND_DATA_WITHOUT_RESPONSE, data)
        return self._sendPacket(packet)


    def programData(self, rowAddr, rowDataChecksum, data):
        # Check input parameters
        if not isinstance(rowAddr, int):
            print("rowAddr must be an int object")
            raise SystemExit
        if not isinstance(rowDataChecksum, int):
            print("rowDataChecksum must be an int object")
            raise SystemExit
        if not isinstance(data, bytes):
            print("data must be a bytes object")
            raise SystemExit

        # Create the packet payload
        payload = struct.pack("<II", rowAddr, rowDataChecksum) + data

        # Send the Program Data command and get the response from the target
        statusCode, respData = self._sendCommandGetResponse(self._CMD_PROGRAM_DATA, payload, 2)

        # Check status code
        if statusCode != self._CODE_DFU_SUCCESS:
            print(f"ERROR: Program Data: Status code {statusCode} returned.")  
            raise SystemExit
        print("Program Data successful.")

        return statusCode
        

    def verifyData(self, rowAddr, rowDataChecksum, data):
        # Check input parameters
        if not isinstance(rowAddr, int):
            print("rowAddr must be an int object")
            raise SystemExit
        if not isinstance(rowDataChecksum, int):
            print("rowDataChecksum must be an int object")
            raise SystemExit
        if not isinstance(data, bytes):
            print("data must be a bytes object")
            raise SystemExit

        # Create the packet payload
        payload = struct.pack("<II", rowAddr, rowDataChecksum) + data
        
        # Create the Verify Data command packet
        packet = self._createCmdPacket(self._CMD_VERIFY_DATA, payload)
        return self._sendPacket(packet)
        

    def eraseData(self, rowAddr):
        # Check input parameter
        if not isinstance(rowAddr, int):
            print("rowAddr must be an int object")
            raise SystemExit

        # Create the Erase Data command packet
        packet = self._createCmdPacket(self._CMD_ERASE_DATA, struct.pack("<I", rowAddr))
        return self._sendPacket(packet)
        
    def verifyApplication(self, appNum):
        # Check input parameter
        if not isinstance(appNum, int):
            print("appNum must be an int object")
            raise SystemExit
        
        # Create the packet payload
        payload = struct.pack("<B", appNum)
        
        # Send the Verify Application command and get the response from the target
        statusCode, respData = self._sendCommandGetResponse(self._CMD_VERIFY_APPLICATION, payload, 2)

        # Check status code
        if statusCode != self._CODE_DFU_SUCCESS:
            print(f"ERROR: Verify Application: Status code {statusCode} returned.")  
            raise SystemExit
        print("Verify Application successful.")

        # Parse the response packet payload and print the result of the query
        appValid = struct.unpack("<B", respData)[0]
        print(f"> Result: {appValid}")
        
        return statusCode


    def setApplicationMetadata(self, appNum, appStartAddr, appLength):
        # Check input parameters
        if not isinstance(appNum, int):
            print("appNum must be an int object")
            raise SystemExit
        if not isinstance(appStartAddr, int):
            print("appStartAddr must be an int object")
            raise SystemExit
        # Check input parameter
        if not isinstance(appLength, int):
            print("appLength must be an int object")
            raise SystemExit
        
        # Create the packet payload
        payload = struct.pack("<BII", appNum, appStartAddr, appLength)

        # Send the Set Application Metadata command and get the response from the target
        statusCode, respData = self._sendCommandGetResponse(self._CMD_SET_APPLICATION_METADATA, payload, 2)

        # Check status code
        if statusCode != self._CODE_DFU_SUCCESS:
            printf(f"ERROR: Set Application Metadata: Status code {statusCode} returned.")
            raise SystemExit
        print("Set Application Metadata successful.")
            
        return statusCode

    
    def getMetadata(self, fromRowOffset, toRowOffset):
        # Check input parameters
        if not isinstance(fromRowOffset, int):
            print("fromRowOffset must be an int object")
            raise SystemExit
        if not isinstance(toRowOffset, int):
            print("toRowOffset must be an int object")
            raise SystemExit

        if (fromRowOffset < 0) or (fromRowOffset > 511) or (toRowOffset < 0) or (toRowOffset > 511):
            print("Invalid arguments for getMetadata()")
            raise SystemExit

        # Create the packet payload
        payload = struct.pack("<II", fromRowOffset, toRowOffset)

        # Create the Get Metadata command packet
        packet = self._createCmdPacket(self._CMD_GET_METADATA, payload)
        return self._sendPacket(packet)


    def setEIVector(self, vector):
        "Currently not implemented"
        pass


    def _getResponse(self, packet):
        # TODO Check input parameters
        # Attempt to unpack the response packet according to Figure 33 of AN213924
        try:
            startByte, statusCode, dataLength = struct.unpack("<ccH", packet[0:4])
            payload, checksum, endByte = struct.unpack(f"<{dataLength}sHc", packet[4:])
        except:
            print("The response packet is malformed")
            raise SystemExit

        if (startByte != self._START_OF_PACKET) or (endByte != self._END_OF_PACKET):
            print("The response packet is malformed")
            raise SystemExit

        # Verify packet checksum
        if self._calcChecksum_2sComplement_16bit(packet[:-3]) != checksum:
            print("The response packet is currupted")
            raise SystemExit

        return [statusCode, payload]


    def _createCmdPacket(self, cmd, payload=b''):
        # Check input parameters
        if (not isinstance(cmd, bytes)) or (len(cmd) != 1):
            print("cmd must be a bytes object with a length of 1")
            raise SystemExit

        if not isinstance(payload, bytes):
            print("payload must be a bytes object")
            raise SystemExit

        # Create command packet according to Figure 32 of AN213924
        payloadLength = len(payload)
        packet = struct.pack(f"<ccH{payloadLength}s", self._START_OF_PACKET, cmd, payloadLength, payload)
        return packet + struct.pack("<Hc", self._calcChecksum_2sComplement_16bit(packet), self._END_OF_PACKET)


    def _calcChecksum_2sComplement_16bit(self, data):
        # Check input parameter
        if not isinstance(data, bytes):
            print("data must be a bytes object")
            raise SystemExit

        # Calculate the 16-bit 2's complement checksum
        cs = 0
        for b in data:
            cs = cs + b
        
        return (-cs & 0xFFFF)


    def _sendPacket(self, packet, maxLen=20):
        # Check input parameter
        if not isinstance(packet, bytes):
            print("packet must be a bytes object")
            raise SystemExit
        
        # Send the packet in maxLen increments
        packet = [packet[i:i+maxLen] for i in range(0, len(packet), maxLen)]
        for p in packet:
            self._dfuCmdChar.write(p)


    def _waitForResponse(self, timeout=1):
        "timeout is in seconds"
        
        # Block until either a notification is received from the target or the timeout elapses
        if not self._dfuCmdChar.peripheral.waitForNotifications(timeout):
            return False

        # If received notification is not from the DFU characteristic
        while self._dfuCmdChar.peripheral.delegate.handle != self._dfuCmdChar.getHandle():
            return False

        # TODO handle receiving notifications from multiple characteristics
        return True

    def _sendCommandGetResponse(self, cmd, payload=b'', timeout=1):
        # Create the command packet 
        packet = self._createCmdPacket(cmd, payload)
        for b in struct.unpack(f"{len(packet)}B", packet):
            print(f"{b:02X}:", end='')
        print()

        # Send packet to target
        self._sendPacket(packet)

        # Wait for response from the target
        if not self._waitForResponse(timeout):
            print(f"Notification from handle {self._dfuCmdChar.getHandle()} not received")
            raise SystemExit
        
        # Extract the status code and payload of the target's response packet
        return self._getResponse(self._dfuCmdChar.peripheral.delegate.data)


    def _enableNotifications(self, cccd):
        # Set the enable notifications bit in the CCCD's value
        # Must send write request *with* response
        cccd.write(b'\x01\x00', withResponse=True)

        # Check the value of the CCCD to ensure notifications are enabled
        cccdValue = cccd.read()
        if cccdValue != b'\x01\x00':
            print("Failed to enable notifications from the Bootloader service.")
            raise SystemExit


if __name__ == "__main__":
    h = Host()
    resp = b'\x01\x00\x08\x00\x00\x00\x00\x00\x00\x00\x04\x01\xf2\xff\x17'

