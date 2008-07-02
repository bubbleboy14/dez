class FakeLogger(object):
    def debug(self, *args, **kwargs):
        pass
    info = debug
    access = debug
    warn = debug
    error = debug
    
logger = FakeLogger()

def default_get_logger(name):
    return logger
