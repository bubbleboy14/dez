from dez.network.websocket import WebSocketDaemon

BIG = "big" * 10000

def echo(data, conn):
    print("received", len(data), type(data), end=" - ")
    if data.startswith("small"):
        data = "small"
    elif data.startswith("big"):
        data = BIG
    print("echoing", len(data))
    conn.write(data)

def regConn(conn):
    print("new conn")
    conn.set_cb(echo, [conn])
    conn.set_close_cb(lambda : print("conn closed"))

def main(domain, port):
    WebSocketDaemon(domain, port, regConn).start()