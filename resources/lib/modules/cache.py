# -*- coding: utf-8 -*-

'''
	Venom Add-on
'''

import ast
import hashlib
import re
import time

from resources.lib.modules import control
from resources.lib.modules import log_utils

try:
	from sqlite3 import dbapi2 as db, OperationalError
except ImportError:
	from pysqlite2 import dbapi2 as db, OperationalError

cache_table = 'cache'
notificationSound = False if control.setting('notification.sound') == 'false' else True


def get(function, duration, *args):
	# type: (function, int, object) -> object or None
	"""
	Gets cached value for provided function with optional arguments, or executes and stores the result
	:param function: Function to be executed
	:param duration: Duration of validity of cache in hours
	:param args: Optional arguments for the provided function
	"""

	try:
		key = _hash_function(function, args)
		cache_result = cache_get(key)

		if cache_result:
			if _is_cache_valid(cache_result['date'], duration):
				return ast.literal_eval(cache_result['value'].encode('utf-8'))

		fresh_result = repr(function(*args))

		cache_insert(key, fresh_result)

		# Sometimes None is returned as a string instead of the special value None.
		invalid = False
		try:
			if not fresh_result:
				invalid = True
			elif fresh_result == 'None' or fresh_result == '' or fresh_result == '[]' or fresh_result == '{}':
				invalid = True
			elif len(fresh_result) == 0:
				invalid = True
		except: pass

		# If the cache is old, but we didn't get fresh result, return the old cache
		# if not fresh_result:
		if invalid:
			if cache_result:
				return ast.literal_eval(cache_result['value'].encode('utf-8'))
			else:
				return None

		return ast.literal_eval(fresh_result.encode('utf-8'))
	except:
		log_utils.error()
		return None


def remove(function, *args):
	try:
		key = _hash_function(function, args)
		cursor = _get_connection_cursor()
		cursor.execute("DELETE FROM %s WHERE key = ?" % cache_table, [key])
		cursor.connection.commit()
	except:
		log_utils.error()
		pass
	cursor.close()


def timeout(function, *args):
	try:
		key = _hash_function(function, args)
		result = cache_get(key)
		return int(result['date'])
	except:
		return None


def cache_existing(function, *args):
	try:
		cache_result = cache_get(_hash_function(function, args))
		return ast.literal_eval(cache_result['value'].encode('utf-8'))
	except:
		return None


def cache_get(key):
	try:
		cursor = _get_connection_cursor()
		cursor.execute("SELECT * FROM %s WHERE key = ?" % cache_table, [key])
		results = cursor.fetchone()
		cursor.close()
		return results
	except:
		try:
			cursor.close()
		except:
			pass
		return None


def cache_insert(key, value):
	try:
		cursor = _get_connection_cursor()
		now = int(time.time())

		cursor.execute("CREATE TABLE IF NOT EXISTS %s (key TEXT, value TEXT, date INTEGER, UNIQUE(key))" % cache_table)

		update_result = cursor.execute("UPDATE %s SET value=?,date=? WHERE key=?" % cache_table, (value, now, key))

		if update_result.rowcount is 0:
			cursor.execute("INSERT INTO %s Values (?, ?, ?)" % cache_table, (key, value, now))

		cursor.connection.commit()
	except:
		log_utils.error()
		pass
	cursor.close()


# Remove very old entries to reduce the file size.
# The cache DB can grow very larger with advanced caching.
def cache_clean(duration = 1209600):
	try:
		now = int(time.time())
		cursor = _get_connection_cursor()
		cursor.execute("DELETE FROM %s WHERE date < %d" % (cache_table, now - duration))
		cursor.execute("VACUUM")
		cursor.connection.commit()
	except:
		log_utils.error()
		pass
	cursor.close()


#######################################
def cache_version_check():
	if _find_cache_version():
		cache_clear_all()
		control.notification(title = 'default', message = 32057, icon = 'INFO', sound = notificationSound)


def cache_clear_all():
	cache_clear_providers()
	cache_clear_meta()
	cache_clear()
	cache_clear_search()
	cache_clear_bookmarks()


def cache_clear_providers():
	cursor = _get_connection_cursor_providers()
	for t in ['rel_src', 'rel_url']:
		try:
			cursor.execute("DROP TABLE IF EXISTS %s" % t)
			cursor.execute("VACUUM")
			cursor.connection.commit()
		except:
			log_utils.error()
			pass
	cursor.close()


