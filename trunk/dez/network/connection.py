import event
import dez.io
import dez.buffer

class Connection(object):
    id = 0  
    def __init__(self, addr, sock, pool=None):
#        print 'opening'
        Connection.id += 1
        self.id = Connection.id
        
        self.pool = pool
        self.addr = addr
        self.sock = sock
        self.mode = None
        self.__write_queue = []
        self.__write_chunk = None
        self.__write_buffer = dez.buffer.Buffer()
        self.__read_buffer = dez.buffer.Buffer()
        self.__looping = False
        self.__mode_changed = False
        self.__release_timer = None
        self.__close_cb = None
        self.revent = None
        self.wevent = None
        if not self.pool:
            self.__start()
            
    def connect(self, timeout=5):
        self.connect_timer = event.timeout(timeout, self.__connect_timeout_cb)
        # TODO: maybe there's a better way of detecting a connect
        self.connect_event = event.write(self.sock, self.__connected_cb)
        
        
    def set_close_cb(self, cb, args=[]):
        self.__close_cb = (cb, args)    
            
    def __start(self):
        self.wevent = event.write(self.sock, self.__write_ready)
        self.revent = event.read(self.sock, self.__read_ready)
#        self.revent.delete()
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
    
    def release(self,timeout=0):
#        print 'RELEASE CALLED'
        self.halt_read()
        self.__read_buffer.reset()
        self.__clear_writes("Connection freed")
        #if self.pool and not self.__release_timer:
        if not self.__release_timer:
#            raise "What?"
            self.__ready()
#            self.__release_timer = event.timeout(timeout, self.__release_timer_cb)
        else:
            print 'pool',self.pool
            print 'release_timer',self.__release_timer
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
#        print 'write called'
        self.__write_queue.append(WriteChunk(data, cb, cbargs, eb, ebargs))
        if not self.wevent.pending():
#            print 'self.wevent.add()!'
#            self.wevent = event.write(self.sock, self.__write_ready)
            self.wevent.add()
#        else:
#            print 'no need for wevent.add: %s' % (self.wevent.pending(),)
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
    
    def halt_read(self):
        self.mode = None
#        if self.revent and self.revent.pending():
#            self.revent.delete()
        
    def __start_read(self):
        if self.mode == None:
            raise Exception("NoModeSet"), "First set a read mode"
#        self.revent.add()
        self.__read("")
        
    
    
    def __write_ready(self):
        # Keep a queue of things to write and their related callbacks
        # if we just finished writing some segment, call its callback
        # if there are no more segments, then stop
#        print 'write_ready'
        if self.__write_buffer.empty():
#            print 'self.__write_buffer empty'
            if self.__write_chunk:
                self.__write_chunk.completed()
                self.__write_chunk = None            
            if not self.__write_queue:
#                print 'self.__write_queue exhausted'
                return None # self.wevent.delete()
            self.__write_chunk = self.__write_queue.pop(0)
            self.__write_buffer.reset(self.__write_chunk.data)
#            print 'new chunk %s, %s left' % (len(self.__write_buffer), len(self.__write_queue))
        try:
            bsent = self.sock.send(self.__write_buffer.get_value())
#            print "WRITE:", self.__write_buffer.part(0, bsent).replace('\r\n', '\\r\\n\n')
            self.__write_buffer.move(bsent)
            return True
        except dez.io.socket.error, msg:
            self.close(reason=str(msg))
#            self.write_eb(self.write_ebargs)
            # also loop through response queue and call errbacks
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
#            print "READ:", data.replace('\r\n', '\\r\\n\n')
        except dez.io.socket.error:
            self.close()
            return None
        if not data:
            self.close()
            return None
        self.__read(data)
        return True
    
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
        assert isinstance(size, int)
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
        # If there's any data, we want it
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
        # never issue cb until we close
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
        # If there's any data, we want it
        return len(buffer) > 0
    
    def send_data(self, buffer):
        data = buffer.get_value()
        buffer.reset()
        self.cb(data, *self.args)
        return True
    
    def close(self, buffer):
        if len(buffer) > 0:
            self.cb(buffer.get_value())
            buffer.reset()
        self.cb("", *self.args)
        
class DelimeterReadMode(object):
    def __init__(self, delimiter, cb, args):
        self.completed = False
        self.cb = cb
        self.delimiter = delimiter
        self.args = args
    
    #TODO: ready and send_data require two finds on buffer...
    #      if this was one function we could do it once
    #      or do a find in ready and save results on self for send_data
    def ready(self, buffer):
        c = self.delimiter in buffer
        return c
    
    def send_data(self, buffer):
        i = buffer.find(self.delimiter)
        data = buffer.part(0, i)
        buffer.move(i + len(self.delimiter))
        self.cb(data, *self.args)
        return True
    
    def close(self, buffer):
        pass

