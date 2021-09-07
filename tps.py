#!/usr/bin/env python

# (C) 2002-2009 Chris Liechti <cliechti@gmx.net>
# redirect data from a TCP/IP connection to a serial port and vice versa
# requires Python 2.2 'cause socket.sendall is used


import sys
import os
import time
import threading
import socket
import codecs
import serial


 

try:
    True
except NameError:
    True = 1
    False = 0

class Redirector:
    def __init__(self, serial_instance, socket, ser_newline=None, net_newline=None, spy=False):
        self.serial = serial_instance
        self.socket = socket
        self.ser_newline = ser_newline
        self.net_newline = net_newline
        self.spy = spy
        self._write_lock = threading.Lock()

    def shortcut(self):
        """connect the serial port to the TCP port by copying everything
           from one side to the other"""
        self.alive = True
        self.thread_read = threading.Thread(target=self.reader)
        self.thread_read.setDaemon(True)
        self.thread_read.setName('serial->socket')
        self.thread_read.start()
        self.writer()

    def reader(self):
        """loop forever and copy serial->socket"""
        while self.alive:
            try:
                data = self.serial.read(1)              # read one, blocking
                n = self.serial.inWaiting()             # look if there is more
                if n:
                    data = data + self.serial.read(n)   # and get as much as possible
                if data:
                    # the spy shows what's on the serial port, so log it before converting newlines
                    if self.spy:
                        sys.stdout.write(codecs.escape_encode(data)[0])
                        sys.stdout.flush()
                    if self.ser_newline and self.net_newline:
                        # do the newline conversion
                        # XXX fails for CR+LF in input when it is cut in half at the begin or end of the string
                        data = net_newline.join(data.split(ser_newline))
                    # escape outgoing data when needed (Telnet IAC (0xff) character)
                    self._write_lock.acquire()
                    try:
                        self.socket.sendall(data)           # send it over TCP
                    finally:
                        self._write_lock.release()
            except socket.error, msg:
                sys.stderr.write('ERROR: %s\n' % msg)
                # probably got disconnected
                break
        self.alive = False

    def write(self, data):
        """thread safe socket write with no data escaping. used to send telnet stuff"""
        self._write_lock.acquire()
        try:
            self.socket.sendall(data)
        finally:
            self._write_lock.release()

    def writer(self):
        """loop forever and copy socket->serial"""
        while self.alive:
            try:
                data = self.socket.recv(1024)
                if not data:
                    break
                if self.ser_newline and self.net_newline:
                    # do the newline conversion
                    # XXX fails for CR+LF in input when it is cut in half at the begin or end of the string
                    data = ser_newline.join(data.split(net_newline))
                self.serial.write(data)                 # get a bunch of bytes and send them
                # the spy shows what's on the serial port, so log it after converting newlines
                if self.spy:
                    sys.stdout.write(codecs.escape_encode(data)[0])
                    sys.stdout.flush()
            except socket.error, msg:
                sys.stderr.write('ERROR: %s\n' % msg)
                # probably got disconnected
                break
        self.alive = False
        self.thread_read.join()

    def stop(self):
        """Stop copying"""
        if self.alive:
            self.alive = False
            self.thread_read.join()


