import datetime
import time
from time import mktime
import sys
import re
from cStringIO import StringIO # to capture stdout in to a buff
#import os

class output_handler(object):
	def __init__(self,config):
		self.config = config
		self.height = 0
		self.width = 0
		self.header = """probe_toolkit - Output Handler\n"""
		# http://misc.flogisoft.com/bash/tip_colors_and_formatting		
		self.color = {'RED_BLACK'	: '[41;30m',
				'RED_WHITE'	: '[41;97m',
				'GREEN_BLACK'	: '[42;30m',
				'GREEN_WHITE'	: '[42;97m',
				'YELLOW_BLACK'	: '[43;30m',
				'YELLOW_WHITE'	: '[43;97m',
				'BLUE_BLACK'	: '[44;30m',
				'BLUE_WHITE'	: '[44;97m',
				'PURPLE_HAZE'	: '[45;97m',
			}
		self.log = { 'log_error': 1,
			'log_warn'	: 1,
			'log_info'	: 1,
			'log_notice'	: 1,
			'log_debug'	: 1
				}
		self.out = { 'out_error': 1,
			'out_warn'	: 1,
			'out_info'	: 1,
			'out_notice'	: 1,
			'out_debug'	: 1
			}
		self.input = False
		if 'input' in config:
			self.input = config['input']
		if self.input == True:
			self.matched_keys = list()
			global termios
			import termios
			global os
			import os
			#https://stackoverflow.com/questions/21791621/python-taking-input-from-sys-stdin-non-blocking
			#http://www.unixwiz.net/techtips/termios-vmin-vtime.html
			#http://man7.org/linux/man-pages/man3/termios.3.html
			#https://wiki.python.org/moin/BitwiseOperators
			#https://www.gnu.org/software/libc/manual/html_node/Mode-Data-Types.html
			term_attr = {'iflag'	: 0,
				'oflag'		: 1,
				'cflag'		: 2,
				'lflag'		: 3,
				'ispeed'	: 4,
				'ospeed'	: 5,
				'cc'		: 6
			}
			self.term_attr_backup = termios.tcgetattr(sys.stdin)
			self.term_attr = termios.tcgetattr(sys.stdin)
			# Bitwiser operations to disable echo and canonical mode.
			self.term_attr[term_attr['lflag']] = self.term_attr[term_attr['lflag']] & ~(termios.ECHO | termios.ICANON)
			# Set non-blocking read.
			self.term_attr[term_attr['cc']][termios.VMIN] = '\x00'
			self.term_attr[term_attr['cc']][termios.VTIME] = '\x00'
			# Apply new settings
			termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.term_attr)
			# end termios
			self.selected_line = 0
		if 'log_stdout' in config:
			self.stdout_log = config['log_stdout']
			self.stdout_capture_buff = StringIO()
			self.stdout_backup = sys.stdout
			self.stdout_buff = ""
		self.clear_screen()
		self.disable_color = True
		if 'disable_color' in config:
			self.disable_color = config['disable_color']
		self.line_buffer = list()
		self.header_size = 0
		self.height_offset = 2
		self.set_dimensions()
		self.set_vars(self.out,config)
		self.set_vars(self.log,config)
		self.time_ago_format = False
		self.fill_bg = True
		if 'scroll' in config:
			self.scroll = config['scroll']
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
		self.print_header()

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		print ""# new line
		if self.input:
			termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.term_attr_backup)
		if self.stdout_log == True:
			self.log_stdout()
		self.log_file.close()

	def clear_screen(self):
		# use sys.stdout.write so there is no new line.
		# first clear screen then set cur pos top left
		sys.stdout.write(chr(27) + "[2J" + chr(27) + "[0;0H")

	def stdout_capture(self):
		self.stdout_buff += self.stdout_capture_buff.getvalue()
		sys.stdout = self.stdout_capture_buff = StringIO()

	def stdout_restore(self):
		sys.stdout = self.stdout_backup
		self.stdout_buff += self.stdout_capture_buff.getvalue()
		self.stdout_capture_buff = StringIO()
		#sys.__stdout__

	def log_stdout(self):
		for msg in self.stdout_buff.splitlines():
			if msg != "":
				msg_datetime = str(datetime.datetime.now())[:19]
				self.log_file.write(msg_datetime + ",STDOUT," + msg + "\n");
		self.stdout_buff = ""
		self.log_file.flush()

	# Need to do this after something changed, example the header size
	# This will reset the line buffer
	def set_dimensions(self):
		self.header_size = len(self.header.split('\n'))
		if not self.config['height'] or not self.config['width']:
			import os
			term_rows, term_columns = os.popen('stty size', 'r').read().split() # https://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
			if not self.config['height']:
				self.height = int(term_rows) - (self.header_size+self.height_offset)
			else:
				self.height = int(self.config['height']) - (self.header_size+self.height_offset)
			if not self.config['width']:
				self.width = int(term_columns)
			else:
				self.width = int(self.config['width'])
		else: # if both are set in the config (and both are not 0)
			self.height = int(self.config['height']) - (self.header_size+self.height_offset)
			self.width = int(self.config['width'])
		w_buff = "".ljust(self.width,'*')
		self.line_buffer = [w_buff]*self.height

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

	def print_header(self):
		if self.stdout_log == True:
			self.stdout_restore()
		header_chunks = self.header.split('\n')
		self.header_size = len(header_chunks)
		sys.stdout.write(chr(27) + "[0;0H")			# Go to top left
		for chunk in header_chunks:
			sys.stdout.write(chr(27) + "[K")		# erase line
			print chunk					# add new
		sys.stdout.write(chr(27) + "[s") 			# save cur pos
		if self.stdout_log == True:
			self.stdout_capture()

	def print_buffer(self):
		if self.stdout_log == True:
			self.stdout_restore()
		sys.stdout.write(chr(27) + "[{};0H".format(self.header_size+1))
		for l in self.line_buffer:
			if self.time_ago_format:			# if time_ago_format is set True in config
				l = self.redraw_time_ago(l)		# return time ago string
			print(chr(27) + "[K" + l) 			# erase line + add new
		if self.stdout_log == True:
			self.stdout_capture()

	def set_line_selected(self,line_num):
		self.selected_line = line_num
		line_num += self.header_size				# header size + offset need to make dynamic.
		sys.stdout.write(chr(27) + "[s") 			# save cur pos
		sys.stdout.write(chr(27) + "[{};0f".format(line_num))	# Go to linenum
		x = self.overrule_coloring(self.line_buffer[line_num-(self.header_size+self.height_offset)+1],self.color['PURPLE_HAZE'])
		sys.stdout.write(chr(27) + "[K")			# erase line
		print(x) 						# add new
		sys.stdout.write(chr(27) + "[u") 			# restore cur pos

	def unset_line_selected(self,line_num):
		if line_num != 0:
			line_num += self.header_size			# header size + offset need to make dynamic.
			sys.stdout.write(chr(27) + "[s")		# save cur pos
			sys.stdout.write(chr(27) + "[{};0H".format(line_num))# Go to linenum
			sys.stdout.write(chr(27) + "[K")		# erase line
			print(self.line_buffer[line_num-(self.header_size+self.height_offset)+1]) # add old
			sys.stdout.write(chr(27) + "[u")		# restore cur pos

	def overrule_coloring(self,msg,colors):
		# lots of assumptions here
		# need to check previous color format length.
		tmp_msg=msg
		for k,v in self.color.iteritems():
			if msg[1:8] == v:
				msg = chr(27) + colors + msg[8:];
		if tmp_msg == msg:
			msg = chr(27) + colors + msg + chr(27) + "[0m";
		return msg

	def add_coloring(self,msg,colors):
		msg = chr(27) + colors + msg;
		msg += chr(27) + "[0m"
		return msg

	def fill_str_size(self,msg,width):
		msg=msg.replace('\t','        ')
		return msg.ljust(width)

	def redraw_time_ago(self,line):
		if len(line) > 25:
			if not self.disable_color: offset = 10
			else: offset = 2
			_datetime = line[offset:19+offset]
			if _datetime == "*"*19:
				return line
			t_ago = self.time_ago(_datetime)
			line = line[0:offset] + t_ago + line[offset+19:]
		return line

	def time_ago(self,_datetime):
		time_ago_str = ""
		if isinstance(_datetime, basestring):
			m_datetime = datetime.datetime.strptime(_datetime, '%Y-%m-%d %H:%M:%S')
		elif isinstance(_datetime, datetime.datetime):
			m_datetime = _datetime
		_time_ago = datetime.datetime.now() - m_datetime
		hours = _time_ago.seconds / 3600
		if hours > 24:
			return _datetime
		if hours > 0:
			time_ago_str += "%02dh "%hours
		seconds = _time_ago.seconds
		if seconds < 2:
			return "just now.".ljust(19)
		minutes = _time_ago.seconds / 60
		if minutes  - (hours * 3600) > 0:
			time_ago_str += "%02dm "%minutes
		if seconds - (minutes * 60) > 0:
			time_ago_str += "%02ds "%(seconds - (minutes * 60))
		time_ago_str += "ago."
		return time_ago_str.rjust(19)
			

	def read_input_keys(self):
		k = []
		keys = os.read(sys.stdin.fileno(),1)
		while keys and len(keys) > 0:
			k.append(ord(keys[0]))
			keys = os.read(sys.stdin.fileno(),1)
		return k

	def key_pressed(self,pressed_key):
		if pressed_key in self.matched_keys:
			del self.matched_keys[self.matched_keys.index(pressed_key)]
			return True
		return False

	def match_keys(self,keys):
		pressed_keys = list()
		while keys:
			up = [27, 91, 65]
			down = [27, 91, 66]
			left= [27, 91, 68]
			right = [27, 91, 67]
			shift_tab = [27, 91, 90]
			match = False
			if len(keys) >= 3:
				print keys[:3]
				if keys[:3] == up:
					pressed_keys.append("up")
					keys.pop(0)
					keys.pop(0)
					keys.pop(0)
					match = True
				elif keys[:3] == down:
					pressed_keys.append("down")
					keys.pop(0)
					keys.pop(0)
					keys.pop(0)
					match = True
				elif keys[:3] == left:
					pressed_keys.append("left")
					keys.pop(0)
					keys.pop(0)
					keys.pop(0)
					match = True
				elif keys[:3] == right:
					pressed_keys.append("right")
					keys.pop(0)
					keys.pop(0)
					keys.pop(0)
					match = True
				elif keys[:3] == shift_tab:
					pressed_keys.append("shift_tab")
					keys.pop(0)
					keys.pop(0)
					keys.pop(0)
					match = True
			if len(keys) > 0 and not match:
				if keys[0] in range(97,122) or keys[0] in range(65,90):
					pressed_keys.append(chr(keys[0]))
					keys.pop(0)
				elif keys[0] == 9:
					pressed_keys.append("tab")
					keys.pop(0)
				elif keys[0] == 27:
					pressed_keys.append("esc")
					keys.pop(0)
				elif keys[0] == 32:
					pressed_keys.append(" ")
					keys.pop(0)
				elif keys[0] == 0:
					pressed_keys.append("ctrl_space")
					keys.pop(0)
				elif keys[0] == 10:
					pressed_keys.append("return")
					keys.pop(0)
				elif keys[0] == 127:
					pressed_keys.append("backspace")
					keys.pop(0)
				elif keys[0] in range(1,26):
					pressed_keys.append("ctrl_"+chr(keys[0]+64))
					keys.pop(0)
				else:
					pressed_keys.append(chr(keys[0]))
					keys.pop(0)
		self.matched_keys = pressed_keys

	def format_msg(self,msg_level,msg,msg_datetime):
		switch = { 'ERROR'	: self.color['RED_BLACK'],
			'INFO'		: self.color['GREEN_WHITE'],
			'NOTICE'	: self.color['BLUE_WHITE'],
			'DEBUG'		: self.color['YELLOW_BLACK'],
			'WARN'		: self.color['PURPLE_HAZE'],
		}
		msg = "[ " + msg_datetime + " " + msg_level.rjust(6) + " ] " + msg
		msg = self.fill_str_size(msg,self.width)
		if not self.disable_color:
			msg = self.add_coloring(msg,switch[msg_level])
		return msg

	def output(self,msg_level,msg,msg_datetime=None):
		switch = { 'ERROR'	: (self.log['log_error'],self.out['out_error']),
			'INFO'		: (self.log['log_info'],self.out['out_info']),
			'NOTICE'	: (self.log['log_notice'],self.out['out_notice']),
			'DEBUG'		: (self.log['log_debug'],self.out['out_debug']),
			'WARN'		: (self.log['log_warn'],self.out['out_warn']),
		}
		if not msg_datetime:
			msg_datetime = str(datetime.datetime.now())[:19]
		if switch[msg_level][0]:
			self.log_file.write(msg_datetime + "," + msg_level + "," + msg + "\n");
		if switch[msg_level][1]:
			msg = self.format_msg(msg_level,msg,msg_datetime)
			self.update_buffer(msg)
		self.log_file.flush()

	def do_style(self,string,style):
		#color = {'RED_BLACK'	: '[41;30m',
		#		'RED_WHITE'	: '[41;97m',
		#		'GREEN_BLACK'	: '[42;30m',
		#		'GREEN_WHITE'	: '[42;97m',
		#		'YELLOW_BLACK'	: '[43;30m',
		#		'YELLOW_WHITE'	: '[43;97m',
		#		'BLUE_BLACK'	: '[44;30m',
		#		'BLUE_WHITE'	: '[44;97m',
		#		'PURPLE_HAZE'	: '[45;97m',
		#	}
		# while 40-47 selected the background
		colors_bg = {	'BLACK'		: '40',
				'RED'		: '41',
				'GREEN'		: '42',
				'YELLOW'	: '43',
				'BLUE'		: '44',
				'MAGENTA'	: '45',
				'CYAN'		: '46',
				'WHITE'		: '47'}
		# The SGR parameters 30-37 selected the foreground color,
		colors_fg = {	'BLACK'		: '30',
				'RED'		: '31',
				'GREEN'		: '32',
				'YELLOW'	: '33',
				'BLUE'		: '34',
				'MAGENTA'	: '35',
				'CYAN'		: '36',
				'WHITE'		: '37'}
		_style = {	'BOLD'		: '1',
				'BRIGHT'	: '1',
				'NORMAL'	: '22',
			}
		seq = chr(27) + "["
		counter = 0
		if 'txt' in style:
			seq += _style[style['txt']]
			counter += 1
		if 'fg' in style:
			if counter > 0: seq += ";"
			seq += colors_fg[style['fg']]
			counter += 1
		if 'bg' in style:
			if counter > 0: seq += ";"
			seq += colors_bg[style['bg']]
		seq += "m"
		#seq = chr(27) + "[45;97m"
		return seq + string + chr(27) + "[0m" # need to get previous style somehow instead of [0m (reset)
			
	def strip_ansi(self,string):
		pattern_ansi = re.compile("(\x1b\[[;0-9]+[a-z])", re.IGNORECASE).sub
		return pattern_ansi('',string)

