# -*- coding: utf-8 -*-

'''
	Venom Add-on
'''

import os, re, imp, json, urlparse
import time, threading

from resources.lib.modules import cache
from resources.lib.modules import cleandate
from resources.lib.modules import client
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import utils

from resources.lib.extensions import database

BASE_URL = 'http://api.trakt.tv'
V2_BASE_URL = 'http://api-v2launch.trakt.tv'
V2_API_KEY = 'c622fa66e6cdd783b23f2fc1a1abedc1f1e6ea739d8755248487d1dcfeda66e5'
CLIENT_SECRET = '3430dbd20bd3eb55c0f4e3dc05c7cbbadaf1fd4b8e2a572f4200e482a2041bd8'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

databaseName = control.cacheFile
databaseTable = 'trakt'
server_notification = False if control.setting('trakt.server.notifications') == 'false' else True
general_notification = False if control.setting('trakt.general.notifications') == 'false' else True
notificationSound = False if control.setting('notification.sound') == 'false' else True


def getTrakt(url, post = None, cache = True, check = False, timestamp = None, extended = False, direct = False, authentication = None):
# def getTrakt(url, post = None, cache = True, check = True, timestamp = None, extended = False, direct = False, authentication = None):
	try:
		if not url.startswith(BASE_URL):
			url = urlparse.urljoin(BASE_URL, url)

		if authentication:
			valid = True
			token = authentication['token']
			refresh = authentication['refresh']
		else:
			valid = getTraktCredentialsInfo() is True
			token = control.setting('trakt.token')
			refresh = control.setting('trakt.refresh')

		headers = {'Content-Type': 'application/json', 'trakt-api-key': V2_API_KEY, 'trakt-api-version': '2'}

		if post is not None:
			post = json.dumps(post)

		if direct or not valid:
			result = client.request(url, post = post, headers = headers)
			return result

		headers['Authorization'] = 'Bearer %s' % token

		result = client.request(url, post = post, headers = headers, output = 'extended', error = True)
		if result and not (result[1] == '401' or result[1] == '405'):
			if check:
				_cacheCheck()
			if extended:
				return result[0], result[2]
			else:
				return result[0]

		try:
			code = str(result[1])
		except:
			code = ''

		if code.startswith('5') or (result and isinstance(result, basestring) and '<html' in result) or not result:
			return _error(url = url, post = post, timestamp = timestamp, message = 33676)

		oauth = urlparse.urljoin(BASE_URL, '/oauth/token')
		opost = {'client_id': V2_API_KEY, 'client_secret': CLIENT_SECRET, 'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob', 'grant_type': 'refresh_token', 'refresh_token': refresh}

		result = client.request(oauth, post = json.dumps(opost), headers = headers, error = True)

		try:
			code = str(result[1])
		except:
			code = ''

		if code.startswith('5') or not result or (result and isinstance(result, basestring) and '<html' in result):
			return _error(url = url, post = post, timestamp = timestamp, message = 33676)
		elif result and code in ['404']:
			return _error(url = url, post = post, timestamp = timestamp, message = 33786)
		elif result and code in ['401', '405']:
			return _error(url = url, post = post, timestamp = timestamp, message = 33677)

		result = json.loads(result)

		token, refresh = result['access_token'], result['refresh_token']
		control.setSetting('trakt.token', token)
		control.setSetting('trakt.refresh', refresh)

		headers['Authorization'] = 'Bearer %s' % token

		result = client.request(url, post = post, headers = headers, output = 'extended')
		if check:
			_cacheCheck()

		if extended:
			return result[0], result[2]
		else: return result[0]
	except:
		log_utils.error()

	return None


def getTraktAsJson(url, post = None, authentication = None):
	try:
		res_headers = {}

		r = getTrakt(url = url, post = post, extended = True, authentication = authentication)

		if isinstance(r, tuple) and len(r) == 2:
			res_headers = r[1]
			r = r[0]
		r = utils.json_loads_as_str(r)
		res_headers = dict((k.lower(), v) for k, v in res_headers.iteritems())
		if 'x-sort-by' in res_headers and 'x-sort-how' in res_headers:
			r = sort_list(res_headers['x-sort-by'], res_headers['x-sort-how'], r)
		return r
	except:
		pass


def _error(url, post, timestamp, message):
	_cache(url = url, post = post, timestamp = timestamp)
	if server_notification:
		control.notification(title = 32315, message = message, icon = 'ERROR', sound = notificationSound)
	control.hide()
	return None


