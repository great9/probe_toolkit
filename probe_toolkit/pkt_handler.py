import struct
import utils
"""
	Sources
	https://docs.python.org/2/library/struct.html
	https://github.com/aircrack-ng/aircrack-ng/blob/master/src/pcap.h
	https://stackoverflow.com/questions/8815592/convert-bytes-to-bits-in-python
	https://www.technologyuk.net/telecommunications/networks/wireless-networks.shtml
	Wireshark itself.

TCPDump pcap (802.11 probe-req) unpacker
"""

class pkt_handler(object):
	def __init__(self,filename=None):
		self.offset = 0
		self.skip_truncated = True
		self.buffer_size = 1024 * 4
		self.read_header = False
		self.counter = 0

		self.packets = list()

		self.header = [0,0,0,0]

		if filename != None:
			self.read_pcap_file(filename)
		else:
			self.buffer = ''

	def __enter__(self):
		return self

	def __exit__(self):
		print self.counter

	def new_data(self,data):#hook
		self.add_to_buffer(data)
		if self.read_header == False:
			print self.read_global_header()
			self.read_header = True
		while True:
			if len(self.buffer) >= 16 and self.header == [0,0,0,0]: # we can read the header, and it needs to be read.
				self.header = self.read_rec_packet_header()
				if self.header == False: # if it fails somehow
					self.header = [0,0,0,0]
					print "breaking, header is false"
					break
				#print "New packet, header: {}".format(self.header)

			# If we already have the header now need to unpack the payload
			if len(self.buffer) >= self.header[2] and self.header[2] > 24:
				self.read_packet()
				self.counter += 1
				self.header = [0,0,0,0] # reset header, closing this packet
			else:
				#print "breaking, not enough data"
				break

	def add_to_buffer(self,data):
		self.buffer += data

	def get_from_buffer(self,size):# gets and deletes from buffer
		data = self.buffer[:size]
		self.buffer = self.buffer[size:]
		return data

	def read_packet(self):
		payload = self.get_from_buffer(self.header[2])

		if self.header[3] > self.header[2] and self.skip_truncated == True:
			#if _DEBUG_: print "Truncated, skipping."
			print "Truncated, skipping"
			return False
		try:
			radiotap, present_flags = self.read_radiotap_header(payload[0:8])
			payload_offset = radiotap[2]
			radiotap = self.read_radiotap(payload[8:(radiotap[2])],present_flags)
		except:
			print "Guessing PCAP file is corrupted, breaking."
			print "  PS: This does not mean nothing is done."
			return False

		if payload_offset <= len(payload):
			frame_ctrl = self.read_frame_ctrl(payload[payload_offset:payload_offset+2])
			if frame_ctrl['subtype'] == 4:
				probe_request_frame = self.read_probe_request_frame(payload[payload_offset+2:payload_offset+24])
				source_addr = probe_request_frame['source_addr'][:6]
				payload_offset += 24# for the probe request frame
				tags = self.read_wireless_mgt_frame(payload[payload_offset:])
		else:
			print "Something is wrong..."
			return False

		self.packets.append([self.header,radiotap,probe_request_frame,tags])

	def read_pcap_file(self,filename):
		with open(pcap_file, mode='rb') as file:
			file_content = file.read()
			length = len(file_content)
			file_header = read_global_header(file_content,self.offset)
			#if _DEBUG_: print "self.offset: {}\tPCAP_FILE_HEADER: {}".format(self.offset,file_header[1])
			#self.offset = file_header[0]

			while self.offset < length:
				self.read_packet(packet,file_content)


	"""Global Header - file header
	typedef struct pcap_hdr_s {
		guint32 magic_number;   /* magic number */
		guint16 version_major;  /* major version number */
		guint16 version_minor;  /* minor version number */
		gint32  thiszone;       /* GMT to local correction */
		guint32 sigfigs;        /* accuracy of timestamps */
		guint32 snaplen;        /* max length of captured packets, in octets */
		guint32 network;        /* data link type */
	} pcap_hdr_t;"""
	def read_global_header(self):
		pcap_file_header = struct.unpack("I H H i I I I", self.get_from_buffer(24))
		return pcap_file_header

	"""Record (Packet) Header
	typedef struct pcaprec_hdr_s {
		guint32 ts_sec;         /* timestamp seconds */
		guint32 ts_usec;        /* timestamp microseconds */
		guint32 incl_len;       /* number of octets of packet saved in file */
		guint32 orig_len;       /* actual length of packet */
	} pcaprec_hdr_t;"""
	def read_rec_packet_header(self):
		try:
			pcap_rec_header = struct.unpack("I I I I", self.get_from_buffer(16))
		except:
			return False
		return pcap_rec_header

	def read_payload(self,data,lent):
		return data[self.offset:(self.offset+lent)]

	def uchar_tuple_to_bits(self,utuple):
		if isinstance(utuple, tuple):
			buf = ''
			for uc in utuple:
				uc = self.uchar_to_bits(uc)
				if uc != None:
					buf = uc + buf
			return buf

	def read_frame_ctrl(self,data):
		fc = struct.unpack("2B", data)

		"""	2bits	protocol version
			2bits	type
			4bits	subtype"""
		bits1 = uchar_to_bits(fc[0])

		"""	1bit	to ds
			1bit	from ds
			1bit	more flag
			1bit	retry
			1bit	power management
			1bit	more data
			1bit	WEP
			1bit	other"""
		bits2 = uchar_to_bits(fc[1])

		fc = {	'proto_v'	: int(bits1[6:8],2),
			'type'		: int(bits1[4:6],2),
			'subtype'	: int(bits1[0:4],2),
			'to_ds'		: int(bits2[0:1],2),
			'from_ds'	: int(bits2[1:2],2),
			'more_flag'	: int(bits2[2:3],2),
			'retry'		: int(bits2[3:4],2),
			'pwdr_mgt'	: int(bits2[4:5],2),
			'more_data'	: int(bits2[5:6],2),
			'wep'		: int(bits2[6:7],2),
			'other'		: int(bits2[7:8],2)
		}
		return fc

	def read_probe_request_frame(self,data):
		probe_request_frame = {	'duration'		: struct.unpack("h", data[0:2]),
					'destination_addr'	: char_to_hex(struct.unpack("cccccc", data[2:8])),
					'source_addr'		: char_to_hex(struct.unpack("cccccc", data[8:14])),
					'bssid'			: char_to_hex(struct.unpack("cccccc", data[14:20])),
					'mask'			: struct.unpack("2B", data[20:22]),
					}
		return probe_request_frame

	def read_wireless_mgt_frame(self,data):
		offset = 0
		tags = dict()
		counter = 0
		while offset+2 < len(data): # the +2 is for future values, if < than that there is no need to read.
			tag_num, tag_len, tag_val = self.read_80211_frame_tags(data,offset)
			offset += tag_len+2
			str_num = "{}{}".format(str(counter).rjust(6,'0'),str(tag_num))
			tags.update( { str_num : { 'len' : tag_len, 'val' : tag_val } } )
			counter += 1
		return tags

	def read_radiotap_header(self,data):
		"""	revision	u_int8_t		1 byte		B
			pad		u_int8_t		1 byte		B
			length		u_int16_t		2 byte		H
			present-flags	u_int32_t		4 byte bitmask	BBBB
			.. depends on the flags (pad will be 1 with no present flags)
		"""
		pcap_radiotap_hdr = struct.unpack("B B H 4c", data)

		present_flags = self.uchar_tuple_to_bits(pcap_radiotap_hdr[3:7])

		"""	0	1	EXT
			1	1	Vendor NS next
			2	1	Radiotap NS next
			3	7	Reversed
			10	1	VHT information
			11	1	A-MPDU status
			12	1	HT Information
			13	1	Channel+
				3 pad
			17	1	RX flags			2 byte bitmask
			18	1	dB Antenna Noise
			19	1	dB Antenna Signal
			20	1	Antenna				1 byte int
			21	1 	dBm TX Power
			22	1	dB TX Attenuation
			23	1	TX Attenuation
			24	1	Lock Quality
			25	1	dBm Antenna Noise
			26	1	dBm Antenna Signal		1 byte	unsigned int u_int8_t
			27	1	FHSS
			28	1	Channel				2 byte int + 2 byte channel type bitmask
			29	1	Rate				1 byte 			* 512 kbps = rate in mbps
			30	1	Flags				1 byte (bitmask)
			31	1	TSFT"""
		return pcap_radiotap_hdr, present_flags

	def read_radiotap(self,data,present_flags):
		flags_data = { 17 : ['BB'],
				20 : ['B'],
				25 : ['b'],
				26 : ['b'],
				28 : ['h cc'],
				29 : ['B'],
				30 : ['B'],
				31 : ['q'],
			}
		length = len(present_flags)
		for i in reversed(range(0,length)):
			if int(present_flags[i]) == 1 and i in flags_data:
				fmt_size = struct.calcsize(flags_data[i][0])
				flags_data[i].append( struct.unpack(flags_data[i][0], data[:fmt_size]) )
				if len(data) != fmt_size:
					data = data[fmt_size:]# -1 'cause we start at 0 and it calculates at 1
		return flags_data

	def read_80211_frame_tags(self,data,offset=0):
		if len(data)-(offset+2) < 0:
			return False
		tag_num = struct.unpack("B", data[offset:(offset+1)])[0]
		offset += 1
		tag_len = struct.unpack("B", data[offset:(offset+1)])[0]
		offset += 1

		if tag_len > (len(data) - offset):
			tag_val = "__TRUNCATED__"
		elif tag_len == 0:
			tag_val = ""
		else:
			tag_val = data[offset:(offset+tag_len)]
		offset += tag_len
		return tag_num, tag_len, tag_val
