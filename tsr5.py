#!/usr/bin/env python

# (C) 2002-2009 Chris Liechti <cliechti@gmx.net>
# redirect data from a TCP/IP connection to a serial port and vice versa
# requires Python 2.2 'cause socket.sendall is used

# write (self) revisa el dato de los sockets en la misma funcion

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
    
def ascii_to_gsm(ch):
    s = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    n = '0123456789:'
    
    idx = s.find(ch)
    if idx != -1:
        return bin(65+s.index(idx))
    idx = n.find(ch)
    if idx != -1:
        return bin(48+n.index(idx))
    if ch == '\n':
        return bin('\n')
    if ch == '\r':
        return bin('\r')
    return '?'

def ascii_to_str(s):
    return ''.join([str(ascii_to_gsm(ch))[2:] for ch in s])


class Redirector:
    def __init__(self, serial_instance, socket, socket2, ser_newline=None, net_newline=None, spy=False, rts_pre=10, rts_pos=100, no_resp=5):
        self.serial = serial_instance
        self.socket = socket
        self.socket2 = socket2
        self.ser_newline = ser_newline
        self.net_newline = net_newline
        self.spy = spy
        self._write_lock = threading.Lock()
        self.banderasocket = 0
        self.banderasocket2 = 0
        self.rts_pre = rts_pre / 1000
        self.rts_pos = rts_pos / 1000
        self.no_resp = no_resp
        self.timeron = 0

    def shortcut(self):
        """connect the serial port to the TCP port by copying everything
           from one side to the other"""
        self.alive = True
        self.thread_read = threading.Thread(target=self.reader)
        self.thread_read.setDaemon(True)
        self.thread_read.setName('serial->socket')
        self.thread_read.start()
   
        self.thread_rec = threading.Thread(target=self.timerrec)
        self.thread_rec.setDaemon(True)
        self.thread_rec.setName('Timer reciving resp')
        self.thread_rec.start()
        
        self.thread_writer2 = threading.Thread(target=self.writer2)
        self.thread_writer2.setDaemon(True)
        self.thread_writer2.setName('socket->serial')
        self.thread_writer2.start()
        
        self.writer()
        
    def timerrec(self):
        """timer que espera recibir la respuesta del punto remoto"""
        timeron = self.no_resp




    def reader(self):
        """loop forever and copy serial->socket"""
        while self.alive:
            try:
                data = self.serial.read(1)              # read one, blocking
                #sys.stdout.write('\n___%s' % data)
                time.sleep(3)
                n = self.serial.inWaiting()             # look if there is more
                if n:
                    data = data + self.serial.read(n)   # and get as much as possible
                
                #a= 'False'
                #if  '\n' in data :
                #    a='true'
                #sys.stdout.write('\n___%s : ' % a )
                #sys.stdout.write('___%s' % data)
                if data:
                    # the spy shows what's on the serial port, so log it before converting newlines
                    if self.spy:
                        if self.banderasocket == 1:
                            sys.stdout.write('\nRX S1<-: ')
                        if self.banderasocket2 == 1:
                            sys.stdout.write('\nRX S2<-: ')
                        sys.stdout.write(codecs.escape_encode(data)[0])
                        sys.stdout.flush()
                        
                    if self.ser_newline and self.net_newline:
                        # do the newline conversion
                        # XXX fails for CR+LF in input when it is cutc in half at the begin or end of the string
                        
                        sys.stdout.write('\nRa Sx<-: %s' % codecs.escape_encode(data)[0])
                        sys.stdout.flush()
                    # escape outgoing data when needed (Telnet IAC (0xff) character)
                    self._write_lock.acquire()
                    try:

                        #self.socket.sendall(data)
                        if self.banderasocket == 1:
                            #self.socket.sendall('ascii')           # send it over TCP
                            #data1 = ''.join([str((ch))[2:] for ch in data])+ '\r\n'
                            #data2 =    ':%s\r\n' %(data1[5:6])                    #self.socket.sendall(data+'\r\n')
                            
                            self.socket.sendall(data)
                            #self.socket.sendall(':'+data2+'\r\n')
                            #self.socket.sendall(':1503080000000000000000E0\r\n')
                            self.banderasocket = 0
                            #sys.stdout.write('\nRs test<-: %s' %(data2[5:]))
                        if self.banderasocket2 == 1:
                            self.socket2.sendall(data)           # send it over TCP
                            self.banderasocket2 = 0
                        # sys.stdout.write('\nRb Sx<-: %s' % codecs.escape_encode(data)[0])
                        # sys.stdout.write('\nRc Sx<-: %s' % ascii_to_str(data))
                        sys.stdout.flush()
                    finally:
                        self._write_lock.release()
            except socket.error, msg:
                sys.stderr.write('ERROR: %sc' % msg)
                # probably got disconnected
                break
        self.alive = False

    def write(self, data):
        """thread safe socket write with no data escaping. used to send telnet stuff"""
        self._write_lock.acquire()
        try:
            self.socket.sendall(data)
            self.socket2.sendall(data)

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
                   
                if self.banderasocket2 == 0:      
                    self.banderasocket =1
                    self.serial.setRTS(True)
                    time.sleep(0.1)
                    self.serial.write(data)                 # get a bunch of bytes and send them
                    #self.serial.write(':47031BC50002D4\r\n')                 # get a bunch of bytes and send them
                    time.sleep(0.1)
                    self.serial.setRTS(False)
                    # the spy shows what's on the serial port, so log it after converting newlines
                    if self.spy:
                        sys.stdout.write('\nTX S1->: ')
                        sys.stdout.write(codecs.escape_encode(data)[0])
                        sys.stdout.flush()
                    time.sleep(self.no_resp)
                    #self.banderasocket = 0
                else :
                     # the spy shows what's on the serial port, so log it after converting newlines
                    if self.spy:
                        sys.stdout.write('\nTX S1  : ')
                        sys.stdout.write(codecs.escape_encode(data)[0])
                        sys.stdout.flush()
            except socket.error, msg:
                sys.stderr.write('ERROR: %s\n' % msg)
                # probably got disconnected
                break
        self.alive = False
        self.thread_read.join()
    def writer2(self):
        """loop forever and copy socket->serial"""
        while self.alive:
            try:
                data2 = self.socket2.recv(1024)
                if not data2:
                    break
                if self.ser_newline and self.net_newline:
                    # do the newline conversion
                    # XXX fails for CR+LF in input when it is cut in half at the begin or end of the string
                    data2 = ser_newline.join(data2.split(net_newline))
                if self.banderasocket == 0:   
                    self.banderasocket2 = 1
                    self.serial.setRTS(True)
                    time.sleep(0.1)
                    self.serial.write(data2)                 # get a bunch of bytes and send them
                    time.sleep(0.1)
                    self.serial.setRTS(False)
                    # the spy shows what's on the serial port, so log it after converting newlines
                    if self.spy:
                        sys.stdout.write('\nTX S2->: ')
                        sys.stdout.write(codecs.escape_encode(data2)[0])
                        sys.stdout.flush()
                    time.sleep(self.no_resp)
                    
                    
                else :
                     # the spy shows what's on the serial port, so log it after converting newlines
                    if self.spy:
                        sys.stdout.write('\nTX S2  : ')
                        sys.stdout.write(codecs.escape_encode(data2)[0])
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
        description = "Two Network (TCP/IP) to Simple Serial redirector.",
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
        default = True
    )
    
    parser.add_option("--tcpspy",
        dest = "spy",
        action = "store_true",
        help = "peek at the communication and print all data to TCP port",
        default = True
    )

    group = optparse.OptionGroup(parser,
        "Serial Port",
        "Serial port settings"
    )
    parser.add_option_group(group)

    group.add_option("-p", "--port",
        dest = "port",
        help = "port, a number (default 0) or a device name",
        default = 1
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
    
    group.add_option("--rtspre",
        dest = "rts_pre",
        action = "store",
        type = 'int',
        help = "set delay time  for PTT (prev RTS)(possible values: 0 a 30ms), default=%default",
        default = 30
    )

    group.add_option("--rtspos",
        dest = "rts_pos",
        action = "store",
        type = 'int',
        help = "set delay time for soft carrier dekey (pos RTS)(possible values: 0 to 200ms), default=%default ms.",
        default = 100
    )
    group.add_option("--noresp",
        dest = "no_resp",
        action = "store",
        type = 'int',
        help = "set time to wait response(possible values: 0 to 30sec.), default=%default sec.",
        default = 1
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
        help = "local TCP port, default=%default",
        default = 7777
    )
    

    
    group.add_option("-Q", "--localport2",
        dest = "local_port2",
        action = "store",
        type = 'int',
        help = "Second local TCP port, default=%default",
        default = 7778
    )
    
    group.add_option("-R", "--localportspy",
        dest = "local_port_spy",
        action = "store",
        type = 'int',
        help = "Spy TCP port, default=%default",
        default = 8888
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
    port = options.port
    baudrate = options.baudrate
    if args:
        if options.port is not None:
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
        if port is None: port = 0

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

    # connect to serial port
    ser = serial.Serial()
    ser.port     = port
    ser.baudrate = baudrate
    ser.bytesize = options.bytesize
    ser.parity   = options.parity
    ser.rtscts   = options.rtscts
    ser.xonxoff  = options.xonxoff
    ser.timeout  = 1     # required so that the reader thread can exit

    if not options.quiet:
        sys.stderr.write("--- TCP/IP to Serial redirector --- type Ctrl-C / BREAK to quit\n")
        sys.stderr.write("--- %s %s,%s,%s,%s ---\n" % (ser.portstr, ser.baudrate, ser.bytesize, ser.parity, 1))

    try:
        ser.open()
    except serial.SerialException, e:
        sys.stderr.write("Could not open serial port %s: %s\n" % (ser.portstr, e))
        sys.exit(1)

    ser.setRTS(False)
    if options.rts_state is not None:
        ser.setRTS(options.rts_state)

    ser.setDTR(False)
    if options.dtr_state is not None:
        ser.setDTR(options.dtr_state)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind( ('', options.local_port) )
    srv2.bind( ('', options.local_port2) )
    srv.listen(1)
    srv2.listen(1)
    while True:
        try:
            sys.stderr.write("recusion limit %s...\n" % sys.getrecursionlimit())
            sys.stderr.write("Waiting for connection on %s...\n" % options.local_port)
            connection, addr = srv.accept()
            sys.stderr.write('Connected by %s\n' % (addr,))
            
            sys.stderr.write("Waiting for connection on %s...\n" % options.local_port2)
            connection2, addr2 = srv2.accept()
            sys.stderr.write('Connected by %s\n' % (addr2,))
            
            # enter network <-> serial loop
            r = Redirector(
                ser,
                connection,
                connection2,
                options.convert and ser_newline or None,
                options.convert and net_newline or None,
                options.spy,
                options.rts_pre,
                options.rts_pos,
                options.no_resp,
                
            )


            r.shortcut()
            if options.spy: sys.stdout.write('\n')
            sys.stderr.write('Disconnected\n')
            connection.close()
            connection2.close()
        except KeyboardInterrupt:
            break
        except socket.error, msg:
            sys.stderr.write('ERROR: %s\n' % msg)


    sys.stderr.write('\n--- exit ---\n')