def _cache(url, post = None, timestamp = None):
	try:
		# Only cache the requests that change something on the Trakt account.
		# Trakt uses JSON post data to set things and only uses GET parameters to retrieve things.
		if post is None:
			return None
		data = database.Database(databaseName, connect = True)
		_cacheCreate(data)
		# post parameter already json.dumps from getTrakt.
		post = ('"%s"' % post.replace('"', '""').replace("'", "''")) if post is not None else data._null()

		if timestamp is None:
			timestamp = int(time.time())

		data._insert('''
			INSERT INTO %s (time, link, data)
			VALUES (%d, "%s", %s);
			''' % (databaseTable, timestamp, url, post)
			, commit = True
		)
		data._close()
	except:
		log_utils.error()


def _cacheCreate(data):
	try:
		data._create('''
		CREATE TABLE IF NOT EXISTS %s
		(
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			time INTEGER,
			link TEXT,
			data TEXT
			);
			''' % (databaseTable)
		)
	except: pass


def _cacheCheck():
	thread = threading.Thread(target = _cacheProcess)
	thread.start()


def _cacheProcess():
	data = database.Database(databaseName, connect = True)
	data._lock()
	_cacheCreate(data)
	data._unlock()
	try:
		while True:
			# Execute the select and delete as atomic operations.
			data._lock()
			result = data._selectSingle('SELECT id, time, link, data FROM %s ORDER BY time ASC LIMIT 1;' % (databaseTable))

			if not result:
				raise Exception()

			data._delete('DELETE FROM %s WHERE id IS %d;' % (databaseTable, result[0]), commit = True)
			data._unlock()
			result = getTrakt(url = result[2], post = json.loads(result[3]) if result[3] else None, cache = True, check = False, timestamp = result[1])
	except:
		data._unlock()
	data._close()


def _cacheClear():
	try:
		data = database.Database(databaseName, connect = True)
		data._drop(databaseTable, commit = True)
		data._close()
	except:
		log_utils.error()


def authTrakt():
	try:
		if getTraktCredentialsInfo() is True:
			if control.yesnoDialog(control.lang(32511).encode('utf-8'), control.lang(32512).encode('utf-8'), '', 'Trakt'):
				control.setSetting(id='trakt.user', value='')
				control.setSetting(id='trakt.userHidden', value='')
				control.setSetting(id='trakt.token', value='')
				control.setSetting(id='trakt.refresh', value='')
			raise Exception()

		result = getTraktAsJson('/oauth/device/code', {'client_id': V2_API_KEY})
		verification_url = (control.lang(32513) % result['verification_url']).encode('utf-8')
		user_code = (control.lang(32514) % result['user_code']).encode('utf-8')
		expires_in = int(result['expires_in'])
		device_code = result['device_code']
		interval = result['interval']
		progressDialog = control.progressDialog
		progressDialog.create('Trakt', verification_url, user_code)

		for i in range(0, expires_in):
			try:
				if progressDialog.iscanceled():
					break
				time.sleep(1)
				if not float(i) % interval == 0:
					raise Exception()
				r = getTraktAsJson('/oauth/device/token', {'client_id': V2_API_KEY, 'client_secret': CLIENT_SECRET, 'code': device_code})
				if 'access_token' in r:
					break
			except:
				pass

		try:
			progressDialog.close()
		except:
			pass

		token, refresh = r['access_token'], r['refresh_token']
		headers = {'Content-Type': 'application/json', 'trakt-api-key': V2_API_KEY, 'trakt-api-version': 2, 'Authorization': 'Bearer %s' % token}

		result = client.request(urlparse.urljoin(BASE_URL, '/users/me'), headers=headers)
		result = utils.json_loads_as_str(result)

		user = result['username']

		control.setSetting(id='trakt.user', value=user)
		control.setSetting(id='trakt.userHidden', value=user)
		control.setSetting(id='trakt.token', value=token)
		control.setSetting(id='trakt.refresh', value=refresh)
		raise Exception()
	except:
		pass


def getTraktCredentialsInfo():
	user = control.setting('trakt.user').strip()
	token = control.setting('trakt.token')
	refresh = control.setting('trakt.refresh')
	if (user == '' or token == '' or refresh == ''):
		return False
	return True


def getTraktIndicatorsInfo():
	indicators = control.setting('indicators') if getTraktCredentialsInfo() is False else control.setting('indicators.alt')
	indicators = True if indicators == '1' else False
	return indicators


def getTraktAddonMovieInfo():
	try:
		scrobble = control.addon('script.trakt').getSetting('scrobble_movie')
	except:
		scrobble = ''
	try:
		ExcludeHTTP = control.addon('script.trakt').getSetting('ExcludeHTTP')
	except:
		ExcludeHTTP = ''
	try:
		authorization = control.addon('script.trakt').getSetting('authorization')
	except:
		authorization = ''
	if scrobble == 'true' and ExcludeHTTP == 'false' and authorization != '':
		return True
	else:
		return False


