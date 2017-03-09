class db_handler(object):
	def __init__(self, db_config):# db_config is a dict like { 'db_type' : '1', 'pg_host' : '127.0.0.1' etc..}
		self.db_config = db_config
		self.con = None
		if self.db_config['db_type'] == '1':
			self.init_postgresql()
		elif self.db_config['db_type'] == '2':
			self.init_sqlite()
		else:
			print "wrong db type"

	def init_postgresql(self):
		import psycopg2
		try:		
			self.con = psycopg2.connect("host='{}' dbname='{}' user='{}' password='{}'".format(self.db_config['pg_host'],
					self.db_config['pg_db'],
					self.db_config['pg_user'],
					self.db_config['pg_pass']))
		except:
			print "No. Not good (postgresql connect)"
		if not self.pgsql_check_if_table_present('probe_id'):
			self.pgsql_create_table('probe_id')
		if not self.pgsql_check_if_table_present('probe_log_ap'):
			self.pgsql_create_table('probe_log_ap')
		if not self.pgsql_check_if_table_present('probe_log_signal'):
			self.pgsql_create_table('probe_log_signal')
		if not self.pgsql_check_if_table_present('probe_log_fingerdict'):
			self.pgsql_create_table('probe_log_fingerdict')

	def init_sqlite(self):
		import sqlite3 as lite
		global re
		import re# needed to convert postgresql query to sqlite query
		self.con = lite.connect(self.db_config['db_sqlite_db'])
		if not self.sqlite_check_if_table_present('probe_id'):
			self.sqlite_create_table('probe_id')
		if not self.sqlite_check_if_table_present('probe_log_ap'):
			self.sqlite_create_table('probe_log_ap')
		if not self.sqlite_check_if_table_present('probe_log_signal'):
			self.sqlite_create_table('probe_log_signal')
		if not self.sqlite_check_if_table_present('probe_log_fingerdict'):
			self.sqlite_create_table('probe_log_fingerdict')

	def pgsql_check_if_table_present(self,table_name):
		with self.con:
			cur = self.con.cursor()
			cur.execute("select exists(select * from information_schema.tables where table_name=%s)", (table_name,))
			return cur.fetchone()[0]

	def pgsql_create_table(self,table_name):
		with self.con:
			q = { 'probe_id' : "CREATE TABLE probe_id ( src macaddr PRIMARY KEY );",
				'probe_log_ap' : 
				"""CREATE TABLE probe_log_ap (
					src macaddr NOT NULL,
					dst macaddr,
					bssid macaddr,
					first_seen timestamp without time zone,
					last_seen timestamp without time zone,
					essid character varying(32),
					FOREIGN KEY (src) REFERENCES probe_id(src)
				);""",
				'probe_log_signal' : 
				"""CREATE TABLE probe_log_signal (
					datetime timestamp without time zone,
					src macaddr,
					signal smallint,
					FOREIGN KEY (src) REFERENCES probe_id(src)
				);""",
				'probe_log_fingerdict' :
				"""CREATE TABLE probe_log_fingerdict (
					src macaddr,
					first_seen timestamp without time zone,
					last_seen timestamp without time zone,
					fingerprint_hash uuid,
					FOREIGN KEY (src) REFERENCES probe_id(src)
				);"""}
			cur = self.con.cursor()
			cur.execute(q[table_name])
			self.con.commit()
				

	def sqlite_check_if_table_present(self,table_name):
		with self.con:
			cur = self.con.cursor()
			cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % table_name)
			if cur.fetchone():
				return True
			else:
				return False

	def sqlite_create_table(self,table_name):
		with self.con:
			cur = self.con.cursor()
			q = { 'probe_id' : "CREATE TABLE probe_id ( src CHARACTER PRIMARY KEY );",
				'probe_log_ap' :
				"""CREATE TABLE probe_log_ap(
						src CHARACTER,
						dst CHARACTER,
						bssid CHARACTER,
						first_seen DATETIME,
						last_seen DATETIME,
						essid NATIVE CHARACTER,
						FOREIGN KEY(src) REFERENCES probe_id(src)
					);""",
					'probe_log_signal' :
					"""CREATE TABLE probe_log_signal(
						datetime DATETIME,
						src CHARACTER,
						signal SMALLINT,
						FOREIGN KEY(src) REFERENCES probe_id(src)
					);""",
					'probe_log_fingerdict' :
					"""CREATE TABLE probe_log_fingerdict (
						src CHARACTER,
						first_seen DATETIME,
						last_seen DATETIME,
						fingerprint_hash NCHAR,
						FOREIGN KEY (src) REFERENCES probe_id(src)
					);""" }
			cur.execute(q[table_name])
			self.con.commit()

	def query(self,query):
		if self.db_config['db_type'] == '1':
			return query
		elif self.db_config['db_type'] == '2':
			query = query.replace('%s', '?')
			query = re.sub(r"returning \w+", "", query)
		return query

	def insert_probe_log_ap(self,src,dst,bssid,first_seen,last_seen,essid):
		cur = self.con.cursor()
		try:
			cur.execute(self.query("INSERT INTO probe_log_ap (src,essid,bssid,dst,first_seen,last_seen) VALUES (%s,%s,%s,%s,%s,%s);"),
						(src,essid,bssid,dst,first_seen,last_seen))
			self.con.commit()
			return True
		except:
			print("Could not insert probe log ap.")
			return False

	def update_probe_log_ap_last_seen(self,src,bssid,essid,last_seen):
		cur = self.con.cursor()
		try:
			cur.execute(self.query("UPDATE probe_log_ap SET last_seen=%s WHERE src=%s AND bssid=%s AND essid=%s returning src;"),
						(last_seen,src,bssid,essid))
			if cur.rowcount > 0:
				self.con.commit()
				return True
			return False
		except:
			print("Could not update probe log ap.")
			return False

	def insert_probe_log_signal(self,datetime,src,signal):
		cur = self.con.cursor()
		try:
			cur.execute(self.query("INSERT INTO probe_log_signal (datetime,src,signal) VALUES (%s, %s, %s);"),
						(datetime,src,signal))
			self.con.commit()
			return True
		except:
			print("Could not insert probe log signal.")
			return False

	def update_probe_log_fingerdict_last_seen(self,src,tags_hash,last_seen):
		cur = self.con.cursor()
		try:
			cur.execute(self.query("UPDATE probe_log_fingerdict SET last_seen=%s WHERE src=%s AND fingerprint_hash=%s returning src;"),
						(last_seen,src,tags_hash))
			if cur.rowcount > 0:
				self.con.commit()
				return True
			return False
		except:
			print("Could not update probe log fingerdict.")
			return False

	def insert_probe_log_fingerdict(self,src,first_seen,last_seen,tags_hash):
		cur = self.con.cursor()
		try:
			cur.execute(self.query("INSERT INTO probe_log_fingerdict (src,first_seen,last_seen,fingerprint_hash) VALUES (%s, %s, %s, %s);"),
						(src,first_seen,last_seen,tags_hash))
			self.con.commit()
			return True
		except:
			print("Could not insert probe log fingerdict.")
			return False

	def insert_probe_id(self,src):
		cur = self.con.cursor()
		cur.execute(self.query("SELECT count(*) FROM probe_id WHERE src=%s"), (src,))
		if cur.fetchone()[0] == 0:
			try:
				cur.execute(self.query("INSERT INTO probe_id (src) VALUES (%s);"), (src,))
				self.con.commit()
				return True
			except:
				return False
		return False

