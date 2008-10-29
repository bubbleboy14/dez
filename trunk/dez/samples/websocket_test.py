from dez.network import WebSocketDaemon

def new_conn(conn):
    print "new connection"
    conn.write('you are connected!')
    def recv(frame):
        response = "ECHO: %s"%(frame)
        print response
        conn.write(response)
    conn.set_cb(recv)

def main(domain, port):
    server = WebSocketDaemon(domain, port, new_conn)
    server.start()