def getTraktAddonEpisodeInfo():
	try:
		scrobble = control.addon('script.trakt').getSetting('scrobble_episode')
	except:
		scrobble = ''
	try:
		ExcludeHTTP = control.addon('script.trakt').getSetting('ExcludeHTTP')
	except:
		ExcludeHTTP = ''
	try:
		authorization = control.addon('script.trakt').getSetting('authorization')
	except:
		authorization = ''
	if scrobble == 'true' and ExcludeHTTP == 'false' and authorization != '':
		return True
	else:
		return False


def watch(name, imdb = None, tvdb = None, season = None, episode = None, refresh = True):
	if tvdb is None:
		markMovieAsWatched(imdb)
		cachesyncMovies()
	elif episode is not None:
		markEpisodeAsWatched(imdb, tvdb, season, episode)
		cachesyncTV(imdb)
	elif season is not None:
		markSeasonAsWatched(imdb, tvdb, season)
		cachesyncTV(imdb)
	elif tvdb is not None:
		markTVShowAsWatched(imdb, tvdb)
		cachesyncTV(imdb)
	else:
		markMovieAsWatched(imdb)
		cachesyncMovies()
	if refresh:
		control.refresh()
	control.trigger_widget_refresh()
	if general_notification:
		if season and not episode:
			name = '%s-Season%s...' % (name, season)
		if season and episode:
			name = '%s-S%sxE%02d...' % (name, season, int(episode))
		control.notification(title = 32315, message = control.lang(35502) % name, icon = 'INFO', sound = notificationSound)


def unwatch(name, imdb = None, tvdb = None, season = None, episode = None, refresh = True):
	if tvdb is None:
		markMovieAsNotWatched(imdb)
		cachesyncMovies()
	elif episode is not None:
		markEpisodeAsNotWatched(imdb, tvdb, season, episode)
		cachesyncTV(imdb)
	elif season is not None:
		markSeasonAsNotWatched(imdb, tvdb, season)
		cachesyncTV(imdb)
	elif tvdb is not None:
		markTVShowAsNotWatched(imdb, tvdb)
		cachesyncTV(imdb)
	else:
		markMovieAsNotWatched(imdb)
		cachesyncMovies()
	if refresh:
		control.refresh()
	control.trigger_widget_refresh()
	if general_notification:
		if season and not episode:
			name = '%s-Season%s...' % (name, season)
		if season and episode:
			name = '%s-S%sxE%02d...' % (name, season, int(episode))
		control.notification(title = 32315, message = control.lang(35503) % name, icon = 'INFO', sound = notificationSound)


def rate(imdb = None, tvdb = None, season = None, episode = None):
	return _rating(action = 'rate', imdb = imdb, tvdb = tvdb, season = season, episode = episode)


def unrate(imdb = None, tvdb = None, season = None, episode = None):
	return _rating(action = 'unrate', imdb = imdb, tvdb = tvdb, season = season, episode = episode)


def rateShow(imdb = None, tvdb = None, season = None, episode = None):
	if control.setting('trakt.rating') == 1:
		rate(imdb = imdb, tvdb = tvdb, season = season, episode = episode)


def _rating(action, imdb = None, tvdb = None, season = None, episode = None):
	try:
		addon = 'script.trakt'
		if control.condVisibility('System.HasAddon(%s)' % addon):
			data = {}
			data['action'] = action
			if tvdb is not None:
				data['video_id'] = tvdb
				if episode is not None:
					data['media_type'] = 'episode'
					data['dbid'] = 1
					data['season'] = int(season)
					data['episode'] = int(episode)
				elif season is not None:
					data['media_type'] = 'season'
					data['dbid'] = 5
					data['season'] = int(season)
				else:
					data['media_type'] = 'show'
					data['dbid'] = 2
			else:
				data['video_id'] = imdb
				data['media_type'] = 'movie'
				data['dbid'] = 4

			script = os.path.join(control.addonPath(addon), 'resources', 'lib', 'sqlitequeue.py')
			sqlitequeue = imp.load_source('sqlitequeue', script)
			data = {'action': 'manualRating', 'ratingData': data}
			sqlitequeue.SqliteQueue().append(data)
		else:
			control.notification(title = 32315, message = 33659, icon = 'INFO', sound = notificationSound)
	except:
		pass


