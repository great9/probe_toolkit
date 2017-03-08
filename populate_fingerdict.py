from probe_toolkit.pkt_handler import pkt_handler
from probe_toolkit.fingerdict import fingerdict

filename = 'fingerprints_dict.py'

pkt = pkt_handler()

fd = fingerdict()
fd.read_fingerprints_dump(filename)

with open('probes.dump_', mode='rb') as file: # b is important -> binary
	offset = 0
	fileContent = file.read()
	length = len(fileContent)

	pkt.new_data(fileContent)
	for packet in pkt.packets:
		label, tags_hash = fd.update_finterprints(packet[3],packet[2]['source_addr'])
		set_label = True
		match_src = '12:34:56:78:90:FF'
		new_label = 'Example label'

		if set_label == True and match_src == packet[2]['source_addr']:
			fd.update_label(tags_hash,new_label)
			#set_label = False
	fd.dump_fingerprints(filename)
file.close()