class menu(object):
	def __init__(self,out,width,items=list(),subitems=list()):
		self.items = items		# list ['name0','name1','name2']
		self.subitems = subitems	# list [ [patent_id0,name0], [..] ]

class label(object):
	def __init__(self,width,x,y):
		self.width = width

class input_field(object):
	def __init__(self,out,width,x,y):
		self.width = width
		self.selected = False
		self.x = x
		self.y = y
		self.out = out
		self.pos = 0
		self.input_txt = ""
		self.last_updated = datetime.datetime.now()
		self.print_field()

	def print_field(self):
		if self.out.stdout_log == True:
			out.stdout_restore()
		field = self.input_txt
		if self.selected == True:
			now = datetime.datetime.now()
			field_len = len(field)
			if self.pos > field_len:
				self.pos = field_len
			elif self.pos < 0:
				self.pos = 0
			if (now - self.last_updated) > datetime.timedelta(seconds=1):
				field = field[:self.pos] + str(chr(124)) + field[self.pos:]
				if (now - self.last_updated) > datetime.timedelta(seconds=3):
					self.last_updated = now
			else:
				field = field[:self.pos] + " " + field[self.pos:]
			field = self.out.do_style(field.ljust(self.width),{'bg':'WHITE','fg':'RED','txt':'BOLD'})
		else:
			field = field.ljust(self.width)
		sys.stdout.write(chr(27) + "[" + str(self.y+self.out.header_size+self.out.height_offset) + ";" + str(self.x+1) + "H" + field)
		if self.out.stdout_log == True:
			out.stdout_capture()

	def add_text(self,text):
		if len(self.input_txt) < self.width-1:# -1 for the blinker
			#self.input_txt += text
			self.input_txt = self.input_txt[:self.pos] + text + self.input_txt[self.pos:]
			self.pos += len(text)

	def backspace(self):
		self.input_txt = self.input_txt[:len(self.input_txt)-1]