class client(db_handler):
	def __init__(self,db_config):
		print "Init client"
		super(client, self).__init__(db_config)

	def add_like(self,query,oval,ival,ikey):
		query += "{} LIKE %s ".format(ikey)
		oval.append(ival)
		return (query,oval)

	def add_not(self,query,oval,ival,ikey):
		query += "{}!=%s ".format(ikey)
		oval.append(ival)
		return (query,oval)

	def add_between(self,query,oval,ival,ikey):
		query += "{} BETWEEN %s AND %s ".format(ikey)
		oval.append(str(ival[0])[:19])
		oval.append(str(ival[1])[:19])
		return (query,oval)

	def make_query(self,_filter,_options,col_name):
		query = "SELECT * FROM {} WHERE ".format(col_name)
		values = list()
		count = 0
		count_order = 0
		for k, v in _filter.iteritems():
			if count > 0 and count < len(_filter):
				query += "AND "
			if k in _options:
				if _options[k] == 'like':
					query += "{} LIKE %s ".format(k)
					values.append(ival)
				elif _options[k] == 'between':
					query += "{} BETWEEN %s AND %s ".format(k)
					values.append(str(v[0])[:19])
					values.append(str(v[1])[:19])
				elif _options[k] == 'not':
					query += "{}!=%s ".format(k)
					values.append(v)
				elif _options[k] == 'orderdesc':
					query = query[:len(query)-4]
					if count_order > 0:
						query += ", "
					query += "ORDER BY {} DESC".format(k)
					#values.append(v)
					count_order += 1
				elif _options[k] == 'orderasc':
					query = query[:len(query)-4]
					if count_order > 0:
						query += ", "
					query += "ORDER BY {} ASC".format(k)
					#values.append(v)
					count_order += 1
			else:
				query += "{}=%s ".format(k)
				values.append(v)
			count += 1
		query += ";"
		return (query, values)

	def get_probe(self,col_name,_filter,_options):
		cur = self.con.cursor()
		query ,values = self.make_query(_filter,_options,col_name)
		try:
			#print self.query(query)
			cur.execute(self.query(query), (values))
			return cur.fetchall()
		except:
			return ""

	def get_fingerprint_hash(self,src):
		cur = self.con.cursor()
		query = "SELECT fingerprint_hash FROM probe_log_fingerdict WHERE src=%s LIMIT 1;"
		try:
			#print self.query(query)
			cur.execute(self.query(query), (src,))
			#return cur.fetchall()[0]
			#print 
			return str(cur.fetchone()[0]).replace('-','')
		except:
			return ""
