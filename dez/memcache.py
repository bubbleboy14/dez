import json

MC = None

class Memcache(object):
	def __init__(self):
		self.cache = {}

	def get(self, key, tojson=True):
		val = self.cache.get(key)
		return (val and tojson) and json.encode(val) or val

	def set(self, key, val, fromjson=True):
		self.cache[key] = fromjson and json.decode(val) or val

	def rm(self, key):
		if key in self.cache:
			del self.cache[key]

	def clear(self):
		self.cache = {}

def get_memcache():
	global MC
	if not MC:
		MC = Memcache()
	return MC