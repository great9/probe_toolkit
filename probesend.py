#!/usr/bin/env python
import logging
import random
import time
import datetime
from random import randint
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import *
from probe_toolkit.gen_ssid import gen_ssid
from probe_toolkit.output_handler import output_handler

# [ Sources ]
### http://blog.packetheader.net/2014/01/sending-80211-packets-with-scapy.html
### https://www.centos.org/docs/5/html/5.2/Virtualization/sect-Virtualization-Tips_and_tricks-Generating_a_new_unique_MAC_address.html
### http://www.willhackforsushi.com/papers/80211_Pocket_Reference_Guide.pdf

src='ff:ff:ff:ff:ff:ff'

def random_mac():
	mac = [ random.randint(0x00, 0xff),
		random.randint(0x00, 0xff),
		random.randint(0x00, 0xff),
                random.randint(0x00, 0xff),
                random.randint(0x00, 0xff),
                random.randint(0x00, 0xff) ]
        return ':'.join(map(lambda x: "%02x" % x, mac))

def transmit_probe_request(out,iface='mon0',count=1,ssid='LOL'):
	conf.iface = iface # Interface
	dst = "ff:ff:ff:ff:ff:ff" # Destination (broadcast)
	global src
	src = random_mac() # Source
	bssid = random_mac() # BSSID

	param = Dot11ProbeReq()
	essid = Dot11Elt(ID='SSID',info=ssid)
	#rates = Dot11Elt(ID='Rates',info="\x03\x12\x96\x18\x24\x30\x48\x60")
	rates = Dot11Elt(ID='Rates',info="\x01\x08\x82\x84\x8b\x96\x12\x24\x48\x6c")
	dsset = Dot11Elt(ID='DSset',info='\x01')
	pkt = RadioTap()/Dot11(type=0,subtype=4,addr1=dst,addr2=src,addr3=bssid)/param/essid/rates/dsset

	try:
		sendp(pkt,count=count,inter=0.01,verbose=0)
		out.output("INFO","\t"+ str(count) +"\t" + src + "\t" + ssid)
	except:
		raise


#with open('./sql_injection.vector') as f:
#	for line in f:
#		transmit_probe_request(out,ssid=line)

config = {}
try:
	execfile("probesend.conf", config)
except:
	print """No config file found or error, exiting."""

out = output_handler(config['output'])
out.header += """802.11 Probe Request
datetime\t\t\t\tcount\tsource\t\t\tssid
-----------------------\t\t\t---\t------------------\t--------------------------------"""
test = gen_ssid()
time.sleep(1)
for mask in config['probesend']['mask_files']:
	out.output("DEBUG",mask)
	test.mask_file=mask
	test.load_mask_file()

while True:
	test.set_random_mask()
	transmit_probe_request(out,config['probesend']['mon_if'],count=config['probesend']['count'],ssid=test.do_mask())
	time.sleep(config['probesend']['interval'])
