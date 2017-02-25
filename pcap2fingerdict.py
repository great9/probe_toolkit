#!/usr/bin/python
# Sources:
#	https://docs.python.org/2/library/struct.html
#	https://github.com/aircrack-ng/aircrack-ng/blob/master/src/pcap.h
#	https://stackoverflow.com/questions/8815592/convert-bytes-to-bits-in-python
#	https://www.technologyuk.net/telecommunications/networks/wireless-networks.shtml
#	Wireshark itself.
import struct
from bitarray import bitarray
import binascii
import string
import random
import hashlib
import sys

"""
CONFIG START
TODO Need to make some checks here.
"""
# if set True it will print some things I used for debugging the script.
_DEBUG_ = False

# Only save fingerprint if a minimum of x devices share the same print.
# This will also filter out device unique fingerprints, like for example
# Nintendo DS will send probe requests with personal data.
min_dev_count = 5
"""
CONFIG END
"""

args = sys.argv
if args[1] != "":
	pcap_file = args[1]
else:
	print "Specify a valid pcap file as the first argument"
	sys.exit()
if args[2] != "":
	fp_file = args[2]
else:
	print "Specify a valid output file as the second argument"
	sys.exit()

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
def read_global_header(data,offset):
	pcap_file_header = struct.unpack("I H H i I I I", fileContent[offset:(offset+24)])
	offset += 24
	return offset, pcap_file_header

"""Record (Packet) Header
typedef struct pcaprec_hdr_s {
        guint32 ts_sec;         /* timestamp seconds */
        guint32 ts_usec;        /* timestamp microseconds */
        guint32 incl_len;       /* number of octets of packet saved in file */
        guint32 orig_len;       /* actual length of packet */
} pcaprec_hdr_t;"""
def read_rec_packet_header(data,offset):
	pcap_rec_header = struct.unpack("I I I I", fileContent[offset:(offset+16)])
	offset += 16
	return offset, pcap_rec_header

def read_payload(data,offset,lent):
	return data[offset:(offset+lent)]

def uchar_tuple_to_bits(utuple):
	if isinstance(utuple, tuple):
		buf = ''
		for uc in utuple:
			uc = uchar_to_bits(uc)
			if uc != None:
				buf = uc + buf
		return buf

def uchar_to_bits(uchar):
	if isinstance(uchar, int):
		bits = bin(uchar)[2:]
	elif len(uchar)==1:
		bits = bin(ord(uchar))[2:] 	# cause the first two are 0b
	for x in range(len(bits),8):		# 1 uchar should return 8 bits
		bits = '0{}'.format(bits)
	return bits

def extract_bits(bits,lbits):
	extracted = bits[0:lbits]
	leftover = bits[lbits:]
	return leftover, extracted

def reverse_bits(bits):
	out = ''
	length = len(bits) -1
	for x in range(0,length+1):
		out += bits[(length-x)]
	return out

def read_frame_ctrl(data):
	if len(data) == 2:
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

def read_probe_request_frame(data):
	probe_request_frame = {	'duration'		: struct.unpack("h", data[0:2]),
				'destination_addr'	: char_to_hex(struct.unpack("cccccc", data[2:8])),
				'source_addr'		: char_to_hex(struct.unpack("cccccc", data[8:14])),
				'bssid'			: char_to_hex(struct.unpack("cccccc", data[14:20])),
				'mask'			: struct.unpack("2B", data[20:22]),
				}
	return probe_request_frame

def char_to_hex(char):
	buf = ''
	for x in char:
		buf += hex(ord(x))[2:].rjust(2,'0')
	return buf

def read_wireless_mgt_frame(data):
	offset = 0
	big_list = dict()
	counter = 0
	while offset+2 < len(data): # the +2 is for future values, if < than that there is no need to read.
		tag_num, tag_len, tag_val = read_80211_frame_tags(data,offset)
		offset += tag_len+2
		str_num = "{}{}".format(str(counter).rjust(6,'0'),str(tag_num))
		big_list.update( { str_num : { 'len' : tag_len, 'val' : tag_val } } )
		counter += 1
	return big_list

