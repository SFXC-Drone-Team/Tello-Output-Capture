import netifaces
import threading
import socket
import select
import time


class Datagram:
    def __init__(self, raw: tuple[bin, tuple[str, int]], decode: bool):
        """
        Datagram container.
        """
        self.raw = raw
        # Content
        self.content = raw[0]
        self.text = "114514"
        if decode:
            self.text = raw[0].decode("utf-8", errors="ignore")
        # Address
        self.ip = raw[1][0]
        self.port = raw[1][1]
        # Timestamp
        self.time = time.time()


class Server:
    def __init__(self, port: int = 8889, decode: bool = True, enable_filter: bool = True, debug: bool = False):
        # Start parameters
        self.__port = port
        self.__decode = decode
        self.__enable_filter = enable_filter
        self.__debug = debug
        # Host info
        self.__ip = []
        for item in netifaces.interfaces():
            try:
                # noinspection SpellCheckingInspection
                self.__ip.append(netifaces.ifaddresses(item)[2][0]['addr'])
            except (KeyError, IndexError):
                pass
        # Init socket
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IPV4, UDP
        self.__sock.setblocking(False)  # Socket timeout = 0
        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)  # Enable subnet broadcast
        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4194304)  # 4MB receive buffer
        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4194304)  # 4MB send buffer
        self.__sock.bind(("0.0.0.0", port))
        # Init data storage
        self.__data = []
        # Init indicator for new message
        self.new = False
        # Init receiving thread
        self.__recv_thread = threading.Thread(target=self.__recv, daemon=True)
        self.__recv_thread.start()

    def __recv(self) -> None:
        """
        Internal message receiving thread.
        """
        while True:
            select.select([self.__sock], [], [])  # Block until datagram in socket.
            try:
                datagram = self.__sock.recvfrom(8192)
            except (socket.herror, socket.gaierror):
                pass
            except socket.timeout:
                pass
            except (ConnectionResetError, ConnectionError):
                pass
            except OSError:
                pass
            else:
                if not self.__enable_filter:
                    self.__data.append(
                        Datagram(datagram, self.__decode)
                    )
                    self.new = True
                else:
                    if len(datagram[0]) == 0:
                        pass
                    elif datagram[1][0] in self.__ip:
                        pass
                    else:
                        self.__data.append(
                            Datagram(datagram, self.__decode)
                        )
                        self.new = True

    def read(self) -> Datagram:
        """
        Read the datagram in storage based on FIFO sequence.
        """
        # Block until datagram arrive.
        while not self.__data:
            pass
        # Reset indicator if necessary.
        if len(self.__data) == 1:
            self.new = False
        # Return datagram.
        return self.__data.pop(0)

    def send(self, text: str, ip: str, port: int, internal: bool = False) -> None:
        """
        Encode the text with utf-8, and sent it as datagram.
        """
        try:
            # Slow down the whole sending process to prevent exceeding buffer. (No meaning at all.)
            socket.gethostbyname(socket.gethostname())
            # Real sending part
            self.__sock.sendto(text.encode("utf-8", errors="ignore"), (ip, port))
            if not internal:
                pass
        except (socket.herror, socket.gaierror):
            pass
        except OSError:
            pass

    def broadcast(self, text: str, port: int) -> None:
        """
        Broadcast the datagram to the whole subnet on all NIC. (XXX.XXX.XXX.255)
        """
        # Grab broadcast ip of all NIC
        broadcast_ip = []
        for item in netifaces.interfaces():
            try:
                broadcast_ip.append(netifaces.ifaddresses(item)[2][0]['broadcast'])
            except (IndexError, KeyError):
                pass
        # Send datagram to these ip
        for ip in broadcast_ip:
            self.send(
                text=text,
                ip=ip,
                port=port,
                internal=True
            )
        pass
