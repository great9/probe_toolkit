#!/usr/bin/env python
import os			# needed to get terminal window sizes
import datetime
import time
import re
import subprocess as sub
from probe_toolkit.db_handler import db_handler
from probe_toolkit.output_handler import output_handler

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
	out.header += """datetime\t\t\tfreq  std  ant   signal    bssid              dst                src                rate      essid
-----------------------------  ----  ---  -     ---       -----------------  -----------------  -----------------  --------  --------------------------------"""
	"""
		tcpdump -i $wifi_if -e -s 256 type mgt subtype probe-req
		-i								interface
		-l								make stdout line buffered
		-e								print link header, else it won't print adresses
		-s								snaplength
		type mgt subtype probe-req					probe filter options
	"""
	if 'dump' not in config['general']:
		config['general']['dump'] = False
	if 'dumpfile' not in config['general']:
		config['general']['dump'] = 'probe.dump'
	if 'use_sudo' not in config['general']:
		config['general']['use_sudo'] = False
	if config['general']['use_sudo'] == True:
		if config['general']['dump'] == True:
			o = sub.Popen(('sudo', 'tcpdump', '-i', config['general']['mon_if'], '-U', '-s', '256', 'type mgt subtype probe-req', '-w', '-'), stdout=sub.PIPE)
			l = sub.Popen(('tee', config['general']['dumpfile']), stdin=o.stdout, stdout=sub.PIPE)
			p = sub.Popen(('tcpdump', '-l', '-e', '-r', '-'), stdin=l.stdout, stdout=sub.PIPE)
		else:
			p = sub.Popen(('sudo', 'tcpdump', '-i', config['general']['mon_if'], '-l', '-e', '-s', '256', 'type mgt subtype probe-req'), stdout=sub.PIPE)
	else:
		if config['general']['dump'] == True:
			o = sub.Popen(('tcpdump', '-i', config['general']['mon_if'], '-U', '-s', '256', 'type mgt subtype probe-req', '-w', '-'), stdout=sub.PIPE)
			l = sub.Popen(('tee', config['general']['dumpfile']), stdin=o.stdout, stdout=sub.PIPE)
			p = sub.Popen(('tcpdump', '-l', '-e', '-r', '-'), stdin=l.stdout, stdout=sub.PIPE)
		else:
			p = sub.Popen(('tcpdump', '-i', config['general']['mon_if'], '-l', '-e', '-s', '256', 'type mgt subtype probe-req'), stdout=sub.PIPE)
	db = db_handler(config['db_conf'])

	pattern_freq = re.compile("((\d{4}) (M|G)hz)", re.IGNORECASE)
	pattern_rate = re.compile("(\d+.\d+ (M|G)b\/s)", re.IGNORECASE)
	pattern_80211std = re.compile("(11(a|b|g|n))")
	pattern_signal = re.compile("((-\d{2})dB[m]? signal)")
	pattern_antenna = re.compile("(antenna (\d+))")
	pattern_bssid = re.compile("BSSID:(([0-9a-fA-F]{2}[:]?){6}|Broadcast)")
	pattern_dst = re.compile("DA:(([0-9a-fA-F]{2}[:]?){6}|Broadcast)")
	pattern_src = re.compile("SA:(([0-9a-fA-F]{2}[:]?){6}|Broadcast)")
	pattern_essid = re.compile("Probe Request \((.*?)\)")

	try:
		previous = ""
		for row in iter(p.stdout.readline, b''):
			_datetime = str(datetime.date.today())
			_datetime += " {}".format(row[:8])

			row = row[16:] # We already have the time, so we can skip it, no need to process.

			_freq = pattern_freq.search(row)
			_freq = set_match_value(_freq,2)

			_rate = pattern_rate.search(row)
			_rate = set_match_value(_rate)

			_std = pattern_80211std.search(row)
			_std = set_match_value(_std,1)

			_sig = pattern_signal.search(row)
			_sig = set_match_value(_sig,2)

			_ant = pattern_antenna.search(row)
			_ant = set_match_value(_ant,2)

			_bssid = pattern_bssid.search(row)
			_bssid = set_match_value(_bssid,1)
			if _bssid == "Broadcast":
				_bssid = "ff:ff:ff:ff:ff:ff"

			_dst = pattern_dst.search(row)
			_dst = set_match_value(_dst,1)
			if _dst == "Broadcast":
				_dst = "ff:ff:ff:ff:ff:ff"

			_src = pattern_src.search(row)
			_src = set_match_value(_src,1)
			if _src == "NOT_SET":
				out.output("WARN","no src matched. Line: \"{}\"".format(row))
				continue

			_essid = pattern_essid.search(row)
			_essid = set_match_value(_essid,1)
			if len(_essid) >32:
				out.output("WARN","SSID is too long. SSID: \"{}\", Line: \"{}\"".format(_essid,row))
				continue

			level = "NOTICE"
			db.insert_probe_id(_src)
			if db.update_probe_log_ap_last_seen(_src,_bssid,_essid,_datetime) == False: # if this failes then; insert ..
				if db.insert_probe_log_ap(_src,_dst,_bssid,_datetime,_datetime,_essid):
					level = "INFO" # cause it's a new entry :-)
			if previous == (_datetime+""+_src+""+_sig):
				out.output("DEBUG","Skipped duplicate input: {}".format(previous))
			else:
				db.insert_probe_log_signal(_datetime,_src,_sig)
			out.output(level," {}  {}  {}     {}       {}  {}  {}  {}  {}".format(_freq,_std,_ant,_sig,_bssid,_dst,_src,_rate,_essid),_datetime)
			previous = (_datetime+""+_src+""+_sig)

	except KeyboardInterrupt:
		if config['general']['use_sudo']:
			os.system("sudo kill {}".format(p.pid))
		else:
			p.kill()
