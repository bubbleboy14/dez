from base64 import b64encode, b64decode
from dez.io import BUFFER_SIZE

class Buffer(object):
    ''' A Buffer object buffers text, and has two modes, 'index' and 'consume'

        In index mode, the buffer object keeps track of a position 'pos',
        which can be altered by calling b.move, or by b.exhaust, which
        moves 'pos' to the end of the file.

        In consume mode (default), a buffer is essentially just a proxy
        for its contained string b.data.

        If you experience memory leaks, make sure you don't have
        buffers sitting around in 'index' mode.
    '''
    def __init__(self, initial_data=b'', mode='consume'):
        self.mode = None
        self.pos = None
        self.data = initial_data
        self.set_mode(mode)

    def set_mode(self, mode):
        # No change
        if self.mode == mode:
            return
        # Switch from consume to index or initial mode is index
        elif mode == 'index':
            self.mode = 'index'
            self.pos = 0
        # Switch from index to consume
        elif mode == 'consume' and self.pos is not None:
            self.data = self.data[self.pos:]
            self.pos = None
            self.mode = 'consume'
        # initial mode is consume
        else:
            self.mode = 'consume'
            self.pos = None

    def find(self, marker, i=0):
        if isinstance(marker, str):
            marker = marker.encode()
        if self.mode == 'consume':
            return self.data.find(marker, i)
        elif self.mode == 'index':
            pos =  self.data.find(marker, i + self.pos)
            if pos == -1:
                return -1
            return pos - self.pos

    def __str__(self):
        return self.get_value()

    def get_value(self):
        ''' Return the data in consume mode, or the remainder of the data in
            index mode.
        '''
        if self.mode == 'consume':
            return self.data
        elif self.mode == 'index':
            return self.data[self.pos:]

    def get_full_value(self):
        ''' Returns the full value of the string, even in index mode. '''
        return self.data

    def exhaust(self):
        ''' In index mode, sets position to the end of the buffered data.  In
            consume mode, sets data to empty.
        '''
        if self.mode == 'consume':
            self.data = b''
        elif self.mode == 'index':
            self.pos = len(self.data)

    def reset_position(self):
        ''' Resets position to 0. '''
        if self.mode == 'index':
            self.pos = 0

    def reset(self, content = b''):
        ''' Resets data to empty, or an opional 'content' string, and position
            to 0.
        '''
        if isinstance(content, str):
            content = content.encode()
        self.data = content
        self.reset_position()

    def empty(self):
        ''' Boolean; is true if the the buffer is empty '''
        if self.mode == 'consume':
            return len(self.data) == 0
        elif self.mode == 'index':
            return (len(self.data) - self.pos) == 0

    def move(self, i):
        if self.mode == 'consume':
            self.data = self.data[i:]
        elif self.mode == 'index':
            self.pos += i

    def part(self, start, end):
        if self.mode == 'consume':
            return self.data[start:end]
        elif self.mode == 'index':
            return self.data[self.pos + start: self.pos + end]

    def __contains__(self, data):
        if isinstance(data, str):
            data = data.encode()
        if self.mode == 'consume':
            return data in self.data
        elif self.mode == 'index':
            return self.data.find(data, self.pos) != -1

    def __eq__(self, data):
        if isinstance(data, str):
            data = data.encode()
        if self.mode == 'consume':
            return self.data == data
        elif self.mode == 'index':
            return self.data[self.pos:] == data

    def __len__(self):
        if self.mode == 'consume':
            return len(self.data)
        elif self.mode == 'index':
            return len(self.data) - self.pos

    def __get_slice__(self, start, end):
        return self.part(self, start, end)

    def __getitem__(self, key):
        return self.data[key]

    def __add__(self, add_data):
        ''' Add the passed-in string to the buffer '''
        if add_data:
            if isinstance(add_data, str):
                add_data = add_data.encode()
            self.data += add_data
        return self

class ReadBuffer(Buffer):
    ''' This works exactly like the Buffer class, except it
        decode()s incoming bytes before passing them off
    '''
    def stringy(self):
        try:
            self.data.decode()
            return True
        except:
            return False

    def part(self, start, end):
        d = Buffer.part(self, start, end)
        try:
            return d.decode()
        except:
            return d

    def get_value(self):
        d = Buffer.get_value(self)
        try:
            return d.decode()
        except:
            return d

class WriteBuffer(Buffer):
    ''' This works exactly like the Buffer class, with the
        addition of send()
    '''
    def send(self, sock):
        self.move(sock.send(self.get_value()[:BUFFER_SIZE]))

class B64ReadBuffer(ReadBuffer):
    ''' This works exactly like the ReadBuffer class, except it
        reads base64-encoded strings separated by whitespace.
    '''
    def __init__(self, initial_data=b'', mode='consume'):
        self.raw_data = b''
        ReadBuffer.__init__(self, initial_data, mode)

    def __add__(self, add_data):
        ''' Add the passed-in base64-encoded string to the pre-buffer '''
        s = add_data.find(' ')
        if s != -1:
            self.data += b64decode(self.raw_data+add_data[:s])
            add_data = add_data[s+1:]
            self.raw_data = b''
        self.raw_data += add_data
        return self

class B64WriteBuffer(WriteBuffer):
    ''' This works exactly like the WriteBuffer class, except
        get_value() returns a base64-encoded string
    '''
    def get_value(self):
        ''' Return the base64-encoded data in consume mode, or the base64-encoded remainder of the data in
            index mode.
        '''
        return b64encode(WriteBuffer.get_value(self)) + b' '