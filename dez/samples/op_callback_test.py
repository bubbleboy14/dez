from dez.op.server.connection import Callback_Handler
import event

def main(**kwargs):
    c = Callback_Handler(None)
    domain = kwargs['domain']
    port = kwargs['port']
    c.set_url("success","http://"+domain+":"+str(port)+"/")
    c.set_url("failure","http://"+domain+":"+str(port)+"/")
    c.dispatch("success",{"key1":"value1","key2":"value2"})
    c.dispatch("failure",{"fkey":"fval","recipients":["r1","r2","r3","r4","r5"]})
    event.timeout(2,event.abort)
    event.dispatch()
