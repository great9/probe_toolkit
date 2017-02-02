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
		if not self.pgsql_check_if_table_present('probe_log'):
			self.pgsql_create_table('probe_log')

	def init_sqlite(self):
		import sqlite3 as lite
		self.con = lite.connect(self.db_config['db_sqlite_db'])
		if not self.sqlite_check_if_table_present('probe_id'):
			self.sqlite_create_table('probe_id')
		if not self.sqlite_check_if_table_present('probe_log'):
			self.sqlite_create_table('probe_log')

	def pgsql_check_if_table_present(self,table_name):
		with self.con:
			cur = self.con.cursor()
			cur.execute("select exists(select * from information_schema.tables where table_name=%s)", (table_name,))
			return cur.fetchone()[0]

	def pgsql_create_table(self,table_name):
		with self.con:
			q = { 'probe_id' : 
				"""CREATE TABLE probe_id (
					src macaddr primary key,
					dst macaddr,
					bssid macaddr,
					first_seen timestamp without time zone,
					last_seen timestamp without time zone,
					essid character varying(32)
				);""",
				'probe_log' : 
				"""CREATE TABLE probe_log (
					datetime timestamp without time zone,
					src macaddr references probe_id(src),
					signal smallint
				);""" }
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
			q = { 'probe_id' :
				"""CREATE TABLE probe_id(
						src CHARACTER PRIMARY KEY,
						essid NATIVE CHARACTER,
						bssid CHARACTER,
						dst CHARACTER,
						first_seen DATETIME,
						last_seen DATETIME
					);""",
					'probe_log' :
					"""CREATE TABLE probe_log(
						datetime DATETIME,
						src CHARACTER,
						signal SMALLINT,
						FOREIGN KEY(src) REFERENCES probe_id(src)
					);""" }
			cur.execute(q[table_name])
			self.con.commit()
		

	def insert_probe_id(self,src,dst,bssid,first_seen,last_seen,essid):
		cur = self.con.cursor()
		try:
			if self.db_config['db_type'] == '1':
				# Postgresql
				cur.execute("INSERT INTO probe_id (src,essid,bssid,dst,first_seen,last_seen) VALUES (%s,%s,%s,%s,%s,%s)", (src,essid,bssid,dst,first_seen,last_seen))
			elif self.db_config['db_type'] == '2':
				# SQLlite query
				cur.execute("INSERT INTO probe_id (src,essid,bssid,dst,first_seen,last_seen) VALUES (?,?,?,?,?,?)", (src,essid,bssid,dst,first_seen,last_seen))
			self.con.commit()
			return True
		except:
			print("Could not insert probe id.")
			return False

	def update_probe_id_last_seen(self,src,bssid,essid,last_seen):
		cur = self.con.cursor()
		try:
			if self.db_config['db_type'] == '1':
				# Postgresql query
				cur.execute("UPDATE probe_id SET last_seen=%s WHERE src=%s AND bssid=%s AND essid=%s returning src", (last_seen,src,bssid,essid))
			elif self.db_config['db_type'] == '2':
				# SQLlite query
				cur.execute("""UPDATE probe_id SET last_seen = ? WHERE src = ? AND bssid = ? AND essid = ?""", (last_seen,src,bssid,essid))			
			if cur.rowcount > 0:
				self.con.commit()
				return 1
			else:
				return 0
		except:
			print("Could not update probe id.")
			return 0

	def insert_probe_log(self,datetime,src,signal):
		cur = self.con.cursor()
		try:
			if self.db_config['db_type'] == '1':
				# Postgresql
				cur.execute("INSERT INTO probe_log (datetime,src,signal) VALUES (%s, %s, %s)", (datetime,src,signal))
			elif self.db_config['db_type'] == '2':
				# SQLlite query
				cur.execute("INSERT INTO probe_log (datetime,src,signal) VALUES (?, ?, ?)", (datetime,src,signal))
			self.con.commit()
		except:
			print("Could not insert probe log.")
