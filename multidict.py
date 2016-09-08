from collections import OrderedDict

class MultiDict(OrderedDict):
	def __setitem__(self, key, val):
		if key in self:
			if isinstance(self[key], list):
				self[key].append(val)
			else:
				OrderedDict.__setitem__(self, key, [self[key], val])
		else:
			OrderedDict.__setitem__(self, key, val)
			
	def set(self, key, val):
		OrderedDict.__setitem__(self, key, val)