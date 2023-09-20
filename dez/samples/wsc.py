# run dez_test wsecho, then this

import rel
try:
    import websocket
except:
    print("this demo requires websocket-client")

mult = 20000

class Bouncer(object):
    def __init__(self, domain, port):
        self.payload = self.getPayload()
        self.ws = self.getWS(domain, port)

    def send(self, ws):
        print("sending", len(self.payload), "bytes")
        ws.send(self.payload)
        return True

    def recv(self, ws, msg):
        print("received", len(msg), type(msg))

    def start(self):
        rel.timeout(0.5, self.send, self.ws)
        rel.dispatch()

    def getWS(self, domain, port):
        ws = websocket.WebSocketApp("ws://%s:%s"%(domain, port), on_message=self.recv)
        ws.run_forever(dispatcher=rel)
        return ws

    def getPayload(self):
        print("heavy traffic can be upstream, downstream, both [the default], or neither")
        mode = input("enter '[u]pstream' or '[d]ownstream' or '[n]either' - default is '[b]oth': ")
        if mode.startswith("u"):
            return "small" * mult
        elif mode.startswith("d"):
            return "big"
        elif mode.startswith("n"):
            return "small"
        else: # both
            return "echo" * mult

def main(domain, port):
    Bouncer(domain, port).start()