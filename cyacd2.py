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
        print("File Version:", self.fileVersion)
        print("Silicon ID", self.siliconID)
        print("Silicon Revision", self.siliconRevision)
        print("Checksum Type", self.checksumType)
        print("App ID", self.appID)
        print("Product ID", self.productID)

        # Read and print application verification information
        self.getAppInfo()
        print("Application Start Address:", self.appStartAddr)
        print("Application Length:", self.appLength)

        # TODO Handle files with an EIV (Encryption Initial Vector) row


    def getHeader(self):
        # Read the header 
        header = next(self._app).strip()

        # Verify header length
        if len(header) != 24:
            printf("Invalid cyacd2 file: Header")
            raise SystemExit

        # Extract fields from header
        self.fileVersion = int(header[0:2], 16)
        self.siliconID = header[2:10] # little endian
        self.siliconRevision = int(header[10:12], 16)
        self.checksumType = int(header[12:14], 16)
        self.appID = int(header[14:16], 16)
        self.productID = header[16:24] # little endian


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