def hideItem(name, imdb = None, tvdb = None, season = None, episode = None, refresh = True):
	sections = ['progress_watched', 'calendar']
	sections_display = [control.lang(40072).encode('utf-8'), control.lang(40073).encode('utf-8')]
	selection = control.selectDialog([i for i in sections_display], heading = control.addonInfo('name') + ' - ' + control.lang(40074).encode('utf-8'))

	if selection == -1:
		return

	section = sections[selection]

	if episode is not None:
		post = {"shows": [{"ids": {"tvdb": tvdb}}]}
	else:
		post = {"movies": [{"ids": {"imdb": imdb}}]}

	getTrakt('users/hidden/%s' % section, post = post)[0]

	if refresh:
		control.refresh()
	control.trigger_widget_refresh()
	if general_notification:
		control.notification(title = 32315, message = control.lang(33053) % (name, sections_display[selection]), icon = 'INFO', sound = notificationSound)


def manager(name, imdb = None, tvdb = None, season = None, episode = None, refresh = True):
	lists = []
	try:
		if season is not None:
			season = int(season)
		if episode is not None:
			episode = int(episode)
		if tvdb is not None:
			media_type = 'Show'
		else:
			media_type = 'Movie'

		items = [(control.lang(33651).encode('utf-8'), 'watch')]
		items += [(control.lang(33652).encode('utf-8'), 'unwatch')]
		items += [(control.lang(33653).encode('utf-8'), 'rate')]
		items += [(control.lang(33654).encode('utf-8'), 'unrate')]
		items += [(control.lang(40075).encode('utf-8') % media_type, 'hideItem')]
		items += [(control.lang(33575).encode('utf-8'), '/sync/collection')]
		items += [(control.lang(33576).encode('utf-8'), '/sync/collection/remove')]
		if season or episode is not None:
			items += [(control.lang(33573).encode('utf-8'), '/sync/watchlist')]
			items += [(control.lang(33574).encode('utf-8'), '/sync/watchlist/remove')]
		items += [(control.lang(33577).encode('utf-8'), '/sync/watchlist')]
		items += [(control.lang(33578).encode('utf-8'), '/sync/watchlist/remove')]
		items += [(control.lang(33579).encode('utf-8'), '/users/me/lists/%s/items')]

		result = getTraktAsJson('/users/me/lists')
		lists = [(i['name'], i['ids']['slug']) for i in result]
		lists = [lists[i//2] for i in range(len(lists)*2)]

		for i in range(0, len(lists), 2):
			lists[i] = ((control.lang(33580) % lists[i][0]).encode('utf-8'), '/users/me/lists/%s/items' % lists[i][1])

		for i in range(1, len(lists), 2):
			lists[i] = ((control.lang(33581) % lists[i][0]).encode('utf-8'), '/users/me/lists/%s/items/remove' % lists[i][1])
		items += lists

		control.hide()
		select = control.selectDialog([i[0] for i in items], heading = control.addonInfo('name') + ' - ' + control.lang(32515).encode('utf-8'))

		if select == -1:
			return
		if select >= 0:
			# if select == 0:
			if items[select][0] == control.lang(33651).encode('utf-8'):
				control.busy()
				watch(name, imdb = imdb, tvdb = tvdb, season = season, episode = episode, refresh = refresh)
				control.hide()
			# elif select == 1:
			elif items[select][0] == control.lang(33652).encode('utf-8'):
				control.busy()
				unwatch(name, imdb = imdb, tvdb = tvdb, season = season, episode = episode, refresh = refresh)
				control.hide()
			# elif select == 2:
			elif items[select][0] == control.lang(33653).encode('utf-8'):
				control.busy()
				rate(imdb = imdb, tvdb = tvdb, season = season, episode = episode)
				control.hide()
			# elif select == 3:
			elif items[select][0] == control.lang(33654).encode('utf-8'):
				control.busy()
				unrate(imdb = imdb, tvdb = tvdb, season = season, episode = episode)
				control.hide()
			# elif select == 4:
			elif items[select][0] == control.lang(40075).encode('utf-8') % media_type:
				control.busy()
				hideItem(name = name, imdb = imdb, tvdb = tvdb, season = season, episode = episode)
				control.hide()

			else:
				if tvdb is None:
					post = {"movies": [{"ids": {"imdb": imdb}}]}
				else:
					if episode is not None:
						if items[select][0] == control.lang(33573).encode('utf-8') or items[select][0] == control.lang(33574).encode('utf-8') :
							post = {"shows": [{"ids": {"tvdb": tvdb}}]}
						else:
							post = {"shows": [{"ids": {"tvdb": tvdb}, "seasons": [{"number": season, "episodes": [{"number": episode}]}]}]}
							name = name + ' - ' + '%sx%02d' % (season, episode)
					elif season is not None:
						if items[select][0] == control.lang(33573).encode('utf-8') or items[select][0] == control.lang(33574).encode('utf-8') :
							post = {"shows": [{"ids": {"tvdb": tvdb}}]}
						else:
							post = {"shows": [{"ids": {"tvdb": tvdb}, "seasons": [{"number": season}]}]}
							name = name + ' - ' + 'Season %s' % season
					else:
						post = {"shows": [{"ids": {"tvdb": tvdb}}]}

				# if select == 8:
				if items[select][0] == control.lang(33579).encode('utf-8'):
					slug = listAdd(successNotification = True)
					if slug is not None:
						getTrakt(items[select][1] % slug, post = post)[0]
				else:
					getTrakt(items[select][1], post = post)[0]

				control.hide()
				# message = 33583 if (select % 2) == 0 else 33582
				message = 33583 if 'remove' in items[select][1] else 33582

				if refresh:
					control.refresh()
				control.trigger_widget_refresh()
				if general_notification:
					control.notification(title = name, message = message, icon = 'INFO', sound = notificationSound)
	except:
		log_utils.error()
		control.hide()


def listAdd(successNotification = True):
	t = control.lang(32520).encode('utf-8')
	k = control.keyboard('', t) ; k.doModal()
	new = k.getText() if k.isConfirmed() else None

	if (new is None or new == ''):
		return

	result = getTrakt('/users/me/lists', post = {"name" : new, "privacy" : "private"})

	try:
		slug = json.loads(result)['ids']['slug']
		if successNotification:
			control.notification(title = 32070, message = 33661, icon = 'INFO', sound = notificationSound)
		return slug
	except:
		control.notification(title = 32070, message = 33584, icon = 'iNFO', sound = notificationSound)
		return None


def lists(id = None):
	return cache.get(getTraktAsJson, 48, 'https://api.trakt.tv/users/me/lists' + ('' if id is None else ('/' + str(id))))


def list(id):
	return lists(id = id)


def slug(name):
	name = name.strip()
	name = name.lower()
	name = re.sub('[^a-z0-9_]', '-', name)
	name = re.sub('--+', '-', name)
	return name


def verify(authentication = None):
	try:
		if getTraktAsJson('/sync/last_activities', authentication = authentication):
			return True
	except:
		pass
	return False


def getActivity():
	try:
		i = getTraktAsJson('/sync/last_activities')
		activity = []
		activity.append(i['movies']['collected_at'])
		activity.append(i['episodes']['collected_at'])
		activity.append(i['movies']['watchlisted_at'])
		activity.append(i['shows']['watchlisted_at'])
		activity.append(i['seasons']['watchlisted_at'])
		activity.append(i['episodes']['watchlisted_at'])
		activity.append(i['lists']['updated_at'])
		activity.append(i['lists']['liked_at'])
		activity = [int(cleandate.iso_2_utc(i)) for i in activity]
		activity = sorted(activity, key=int)[-1]
		return activity
	except:
		pass


def getWatchedActivity():
	try:
		i = getTraktAsJson('/sync/last_activities')
		activity = []
		activity.append(i['movies']['watched_at'])
		activity.append(i['episodes']['watched_at'])
		activity = [int(cleandate.iso_2_utc(i)) for i in activity]
		activity = sorted(activity, key=int)[-1]
		return activity
	except:
		pass


def getCollectedActivity():
	try:
		i = getTraktAsJson('/sync/last_activities')
		activity = []
		activity.append(i['movies']['collected_at'])
		activity.append(i['episodes']['collected_at'])
		activity = [int(cleandate.iso_2_utc(i)) for i in activity]
		activity = sorted(activity, key=int)[-1]
		return activity
	except:
		pass


def cachesyncMovies(timeout=0):
	indicators = cache.get(syncMovies, timeout)
	return indicators


def timeoutsyncMovies():
	timeout = cache.timeout(syncMovies)
	return timeout


def syncMovies():
	try:
		if getTraktCredentialsInfo() is False:
			return
		indicators = getTraktAsJson('/users/me/watched/movies')
		indicators = [i['movie']['ids'] for i in indicators]
		indicators = [str(i['imdb']) for i in indicators if 'imdb' in i]
		return indicators
	except:
		pass


def watchedMovies():
	try:
		if getTraktCredentialsInfo() is False:
			return
		return getTraktAsJson('/users/me/watched/movies?extended=full')
	except:
		pass


def watchedMoviesTime(imdb):
	try:
		imdb = str(imdb)
		items = watchedMovies()
		for item in items:
			if str(item['movie']['ids']['imdb']) == imdb:
				return item['last_watched_at']
	except:
		pass


def cachesyncTV(imdb):
	threads = [threading.Thread(target = cachesyncTVShows), threading.Thread(target = cachesyncSeason, args = (imdb,))]
	[i.start() for i in threads]
	[i.join() for i in threads]


def cachesyncTVShows(timeout=0):
	indicators = cache.get(syncTVShows, timeout)
	return indicators


def timeoutsyncTVShows():
	timeout = cache.timeout(syncTVShows)
	return timeout


def syncTVShows():
	try:
		if getTraktCredentialsInfo() is False:
			return
		indicators = getTraktAsJson('/users/me/watched/shows?extended=full')
		indicators = [(i['show']['ids']['tvdb'], i['show']['aired_episodes'], sum([[(s['number'], e['number']) for e in s['episodes']] for s in i['seasons']], [])) for i in indicators]
		indicators = [(str(i[0]), int(i[1]), i[2]) for i in indicators]
		return indicators
	except:
		pass


def watchedShows():
	try:
		if getTraktCredentialsInfo() is False:
			return
		return getTraktAsJson('/users/me/watched/shows?extended=full')
	except:
		pass


def watchedShowsTime(tvdb, season, episode):
	try:
		tvdb = str(tvdb)
		season = int(season)
		episode = int(episode)
		items = watchedShows()

		for item in items:
			if str(item['show']['ids']['tvdb']) == tvdb:
				seasons = item['seasons']
				for s in seasons:
					if s['number'] == season:
						episodes = s['episodes']
						for e in episodes:
							if e['number'] == episode:
								return e['last_watched_at']
	except:
		pass


def cachesyncSeason(imdb, timeout=0):
	indicators = cache.get(syncSeason, timeout, imdb)
	return indicators


def timeoutsyncSeason(imdb):
	timeout = cache.timeout(syncSeason, imdb)
	return timeout


def syncSeason(imdb):
	try:
		if getTraktCredentialsInfo() is False: return

		if control.setting('tv.specials') == 'true':
			indicators = getTraktAsJson('/shows/%s/progress/watched?specials=true&hidden=true' % imdb)
		else:
			indicators = getTraktAsJson('/shows/%s/progress/watched?specials=false&hidden=false' % imdb)

		indicators = indicators['seasons']
		indicators = [(i['number'], [x['completed'] for x in i['episodes']]) for i in indicators]
		indicators = ['%01d' % int(i[0]) for i in indicators if False not in i[1]]
		return indicators
	except:
		pass


def showCount(imdb, refresh = True, wait = False):
	try:
		if not imdb:
			return None

		result = {'total': 0, 'watched': 0, 'unwatched': 0}
		indicators = seasonCount(imdb = imdb, refresh = refresh, wait = wait)

		for indicator in indicators:
			result['total'] += indicator['total']
			result['watched'] += indicator['watched']
			result['unwatched'] += indicator['unwatched']
		return result
	except:
		return None


def seasonCount(imdb, refresh = True, wait = False):
	try:
		if not imdb:
			return None

		if not imdb.startswith('tt'):
			imdb = 'tt' + imdb

		indicators = cache.cache_existing(_seasonCountRetrieve, imdb)

		if refresh:
			# NB: Do not retrieve a fresh count, otherwise loading show/season menus are slow.
			thread = threading.Thread(target = _seasonCountCache, args = (imdb,))
			thread.start()
			if wait:
				thread.join()
				indicators = cache.cache_existing(_seasonCountRetrieve, imdb)
		return indicators
	except:
		return None


def _seasonCountCache(imdb):
	return cache.get(_seasonCountRetrieve, 0, imdb)


def _seasonCountRetrieve(imdb):
	try:
		if getTraktCredentialsInfo() is False:
			return

		if control.setting('tv.specials') == 'true':
			indicators = getTraktAsJson('/shows/%s/progress/watched?specials=true&hidden=false&count_specials=true' % imdb)
		else:
			indicators = getTraktAsJson('/shows/%s/progress/watched?specials=false&hidden=false' % imdb)
		seasons = indicators['seasons']

		return [{'total': season['aired'], 'watched': season['completed'], 'unwatched': season['aired'] - season['completed']} for season in seasons]
		# return [{season['number']: {'total': season['aired'], 'watched': season['completed'], 'unwatched': season['aired'] - season['completed']} for season in seasons}]
	except:
		log_utils.error()
		return None


def markMovieAsWatched(imdb):
	if not imdb.startswith('tt'):
		imdb = 'tt' + imdb
	return getTrakt('/sync/history', {"movies": [{"ids": {"imdb": imdb}}]})[0]


def markMovieAsNotWatched(imdb):
	if not imdb.startswith('tt'):
		imdb = 'tt' + imdb
	return getTrakt('/sync/history/remove', {"movies": [{"ids": {"imdb": imdb}}]})[0]


def markTVShowAsWatched(imdb, tvdb):
	if imdb and not imdb.startswith('tt'):
		imdb = 'tt' + imdb
	result = getTrakt('/sync/history', {"shows": [{"ids": {"tvdb": tvdb}}]})[0]
	seasonCount(imdb)
	return result


def markTVShowAsNotWatched(imdb, tvdb):
	if imdb and not imdb.startswith('tt'):
		imdb = 'tt' + imdb
	result = getTrakt('/sync/history/remove', {"shows": [{"ids": {"tvdb": tvdb}}]})[0]
	seasonCount(imdb)
	return result


def markSeasonAsWatched(imdb, tvdb, season):
	if imdb and not imdb.startswith('tt'):
		imdb = 'tt' + imdb
	season = int('%01d' % int(season))
	result = getTrakt('/sync/history', {"shows": [{"seasons": [{"number": season}], "ids": {"tvdb": tvdb}}]})[0]
	seasonCount(imdb)
	return result


def markSeasonAsNotWatched(imdb, tvdb, season):
	if imdb and not imdb.startswith('tt'):
		imdb = 'tt' + imdb
	season = int('%01d' % int(season))
	result = getTrakt('/sync/history/remove', {"shows": [{"seasons": [{"number": season}], "ids": {"tvdb": tvdb}}]})[0]
	seasonCount(imdb)
	return result


def markEpisodeAsWatched(imdb, tvdb, season, episode):
	if imdb and not imdb.startswith('tt'):
		imdb = 'tt' + imdb
	season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
	result = getTrakt('/sync/history', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"tvdb": tvdb}}]})[0]
	seasonCount(imdb)
	return result


