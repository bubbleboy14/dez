import socket, ssl, time, rel
LQUEUE_SIZE = 4096
BUFFER_SIZE = 65536 # higher values (previously 131072) break ssl sometimes
SSL_HANDSHAKE_TICK = 0.002
SSL_HANDSHAKE_TIMEOUT = 0.5
SSL_HANDSHAKE_DEADLINE = 5
# pre-2.7.9 ssl
# - cipher list adapted from https://bugs.python.org/issue20995
# - don't force (old) TLSv1 
#   - would avoid (broken) SSLv2 and SSLv3
#   - but TLSv1 sux :(
PY27_OLD_CIPHERS = "ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+3DES:ECDH+HIGH:DH+HIGH:RSA+HIGH:!aNULL:!eNULL:!MD5:!DSS"
locz = ["localhost", "0.0.0.0", "127.0.0.1", "::1", "::ffff:127.0.0.1"]
ipversions = ["dual"]#["ipv4", "ipv6"]

def ssl_handshake(sock, cb, *args):
    deadline = time.time() + SSL_HANDSHAKE_DEADLINE
    def shaker():
        try:
            sock.settimeout(SSL_HANDSHAKE_TIMEOUT)
            sock.do_handshake()
            sock.settimeout(0)
        except Exception as e:
            if time.time() > deadline:
                print("HANDSHAKE FAILED!", str(e))
                sock.close()
            else:
                return True
        else:
            cb(*args)
    rel.timeout(SSL_HANDSHAKE_TICK, shaker)

def accept_connection(sock, regConn, secure):
    try:
        sock, addr = sock.accept()
        addr = (addr[0], addr[1]) # for ipv6
        cb = regConn(sock, addr)
        if secure:
            ssl_handshake(sock, cb)
        else:
            cb()
    except socket.error as e:
        print("abandoning connection on socket error: %s"%(e,))
    return True

def listen(port, regConn, certfile=None, keyfile=None, cacerts=None):
    for ipv in ipversions:
        sock = server_socket(port, certfile, keyfile, cacerts, ipv)
        rel.read(sock, accept_connection, sock, regConn, bool(certfile))

def server_socket(port, certfile=None, keyfile=None, cacerts=None, ipv="dual"):
    ''' Return a listening socket bound to the given interface and port. '''
    if ipv == "dual":
        sock = socket.create_server(("", port), family=socket.AF_INET6,
            backlog=LQUEUE_SIZE, reuse_port=True, dualstack_ipv6=True)
        sock.setblocking(0)
    else:
        if ipv == "ipv6":
            fam = socket.AF_INET6
            host = '::1'
        else:
            fam = socket.AF_INET
            host = ''
        sock = socket.socket(fam, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)
        sock.bind((host, port))
        sock.listen(LQUEUE_SIZE)
    if certfile:
        if hasattr(ssl, "SSLContext"):
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(certfile, keyfile)
            ctx.load_default_certs()
            if cacerts:
                ctx.verify_mode = ssl.CERT_OPTIONAL
                ctx.load_verify_locations(cacerts)
            return ctx.wrap_socket(sock, server_side=True, do_handshake_on_connect=False)
        return ssl.wrap_socket(sock, certfile=certfile, keyfile=keyfile,
            ciphers=PY27_OLD_CIPHERS, server_side=True, do_handshake_on_connect=False)
    return sock

def client_socket(addr, port, secure=False):
    sock = socket.create_connection((addr, port))
    if secure:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.load_default_certs()
        if addr in locz:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            sock = ctx.wrap_socket(sock)
        else:
            sock = ctx.wrap_socket(sock, server_hostname=addr)
    sock.setblocking(False)
    return sock

class SocketError(Exception):
    pass
