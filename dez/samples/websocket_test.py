from dez.network import WebSocketDaemon

def new_conn(conn):
    conn.write('you are connected!')
    def recv(frame):
        conn.write("ECHO: %s"%(frame))
    conn.set_cb(recv)

def log(msg):
    print "* " + msg

def main(domain, port):
    log("starting WebSocket Test")
    log("a sample client is provided in the 'dez/samples/html' directory")
    server = WebSocketDaemon(domain, port, new_conn, report_cb=log)
    server.start()