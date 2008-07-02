import event, os, struct, ctypes, ctypes.util

class INotify(object):
    def __init__(self, cb):
        self.__cb = cb
        self.__struct_size = 16
        self.__files = {}
        self.__clib = ctypes.cdll.LoadLibrary(ctypes.util.find_library('libc'))
        self.__fd = self.__clib.inotify_init()
        if self.__fd < 0:
            raise Exception, "INotify: bad file descriptor! Make sure your kernel supports inotify."
        event.read(self.__fd, self.__read_ready)

    def __read_ready(self):
        buff = os.read(self.__fd, 64)
        buff_index = 0
        while buff_index < len(buff):
            s = struct.unpack('iIII', buff[buff_index:buff_index+self.__struct_size])
            event.timeout(.1,self.__cb_handler,s)
            buff_index += self.__struct_size
        return True

    def __cb_handler(self, s):
        wd = s[0]
        if wd not in self.__files:
            return
        path = self.__files[wd]
        self.__cb(path)
        if s[1] == 2048:
            del self.__files[wd]
            self.add_path(path)

    def add_path(self, path):
        wd = self.__clib.inotify_add_watch(self.__fd, path, 4038)
        self.__files[wd] = path