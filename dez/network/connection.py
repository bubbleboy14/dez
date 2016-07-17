import event
import dez.io
from dez.buffer import Buffer, B64ReadBuffer, B64WriteBuffer
from dez.json import decode
from dez.xml_tools import extract_xml, XMLNode

RBUFF = {True:B64ReadBuffer, False:Buffer}
WBUFF = {True:B64WriteBuffer, False:Buffer}

class Connection(object):
    id = 0
    def __init__(self, addr, sock, pool=None, b64=False):
        Connection.id += 1
        self.id = Connection.id
        self.pool = pool
        self.addr = addr
        self.sock = sock
        self.b64 = b64
        self.mode = None
        self.__write_queue = []
        self.__write_chunk = None
        self.__write_buffer = WBUFF[b64]()
        self.__read_buffer = RBUFF[b64]()
        self.__looping = False
        self.__mode_changed = False
        self.__release_timer = None
        self.__close_cb = None
        self.__soft_close = False
        self.revent = None
        self.wevent = None
        if not self.pool:
            self.__start()

    def set_b64(self, val):
        if val is not self.b64:
            self.b64 = val
            self.__write_buffer = WBUFF[val](str(self.__write_buffer))
            self.__read_buffer = RBUFF[val](str(self.__read_buffer))

    def connect(self, timeout=5):
        self.connect_timer = event.timeout(timeout, self.__connect_timeout_cb)
        self.connect_event = event.write(self.sock, self.__connected_cb)

    def set_close_cb(self, cb, args=[]):
        self.__close_cb = (cb, args)

    def __start(self):
        self.wevent = event.write(self.sock, self.__write_ready)
        self.revent = event.read(self.sock, self.__read_ready)
        self.wevent.delete()

    def __connected_cb(self):
        self.connect_event.delete()
        self.connect_event = None
        self.connect_timer.delete()
        self.connect_timer = None
        self.__start()
        self.__ready()

    def __connect_timeout_cb(self):
        self.connect_timer.delete()
        self.connect_timer = None
        self.close()

    def soft_close(self, reason=""):
        if self.__write_chunk or self.__write_queue:
            self.__soft_close = True
            if not self.wevent.pending():
                self.wevent.add()
            return
        self.close(reason)

    def close(self, reason=""):
        if self.revent:
            self.revent.delete()
            self.revent = None
        if self.wevent:
            self.wevent.delete()
            self.wevent = None
        self.sock.close()
        self.__clear_writes(reason)
        if self.pool:
            self.pool.connection_closed(self)
            self.pool = None
        if self.mode:
            self.mode.close(self.__read_buffer)
            self.mode = None
        if self.__close_cb:
            cb, args = self.__close_cb
            self.__close_cb = None
            if cb:
                cb(*args)

    def __clear_writes(self, reason=""):
        if self.__write_chunk:
            self.__write_chunk.error(reason)
            self.__write_chunk = None
        while self.__write_queue:
            self.__write_queue.pop(0).error(reason)

    def release(self, timeout=0):
        self.halt_read()
        self.__read_buffer.reset()
        self.__clear_writes("Connection freed")
        if not self.__release_timer:
            self.__ready()
        else:
            print 'pool', self.pool
            print 'release_timer', self.__release_timer
            raise "What?"

    def __release_timer_cb(self):
        self.__release_timer.delete()
        self.__release_timer = None
        self.pool.connection_available(self)

    def __ready(self):
        self.halt_read()
        self.__read_buffer.reset()
        self.__clear_writes("Connection freed")
        if self.pool:
            self.pool.connection_available(self)

    def write(self, data, cb=None, cbargs=[], eb=None, ebargs=[]):
        if data.__class__ == XMLNode:
            data = str(data)
        self.__write_queue.append(WriteChunk(data, cb, cbargs, eb, ebargs))
        if not self.wevent:
            raise ConnectionClosedException, "Connection %s is closed and can no longer write. Call Connection.set_close_cb for close notification."%self.id
        if not self.wevent.pending():
            self.wevent.add()

    def set_rmode_size(self, size, cb, args=[]):
        self.mode = SizeReadMode(size, cb, args)
        self.__mode_changed = True
        self.__start_read()

    def set_rmode_size_chunked(self, size, cb, args=[]):
        self.mode = SizeChunkedReadMode(size, cb, args)
        self.__mode_changed = True
        self.__start_read()

    def set_rmode_close(self, cb, args=[]):
        self.mode = CloseReadMode(cb, args)
        self.__mode_changed = True
        self.__start_read()

    def set_rmode_close_chunked(self, cb, args=[]):
        self.mode = CloseChunkedReadMode(cb, args)
        self.__mode_changed = True
        self.__start_read()

    def set_rmode_delimiter(self, delimiter, cb, args=[]):
        self.mode = DelimeterReadMode(delimiter, cb, args)
        self.__mode_changed = True
        self.__start_read()

    def set_rmode_json(self, cb, args=[]):
        self.mode = JSONReadMode(cb, args)
        self.__mode_changed = True
        self.__start_read()

    def set_rmode_xml(self, cb, args=[], silent_readerror=True):
        """
        silent_readerror
            the default setting (True) allows stray characters
            (spaces, line delimiters, etc) between valid nodes
        """
        self.mode = XMLReadMode(cb, args, silent_readerror)
        self.__mode_changed = True
        self.__start_read()

    def halt_read(self):
        self.mode = None

    def __start_read(self):
        if self.mode == None:
            raise Exception("NoModeSet"), "First set a read mode"
        self.__read("")

    # Keep a queue of things to write and their related callbacks
    # if we just finished writing some segment, call its callback
    # if there are no more segments, then stop
    def __write_ready(self):
        if self.__write_buffer.empty():
            if self.__write_chunk:
                self.__write_chunk.completed()
                self.__write_chunk = None
            if not self.__write_queue:
                if self.__soft_close:
                    self.close("soft close")
                return None
            self.__write_chunk = self.__write_queue.pop(0)
            self.__write_buffer.reset(self.__write_chunk.data)
        try:
            bsent = self.sock.send(self.__write_buffer.get_value())
            self.__write_buffer.move(bsent)
            return True
        except dez.io.socket.error, msg:
            self.close(reason=str(msg))
            return None

    # This function is far trickier than it originally seemed.
    # the __looping and __mode_changed variables are required to keep
    # from ignoring mode changes in the middle of the loop.
    def __read(self, data):
        self.__read_buffer += data
        if self.__looping:
            return
        self.__looping = True
        while self.mode:
            self.__mode_changed = False
            if not self.mode.ready(self.__read_buffer):
                break
            reschedule = self.mode.send_data(self.__read_buffer)
            if not reschedule and not self.__mode_changed:
                self.mode = None
        self.__looping = False

    def __read_ready(self):
        try:
            data = self.sock.recv(dez.io.BUFFER_SIZE)
        except dez.io.socket.error:
            self.close()
            return None
        if not data:
            self.close()
            return None
        self.__read(data)
        return True