class table(object):
	def __init__(self,panel,columns):
		self.width=0
		self.columns = columns
		self.panel = panel
		self.print_column_names = True
		#self.buffer = list()
		self.col_separator = "  "
		self.selected_row = 0
		col_names = ""
		for name, args in columns.iteritems():
			self.width += args[0]
			self.width += len(self.col_separator)
			col_names += name.ljust(self.columns[name][0]) + self.col_separator 
		if self.print_column_names == True:
			self.panel.header = chr(27) + "[1m" + col_names + chr(27) + "[0m"
		if panel.width == 0:#auto
			panel.width = self.width
		self.max_width = panel.width

	def update_column(self,row_num,column_name,data):
		# TODO check if row_num exists, else create it?
		# TODO check if data isn't longer than column size, else split into multiple lines?
		column_offset = 0
		#sep_lenght = len(self.col_separator)
		if column_name in self.columns:
			column_length = self.columns[column_name][0]
			for name, length in self.columns.iteritems():
				if name == column_name:
					break
				column_offset += length[0]
				#column_offset += sep_lenght
		self.panel.update_buffer(data.ljust(column_length),row_num,column_offset)
		
	def update_table(self,columns,row_num=-1):
		buf = ""
		for name, args in columns.iteritems():
			buf += str(args[1]).ljust(int(args[0])) + self.col_separator#add value and ljust to column size + add the column separator
		self.panel.update_buffer(buf,row_num)

	def update_row_style(self,row_num):
		self.panel.update_buffer(buf,row_num)

