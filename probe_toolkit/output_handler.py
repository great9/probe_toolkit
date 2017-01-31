import datetime
class output_handler(object):
	def __init__(self,config):
		#self.line_buffer = list()
		self.height = 0
		self.width = 0
		self.header = """probe_toolkit - probecap\n"""
		# http://misc.flogisoft.com/bash/tip_colors_and_formatting		
		self.color = {	'RED_BLACK'		: '[41;30m',
						'RED_WHITE'		: '[41;97m',
						'GREEN_BLACK'	: '[42;30m',
						'GREEN_WHITE'	: '[42;97m',
						'YELLOW_BLACK'	: '[43;30m',
						'YELLOW_WHITE'	: '[43;97m',
						'BLUE_BLACK'	: '[44;30m',
						'BLUE_WHITE'	: '[44;97m',
						'PURPLE_HAZE'	: '[45;97m'
			}
		self.log = { 'log_error'	: 1,
					'log_warn'		: 1,
					'log_info'		: 1,
					'log_notice'	: 1,
					'log_debug'		: 1
				}
		self.out = { 'out_error'	: 1,
					'out_warn'		: 1,
					'out_info'		: 1,
					'out_notice'	: 1,
					'out_debug'		: 1
				}
		self.set_dimensions(config)
		self.line_buffer = [""]*self.height
		self.set_vars(self.out,config)
		self.set_vars(self.log,config)
		print(chr(27) + "[2J") # clear screen

		if (config['log_info']
			or config['log_debug'] 
			or config['log_warn']
			or config['log_notice']
			or config['log_error']) and config['log_file'] != '':
			try:
				self.log_file = open(config['log_file'], 'a')
			except:
				self.output("ERROR","Could not open log_file")

		self.print_vars(config)

	def __exit__():
		self.log_file.close()

	# Need to do this after something changed, example the header size
	def set_dimensions(self,config=None):
		height_offet = 2
		if not config['height'] or not config['width']:
			import os
			term_rows, term_columns = os.popen('stty size', 'r').read().split() # https://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
			if not config['height']:
				self.height = int(term_rows) - (len(self.header.split('\n'))+height_offet)
			else:
				self.height = int(config['height']) - (len(self.header.split('\n'))+height_offet)
			if not config['width']:
				self.width = int(term_columns)
			else:
				self.width = int(config['width'])
		else: # if both are set in the config (and both are not 0)
			self.height = int(config['height']) - (len(self.header.split('\n'))+height_offet)
			self.width = int(config['width'])

	def set_vars(self,var,config):
		for k in var:
			if int(config[k]) == 1:
				if k[:3] == "log":
					self.log[k] = 1
				elif k[:3] == "out":
					self.out[k] = 1
			else:
				if k[:3] == "log":
					self.log[k] = 0
				elif k[:3] == "out":
					self.out[k] = 0

	def print_vars(self,config):
		for k in self.log:
			self.output("DEBUG",k+" "+str(self.log[k]))
		for k in self.out:
			self.output("DEBUG",k+" "+str(self.out[k]))
		for k in config:
			self.output("DEBUG","CONFIG:"+k+" "+str(config[k]))

	def update_buffer(self,line):
		if len(self.line_buffer) == self.height:
			self.line_buffer.pop(self.height-1)
			self.line_buffer = [line] + self.line_buffer
		else:
			self.line_buffer = [line] + self.line_buffer

	def print_buffer(self):
		print(chr(27) + "[2J") #http://bluesock.org/~willg/dev/ansi.html
		print(self.header)	
		# if we do this the above way, we need atleast 153 chars width
		for l in self.line_buffer:
			print(l)

	def add_coloring(self,msg,colors):
		msg = chr(27) + colors + msg;
		msg += chr(27) + "[0m"
		return msg

	def fill_str_size(self,msg):
		for x in range(1,(int(self.width) - len(msg.expandtabs()))):
			msg += " "
		return msg
		
	def output(self,msg_level,msg,msg_datetime=str(datetime.datetime.now())):
		switch = { 'ERROR'	: (self.log['log_error'],self.out['out_error'],self.color['RED_BLACK']),
					'INFO'	: (self.log['log_info'],self.out['out_info'],self.color['GREEN_WHITE']),
					'NOTICE': (self.log['log_notice'],self.out['out_notice'],self.color['BLUE_WHITE']),
					'DEBUG'	: (self.log['log_debug'],self.out['out_debug'],self.color['YELLOW_BLACK']),
					'WARN'	: (self.log['log_warn'],self.out['out_warn'],self.color['PURPLE_HAZE']),
		}
		if switch[msg_level][0]:
			self.log_file.write(msg_datetime + "," + msg_level + "," + msg + "\n");
		if switch[msg_level][1]:
			msg = "[" + msg_datetime + " " + msg_level + "] " + msg
			msg = self.fill_str_size(msg)
			msg = self.add_coloring(msg,switch[msg_level][2])
			self.update_buffer(msg)
			self.print_buffer()
		self.log_file.flush()
