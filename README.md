# dualserialport

Usage: 
dsp [options] [port [baudrate]]
Usage: 
dsp --porta COM7 --portc COM8 --portb COM9 --timenoresp 3

--- COM7>COM8<COM9 4800,7,E,1 ---

Simple Serial to Network (TCP/IP) redirector.

Options:
  -h, --help            show this help message and exit
  -q, --quiet           suppress non error messages
  --spy                 peek at the communication and print all data to the
                        console

  Serial Port:
    Serial port settings

    -p PORT, --porta=PORT
                        port A(shared), a number (default 0) or a device name
    --portb=PORTB       port B, a number (default 1) or a device name
    --portc=PORTC       port C, a number (default 2) or a device name
    -b BAUDRATE, --baud=BAUDRATE
                        set baud rate, default: 4800
    -s BYTESIZE, --bytesize=BYTESIZE
                        set bytesize, default: 7
    --parity=PARITY     set parity, one of [N, E, O], default=E
    --rtscts            enable RTS/CTS flow control (default off)
    --xonxoff           enable software flow control (default off)
    --rts=RTS_STATE     set initial RTS line state (possible values: 0, 1)
    --dtr=DTR_STATE     set initial DTR line state (possible values: 0, 1)
    --keyup=KEY_UP      set delay time  for PTT (prev RTS)(possible values: 0
                        a 300ms), default=300
    --keydown=KEY_DOWN  set delay time for soft carrier dekey (pos
                        RTS)(possible values: 0 to 200ms), default=30 ms.
    --timenoresp=TIME_NO_RESPONSE
                        Time wait for response in sec,default=5
    --serreadout=SERIAL_READ_TIMOUT
                        Time wait for read serial port in sec,default=0.5

  Network settings:
    Network configuration.

    -P LOCAL_PORT, --localport=LOCAL_PORT
                        local TCP port

  Newline Settings:
    Convert newlines between network and serial port. Conversion is
    normally disabled and can be enabled by --convert.

    -c, --convert       enable newline conversion (default off)
    --net-nl=NET_NEWLINE
                        type of newlines that are expected on the network
                        (default: LF)
    --ser-nl=SER_NEWLINE
                        type of newlines that are expected on the serial port
                        (default: CR+LF)

NOTE: no security measures are implemented. Anyone can remotely connect to
this service over the network.  Only one connection at once is supported. When
the connection is terminated it waits for the next connect.