def markEpisodeAsNotWatched(imdb, tvdb, season, episode):
	if imdb and not imdb.startswith('tt'):
		imdb = 'tt' + imdb
	season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
	result = getTrakt('/sync/history/remove', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"tvdb": tvdb}}]})[0]
	seasonCount(imdb)
	return result


def getMovieTranslation(id, lang, full=False):
	url = '/movies/%s/translations/%s' % (id, lang)
	try:
		item = cache.get(getTraktAsJson, 48, url)[0]
		result = item if full else item.get('title')
		return None if result == 'none' else result
	except:
		pass


def getTVShowTranslation(id, lang, season=None, episode=None, full=False):
	if season and episode:
		url = '/shows/%s/seasons/%s/episodes/%s/translations/%s' % (id, season, episode, lang)
	else:
		url = '/shows/%s/translations/%s' % (id, lang)
	try:
		item = cache.get(getTraktAsJson, 48, url)[0]
		result = item if full else item.get('title')
		return None if result == 'none' else result
	except:
		pass


def getMovieSummary(id, full=True):
	try:
		url = '/movies/%s' % id
		if full:
			url += '?extended=full'
		return cache.get(getTraktAsJson, 48, url)
	except:
		log_utils.error()


def getTVShowSummary(id, full=True):
	try:
		url = '/shows/%s' % id
		if full:
			url += '?extended=full'
		return cache.get(getTraktAsJson, 48, url)
	except:
		log_utils.error()


