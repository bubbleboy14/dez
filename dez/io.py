import socket
LQUEUE_SIZE = 5
BUFFER_SIZE = 131072

def server_socket(port, certfile=None):
    ''' Return a listening socket bound to the given interface and port. '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(0)
    sock.bind(('', port))
    sock.listen(LQUEUE_SIZE)
    if certfile:
        import ssl
        return ssl.wrap_socket(sock, certfile=certfile)
    return sock

def client_socket(addr, port):
    sock = socket.socket()
    sock.setblocking(False)
    try:
        sock.connect_ex((addr, port))
    except socket.error:
        # this seems to happen when there are
        # > 1016 connections, for some reason.
        # we need to get to the bottom of this
        raise SocketError, "the python socket cannot open another connection"
    return sock

class SocketError(Exception):
    pass
