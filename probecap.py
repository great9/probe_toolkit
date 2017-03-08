#!/usr/bin/env python
import os			# needed to get terminal window sizes
import datetime
import time
import re
import subprocess as sub
from probe_toolkit.db_handler import db_handler
from probe_toolkit.output_handler import output_handler
from probe_toolkit.pkt_handler import pkt_handler
from probe_toolkit.fingerdict import fingerdict
from probe_toolkit.periodical import periodical
from probe_toolkit import utils

from fcntl import fcntl, F_GETFL, F_SETFL
from os import O_NONBLOCK, read

def set_match_value(value, match_id = 0, default = "NOT_SET"):
		if value:
			value = value.group(match_id)
		else:
			value = default
		return value

def main():
	print_buffer("probe_toolkit")

if __name__ == "__main__":
	config = {}
	try:
		execfile("probecap.conf", config)
	except:
		print """No config file found or error, exiting.
Please be sure you have a valid probe_toolkit.conf in this dir."""
		sys.exit(2)
	
	out = output_handler(config['output'])
	out.header += """datetime                       freq  std  ant   signal    bssid              dst                src                rate      essid
-----------------------------  ----  ---  -     ---       -----------------  -----------------  -----------------  --------  --------------------------------"""
	out.print_header()
	"""
		tcpdump -i $wifi_if -e -s 256 type mgt subtype probe-req
		-i								interface
		-l								make stdout line buffered
		-e								print link header, else it won't print adresses
		-s								snaplength
		type mgt subtype probe-req					probe filter options
	"""
	if 'fingerdict' not in config['general']:
		config['general']['fingerdict'] = False
	if 'dump' not in config['general']:
		config['general']['dump'] = False
	if 'dumpfile' not in config['general']:
		config['general']['dump'] = 'probe.dump'
	if 'use_sudo' not in config['general']:
		config['general']['use_sudo'] = False
	#print type(config['general']['cap_size'])
	if 'cap_size' not in config['general']:
		config['general']['cap_size'] = 256
	elif not isinstance(config['general']['cap_size'], int):
		config['general']['cap_size'] = 256
	config['general']['cap_size'] = str(config['general']['cap_size'])
	"""if config['general']['use_sudo'] == True:
		if config['general']['dump'] == True:
			o = sub.Popen(('sudo', 'tcpdump', '-i', config['general']['mon_if'], '-U', '-s', config['general']['cap_size'], 'type mgt subtype probe-req', '-w', '-'), stdout=sub.PIPE)
			l = sub.Popen(('tee', config['general']['dumpfile']), stdin=o.stdout, stdout=sub.PIPE)
			p = sub.Popen(('tcpdump', '-l', '-e', '-r', '-'), stdin=l.stdout, stdout=sub.PIPE)
		else:
			p = sub.Popen(('sudo', 'tcpdump', '-i', config['general']['mon_if'], '-l', '-e', '-s', config['general']['cap_size'], 'type mgt subtype probe-req'), stdout=sub.PIPE)
	else:
		if config['general']['dump'] == True:
			p = sub.Popen(('tcpdump', '-i', config['general']['mon_if'], '-U', '-s', config['general']['cap_size'], 'type mgt subtype probe-req', '-w', '-'), stdout=sub.PIPE)
			#l = sub.Popen(('tee', config['general']['dumpfile']), stdin=o.stdout, stdout=sub.PIPE)
			#p = sub.Popen(('tcpdump', '-l', '-e', '-r', '-'), stdin=l.stdout, stdout=sub.PIPE)
		else:
			p = sub.Popen(('tcpdump', '-i', config['general']['mon_if'], '-l', '-e', '-s', config['general']['cap_size'], 'type mgt subtype probe-req'), stdout=sub.PIPE)
	"""
	p = sub.Popen(('sudo', 'tcpdump', '-i', config['general']['mon_if'], '-U', '-s', config['general']['cap_size'], 'type mgt subtype probe-req', '-w', '-'), stdout=sub.PIPE)
	#fcntl_flags = fcntl(p.stdout, F_GETFL)
	#fcntl(p.stdout, F_SETFL, fcntl_flags | O_NONBLOCK)


	db = db_handler(config['db_conf'])
	pkt = pkt_handler()
	if config['general']['fingerdict'] == True:
		fd = fingerdict()
		fd.read_fingerprints_dump('fingerprints_dict.py')
	count = 0
	try:
		previous = ""
		
		timer_output = periodical(0.5)
		
		#for row in iter(p.stdout.readline, b''):
		while True:
			try:
				data = read(p.stdout.fileno(),32)
				pkt.new_data(data)
				time.sleep(0.1)
			except:
				time.sleep(0.1)
				continue

			for packet in pkt.packets:
				"""
					0 header
						0	timestamp seconds
						1	timestamp miliseconds
						2	number of octets of packet saved in file
						3	actual length of packet

					1 radiotap
						0	1	EXT
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
						31	1	TSFT

							0	the fmt used
							1	values extracted

								0 default value
					2 probe req
						'duration'
						'destination_addr'
						'source_addr'
						'bssid'
						'mask'

					3 tags
				"""

				_datetime = datetime.datetime.fromtimestamp(int(packet[0][0])).strftime('%Y-%m-%d %H:%M:%S')
				_essid = packet[3]['0000000']['val']
				#for tag_id, tag in packet[3].iteritems():
				#	if tag_id[6:] == '0':
				#		_essid = tag['val']

				_src = utils.fancy_hex(packet[2]['source_addr'])
				_dst = utils.fancy_hex(packet[2]['destination_addr'])
				_bssid = utils.fancy_hex(packet[2]['bssid'])
				try:# got a index error on _rate
					_signal = str(packet[1][26][1][0])
					_freq = packet[1][28][1][0]
					_rate = packet[1][29][1][0] * 0.5# multiplier 512kbps
					_ant = packet[1][20][1][0]
					_std = utils.char_to_hex(packet[1][28][1][1])
				except IndexError:
					out.output("ERROR",IndexError)
					out.output("ERROR",packet)
					out.output("ERROR","")

				label = ""
				if config['general']['fingerdict'] == True:
					# Need to make this threaded for faster results.
					label, tags_hash = fd.update_finterprints(packet[3],packet[2]['source_addr'])

					set_label = True
					match_src = '12:34:56:78:9A:BC'
					new_label = 'Test Label'

					if set_label == True and match_src == _src:
						fd.update_label(tags_hash,new_label)
						#set_label = False

				pkt.packets.remove(packet) # else it will loop over and over again.

				if len(_essid) >32:
					out.output("WARN","SSID is too long. SSID: \"{}\", Line: \"{}\"".format(_essid,row))
					continue

				level = "NOTICE"
				db.insert_probe_id(_src)
				if db.update_probe_log_ap_last_seen(_src,_bssid,_essid,_datetime) == False: # if this failes then; insert ..
					if db.insert_probe_log_ap(_src,_dst,_bssid,_datetime,_datetime,_essid):
						level = "INFO" # cause it's a new entry :-)
				if previous == (_datetime+""+_src+""+_signal):
					out.output("DEBUG","Skipped duplicate input: {}".format(previous))
				else:
					db.insert_probe_log_signal(_datetime,_src,_signal)
				if db.update_probe_log_fingerdict_last_seen(_src,tags_hash,_datetime) == False: # if this failes then; insert ..
					db.insert_probe_log_fingerdict(_src,_datetime,_datetime,tags_hash)
				out.output(level,"{}  {}   {}     {}       {}  {}  {}  {} Mb/s  {}  {}".format(_freq,_std,_ant,_signal,_bssid,_dst,_src,_rate,_essid.ljust(32),label),_datetime)
				previous = (_datetime+""+_src+""+_signal)
				count += 1
			if timer_output.check():
				out.print_buffer()
	except KeyboardInterrupt:
		# TODO periodical function
		fd.dump_fingerprints('fingerprints_dict.py')
		print "Packet_count: {}".format(count)

		if config['general']['use_sudo']:
			os.system("sudo kill {}".format(p.pid))
		else:
			p.kill()