class panel(object):
	def __init__(self,out,width,height,x,y,scroll_buffer_size=0):
		if x+width > out.width-1 or y+height > out.height:
			print "Panel doesnt fit on screen. height:{} width:{} x:{} y:{}".format(height,width,x,y)
			sys.exit()
		self.width = width
		self.height = height
		self.header = None
		self.header_size = 0
		self.x = x
		self.y = y
		self.out = out
		sys.stdout.write(chr(27) + "[?25l") # hide cursor

		if scroll_buffer_size > 0:
			self.scroll_buffer = [""] # TODO need to remove the normal buffer and merge with scroll buffer (rm buffer, mv scroll_buffer buffer, and do check if scroll buffer is set then it can override max height.)
			self.scroll_pos = 0
			self.scroll_buffer_size = scroll_buffer_size
			self.scroll_buffer_count = 0
		self.buffer_count = 0
		self.buffer = [""]
		self.selected_line = -1
		self.print_filter = ""
		self.reverse_output = False

		self.update_buffer()

		self.selected = False

	"""
		TODO
			massive cleanup :-)
			remove most -1's (trace them back)
			data columns (tables)
			check boxes
			select boxes
			multiline input
			update output_handler.print_buffer (so it can change colomn specific too, so we don't have to refresh the whole line.)
			scroll-bar
			borders
			color attr (bg,fg) (not in buffer, but direct on stdout.write)
			select row, column (and get selected data so we can pass it to whatever)
			rename all variables (of all classes) with the same purpose to the same name
			make some global functions like hide_cursor, show_cursor etc
				set attributes on rows, columns, header
			set panel and window sizes in percentage (option)
			sort on column
	"""
	def fit_string(self,string):
		chunks = list()
		num = int(len(string)/self.width) + (len(string)%self.width > 0)
		for part in range(num,-1,-1):
			chunks.append( string[(part*(self.width)):(part+1)*self.width] )
		return chunks

	def update_buffer(self,buf="",line_num=-1,column_offset=0):
		if len(buf) > self.width:
			# We need to cut :-)
			chunks = self.fit_string(buf)
			for chunk in chunks:
				self.update_buffer(chunk,line_num)
			return
		if hasattr(self, 'scroll_buffer'):
			self.update_scroll_buffer(buf,line_num,column_offset)
		elif isinstance(buf, basestring) and line_num > -1 and line_num < self.height:#buf is just a string (we assume)
			self.out.line_buffer[line_num+self.y] = self.out.line_buffer[line_num+self.y][:self.x+column_offset] + buf + self.out.line_buffer[line_num+self.y][self.width+self.x-column_offset:self.out.width]
		elif isinstance(buf, basestring) and line_num == -1:
			if self.buffer_count-1 == self.height:
				self.buffer.pop(self.height-1)
			else:
				self.buffer_count += 1
			if self.buffer == [""]:
				if buf != self.out.fill_str_size("",self.width):# buffer init (first update)
					self.buffer = [buf]
			if self.reverse_output == False:
				self.buffer += [self.out.fill_str_size(buf,self.width)]
			else:
				self.buffer = [self.out.fill_str_size(buf,self.width)] + self.buffer

	def update_scroll_buffer(self,buf="",line_num=-1,column_offset=0):
		if isinstance(buf, basestring) and line_num == -1:
			if len(self.scroll_buffer) == self.scroll_buffer_size:
				self.scroll_buffer.pop(self.scroll_buffer_size-1)
			else:
				self.scroll_buffer_count += 1
			if self.scroll_buffer == [""]:
				if buf != self.out.fill_str_size("",self.width):# scroll_buffer init (first update)
					self.scroll_buffer = [buf]
			else:
				if self.reverse_output == False:
					self.scroll_buffer += [self.out.fill_str_size(buf,self.width)]
				else:
					self.scroll_buffer = [self.out.fill_str_size(buf,self.width)] + self.scroll_buffer
		elif line_num > -1 and line_num < self.scroll_buffer_size:
			if line_num > len(self.scroll_buffer) and line_num < self.scroll_buffer_size:
				for i in range( line_num - len(self.scroll_buffer)+1 ):
					self.scroll_buffer.append("-".ljust(self.width))
			if column_offset > 0:
				buf_len = len(self.out.strip_ansi(buf))# without ansi
				self.scroll_buffer[line_num] = self.scroll_buffer[line_num][:column_offset] + buf + self.scroll_buffer[line_num][(column_offset+buf_len):]
			else:
				self.scroll_buffer[line_num] = self.out.fill_str_size(buf,self.width)

	def print_header(self):
		if self.out.stdout_log == True:
			out.stdout_restore()
		line_num = 0
		sys.stdout.write(chr(27) + "[s")		# save cur pos
		for h in self.header.split('\n'):		# multiline
			sys.stdout.write(chr(27) + "[" + str(line_num-1+self.y+self.out.header_size+self.out.height_offset) + ";" + str(self.x+1) + "H" + h.ljust(self.width))
			line_num += 1
			self.y += 1
			self.height -= 1
		sys.stdout.write(chr(27) + "[u")		# restore
		if self.out.stdout_log == True:
			out.stdout_capture()

	def print_buffer(self,line_num=-1):
		if self.out.stdout_log == True:
			out.stdout_restore()
		sys.stdout.write(chr(27) + "[s")
		add_front = ""
		add_end = ""
		line = ""
		selected_style = {'bg':'WHITE','fg':'RED'}
		selected_row_style = {'bg':'RED','fg':'WHITE'}

		if self.reverse_output == False:
			_range = range(0,self.height-1)
		else:
			_range = range(self.height-1,-1,-1)
		if hasattr(self, 'scroll_buffer'):
			for line_num in _range:
				if line_num < self.scroll_buffer_count-1:
					pos = line_num+self.scroll_pos
					if line_num > (self.scroll_buffer_count-1 - self.scroll_pos):
						continue # end of buffer, continue
					line = self.scroll_buffer[pos]
				else:
					line = self.out.fill_str_size("",self.width)
				if self.selected == True:
					style = selected_style
					if (self.selected_line >-1 and self.selected_line == line_num):
						style = selected_row_style
						
					line = self.out.do_style(line.ljust(self.width),style)
				if len(self.print_filter) > 0:
					if self.print_filter not in line:
						sys.stdout.write(chr(27) + "[K")
						continue
				sys.stdout.write(chr(27) + "[" + str(line_num-1+self.y+self.out.header_size+self.out.height_offset) + ";" + str(self.x+1) + "H" + line)
		elif line_num == -1:
			for line_num in _range:
				if line_num < self.buffer_count-1: # check if tuple exists
					line = self.buffer[line_num]
				else: # else fill with nothing
					line = "".ljust(self.width,'.')
				if self.selected == True:
					style = selected_style
					if (self.selected_line >-1 and self.selected_line == line_num):
						style = selected_row_style
					line = self.out.do_style(line.ljust(self.width),style)
				if len(self.print_filter) > 0:
					if self.print_filter not in line:
						sys.stdout.write(chr(27) + "[K")
						continue
				sys.stdout.write(chr(27) + "[" + str(line_num-1+self.y+self.out.header_size+self.out.height_offset) + ";" + str(self.x+1) + "H" + line)
		else: # re-print only one line (in the panel)
			line = self.out.line_buffer[line_num+self.y][self.x:self.x+self.width]
			if self.selected == True:
				line = self.out.do_style(line.ljust(self.width),style)

			sys.stdout.write(chr(27) + "[" + str(line_num-1+self.y+self.out.header_size+self.out.height_offset) + ";" + str(self.x+1) + "H" + line)
		sys.stdout.write(chr(27) + "[u") # restore cur pos
		if self.out.stdout_log == True:
			out.stdout_capture()
