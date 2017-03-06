#!/usr/bin/python
import hashlib
import utils

class fingerdict(object):
	def __init__(self):
		# Only save fingerprint if a minimum of x devices share the same print.
		# This will also filter out device unique fingerprints, like for example
		# Nintendo DS will send probe requests with personal data.
		self.min_dev_count = 3
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
		for tag_id, tag in tags.iteritems():
			if(str(tag_id[6:]) != '0'): # we do not want the ssid to be added.
				buf.append([str(tag_id[6:]),char_to_hex(str(tag['val']))])
				tags_string += str(tag_id[6:])
				tags_string += "|"
				tags_string += char_to_hex(str(tag['val']))
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