def read_radiotap_header(data):
	"""	revision	u_int8_t		1 byte		B
		pad		u_int8_t		1 byte		B
		length		u_int16_t		2 byte		H
		present-flags	u_int32_t		4 byte bitmask	BBBB
		.. depends on the flags (pad will be 1 with no present flags)
	"""
	if len(data) != 8:
		return False
	pcap_radiotap_hdr = struct.unpack("B B H 4c", data)

	present_flags = uchar_tuple_to_bits(pcap_radiotap_hdr[3:7])

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
		26	1	dBm Antenna Signal		1 byte	unsigned int
		27	1	FHSS
		28	1	Channel				2 byte int + 2 byte channel type bitmask
		29	1	Rate				1 byte 			* 512 kbps = rate in mbps
		30	1	Flags				1 byte (bitmask)
		31	1	TSFT"""
	return pcap_radiotap_hdr, present_flags

def read_80211_frame_tags(data,offset=0):
	if len(data)-(offset+2) < 0:
		return False
	tag_num = struct.unpack("B", data[offset:(offset+1)])[0]
	offset += 1
	tag_len = struct.unpack("B", data[offset:(offset+1)])[0]
	offset += 1

	if tag_len > (len(data) - offset):
		tag_val = "__TRUNCATED__"
	elif tag_len == 0:
		tag_val = "__BROADCAST__"
	else:
		tag_val = data[offset:(offset+tag_len)]
	offset += tag_len
	return tag_num, tag_len, tag_val

def dump_fingerprints(fingerprints,filename):
	buf = "fingerprints = {\n"
	counter = 0
	for k,v in fingerprints.iteritems():
		device_count = 0
		for oui in v[1]:
			device_count += 1
		if device_count >= min_dev_count:# min_dev_count (Minimal device count) is global defined.
			name = v[0]
			ouis = "[ "
			tags = "[ "
			for oui in v[1]:
				ouis += "'{}',".format(oui)
			for tag in v[2]:
				tags += "{},".format(tag)
			ouis = ouis[0:-1] + " ]"
			tags = tags[0:-1] + " ]"
			buf += " \t\"{}\" : [ \n\t\t\"{}\",\n\t\t{},\n\t\t{} \n\t],\n".format(k,name,ouis,tags)
			counter += 1
	buf += "}"
	with open(filename, mode='w') as file:
		file.write(buf)
	file.close()
	return counter

def read_fingerprints_dump(filename):
	content = dict()
	try:
		execfile(filename, content)
	except:
		return dict()
	if 'fingerprints' in content:
		return content['fingerprints']
	else:
		print "New file"
		return dict()

fingerprint = read_fingerprints_dump(fp_file)
fp_count = len(fingerprint)

print "{} fingerprints in file {}".format(fp_count,fp_file)

with open(pcap_file, mode='rb') as file: # b is important -> binary
	offset = 0
	fileContent = file.read()
	length = len(fileContent)

	file_header = read_global_header(fileContent,offset)
	if _DEBUG_: print "OFFSET: {}\tPCAP_FILE_HEADER: {}".format(offset,file_header[1])
	offset = file_header[0]

	while offset < length:
		header = read_rec_packet_header(fileContent,offset)
		offset = header[0]

		payload = read_payload(fileContent,offset,header[1][2])
		offset += header[1][2]

		if header[1][3] > header[1][2]:
			if _DEBUG_: print "Truncated, skipping."
			continue
		try:
			radiotap, present_flags = read_radiotap_header(payload[0:8])
			payload_offset = radiotap[2]
		except:
			print "Guessing PCAP file is corrupted, breaking."
			print "  PS: This does not mean nothing is done."
			break
		tags_string = ""
		buf = list()
		frame_ctrl = read_frame_ctrl(payload[payload_offset:payload_offset+2])
		if frame_ctrl['subtype'] == 4:
			probe_request_frame = read_probe_request_frame(payload[payload_offset+2:payload_offset+24])
			source_addr = probe_request_frame['source_addr'][:6]
			payload_offset += 24# for the probe request frame

			tags = read_wireless_mgt_frame(payload[payload_offset:])
			if tags:
				for tag_id, tag in tags.iteritems():
					if(str(tag_id[6:]) != '0'):
						buf.append([str(tag_id[6:]),char_to_hex(str(tag['val']))])
						tags_string += str(tag_id[6:])
						tags_string += "|"
						tags_string += char_to_hex(str(tag['val']))
				_hash = hashlib.md5()
				_hash.update(tags_string)
				tags_hash = str(_hash.hexdigest())
				if tags_hash not in fingerprint:
					fingerprint.update( { tags_hash : ["_UNKNOWN_",[source_addr],buf] } )
				elif source_addr not in fingerprint[tags_hash][1]:
					fingerprint[tags_hash][1].append(source_addr)
		else:
			continue# 'cause we don't have functions for other frame types (yet, who knows).
new_fp_count = dump_fingerprints(fingerprint,fp_file)
new_fp_count -= fp_count
print "New fingerprints: {}".format(new_fp_count)
print "Dumped fingerprints to {}".format(fp_file)
