from dez.json import decode
from dez.http.client import HTTPClient

F = None

class Fetcher(HTTPClient):
	def jayornay(self, txt, json=False):
		if json:
			return decode(txt)
		return txt

	def fetch(self, host, path="/", port=80, secure=False, headers={}, cb=None, timeout=1, json=False):
		url = "%s://%s:%s%s"%(secure and "https" or "http", host, port, path)
		self.log("fetching: %s"%(url,))
		self.get_url(url, headers=headers,
			cb=lambda resp : (cb or self.log)(self.jayornay(resp.body.get_value(), json)),
			timeout=timeout)

def fetch(host, path="/", port=80, secure=False, headers={}, cb=None, timeout=1, json=False, dispatch=False):
	global F
	if not F:
		F = Fetcher()
	F.fetch(host, path, port, secure, headers, cb, timeout, json)
	if dispatch:
		import event
		event.signal(2, event.abort)
		event.dispatch()