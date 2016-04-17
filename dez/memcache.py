MC = None

class Memcache(object):
	def __init__(self):
		self.cache = {}

	def get(self, key):
		return self.cache.get(key)

	def set(self, key, val):
		self.cache[key] = val

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