class ConnectionClosedException(Exception):
    pass

class InvalidXMLException(Exception):
    pass

class WriteChunk(object):
    def __init__(self, data, cb=None, args=[], eb=None, ebargs=[]):
        self.data = data
        self.cb = cb
        self.args = args
        self.eb = eb
        self.ebargs = ebargs

    def completed(self):
        if self.cb:
            self.cb(*self.args)

    def error(self, reason=None):
        if self.eb:
            self.eb(*self.ebargs)

class SizeReadMode(object):
    def __init__(self, size, cb, args):
        self.args = args
        self.size = size
        self.completed = False
        self.cb = cb

    def ready(self, buffer):
        return self.size <= len(buffer)

    def send_data(self, buffer):
        data = buffer.part(0, self.size)
        buffer.move(self.size)
        self.cb(data, *self.args)
        return False

    def close(self, buffer):
        pass

class SizeChunkedReadMode(object):
    def __init__(self, size, cb, args):
        self.size = size
        self.completed = False
        self.cb = cb
        self.args = args

    def ready(self, buffer):
        return len(buffer) > 0

    def send_data(self, buffer):
        data = buffer.part(0, min(self.size, len(buffer)))
        buffer.move(len(data))
        self.size -= len(data)
        self.cb(data, *self.args)
        if self.size == 0:
            self.cb("")
            return False
        return True

    def close(self, buffer):
        pass

