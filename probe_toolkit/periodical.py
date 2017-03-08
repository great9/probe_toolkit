from datetime import datetime
from datetime import timedelta
class periodical(object):
	def __init__(self,seconds):
		self.seconds = seconds
		self.end_time = datetime.now() + timedelta(seconds=self.seconds)
	def check(self):
		if datetime.now() >= self.end_time:
			self.end_time = datetime.now() + timedelta(seconds=self.seconds)
			return True
		return False
		