def cache_clear_meta():
	cursor = _get_connection_cursor_meta()
	for t in ['meta']:
		try:
			cursor.execute("DROP TABLE IF EXISTS %s" % t)
			cursor.execute("VACUUM")
			cursor.connection.commit()
		except:
			log_utils.error()
			pass
	cursor.close()


def cache_clear():
	cursor = _get_connection_cursor()
	for t in [cache_table, 'rel_list', 'rel_lib']:
		try:
			cursor.execute("DROP TABLE IF EXISTS %s" % t)
			cursor.execute("VACUUM")
			cursor.connection.commit()
		except:
			log_utils.error()
			pass
	cursor.close()


def cache_clear_search():
	cursor = _get_connection_cursor_search()
	for t in ['tvshow', 'movies']:
		try:
			cursor.execute("DROP TABLE IF EXISTS %s" % t)
			cursor.execute("VACUUM")
			cursor.connection.commit()
		except:
			log_utils.error()
			pass
	cursor.close()
	control.execute('Container.Refresh')


def cache_clear_SearchPhrase(table, key):
	cursor = _get_connection_cursor_search()
	try:
		cursor.execute('DELETE FROM %s WHERE term IS "%s";' % (table, key))
		cursor.connection.commit()
	except:
		log_utils.error()
		pass
	cursor.close()
	control.execute('Container.Refresh')


def cache_clear_bookmarks():
	cursor = _get_connection_cursor_bookmarks()
	for t in ['bookmark']:
		try:
			cursor.execute("DROP TABLE IF EXISTS %s" % t)
			cursor.execute("VACUUM")
			cursor.connection.commit()
		except:
			log_utils.error()
			pass
	cursor.close()


def _get_connection_cursor():
	conn = _get_connection()
	return conn.cursor()


def _get_connection():
	control.makeFile(control.dataPath)
	conn = db.connect(control.cacheFile)
	conn.row_factory = _dict_factory
	return conn


def _get_connection_cursor_meta():
	conn = _get_connection_meta()
	return conn.cursor()


def _get_connection_meta():
	control.makeFile(control.dataPath)
	conn = db.connect(control.metacacheFile)
	conn.row_factory = _dict_factory
	return conn


def _get_connection_cursor_providers():
	conn = _get_connection_providers()
	return conn.cursor()


def _get_connection_providers():
	control.makeFile(control.dataPath)
	conn = db.connect(control.providercacheFile)
	conn.row_factory = _dict_factory
	return conn


def _get_connection_cursor_search():
	conn = _get_connection_search()
	return conn.cursor()


def _get_connection_search():
	control.makeFile(control.dataPath)
	conn = db.connect(control.searchFile)
	conn.row_factory = _dict_factory
	return conn


def _get_connection_cursor_bookmarks():
	conn = _get_connection_bookmarks()
	return conn.cursor()


def _get_connection_bookmarks():
	control.makeFile(control.dataPath)
	conn = db.connect(control.bookmarksFile)
	conn.row_factory = _dict_factory
	return conn


def _dict_factory(cursor, row):
	d = {}
	for idx, col in enumerate(cursor.description):
		d[col[0]] = row[idx]
	return d


def _hash_function(function_instance, *args):
	return _get_function_name(function_instance) + _generate_md5(args)


def _get_function_name(function_instance):
	return re.sub('.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', repr(function_instance))


def _generate_md5(*args):
	md5_hash = hashlib.md5()
	try:
		[md5_hash.update(str(arg)) for arg in args]
	except:
		[md5_hash.update(str(arg).encode('utf-8')) for arg in args]
	return str(md5_hash.hexdigest())


def _is_cache_valid(cached_time, cache_timeout):
	now = int(time.time())
	diff = now - cached_time
	return (cache_timeout * 3600) > diff


def _find_cache_version():
	import os
	versionFile = os.path.join(control.dataPath, 'cache.v')
	try:
		if not os.path.exists(versionFile):
			f = open(versionFile, 'w')
			f.close()
	except:
		import xbmc
		print 'Venom Addon Data Path Does not Exist. Creating Folder....'
		ad_folder = xbmc.translatePath('special://home/userdata/addon_data/plugin.video.venom')
		os.makedirs(ad_folder)

	try:
		with open(versionFile, 'rb') as fh:
			oldVersion = fh.read()
	except:
		oldVersion = '0'

	try:
		curVersion = control.addon('plugin.video.venom').getAddonInfo('version')
		if oldVersion != curVersion:
			with open(versionFile, 'wb') as fh:
				fh.write(curVersion)
			return True
		else:
			return False
	except:
		log_utils.error()
		return False