class CloseReadMode(object):
    def __init__(self,  cb, args):
        self.completed = False
        self.cb = cb
        self.args = args

    def ready(self, buffer):
        return False

    def send_data(self, buffer):
        raise Exception("InvalidCall"), "How did this get called?"

    def close(self, buffer):
        self.cb(buffer.get_value(), *self.args)
        buffer.reset()

class CloseChunkedReadMode(object):
    def __init__(self, cb, args):
        self.completed = False
        self.cb = cb
        self.args = args

    def ready(self, buffer):
        return len(buffer) > 0

    def send_data(self, buffer):
        data = buffer.get_value()
        buffer.reset()
        self.cb(data, *self.args)
        return True

    def close(self, buffer):
        if len(buffer) > 0:
            self.cb(buffer.get_value(), *self.args)
            buffer.reset()

class DelimeterReadMode(object):
    def __init__(self, delimiter, cb, args):
        self.completed = False
        self.cb = cb
        self.delimiter = delimiter
        self.args = args
        self.delim_index = -1

    def ready(self, buffer):
        self.delim_index = buffer.find(self.delimiter)
        return self.delim_index != -1

    def send_data(self, buffer):
        data = buffer.part(0, self.delim_index)
        buffer.move(self.delim_index + len(self.delimiter))
        self.delim_index = -1
        self.cb(data, *self.args)
        return True

    def close(self, buffer):
        pass

class JSONReadMode(object):
    def __init__(self, cb, args):
        self.completed = False
        self.cb = cb
        self.args = args
        self.checked_index = 0
        self.frame = None

    def ready(self, buffer):
        buff = buffer.get_value()
        if not buff:
            return False
        if buff[0] == "[":
            c = ']'
        elif buff[0] == "{":
            c = '}'
        else:
            self.checked_index = 0
            buffer.move(1)
            return self.ready(buffer)
        i = buffer.find(c, self.checked_index)
        while i != -1:
            try:
                self.frame = decode(buffer.part(0, i+1))
                buffer.move(i+1)
                self.checked_index = 0
                return True
            except:
                self.checked_index = i+1
                i = buffer.find(c, self.checked_index)
        return False

    def send_data(self, buffer):
        self.cb(self.frame, *self.args)
        self.frame = None
        return True

    def close(self, buffer):
        pass

class XMLReadMode(object):
    def __init__(self, cb, args, silent_readerror):
        self.completed = False
        self.cb = cb
        self.args = args
        self.checked_index = 0
        self.name = None
        self.name_count = 0
        self.frame = None
        self.silent = silent_readerror

    def ready(self, buffer):
        if not self.name:
            buff = buffer.get_value()
            if not buff:
                return False
            if buff[0] != "<":
                if not self.silent:
                    raise InvalidXMLException, 'Invalid first character in XML node: %s found instead of "<"'%buff[0]
                self.checked_index = 0
                buffer.move(1)
                return self.ready(buffer)
            if ">" not in buff:
                return False
            close_index = buff.index('>')
            if buff[close_index-1] == '/':
                self.frame = extract_xml(buff[:close_index+1])
                buffer.move(close_index+1)
                self.checked_index = 0
                return True
            self.name = buff[1:close_index].split(' ',1)[0]
            self.name_count = 1
            self.checked_index = close_index+1
        i = buffer.find(">", self.checked_index)
        while i != -1:
            if buffer.part(i-1-len(self.name),i+1) == "<"+self.name+">":
                self.name_count += 1
            elif buffer.part(i-2-len(self.name),i+1) == "</"+self.name+">":
                self.name_count -= 1
                if not self.name_count:
                    self.frame = extract_xml(buffer.part(0, i+1))
                    buffer.move(i+1)
                    self.checked_index = 0
                    self.name = None
                    return True
            self.checked_index = i+1
            i = buffer.find(">", self.checked_index)
        return False

    def send_data(self, buffer):
        self.cb(self.frame, *self.args)
        self.frame = None
        return True

    def close(self, buffer):
        pass
