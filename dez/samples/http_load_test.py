import rel
from dez.bench import LoadTester
from optparse import OptionParser

def error(m1, m2):
    print('\n%s\n%s\n\ntry this: "dbench HOSTNAME PORT NUMBER CONCURRENCY [PIPELINERS] [-e]"\nor "dbench -h" for help\n'%(m1,m2))

def main():
    parser = OptionParser("dbench HOSTNAME PORT NUMBER CONCURRENCY [PIPELINERS] [-e]")
    parser.add_option("-p", "--path", dest="path", default="/", help="path -> http://[DOMAIN]:[PORT][PATH]")
    parser.add_option("-e", "--encrypted", action="store_true", dest="encrypted",
        default=False, help="use encrypted (https) connection")
    parser.add_option("-r", "--rel", dest="rel", default="epoll", help="change event delivery system (options: pyevent, epoll, poll, select) default: epoll")
    ops, args = parser.parse_args()
    if len(args) < 4:
        return error("insufficient arguments specified", "dbench requires 4 arguments")
    hostname = args[0]
    try:
        port = int(args[1])
        number = int(args[2])
        concurrency = int(args[3])
        pipeliners = len(args) > 3 and int(args[4]) or 0
    except:
        return error("invalid argument","PORT, NUMBER, and CONCURRENCY (and optional PIPELINERS) must all be integers")
    print("\nLoading Event Listener")
    print(" requesting: %s"%(ops.rel,))
    e = rel.initialize([ops.rel])
    if e != ops.rel:
        print("   failed to load %s!"%(ops.rel,))
    print("        loaded: %s"%(e,))
    LoadTester(hostname, port, ops.path, number, concurrency, pipeliners, ops.encrypted).start()