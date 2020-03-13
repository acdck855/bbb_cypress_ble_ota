#!env/bin/python

from bluepy import btle
import crcmod

class Delegate( btle.DefaultDelegate ):
    def __init__( self ):
        btle.DefaultDelegate.__init__( self )
        self.handle = 0
        self.data = 0

    def handleNotification( self, cHandle, data ):
        print( "cHandle: {}\tdata: {}".format( cHandle, data ) )
        self.handle = cHandle
        self.data = data


node_mac = "00:a0:50:f4:64:be"
dfu_uuid = "00060000-F8CE-11E4-ABF4-0002A5D5C51B"
delegate = Delegate()

crc32c_func = crcmod.predefined.mkCrcFun( 'crc-32c' )

dev = btle.Peripheral( node_mac )
dev.setDelegate( delegate )

dfu_service = dev.getServiceByUUID( dfu_uuid )

print( dev.readCharacteristic( 0x0C ) )

print( dev.writeCharacteristic( 0x0C, bytes.fromhex( "0100" ), withResponse=True ) )
print( dev.readCharacteristic( 0x0C ) )

print( dev.writeCharacteristic( 0x0B, bytes.fromhex( "01380600040302010000B7FF17" ) ) )
if not dev.waitForNotifications( 2 ):
    print( "No response from device!" )
    raise SystemExit

# Set Application Metadata: app# (1-byte) : start_addr (4-bytes) : app_len(4-bytes)
print( dev.writeCharacteristic( 0x0B, bytes.fromhex( "014C09000100000510FCFF000099FD17" ) ) )
if not dev.waitForNotifications( 2 ):
    print( "No response from device!" )
    raise SystemExit

prog = open( "mtb-example-psoc6-capsense-buttons-slider_crc.cyacd2", 'r' )

header = next( prog ).strip()

appinfo = next( prog ).strip().split( ':' )
if appinfo[0] != "@APPINFO":
    print( "Expected \"@APPINFO:\". Invalid program file!" )
    raise SystemExit

pos = prog.tell()
if next( prog ).split( ':' )[0] != '':
    print( "Expected row data. Invalid program file!" )
    raise SystemExit
prog.seek(pos)

for row in prog:


