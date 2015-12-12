from dez.json import decode
from dez.logging import get_logger_getter
from dez.http.client import HTTPClient

F = None

class Fetcher(HTTPClient):
	def __init__(self):
		HTTPClient.__init__(self)
		self.log = get_logger_getter("dez")("Fetcher").simple

	def fetch(self, host, path="/", port=80, cb=None, timeout=1):
		url = "http://%s:%s%s"%(host, port, path)
		self.log("fetching: %s"%(url,))
		HTTPClient().get_url(url,
			cb=lambda resp : (cb and cb or self.log)(resp.body),
			timeout=timeout)

def fetch(host, path="/", port=80, cb=None, timeout=1, json=False, dispatch=False):
	global F
	if not F:
		F = Fetcher()
	if json:
		cb = lambda data : cb(decode(data))
	F.fetch(host, cb, path, port, timeout)
	if dispatch:
		import event
		event.signal(2, event.abort)
		event.dispatch()