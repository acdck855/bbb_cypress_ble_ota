import struct

class Application:
    "Opens and parses the cyacd2 file containing the downloadable application data"

    def __init__(self, cyacd2_file):
        """Opens the cyacd2 file provided. Retrieves file info from header and 
           application data from the APPDATA row"""
        # Ensure the file name has the ".cyacd2" extension
        if not cyacd2_file.endswith(".cyacd2"):
            print("Invalid file type")
            raise SystemExit

        # Open the cyacd2 file
        self._app = open(cyacd2_file, 'r')

        # Read and print the header info
        self.getHeader()
        print(f"File Version: 0x{self.fileVersion:02x}")
        print(f"Silicon ID: 0x{self.siliconID:08x}")
        print(f"Silicon Revision: 0x{self.siliconRevision:02x}")
        print(f"Checksum Type: {self.checksumType}")
        print(f"App ID: 0x{self.appID:02x}")
        print(f"Product ID: 0x{self.productID:08x}")

        # Read and print application verification information
        self.getAppInfo()
        print(f"Application Start Address: 0x{self.appStartAddr:08x}")
        print(f"Application Length: 0x{self.appLength:08x}")

        # TODO Handle files with an EIV (Encryption Initial Vector) row


    def getHeader(self):
        # Read the header 
        header = next(self._app).strip()
        header = bytes.fromhex(header)

        # Verify header length
        if len(header) != 12:
            printf("Invalid cyacd2 file: Header")
            raise SystemExit

        # Extract fields from header
        header = struct.unpack("<BIBBBI", header)
        self.fileVersion = header[0]
        self.siliconID = header[1]
        self.siliconRevision = header[2]
        self.checksumType = header[3]
        self.appID = header[4]
        self.productID = header[5]


    def getAppInfo(self):
        # Read the application verification information
        appinfo = next(self._app).strip()

        # Separate label from metadata
        appinfo = appinfo.split(':')

        # Verify that the label is valid
        if appinfo[0] != "@APPINFO":
            print("Invalid cyacd2 file: APPINFO")
            raise SystemExit

        # Extract fields from metadata
        self.appStartAddr, self.appLength = appinfo[1].split(',') # they are big endian
        self.appStartAddr = int(self.appStartAddr, 0)
        self.appLength = int(self.appLength, 0)


    def getNextRow(self):
        # Read row
        row = next(self._app)

        # Verify row header
        if row[0] != ':':
            print("Invalid cyacd2 file: Data")
            raise SystemExit

        # Extract row data
        _, row = row.split(':', 1)
        row = row.strip()
        row = bytes.fromhex(row)
        dataLength = len(row) - 4 # 4-byte address + N bytes of data
        rowAddr, rowData = struct.unpack(f"<I{dataLength}s", row)
        return [rowAddr, rowData]


    def close(self):
        self._app.close()

if __name__ == "__main__":
    a = Application("mtb-example-psoc6-capsense-buttons-slider_crc.cyacd2")