def getEpisodeSummary(id, season, episode, full=True):
	try:
		url = '/shows/%s/seasons/%s/episodes/%s' % (id, season, episode)
		if full:
			url += '&extended=full'
		return cache.get(getTraktAsJson, 48, url)
	except:
		log_utils.error()


def getSeasons(id, full=True):
	try:
		url = '/shows/%s/seasons' % (id)
		if full:
			url += '&extended=full'
		return cache.get(getTraktAsJson, 48, url)
	except:
		log_utils.error()


def sort_list(sort_key, sort_direction, list_data):
	reverse = False if sort_direction == 'asc' else True
	# log_utils.log('sort_key = %s' % str(sort_key), __name__, log_utils.LOGDEBUG)
	if sort_key == 'rank':
		return sorted(list_data, key=lambda x: x['rank'], reverse=reverse)
	elif sort_key == 'added':
		return sorted(list_data, key=lambda x: x['listed_at'], reverse=reverse)
	elif sort_key == 'title':
		return sorted(list_data, key=lambda x: utils.title_key(x[x['type']].get('title')), reverse=reverse)
	elif sort_key == 'released':
		return sorted(list_data, key=lambda x: _released_key(x[x['type']]), reverse=reverse)
	elif sort_key == 'runtime':
		return sorted(list_data, key=lambda x: x[x['type']].get('runtime', 0), reverse=reverse)
	elif sort_key == 'popularity':
		return sorted(list_data, key=lambda x: x[x['type']].get('votes', 0), reverse=reverse)
	elif sort_key == 'percentage':
		return sorted(list_data, key=lambda x: x[x['type']].get('rating', 0), reverse=reverse)
	elif sort_key == 'votes':
		return sorted(list_data, key=lambda x: x[x['type']].get('votes', 0), reverse=reverse)
	else:
		return list_data


