from dez.network import WebSocketProxy

def main(domain, port):
    proxy = WebSocketProxy('localhost',81,domain,port)
    proxy.start()