if __name__ == '__main__':
    import optparse

    parser = optparse.OptionParser(
        usage = "%prog [options] [port [baudrate]]",
        description = "Simple Serial to Network (TCP/IP) redirector.",
        epilog = """\
NOTE: no security measures are implemented. Anyone can remotely connect
to this service over the network.

Only one connection at once is supported. When the connection is terminated
it waits for the next connect.
""")

    parser.add_option("-q", "--quiet",
        dest = "quiet",
        action = "store_true",
        help = "suppress non error messages",
        default = False
    )

    parser.add_option("--spy",
        dest = "spy",
        action = "store_true",
        help = "peek at the communication and print all data to the console",
        default = False
    )

    group = optparse.OptionGroup(parser,
        "Serial Port",
        "Serial port settings"
    )
    parser.add_option_group(group)

    group.add_option("-p", "--porta",
        dest = "port",
        help = "port A(shared), a number (default 0) or a device name",
        default = 0
    )
    group.add_option("--portb",
        dest = "portb",
        help = "port B, a number (default 1) or a device name",
        default = 1
    )
    group.add_option("--portc",
        dest = "portc",
        help = "port C, a number (default 2) or a device name",
        default = 2
    )

    group.add_option("-b", "--baud",
        dest = "baudrate",
        action = "store",
        type = 'int',
        help = "set baud rate, default: %default",
        default = 4800
    )

    group.add_option("-s", "--bytesize",
        dest = "bytesize",
        action = "store",
        type = 'int',
        help = "set bytesize, default: %default",
        default = 7
    )

    group.add_option("", "--parity",
        dest = "parity",
        action = "store",
        help = "set parity, one of [N, E, O], default=%default",
        default = 'E'
    )

    group.add_option("--rtscts",
        dest = "rtscts",
        action = "store_true",
        help = "enable RTS/CTS flow control (default off)",
        default = False
    )

    group.add_option("--xonxoff",
        dest = "xonxoff",
        action = "store_true",
        help = "enable software flow control (default off)",
        default = False
    )

    group.add_option("--rts",
        dest = "rts_state",
        action = "store",
        type = 'int',
        help = "set initial RTS line state (possible values: 0, 1)",
        default = None
    )

    group.add_option("--dtr",
        dest = "dtr_state",
        action = "store",
        type = 'int',
        help = "set initial DTR line state (possible values: 0, 1)",
        default = None
    )
    group.add_option("--keyup",
        dest = "key_up",
        action = "store",
        type = 'int',
        help = "set delay time  for PTT (prev RTS)(possible values: 0 a 300ms), default=%default",
        default = 300
    )

    group.add_option("--keydown",
        dest = "key_down",
        action = "store",
        type = 'int',
        help = "set delay time for soft carrier dekey (pos RTS)(possible values: 0 to 200ms), default=%default ms.",
        default = 30
    )
    group.add_option("--timenoresp",
        dest = "time_no_response",
        action = "store",
        type = 'int',
        help = "Time wait for response in sec,default=%default",
        default = 5
    )
    group.add_option("--serreadout",
        dest = "serial_read_timout",
        action = "store",
        type = 'int',
        help = "Time wait for read serial port in sec,default=%default",
        default = 0.5
    )

    group = optparse.OptionGroup(parser,
        "Network settings",
        "Network configuration."
    )
    parser.add_option_group(group)

    group.add_option("-P", "--localport",
        dest = "local_port",
        action = "store",
        type = 'int',
        help = "local TCP port",
        default = 7777
    )

    group = optparse.OptionGroup(parser,
        "Newline Settings",
        "Convert newlines between network and serial port. Conversion is normally disabled and can be enabled by --convert."
    )
    parser.add_option_group(group)

    group.add_option("-c", "--convert",
        dest = "convert",
        action = "store_true",
        help = "enable newline conversion (default off)",
        default = False
    )

    group.add_option("--net-nl",
        dest = "net_newline",
        action = "store",
        help = "type of newlines that are expected on the network (default: %default)",
        default = "LF"
    )

    group.add_option("--ser-nl",
        dest = "ser_newline",
        action = "store",
        help = "type of newlines that are expected on the serial port (default: %default)",
        default = "CR+LF"
    )

    (options, args) = parser.parse_args()

    # get port and baud rate from command line arguments or the option switches
    porta = options.port
    portb = options.portb
    portc = options.portc
    baudrate = options.baudrate
    time_no_response = options.time_no_response
    key_up = float(options.key_up) / 1000
    key_down = float(options.key_down) / 1000
    if args:
        if options.porta is not None:
            parser.error("no arguments are allowed, options only when --port is given")
        port = args.pop(0)
        if args:
            try:
                baudrate = int(args[0])
            except ValueError:
                parser.error("baud rate must be a number, not %r" % args[0])
            args.pop(0)
        if args:
            parser.error("too many arguments")
    else:
        if porta is None: port = 0
        if porta is None: port = 0
       if porta is None: port = 0
       if porta is None: port = 0
       if porta is None: port = 0

    # check newline modes for network connection
    mode = options.net_newline.upper()
    if mode == 'CR':
        net_newline = '\r'
    elif mode == 'LF':
        net_newline = '\n'
    elif mode == 'CR+LF' or mode == 'CRLF':
        net_newline = '\r\n'
    else:
        parser.error("Invalid value for --net-nl. Valid are 'CR', 'LF' and 'CR+LF'/'CRLF'.")

    # check newline modes for serial connection
    mode = options.ser_newline.upper()
    if mode == 'CR':
        ser_newline = '\r'
    elif mode == 'LF':
        ser_newline = '\n'
    elif mode == 'CR+LF' or mode == 'CRLF':
        ser_newline = '\r\n'
    else:
        parser.error("Invalid value for --ser-nl. Valid are 'CR', 'LF' and 'CR+LF'/'CRLF'.")


    d={"ID_hex":"Nombre"}

    fh = open('archivo.txt')
    for line in fh:
        linea = line.split(',')
        d[linea[0]] = linea[1] 
    fh.close()
    print '\n'
    print d
    print '\n'

    if options.porta is not None:
        # connect to serial port
        ser = serial.Serial()
        ser.port     = port
        ser.baudrate = baudrate
        ser.bytesize = options.bytesize
        ser.parity   = options.parity
        ser.rtscts   = options.rtscts
        ser.xonxoff  = options.xonxoff
        ser.timeout  = options.serial_read_timout   # required so that the reader thread can exit
        try:
            ser.open()
        except serial.SerialException, e:
            sys.stderr.write("Could not open serial port %s: %s\n" % (ser.portstr, e))
            sys.exit(1)
        #iniciaciòn RTS DTR
        ser.setRTS(False)
        if options.rts_state is not None:
            ser.setRTS(options.rts_state)

        ser.setDTR(options.dtr_state)
        if options.dtr_state is not None:
            ser.setDTR(False)



    if options.portb is not None:
        # connect to serial port
        ser1 = serial.Serial()
        ser1.port     = portb
        ser1.baudrate = baudrate
        ser1.bytesize = options.bytesize
        ser1.parity   = options.parity
        ser1.rtscts   = options.rtscts
        ser1.xonxoff  = options.xonxoff
        ser1.timeout  = options.serial_read_timout     # required so that the reader thread can exit
        try:
            ser1.open()
        except serial.SerialException, e:
            sys.stderr.write("Could not open serial port %s: %s\n" % (ser1.portstr, e))
            sys.exit(1)
            
        ser.setRTS(False)
        if options.rts_state is not None:
            ser.setRTS(options.rts_state)

        ser.setDTR(options.dtr_state)
        if options.dtr_state is not None:
            ser.setDTR(False)


    if options.portc is not None:
        # connect to serial port
        ser2 = serial.Serial()
        ser2.port     = portc
        ser2.baudrate = baudrate
        ser2.bytesize = options.bytesize
        ser2.parity   = options.parity
        ser2.rtscts   = options.rtscts
        ser2.xonxoff  = options.xonxoff
        ser2.timeout  = options.serial_read_timout    # required so that the reader thread can exit
        try:
            ser2.open()
        except serial.SerialException, e:
            sys.stderr.write("Could not open serial port %s: %s\n" % (ser2.portstr, e))
            sys.exit(1)


    if options.portd is not None:
        # connect to serial port
        ser3 = serial.Serial()
        ser3.port     = portd
        ser3.baudrate = baudrate
        ser3.bytesize = options.bytesize
        ser3.parity   = options.parity
        ser3.rtscts   = options.rtscts
        ser3.xonxoff  = options.xonxoff
        ser3.timeout  = options.serial_read_timout    # required so that the reader thread can exit
        try:
            ser3.open()
        except serial.SerialException, e:
            sys.stderr.write("Could not open serial port %s: %s\n" % (ser3.portstr, e))
            sys.exit(1)


    if options.porte is not None:
        # connect to serial port
        ser4 = serial.Serial()
        ser4.port     = portc
        ser4.baudrate = baudrate
        ser4.bytesize = options.bytesize
        ser4.parity   = options.parity
        ser4.rtscts   = options.rtscts
        ser4.xonxoff  = options.xonxoff
        ser4.timeout  = options.serial_read_timout    # required so that the reader thread can exit
        try:
            ser4.open()
        except serial.SerialException, e:
            sys.stderr.write("Could not open serial port %s: %s\n" % (ser4.portstr, e))
            sys.exit(1)
        #iniciaciòn RTS DTR
        ser4.setRTS(False)
        if options.rts_state is not None:
            ser.setRTS(options.rts_state)

        ser4.setDTR(options.dtr_state)
        if options.dtr_state is not None:
            ser.setDTR(False)


    if options.portf is not None:
        # connect to serial port
        ser5 = serial.Serial()
        ser5.port     = portc
        ser5.baudrate = baudrate
        ser5.bytesize = options.bytesize
        ser5.parity   = options.parity
        ser5.rtscts   = options.rtscts
        ser5.xonxoff  = options.xonxoff
        ser5.timeout  = options.serial_read_timout    # required so that the reader thread can exit
        try:
            ser5.open()
        except serial.SerialException, e:
            sys.stderr.write("Could not open serial port %s: %s\n" % (ser5.portstr, e))
            sys.exit(1)
        #iniciaciòn RTS DTR
        ser5.setRTS(False)
        if options.rts_state is not None:
            ser.setRTS(options.rts_state)

        ser5.setDTR(options.dtr_state)
        if options.dtr_state is not None:
            ser.setDTR(False)


        
    if not options.quiet:
        sys.stderr.write("--- COM shared V.1.01 --- type Ctrl-C / BREAK to quit\n")
        sys.stderr.write("--- %s>%s<%s %s,%s,%s,%s ---\n" % (ser1.portstr, ser.portstr, ser2.portstr, ser.baudrate, options.bytesize, ser.parity, 1))







        

    data = ser.read(1)
    data1 = ser1.read(1)
    data2 = ser2.read(1)
    
    
    while True:
        try:
            if options.portb is not None:
                data1 = data1 + ser1.read(1)            # read one, blocking
                if len(data1)>1024 : data1=''
                #data1 = data1[:500]
                if ':' in data1 :
                    
                    n = ser1.inWaiting()
                    if n : data1 = data1 + ser1.read(n)
                    if '\r\n' in data1 :
                        
                        data1 = data1[data1.index(':'):data1.index('\n')+1]
                        
                        if len(data1)> 4:
                            data1_id = data1[1:3]
                        else :
                            data1_id = "??"
                        
                        #enviar dato
                        ser.setRTS(True)
                        time.sleep(key_up)
                        ser.write(data1)                 # get a bunch of bytes and send them
                        
                        sys.stderr.write('\nB->%s' % codecs.escape_encode(data1)[0])
                        if data1_id in d :
                            sys.stderr.write('ID: %s - %s' % (data1_id,d[data1_id]))
                        
                        #self.serial.write(':47031BC50002D4\r\n')                 # get a bunch of bytes and send them
                        time.sleep(key_down)
                        ser.setRTS(False)
                        data1=''
                        time.sleep(0)
                        i=0
                        data = ser.read(1)
                        while True:
                            
                            sys.stderr.write('+')
                            n = ser.inWaiting()             # look if there is more
                            if n:
                                data = data + ser.read(n)   # and get as much as possible
                                if '\n' in data :
                                    sys.stderr.write('\nB<-%s %s' % (data1_id,codecs.escape_encode(data)[0]))
                                    ser1.write(data[:data.index('\n')+1])
                                    
                                    break
                                elif '\r' in data :
                                    sys.stderr.write('\nB<-%s %s' % (data1_id,codecs.escape_encode(data)[0]))
                                    ser1.write(data[:data.index('\r')+1])
                                    
                                    break
                            i =i+1
                            if i > (time_no_response * 2):
                                sys.stderr.write('\nB  %s %s' % (data1_id,codecs.escape_encode(data)[0]))
                                break
                            time.sleep(0.5)
                            
                        
            if options.portb is not None:       
                # Leer lo Com2
                data2 = data2 + ser2.read(1)            # read one, blocking
                if len(data2)>1024 : data2=''
                #data2 = data2[:500]
                if ':' in data2 :
                    n = ser2.inWaiting()
                    if n : data2 = data2 + ser2.read(n)
                    if '\r\n' in data2 :
                        data2 = data2[data2.index(':'):data2.index('\n')+1]
                        if len(data2)> 4:
                            data2_id = data2[1:3]
                        else :
                            data2_id = "??"

                        #enviar dato
                        ser.setRTS(True)
                        time.sleep(key_up)
                        ser.write(data2)                 # get a bunch of bytes and send them
                        sys.stderr.write('\nC->%s %s' % (data2_id,codecs.escape_encode(data2)[0]))
                        if data2_id in d :
                            sys.stderr.write('ID: %s - %s' % (data2_id,d[data2_id]))
                        #self.serial.write(':47031BC50002D4\r\n')                 # get a bunch of bytes and send them
                        time.sleep(key_down)
                        ser.setRTS(False)
                        data2=''
                        time.sleep(0)
                        i=0
                        data = ser.read(1)
                        while True:
                            sys.stderr.write('+')
                            n = ser.inWaiting()             # look if there is more
                            if n:
                                data = data + ser.read(n)   # and get as much as possible
                                if '\n' in data :
                                    sys.stderr.write('\nC<-%s %s' % (data2_id,codecs.escape_encode(data)[0]))
                                    ser2.write(data[:data.index('\n')+1])
                                    
                                    break
                                elif '\r' in data :
                                    sys.stderr.write('\nC<-%s %s' % (data2_id,codecs.escape_encode(data)[0]))
                                    ser2.write(data[:data.index('\r')+1])
                                    
                                    break
                            i =i+1
                            if i > (time_no_response * 2) :
                                sys.stderr.write('\nC  %s %s' % (data2_id,codecs.escape_encode(data)[0]))
                                break
                            time.sleep(0.5)

            n = ser.inWaiting()             # look if there is more
            data = ser.read(n)   # and get as much as possible
            
            
            #if options.spy: sys.stdout.write('\n')
            sys.stderr.write('.')
            
        except KeyboardInterrupt:
            break


    sys.stderr.write('\n--- exit ---\n')