def getMovieAliases(id):
	try:
		return cache.get(getTraktAsJson, 48, '/movies/%s/aliases' % id)
	except:
		return []


def getTVShowAliases(id):
	try:
		return cache.get(getTraktAsJson, 48, '/shows/%s/aliases' % id)
	except:
		return []


def getPeople(id, content_type, full=True):
	try:
		url = '/%s/%s/people' % (content_type, id)
		if full:
			url += '?extended=full'
		return cache.get(getTraktAsJson, 48, url)
	except:
		log_utils.error()


def SearchAll(title, year, full=True):
	try:
		return SearchMovie(title, year, full) + SearchTVShow(title, year, full)
	except:
		return


def SearchMovie(title, year, full=True):
	try:
		url = '/search/movie?query=%s' % title
		if year:
			url += '&year=%s' % year
		if full:
			url += '&extended=full'
		return cache.get(getTraktAsJson, 48, url)
	except:
		return


def SearchTVShow(title, year, full=True):
	try:
		url = '/search/show?query=%s' % title
		if year:
			url += '&year=%s' % year
		if full:
			url += '&extended=full'
		return cache.get(getTraktAsJson, 48, url)
	except:
		return


def SearchEpisode(title, season, episode, full=True):
	try:
		url = '/search/%s/seasons/%s/episodes/%s' % (title, season, episode)
		if full:
			url += '&extended=full'
		return cache.get(getTraktAsJson, 48, url)
	except:
		return


