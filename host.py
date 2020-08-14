import struct

class Host:

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


    def __init__(self):
        pass


    def enterDFU(self, productID = b'\x00\x00\x00\x00'):
        # Check input parameters
        if (not isinstance(productID, bytes)) or (len(productID) != 4):
            print("productID must be a bytes object with a length of 4")
            raise SystemExit

        # Create the Enter DFU command packet 
        packet = self.createCmdPacket(self._CMD_ENTER_DFU, productID)
        return self.sendPacket(packet)


    def syncDFU(self):
        # Create the Sync DFU command packet
        packet = self.createCmdPacket(self._CMD_SYNC_DFU)
        return self.sendPacket(packet)


    def exitDFU(self):
        # Create the Exit DFU command packet
        packet = self.createCmdPacket(self._CMD_EXIT_DFU)
        return self.sendPacket(packet)


    def sendData(self, data):
        # Check input parameters
        if not isinstance(data, bytes):
            print("data must be a bytes object")
            raise SystemExit

        # Create the Send Data command packet
        packet = self.createCmdPacket(self._CMD_SEND_DATA, data)
        return self.sendPacket(packet)


    def sendDataWithoutResponse(self, data):
        # Check input parameters
        if not isinstance(data, bytes):
            print("data must be a bytes object")
            raise SystemExit

        # Create the Send Data Without Response command packet
        packet = self.createCmdPacket(self._CMD_SEND_DATA_WITHOUT_RESPONSE, data)
        return self.sendPacket(packet)


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

        # Create the Program Data command packet
        packet = self.createCmdPacket(self._CMD_PROGRAM_DATA, payload)
        return self.sendPacket(packet)
        

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
        packet = self.createCmdPacket(self._CMD_VERIFY_DATA, payload)
        return self.sendPacket(packet)
        

    def eraseData(self, rowAddr):
        # Check input parameter
        if not isinstance(rowAddr, int):
            print("rowAddr must be an int object")
            raise SystemExit

        # Create the Erase Data command packet
        packet = self.createCmdPacket(self._CMD_ERASE_DATA, struct.pack("<I", rowAddr))
        return self.sendPacket(packet)
        
    def verifyApplication(self, appNum):
        # Check input parameter
        if not isinstance(appNum, int):
            print("appNum must be an int object")
            raise SystemExit
        
        # Create the Verify Application command packet
        packet = self.createCmdPacket(self._CMD_VERIFY_APPLICATION, struct.pack("<B", appNum))
        return self.sendPacket(packet)


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
        payload = struct.pack("<BHH", appNum, appStartAddr, appLength)

        # Create the Set Application Metadata command packet
        packet = self.createCmdPacket(self._CMD_SET_APPLICATION_METADATA, payload)
        return self.sendPacket(packet)

    
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
        payload = struct.pack("<HH", fromRowOffset, toRowOffset)

        # Create the Get Metadata command packet
        packet = self.createCmdPacket(self._CMD_GET_METADATA, payload)
        return self.sendPacket(packet)


    def setEIVector(self, vector):
        "Currently not implemented"
        pass


    def getResponse(self, packet):
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
        if self.calcChecksum_2sComplement_16bit(packet[:-3]) != checksum:
            print("The response packet is currupted")
            raise SystemExit

        return [statusCode, payload]


    def createCmdPacket(self, cmd, payload = b''):
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
        return packet + struct.pack("<Hc", self.calcChecksum_2sComplement_16bit(packet), self._END_OF_PACKET)


    def calcChecksum_2sComplement_16bit(self, data):
        # Check input parameter
        if not isinstance(data, bytes):
            print("data must be a bytes object")
            raise SystemExit

        # Calculate the 16-bit 2's complement checksum
        cs = 0
        for b in data:
            cs = cs + b
        
        return (-cs & 0xFFFF)


    def sendPacket(self, packet):
        # Check input parameter
        if not isinstance(packet, bytes):
            print("packet must be a bytes object")
            raise SystemExit
        
        return packet


if __name__ == "__main__":
    h = Host()
    resp = b'\x01\x00\x08\x00\x00\x00\x00\x00\x00\x00\x04\x01\xf2\xff\x17'

