from dez.http.client.client import HTTPClient, SILENT

HC = None

def http_client(silent=SILENT):
	global HC
	if not HC:
		HC = HTTPClient(silent)
	return HC

def do_dispatch():
	import rel
	rel.signal(2, rel.abort)
	rel.dispatch()

def fetch(host, path="/", port=80, secure=False, headers={}, cb=None, timeout=10, json=False, dispatch=False, silent=SILENT, eb=None):
	http_client(silent).fetch(host, path, port, secure, headers, cb, timeout, json, eb)
	dispatch and do_dispatch()

def post(host, path="/", port=80, secure=False, headers={}, data=None, text=None, cb=None, timeout=10, json=False, dispatch=False, silent=SILENT, eb=None):
	http_client(silent).post(host, path, port, secure, headers, data, text, cb, timeout, json, eb=eb)
	dispatch and do_dispatch()