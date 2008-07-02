from dez.stomp.server.server import STOMPServer, STOMPConnection
from orbited.op.message import OrbitMessage
import random,event

def _key():
    return ''.join([random.choice('0123456789ABCDEF') for i in range(8)])

def _deliver(d):
    event.timeout(random.random(),random.choice([d.success,d.failure]))

class TestDaemon(object):
    def request_cb(self, frame, *args):
        print 'request_cb called'
        print 'args',args
        print 'request:'
        print '----'
        print frame.request
        print '----'
        if frame.action == "CONNECT":
            frame.connected(_key())
        elif frame.action == "DISCONNECT":
            frame.close()
        elif frame.action == "SEND":
            dest = frame.headers["destination"]
            msg = OrbitMessage([dest], frame.body, self.msg_outcome, [frame])
            _deliver(msg.single_recipient_message(dest))

    def msg_outcome(self, message, frame):
        if message.success_recipients:
            frame.success(message.success_recipients)
        if message.failure_recipients:
            frame.failure(message.failure_recipients)

    def close_cb(self, conn, *args):
        print 'connection %s closed' % conn
        print 'args:',args

    def connect_cb(self, conn):
        conn.set_request_cb(self.request_cb, ['print', 'this', 'out'])
        conn.set_close_cb(self.close_cb, ['conn', 'closed'])

def main(**kwargs):
    test = TestDaemon()
    server = STOMPServer(kwargs['domain'], kwargs['port'])
    server.set_connect_cb(test.connect_cb)
    server.start()

