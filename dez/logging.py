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

class BasicLogger(object):
	def __init__(self, name, subname, func):
		self.name = name
		self.subname = subname
		self.func = func

	def _log(self, log_type, msg, *args, **kwargs):
		self.func("[%s] %s | %s :: %s"%(log_type, self.name,
			self.subname, msg), *args, **kwargs)

	def debug(self, msg, *args, **kwargs):
		self._log("debug", msg, *args, **kwargs)

	def info(self, msg, *args, **kwargs):
		self._log("info", msg, *args, **kwargs)

	def access(self, msg, *args, **kwargs):
		self._log("access", msg, *args, **kwargs)

	def warn(self, msg, *args, **kwargs):
		self._log("warn", msg, *args, **kwargs)

	def error(self, msg, *args, **kwargs):
		self._log("error", msg, *args, **kwargs)

def get_logger(name, func):
	return lambda subname : BasicLogger(name, subname, func)