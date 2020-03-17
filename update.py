#!env/bin/python

from bluepy import btle
import crcmod
import time

class Delegate( btle.DefaultDelegate ):
    def __init__( self ):
        btle.DefaultDelegate.__init__( self )
        self.handle = 0
        self.data = 0

    def handleNotification( self, cHandle, data ):
        print( "cHandle: {}\tdata: {}".format( cHandle, data ) )
        self.handle = cHandle
        self.data = data


def enter_dfu( product_id ):
    packet = "01380600" + product_id + "0000"

    cs = 0
    for b in bytes.fromhex( packet ):
        cs = cs + b

    cs_str = "{:04X}".format( int.from_bytes( ( -cs & 0xFFFF ).to_bytes( 2, 'big' ), 'little' ) )
    packet = packet + cs_str + "17"
    return packet


def set_application_metadata( app_num, start_addr, app_len ):
    app_num_str = "{:02X}".format( app_num )
    start_addr_str = "{:08X}".format( int.from_bytes( start_addr.to_bytes( 4, 'big' ), 'little' ) )
    app_len_str = "{:08X}".format( int.from_bytes( app_len.to_bytes( 4, 'big' ), 'little' ) )
    packet = "014C0900" + app_num_str + start_addr_str + app_len_str

    cs = 0
    for b in bytes.fromhex( packet ):
        cs = cs + b

    cs_str = "{:04X}".format( int.from_bytes( ( -cs & 0xFFFF ).to_bytes( 2, 'big' ), 'little' ) )
    packet = packet + cs_str + "17"
    return packet


def send_program_data( row ):
    row_addr = row[0:8]
    row_data = row[8:]

    # calculate the CRC-32C checksum of the row data
    crc = crc32c_func( bytes.fromhex( row_data ) )

    # break the row data into smaller chunks (payload size)
    sd_len = 270 #137
    payload_size = sd_len * 2
    row_data = [ row_data[i:i+payload_size] for i in range( 0, len( row_data ), payload_size ) ]

    # create the Send Data packets
    packet = []
    for rd in row_data[:-1]:
        packet.append( "0137" )
        packet[-1] += "{:04X}".format( int.from_bytes( sd_len.to_bytes( 2, 'big' ), 'little' ) )
        packet[-1] += rd

        cs = 0
        for b in bytes.fromhex( packet[-1] ):
            cs += b

        packet[-1] += "{:04X}".format( int.from_bytes( ( -cs & 0xFFFF ).to_bytes( 2, 'big' ), 'little' ) )
        packet[-1] += "17"

    # get length of Program Data packat payload
    pd_len = int( len( row_data[-1] ) / 2 + 8 ) # 4-byte address + 4-byte checksum

    # create the Program Data packet
    packet.append( "0149" )
    packet[-1] += "{:04X}".format( int.from_bytes( pd_len.to_bytes( 2, 'big' ), 'little' ) )
    packet[-1] += row_addr # already in the proper format
    packet[-1] += "{:08X}".format( int.from_bytes( crc.to_bytes( 4, 'big' ), 'little' ) )
    packet[-1] += row_data[-1]
    
    cs = 0
    for b in bytes.fromhex( packet[-1] ):
        cs += b
                
    packet[-1] += "{:04X}".format( int.from_bytes( ( -cs & 0xFFFF ).to_bytes( 2, 'big' ), 'little' ) )
    packet[-1] += "17"
    return packet


def verify_application( app_num ):
    app_num_str = "{:02X}".format( app_num )
    packet = "01310100" + app_num_str

    cs = 0
    for b in bytes.fromhex( packet ):
        cs += b

    cs_str = "{:04X}".format( int.from_bytes( ( -cs & 0xFFFF ).to_bytes( 2, 'big' ), 'little' ) )
    packet += cs_str + "17"
    return packet
    

def end_dfu():
    packet = "013B0000C4FF17"
    return packet


