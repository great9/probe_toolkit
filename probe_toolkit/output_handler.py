import datetime
import time
from time import mktime
import sys
class output_handler(object):
	def __init__(self,config):
		self.config = config
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
		self.clear_screen()
		self.disable_color = True
		if 'disable_color' in config:
			self.disable_color = config['disable_color']
		self.set_dimensions()
		self.line_buffer = [""]*self.height
		self.set_vars(self.out,config)
		self.set_vars(self.log,config)
		self.time_ago_format = False
		if 'time_ago_format' in config:
			self.time_ago_format = config['time_ago_format']
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

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.log_file.close()

	def clear_screen(self):
		# use sys.stdout.write so there is no new line.
		# first clear screen then set cur pos top left
		sys.stdout.write(chr(27) + "[2J" + chr(27) + "[0;0H")

	# Need to do this after something changed, example the header size
	# This will reset the line buffer
	def set_dimensions(self):
		height_offet = 1
		if not self.config['height'] or not self.config['width']:
			import os
			term_rows, term_columns = os.popen('stty size', 'r').read().split() # https://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
			if not self.config['height']:
				self.height = int(term_rows) - (len(self.header.split('\n'))+height_offet)
			else:
				self.height = int(self.config['height']) - (len(self.header.split('\n'))+height_offet)
			if not self.config['width']:
				self.width = int(term_columns)
			else:
				self.width = int(self.config['width'])
		else: # if both are set in the config (and both are not 0)
			self.height = int(self.config['height']) - (len(self.header.split('\n'))+height_offet)
			self.width = int(self.config['width'])
		self.line_buffer = [""]*self.height

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
			self.output("DEBUG","OUTPUT_CONFIG:"+k+" "+str(config[k]))

	def update_buffer(self,line):
		if len(self.line_buffer) == self.height:
			self.line_buffer.pop(self.height-1)
			self.line_buffer = [line] + self.line_buffer
		else:
			self.line_buffer = [line] + self.line_buffer

	def print_header(self):
		sys.stdout.write(chr(27) + "[0;0H")	# Go to top left
		for x in self.header.split('\n'):
			print(chr(27) + "[K " + x) 		# erase line + add new
		sys.stdout.write(chr(27) + "[s") 	# save cur pos

	def print_buffer(self):
		self.print_header()
		sys.stdout.write(chr(27) + "[u") 	# restore cur pos

		for l in self.line_buffer:
			if self.time_ago_format:		# if time_ago_format is set True in config
				l = self.redraw_time_ago(l)	# return time ago string
			print(chr(27) + "[K" + l) 		# erase line + add new

	def add_coloring(self,msg,colors):
		msg = chr(27) + colors + msg;
		msg += chr(27) + "[0m"
		return msg

	def fill_str_size(self,msg):
		for x in range(1,(int(self.width) - len(msg.expandtabs()))):
			msg += " "
		return msg

	def redraw_time_ago(self,line):
		if len(line) > 25:
			if not self.disable_color: offset = 10
			else: offset = 2
			_datetime = line[offset:19+offset]
			t_ago = self.time_ago(_datetime)
			line = line[0:offset] + t_ago + line[offset+19:]
		return line

	def time_ago(self,_datetime):
		time_ago_str = ""
		if _datetime != '':
			m_datetime = datetime.datetime.strptime(_datetime, '%Y-%m-%d %H:%M:%S')
			_time_ago = datetime.datetime.now() - m_datetime
			hours = _time_ago.seconds / 3600
			if hours > 0:
				return _datetime
			seconds = _time_ago.seconds
			if seconds < 2:
				return "     just now.".ljust(19)
			minutes = _time_ago.seconds / 60
			if minutes > 0:
				time_ago_str += "%02d min "%minutes
			if seconds - (minutes * 60) > 0:
				time_ago_str += "%02d sec "%(seconds - (minutes * 60))
			time_ago_str += "ago."
			return time_ago_str.rjust(19)

		
	def output(self,msg_level,msg,msg_datetime=None):
		switch = { 'ERROR'	: (self.log['log_error'],self.out['out_error'],self.color['RED_BLACK']),
					'INFO'	: (self.log['log_info'],self.out['out_info'],self.color['GREEN_WHITE']),
					'NOTICE': (self.log['log_notice'],self.out['out_notice'],self.color['BLUE_WHITE']),
					'DEBUG'	: (self.log['log_debug'],self.out['out_debug'],self.color['YELLOW_BLACK']),
					'WARN'	: (self.log['log_warn'],self.out['out_warn'],self.color['PURPLE_HAZE']),
		}
		if not msg_datetime:
			msg_datetime = str(datetime.datetime.now())[:19]
		if switch[msg_level][0]:
			self.log_file.write(msg_datetime + "," + msg_level + "," + msg + "\n");
		if switch[msg_level][1]:
			msg = "[ " + msg_datetime + " " + msg_level.rjust(6) + " ] " + msg
			msg = self.fill_str_size(msg)
			if not self.disable_color:
				msg = self.add_coloring(msg,switch[msg_level][2])
			self.update_buffer(msg)
			self.print_buffer()
		self.log_file.flush()
