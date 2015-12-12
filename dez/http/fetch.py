from dez.logging import get_logger_getter
from dez.http.client import HTTPClient

F = None

class Fetcher(HTTPClient):
	def __init__(self):
		HTTPClient.__init__(self)
		self.log = get_logger_getter("dez")("Fetcher").simple

	def fetch(self, host, cb=None, path="/", port=80, timeout=1):
		url = "http://%s:%s%s"%(host, port, path)
		self.log("fetching: %s"%(url,))
		HTTPClient().get_url(url,
			cb=lambda resp : (cb and cb or self.log)(resp.body),
			timeout=timeout)

def fetch(host, cb=None, path="/", port=80, timeout=1, dispatch=False):
	global F
	if not F:
		F = Fetcher()
	F.fetch(host, cb, path, port, timeout)
	if dispatch:
		import event
		event.signal(2, event.abort)
		event.dispatch()