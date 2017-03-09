#!/usr/bin/python
import hashlib
import utils
import operator

class fingerdict(object):
	def __init__(self):
		# Only save fingerprint if a minimum of x devices share the same print.
		# This will also filter out device unique fingerprints, like for example
		# Nintendo DS will send probe requests with personal data.
		self.min_dev_count = 0# set to 0 for debug, set to 3 or higher for normal
		self.default_label = "_UNKNOWN_"
		self.count = 0

		self.fingerprints = dict()

		"""CREATE TABLE probe_log_fingerdict (
					src macaddr,
					first_seen timestamp without time zone,
					last_seen timestamp without time zone,
					fingerprint_hash smallint,
					FOREIGN KEY (src) REFERENCES probe_id(src)
				);"""

	def dump_fingerprints(self,filename):
		buf = "fingerprints = {\n"
		counter = 0
		for k,v in self.fingerprints.iteritems():
			device_count = 0
			for oui in v[1]:
				device_count += 1
			if device_count >= self.min_dev_count:# min_dev_count (Minimal device count) is global defined.
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

	def read_fingerprints_dump(self,filename):
		content = dict()
		try:
			execfile(filename, content)
			if 'fingerprints' in content:
				self.fingerprints = content['fingerprints']
				return True
		except:
			return False

	def update_label(self,tags_hash,_label):
		self.fingerprints[tags_hash][0] = _label
		
	def update_finterprints(self,tags,source_addr):
		buf = list()
		tags_string = ""
		oui = source_addr.strip(':')
		oui = oui[:6]
		for tag_id, tag in sorted(tags.items(), key=lambda (tag_id,tag): (tag['val'],tag_id)):
			tag_id = str(tag_id)[:len(str(tag_id))-6]
			#print utils.char_to_hex(tag['val'])
			#print ""
			if(tag_id != '0') and tag_id != '3': # we do not want the ssid and current channel to be added.
				buf.append([tag_id,utils.char_to_hex(str(tag['val']))])
				tags_string += tag_id
				tags_string += "|"
				tags_string += utils.char_to_hex(str(tag['val']))
				tags_string += "|"
		#print tags_string
		_hash = hashlib.md5()
		_hash.update(tags_string)
		tags_hash = str(_hash.hexdigest())
		if tags_hash not in self.fingerprints:
			self.fingerprints.update( { tags_hash : [self.default_label,[oui],buf] } )
			# New hash
		elif oui not in self.fingerprints[tags_hash][1]:
			self.fingerprints[tags_hash][1].append(oui)
			# New OUI to fingerprint
		return self.fingerprints[tags_hash][0], tags_hash