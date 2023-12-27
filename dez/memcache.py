import json

MC = None

class Memcache(object):
	def __init__(self):
		self.cache = {}
		self.last_count = {}

	def get(self, key, tojson=True):
		val = self.cache.get(key)
		return (val and tojson) and json.dumps(val) or val

	def set(self, key, val, fromjson=True):
		self.cache[key] = fromjson and json.loads(val) or val

	def rm(self, key):
		if key in self.cache:
			del self.cache[key]

	def clear(self):
		self.cache = {}

	def count(self, items=False):
		if items:
			count = {}
			for key, val in list(self.cache.items()):
				count[key] = len(val)
			return count
		return len(self.cache)

	def diff(self):
		diff = {}
		count = self.count(True)
		for key, val in list(count.items()):
			orig = self.last_count.get(key)
			if val != orig:
				diff[key] = [orig, val]
		self.last_count = count
		return diff

def get_memcache():
	global MC
	if not MC:
		MC = Memcache()
	return MC