def getGenre(content, type, type_id):
	try:
		r = '/search/%s/%s?type=%s&extended=full' % (type, type_id, content)
		r = cache.get(getTraktAsJson, 48, r)
		r = r[0].get(content, {}).get('genres', [])
		return r
	except:
		return []


def IdLookup(content, type, type_id):
	try:
		r = '/search/%s/%s?type=%s' % (type, type_id, content)
		r = cache.get(getTraktAsJson, 48, r)
		return r[0].get(content, {}).get('ids', [])
	except:
		return {}


def _scrobbleType(type):
	if type == 'show' or type == 'season' or type == 'episode':
		return 'episode'
	else:
		return 'movie'


def scrobbleProgress(type, imdb = None, tvdb = None, season = None, episode = None):
	try:
		type = _scrobbleType(type)

		if imdb is not None:
			imdb = str(imdb)

		if tvdb is not None:
			tvdb = int(tvdb)

		if episode is not None:
			episode = int(episode)

		if episode is not None:
			episode = int(episode)

		link = '/sync/playback/type'
		items = getTraktAsJson(link)

		if type == 'episode':
			if imdb and items:
				for item in items:
					if 'show' in item and 'imdb' in item['show']['ids'] and item['show']['ids']['imdb'] == imdb:
						if item['episode']['season'] == season and item['episode']['number'] == episode:
							return item['progress']
			if tvdb:
				for item in items:
					if 'show' in item and 'tvdb' in item['show']['ids'] and item['show']['ids']['tvdb'] == tvdb:
						if item['episode']['season'] == season and item['episode']['number'] == episode:
							return item['progress']
		else:
			if imdb and items:
				for item in items:
					if 'movie' in item and 'imdb' in item['movie']['ids'] and item['movie']['ids']['imdb'] == imdb:
						return item['progress']
	except:
		log_utils.error()
	return 0


def scrobbleUpdate(action, type, imdb = None, tvdb = None, season = None, episode = None, progress = 0):
	try:
		if action:
			type = _scrobbleType(type)

			if imdb is not None:
				imdb = str(imdb)

			if tvdb is not None:
				tvdb = int(tvdb)

			if season is not None:
				season = int(season)

			if episode is not None:
				episode = int(episode)

			if imdb:
				link = '/search/imdb/' + str(imdb)

			elif tvdb:
				link = '/search/tvdb/' + str(tvdb)

			if type == 'episode':
				link += '?type=show'
			else:
				link += '?type=movie'

			items = cache.get(getTraktAsJson, 760, link)

			if len(items) > 0:
				item = items[0]
				if type == 'episode':
					slug = item['show']['ids']['slug']
					link = '/shows/%s/seasons/%d/episodes/%d' % (slug, season, episode)
					item = cache.get(getTraktAsJson, 760, link)
				else:
					item = item['movie']

				if item:
					link = '/scrobble/' + action
					data = {
						type : item,
						'progress': progress,
						'app_version': control.addonVersion(addon='plugin.video.venom'),
					}
					result = getTrakt(url = link, post = data)
					return 'progress' in result
	except:
		pass
	return False


def _released_key(item):
	if 'released' in item:
		return item['released']
	elif 'first_aired' in item:
		return item['first_aired']
	else:
		return 0

