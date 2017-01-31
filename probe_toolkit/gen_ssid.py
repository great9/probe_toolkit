import string
import random
import os.path
from random import randint

class gen_ssid(object):
	def __init__(self,mask='NO_MASK_SET_YET'):
		self.mask = mask
		self.buffer = ""
		self.masks = []
		self.mask_file = ""
		
	def do_mask(self):
		i = 0
		while i < len(self.mask):
			if self.mask[i] == "?":
				self.buffer = self.buffer + {'d' : str(randint(0,9)),
							'l' : random.choice(string.ascii_lowercase),
							'u' : random.choice(string.ascii_uppercase),
							'a' : random.choice(string.ascii_lowercase + string.digits),
							'A' : random.choice(string.ascii_uppercase + string.digits),
							'x' : random.choice(string.hexdigits).lower(),
							'X' : random.choice(string.hexdigits).upper(),
				}[self.mask[i+1]]
				i += 1
			else:
				self.buffer = self.buffer + self.mask[i]
			i += 1
		result = self.buffer
		self.buffer = ""
		return result

	def set_random_mask(self):
		self.mask = random.choice(self.masks)

	def return_mask_count(self):
		return str(self.mask_count)

	def load_mask_file(self):
		if self.mask_file:
			if os.path.isfile(self.mask_file):
				with open(self.mask_file) as f:
					for line in f.readlines():
						self.masks.append(line.rstrip('\n'))

