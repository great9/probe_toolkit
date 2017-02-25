# probe_toolkit
##Requirements
 - **tcpdump**
 - **python2**
 - **python-sqlite** or **python-psycopg2**
 - **python-scapy** *(if you are using probesend.py)*

####probecap.py
For capturing probe request and storing them in a SQLite or PostgreSQL db.

####probesend.py
For sending probe requests (for testing only now,don't expect this to work properly unless you do some scripting yourself.)

####probe_toolkit.conf
You need at least to set **mon_if** (wich is your wireless interface in monitor mode) in **general** and configure a db in **db_conf**

####pcap2fingerdict.py
Will generate device (NOT USER) fingerprints from probe requests.
First argument: path to pcap file
Second argument: path to save or update the output to

```pcap2fingerdict.py dump.pcap fingerprints.py```


####Simple SQLite config example for probecap.py
```
general = { 'use_sudo'              : 1,
			'mon_if'				: 'wlan0',
			'dumpfile'				: 'dump.dump',			# File to dump to if dump is True (for debugging)
			'dump'					: False,			
}
output = {	'height'		        : 0,				# 0 means auto else use screen height in characters
			'width'			    	: 0,
			'log_file'				: 'probe.log',
			'log_debug'				: '0',				# 0 means false 1 means true
			'log_error'				: '1',
			'log_warn'				: '1',
			'log_info'				: '0',
			'log_notice'			: '0',
			'out_debug'				: '0',
			'out_error'				: '1',
			'out_warn'				: '0',
			'out_info'				: '1',
			'out_notice'			: '1',
			'disable_color'			: False,
			'time_ago_format'		: True,
}
db_conf = {	'db_type'		        : '2', 
			'pg_host'				: '127.0.0.1',
			'pg_user'				: 'probe_toolkit',
			'pg_pass'				: 'password',
			'pg_db'					: 'probe',
			'db_sqlite_db'	        : 'probe.db' }

# Config for the probe_send script.
# Wich is handy for debugging and flood testing.
# Can be handy for fuzzing either, wip.
probe_send = { 'mask_files'	: ['./masks/nl_ssid.masks','./masks/us_ssid.masks'],
			'mon_if'		: 'wlan0',
			'interval'	    : 5,				# interval in seconds - set to 0 (sec) for very agressive (flood)
			'count'			: 1,				# probe count
      }
```

####How to set your wireless interface in monitor mode
First make sure that your interface is not busy (by Network-Manger etc.)

Assuming your interface name is wlan0, change that to your needs.
*Notice the # in front of the command, you should know what that means.*
```
  # ifconfig wlan0 down
  # iwconfig wlan0 mode monitor
  # ifconfig wlan0 down
```