def check_response( handle, packet ):
    if delegate.handle != handle:
        print( "Expected Response from handle 0x{:02X}.".format( handle ) )
        raise SystemExit

    # Verify packet checksum
    cs = 0
    print( packet )
    for b in packet[:-3]:
        cs += b
    cs = ( -cs & 0xFFFF ) # 2's compliment
    if cs != int.from_bytes( packet[-3:-1], 'little' ):
        print( "The response from handle 0x{:02X} has been currupted.".format( handle ) )
        raise SystemExit
    
    ## Parse response packet
    # check start of packet (1-byte) and end of packet (1-byte)
    if ( packet[0] != 0x01 ) or ( packet[-1] != 0x17 ):
        print( "The response from handle 0x{:02X} is malformed.".format( handle ) )
        raise SystemExit

    # check status code (1-byte)
    status = packet[1]
    if status != 0:
        print( "The target responded with error code 0x{:02X}.".format( status ) )
        raise SystemExit

    # Get data length (2-bytes) and extract data (N-bytes)
    data_len = int.from_bytes( packet[2:4], 'little' )
    data = packet[4:4+data_len]

    return data


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
with open( "mtb-example-psoc6-capsense-buttons-slider_crc.cyacd2", 'r' ) as fw_img:
    # Get the header and extract info
    header = next( fw_img ).strip()
    file_version = int( header[0:2], 16 )
    silicon_id = header[2:10]
    silicon_rev = int( header[10:12], 16 )
    checksum_type = int( header[12:14], 16 )
    app_id = int( header[14:16], 16 )
    product_id = header[16:24]

    # Create Enter DFU packet and send it
    packet = enter_dfu( product_id )
    target.writeCharacteristic( 0x0B, bytes.fromhex( packet ) )

    # check response
    if not target.waitForNotifications( 2 ):
        print( "No response from target!" )
        raise SystemExit
    check_response( delegate.handle, delegate.data )
    
    # Get @APPINFO data and extract info
    appinfo = next( fw_img ).strip().split( ':' )
    if appinfo[0] != "@APPINFO":
        print( "Expected \"@APPINFO:\" (Application verification information). Invalid firmware image file!" )
        raise SystemExit
    start_addr, app_len = appinfo[1].split( ',' )
    start_addr = int( start_addr, 0 )
    app_len = int( app_len, 0 )    

    # Create Set Application Metadata packet and send it
    packet = set_application_metadata( app_id, start_addr, app_len )
    target.writeCharacteristic( 0x0B, bytes.fromhex( packet ) )

    # check response
    if not target.waitForNotifications( 2 ):
        print( "No response from target!" )
        raise SystemExit
    check_response( delegate.handle, delegate.data )
    
    # Iterate through the remaining rows of program data and send them to the target
    for row in fw_img:
        # Ensure 'row' contains a data row
        if row[0] != ':':
            print( "Expecting program data. Invalid firware image file!" )
            raise SystemExit

        # Extract row data
        _, row = row.split( ':', 1 )
        row = row.strip()

        # get Program Data packet
        packets = send_program_data( row )

        # break each packet into smaller packets and send them
        packet_size = 20 * 2 # 20-bytes
        for packet in packets:
            packet = [ packet[i:i+packet_size] for i in range( 0, len( packet ), packet_size ) ]

            for p in packet:
                print( p, target.writeCharacteristic( 0x0B, bytes.fromhex( p ) ) )

            # check response
            if not target.waitForNotifications( 2 ):
                print( "No response from target!" )
                raise SystemExit
            check_response( delegate.handle, delegate.data )

# Send Verify Application command
packet = verify_application( app_id )
target.writeCharacteristic( 0x0B, bytes.fromhex( packet ) )

# check response
if not target.waitForNotifications( 2 ):
    print( "No response from target!" )
    raise SystemExit
check_response( delegate.handle, delegate.data )

# Send the Exit DFU command
packet = end_dfu()
target.writeCharacteristic( 0x0B, bytes.fromhex( packet ) )

try:
    target.disconnect()
except:
    pass
finally:
    print( "Disconnected from DFU Device." )
