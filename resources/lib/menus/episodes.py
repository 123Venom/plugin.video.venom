# -*- coding: utf-8 -*-

"""
	Venom Add-on
"""

import os, sys, re, json, zipfile
import StringIO, urllib, urllib2, urlparse
import datetime, copy

from resources.lib.modules import cache
from resources.lib.modules import cleangenre
from resources.lib.modules import client
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import playcount
from resources.lib.modules import trakt
from resources.lib.modules import views
from resources.lib.modules import workers

from resources.lib.extensions import tools

params = dict(urlparse.parse_qsl(sys.argv[2].replace('?', ''))) if len(sys.argv) > 1 else dict()
action = params.get('action')
notificationSound = False if control.setting('notification.sound') == 'false' else True
disable_fanarttv = control.setting('disable.fanarttv')


class Episodes:
	def __init__(self, type='show', notifications=True):
		self.count = int(control.setting('page.item.limit'))
		self.list = []
		self.threads = []
		self.type = type
		self.lang = control.apiLanguage()['tvdb']
		# self.season_special = False
		self.notifications = notifications

		control.playlist.clear()

		self.datetime = (datetime.datetime.utcnow() - datetime.timedelta(hours=5))
		self.systime = (self.datetime).strftime('%Y%m%d%H%M%S%f')
		self.today_date = (self.datetime).strftime('%Y-%m-%d')

		# self.tvdb_key = control.setting('tvdb.user')
		# if self.tvdb_key == '' or self.tvdb_key is None:
			# self.tvdb_key = '1D62F2F90030C444'
		self.tvdb_key = 'MUQ2MkYyRjkwMDMwQzQ0NA=='

		self.tvdb_info_link = 'http://thetvdb.com/api/%s/series/%s/all/%s.zip' % (self.tvdb_key.decode('base64'), '%s', '%s')
		self.tvdb_by_query = 'http://thetvdb.com/api/GetSeries.php?seriesname=%s'
		self.tvdb_image = 'http://thetvdb.com/banners/'
		self.tvdb_poster = 'http://thetvdb.com/banners/_cache/'

		self.trakt_user = control.setting('trakt.user').strip()
		self.traktCredentials = trakt.getTraktCredentialsInfo()

		self.trakt_link = 'http://api.trakt.tv'
		# self.traktlist_link = 'http://api.trakt.tv/users/%s/lists/%s/items/episodes?page=1&limit=%d' % ('%s', '%s', self.count)
		self.traktlist_link = 'http://api.trakt.tv/users/%s/lists/%s/items/episodes'
		self.traktlists_link = 'http://api.trakt.tv/users/me/lists'
		self.traktlikedlists_link = 'http://api.trakt.tv/users/likes/lists?limit=1000000'
		# self.traktwatchlist_link = 'http://api.trakt.tv/users/me/watchlist/episodes?page=1&limit=%d' % self.count
		self.traktwatchlist_link = 'http://api.trakt.tv/users/me/watchlist/episodes'
		# self.trakthistory_link = 'http://api.trakt.tv/users/me/history/shows?page=1&limit=%d' % self.count
		self.trakthistory_link = 'http://api.trakt.tv/users/me/history/shows?limit=200'
		self.progress_link = 'http://api.trakt.tv/users/me/watched/shows'
		self.hiddenprogress_link = 'http://api.trakt.tv/users/hidden/progress_watched?limit=1000&type=show'

		self.traktonDeck_link = 'http://api.trakt.tv/sync/playback/episodes?extended=full&limit=20'
		self.traktunfinished_link = 'http://api.trakt.tv/sync/playback/episodes'

		self.mycalendar_link = 'http://api.trakt.tv/calendars/my/shows/date[30]/31/'

		self.tvmaze_link = 'http://api.tvmaze.com'
		self.added_link = 'http://api.tvmaze.com/schedule'
		self.calendar_link = 'http://api.tvmaze.com/schedule?date=%s'

		self.showunaired = control.setting('showunaired') or 'true'
		self.unairedcolor = control.setting('unaired.identify')
		self.unairedcolor = self.getUnairedColor(self.unairedcolor)


	def getUnairedColor(self, n):
		if n == '0': n = 'blue'
		elif n == '1': n = 'red'
		elif n == '2': n = 'yellow'
		elif n == '3': n = 'deeppink'
		elif n == '4': n = 'cyan'
		elif n == '5': n = 'lawngreen'
		elif n == '6': n = 'gold'
		elif n == '7': n = 'magenta'
		elif n == '8': n = 'yellowgreen'
		elif n == '9': n = 'skyblue'
		elif n == '10': n = 'lime'
		elif n == '11': n = 'limegreen'
		elif n == '12': n = 'deepskyblue'
		elif n == '13': n = 'white'
		elif n == '14': n = 'whitesmoke'
		elif n == '15': n = 'nocolor'
		else: n == 'skyblue'
		return n


	@classmethod
	def mark(self, title, imdb, tvdb, season, episode, watched=True):
		if watched:
			self.markWatch(title=title, imdb=imdb, tvdb=tvdb, season=season, episode=episode)
		else:
			self.markUnwatch(title=title, imdb=imdb, tvdb=tvdb, season=season, episode=episode)


	@classmethod
	def markWatch(self, title, imdb, tvdb, season, episode):
		control.busy()
		playcount.episodes(imdb, tvdb, season, episode, '7')
		control.hide()
		control.notification(title=35510, message=35513, icon='INFO', sound=notificationSound)


	@classmethod
	def markUnwatch(self, title, imdb, tvdb, season, episode):
		control.busy()
		playcount.episodes(imdb, tvdb, season, episode, '6')
		control.hide()
		control.notification(title=35511, message=35513, icon='INFO', sound=notificationSound)


	def sort(self, type='shows'):
		try:
			attribute = int(control.setting('sort.%s.type' % type))
			reverse = int(control.setting('sort.%s.order' % type)) == 1
			if self.list is None:
				return
			if attribute > 0:
				if attribute == 1:
					try:
						self.list = sorted(self.list, key=lambda k: re.sub('(^the |^a |^an )', '', k['tvshowtitle'].lower()), reverse=reverse)
					except:
						self.list = sorted(self.list, key=lambda k: k['title'].lower(), reverse=reverse)
				elif attribute == 2:
					self.list = sorted(self.list, key=lambda k: float(k['rating']), reverse=reverse)
				elif attribute == 3:
					self.list = sorted(self.list, key=lambda k: int(k['votes'].replace(',', '')), reverse=reverse)
				elif attribute == 4:
					for i in range(len(self.list)):
						if 'premiered' not in self.list[i]:
							self.list[i]['premiered'] = ''
					self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=reverse)
				elif attribute == 5:
					for i in range(len(self.list)):
						if 'added' not in self.list[i]:
							self.list[i]['added'] = ''
					self.list = sorted(self.list, key=lambda k: k['added'], reverse=reverse)
				elif attribute == 6:
					for i in range(len(self.list)):
						if 'lastplayed' not in self.list[i]:
							self.list[i]['lastplayed'] = ''
					self.list = sorted(self.list, key=lambda k: k['lastplayed'], reverse=reverse)
			elif reverse:
				self.list = reversed(self.list)
		except:
			log_utils.error()


	def get(self, tvshowtitle, year, imdb, tvdb, season=None, episode=None, idx=True):
		from resources.lib.menus import seasons
		try:
			if season is None and episode is None:
				self.list = cache.get(seasons.Seasons().tvdb_list, 1, tvshowtitle, year, imdb, tvdb, self.lang, '-1')
			elif episode is None:
				self.list = cache.get(seasons.Seasons().tvdb_list, 1, tvshowtitle, year, imdb, tvdb, self.lang, season)
			else:
				self.list = cache.get(seasons.Seasons().tvdb_list, 1, tvshowtitle, year, imdb, tvdb, self.lang, '-1')
				num = [x for x, y in enumerate(self.list) if y['season'] == str(season) and y['episode'] == str(episode)][-1]
				self.list = [y for x, y in enumerate(self.list) if x >= num]

			if idx is True:
				self.episodeDirectory(self.list)

			return self.list
		except:
			try:
				invalid = (self.list is None) or (len(self.list) == 0)
			except:
				invalid = True
			if invalid:
				control.hide()
				if self.notifications:
					control.notification(title=32326, message=33049, icon='INFO', sound=notificationSound)


	def unfinished(self, url):
		try:
			try:
				url = getattr(self, url + '_link')
			except:
				pass

			activity = trakt.getWatchedActivity()

			self.list = []
			if url == self.traktonDeck_link:
				try:
					# if activity > cache.timeout(self.trakt_list, url, self.trakt_user, False):
					if activity > cache.timeout(self.trakt_episodes_list, url, self.trakt_user, self.lang):
						raise Exception()
					# self.list = cache.get(self.trakt_list, 720, url, self.trakt_user, False)
					self.list = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang)
				except:
					# self.list = cache.get(self.trakt_list, 0, url, self.trakt_user, False)
					self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)

			if url == self.traktunfinished_link :
				try:
					# if activity > cache.timeout(self.trakt_list, url, self.trakt_user, False):
					if activity > cache.timeout(self.trakt_episodes_list, url, self.trakt_user,self.lang):
						raise Exception()
					# self.list = cache.get(self.trakt_list, 720, url, self.trakt_user, False)
					self.list = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang)
				except:
					# self.list = cache.get(self.trakt_list, 0, url, self.trakt_user, False)
					self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)

			self.sort(type = 'calendar')
			self.episodeDirectory(self.list, unfinished=True, next=False)

			return self.list
		except:
			log_utils.error()
			try:
				invalid = (self.list is None or len(self.list) == 0)
			except:
				invalid = True
			if invalid:
				control.idle()
				if self.notifications:
					control.notification(title=32326, message=33049, icon='INFO', sound=notificationSound)


	def calendar(self, url):
		try:
			try:
				url = getattr(self, url + '_link')
			except:
				pass

			direct = False if control.setting('tvshows.direct') == 'false' else True

			if self.trakt_link in url and url == self.progress_link:
				# try:
					# activity = trakt.getWatchedActivity()
					# if activity > cache.timeout(self.trakt_progress_list, url, self.trakt_user, self.lang, direct):
						# raise Exception()
					# self.list = cache.get(self.trakt_progress_list, 12, url, self.trakt_user, self.lang, direct)
				# except:
					# self.list = cache.get(self.trakt_progress_list, 0, url, self.trakt_user, self.lang, direct)
				# self.sort(type = 'progress')

				self.list = cache.get(self.trakt_progress_list, 0, url, self.trakt_user, self.lang, direct)
				self.sort(type = 'progress')


			elif self.trakt_link in url and url == self.mycalendar_link:
				self.list = cache.get(self.trakt_episodes_list, 0.3, url, self.trakt_user, self.lang)
				self.sort(type = 'calendar')

			elif self.trakt_link in url and '/users/' in url:
				# self.list = cache.get(self.trakt_list, 0.3, url, self.trakt_user, True)
				self.list = cache.get(self.trakt_episodes_list, 0.3, url, self.trakt_user, self.lang)
				# self.list = self.list[::-1]
				self.sort(type = 'calendar')

			elif self.trakt_link in url:
				self.list = cache.get(self.trakt_list, 1, url, self.trakt_user, True)

			elif self.tvmaze_link in url and url == self.added_link:
				urls = [i['url'] for i in self.calendars(idx=False)][:5]
				self.list = []
				for url in urls:
					self.list += cache.get(self.tvmaze_list, 720, url, True)

			elif self.tvmaze_link in url:
				self.list = cache.get(self.tvmaze_list, 1, url, False)

			self.episodeDirectory(self.list, unfinished=False, next=False)
			return self.list
		except:
			pass


	def seasonCount(self, items, index):
		if 'seasoncount' not in items[index] or not items[index]['seasoncount']:
			thread = workers.Thread(self._seasonCount, items, index)
			self.threads.append(thread)
			thread.start()


	def seasonCountWait(self):
		[i.join() for i in self.threads]
		self.threads = []


	def _seasonCount(self, items, index):
		try:
			from resources.lib.menus import seasons
			items[index]['seasoncount'] = seasons.Seasons().seasonCount(items[index]['tvshowtitle'],
											items[index]['year'], items[index]['imdb'],
											items[index]['tvdb'], items[index]['season'])
		except:
			log_utils.error()


	def widget(self):
		if trakt.getTraktIndicatorsInfo() is True:
			setting = control.setting('tv.widget.alt')
		else:
			setting = control.setting('tv.widget')
		if setting == '2':
			self.calendar(self.progress_link)
		elif setting == '3':
			self.calendar(self.mycalendar_link)
		else:
			self.calendar(self.added_link)


	def calendars(self, idx=True):
		m = control.lang(32060).encode('utf-8').split('|')
		try:
			months = [(m[0], 'January'), (m[1], 'February'), (m[2], 'March'), (m[3], 'April'), (m[4], 'May'),
					(m[5], 'June'), (m[6], 'July'), (m[7], 'August'), (m[8], 'September'), (m[9], 'October'),
					(m[10], 'November'), (m[11], 'December')]
		except:
			months = []

		d = control.lang(32061).encode('utf-8').split('|')
		try:
			days = [(d[0], 'Monday'), (d[1], 'Tuesday'), (d[2], 'Wednesday'), (d[3], 'Thursday'), (d[4], 'Friday'),
					(d[5], 'Saturday'), (d[6], 'Sunday')]
		except:
			days = []

		for i in range(0, 30):
			try:
				name = (self.datetime - datetime.timedelta(days=i))
				name = (control.lang(32062) % (name.strftime('%A'), name.strftime('%d %B'))).encode('utf-8')
				for m in months:
					name = name.replace(m[1], m[0])
				for d in days:
					name = name.replace(d[1], d[0])
				try:
					name = name.encode('utf-8')
				except:
					pass
				url = self.calendar_link % (self.datetime - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
				self.list.append({'name': name, 'url': url, 'image': 'calendar.png', 'icon': 'DefaultYear.png', 'action': 'calendar'})
			except:
				pass
		if idx is True:
			self.addDirectory(self.list)
		return self.list


	def userlists(self):
		userlists = []
		try:
			if self.traktCredentials is False:
				raise Exception()
			activity = trakt.getActivity()
		except:
			pass

		try:
			if self.traktCredentials is False:
				raise Exception()
			self.list = []
			try:
				if activity > cache.timeout(self.trakt_user_list, self.traktlists_link, self.trakt_user):
					raise Exception()
				userlists += cache.get(self.trakt_user_list, 720, self.traktlists_link, self.trakt_user)
			except:
				userlists += cache.get(self.trakt_user_list, 0, self.traktlists_link, self.trakt_user)
		except:
			pass

		try:
			if self.traktCredentials is False:
				raise Exception()
			self.list = []
			try:
				if activity > cache.timeout(self.trakt_user_list, self.traktlikedlists_link, self.trakt_user):
					raise Exception()
				userlists += cache.get(self.trakt_user_list, 720, self.traktlikedlists_link, self.trakt_user)
			except:
				userlists += cache.get(self.trakt_user_list, 0, self.traktlikedlists_link, self.trakt_user)
		except:
			pass

		self.list = []

		# Filter the user's own lists that were
		for i in range(len(userlists)):
			contains = False
			adapted = userlists[i]['url'].replace('/me/', '/%s/' % self.trakt_user)
			for j in range(len(self.list)):
				if adapted == self.list[j]['url'].replace('/me/', '/%s/' % self.trakt_user):
					contains = True
					break
			if not contains:
				self.list.append(userlists[i])

		for i in range(0, len(self.list)): self.list[i].update({'image': 'trakt.png', 'action': 'calendar'})

		# Trakt Watchlist
		if self.traktCredentials is True:
			self.list.insert(0, {'name': control.lang(32033).encode('utf-8'), 'url': self.traktwatchlist_link, 'image': 'trakt.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'tvshows'})

		self.addDirectory(self.list, queue=True)
		return self.list


	def trakt_user_list(self, url, user):
		try:
			result = trakt.getTrakt(url)
			items = json.loads(result)
		except:
			pass
		for item in items:
			try:
				try:
					name = item['list']['name']
				except:
					name = item['name']
				name = client.replaceHTMLCodes(name)
				name = name.encode('utf-8')
				try:
					url = (trakt.slug(item['list']['user']['username']), item['list']['ids']['slug'])
				except:
					url = ('me', item['ids']['slug'])
				url = self.traktlist_link % url
				url = url.encode('utf-8')

				self.list.append({'name': name, 'url': url})
			except:
				pass

		self.list = sorted(self.list, key=lambda k: re.sub('(^the |^a |^an )', '', k['name'].lower()))
		return self.list


	def trakt_progress_list(self, url, user, lang, direct=False):
		# from resources.lib.menus import seasons
		try:
			url += '?extended=full'
			result = trakt.getTrakt(url)
			result = json.loads(result)
			items = []
		except:
			return

		for item in result:
			try:
				num_1 = 0
				for i in range(0, len(item['seasons'])):
					num_1 += len(item['seasons'][i]['episodes'])
				num_2 = int(item['show']['aired_episodes'])
				if num_1 >= num_2:
					continue

				season = str(item['seasons'][-1]['number'])
				episode = str(item['seasons'][-1]['episodes'][-1]['number'])

				try:
					tvshowtitle = (item['show']['title']).encode('utf-8')
				except:
					tvshowtitle = item['show']['title']
				if tvshowtitle is None or tvshowtitle == '':
					continue

				year = str(item.get('show').get('year'))

				imdb = str(item.get('show', {}).get('ids', {}).get('imdb', '0'))
				if imdb == '' or imdb is None or imdb == 'None':
					imdb = '0'

				tmdb = str(item.get('show', {}).get('ids', {}).get('tmdb', '0'))
				if tmdb == '' or tmdb is None or tmdb == 'None':
					tmdb = '0'

				tvdb = str(item.get('show', {}).get('ids', {}).get('tvdb', '0'))
				if tvdb == '' or tvdb is None or tvdb == 'None':
					tvdb = '0'

# ### episode IDS
				episodeIDS = {}
				if control.setting('enable.upnext') == 'true':
					episodeIDS = trakt.getEpisodeSummary(imdb, season, episode, full=False) or {}
					if episodeIDS != {}:
						episodeIDS = episodeIDS.get('ids', {})
##------------------

				try:
					added = item['show']['updated_at']
				except:
					added = None

				lastplayed = item.get('show').get('last_watched_at') or item.get('last_watched_at')

				studio = item.get('show').get('network', '0')
				status = item.get('show').get('status', '0')
				trailer =  item.get('show').get('trailer', '0')

				values = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year, 'snum': season,
								'enum': episode, 'added': added, 'lastplayed': lastplayed, 'studio': studio, 'status': status, 'episodeIDS': episodeIDS}

				try:
					air = item['show']['airs']
					values['airday'] = air['day']
					values['airtime'] = air['time']
					values['airzone'] = air['timezone']
				except:
					pass

				items.append(values)
			except:
				pass

		try:
			result = trakt.getTrakt(self.hiddenprogress_link)
			result = json.loads(result)
			result = [str(i['show']['ids']['tvdb']) for i in result]

			items = [i for i in items if i['tvdb'] not in result]
		except:
			pass

		def items_list(i):
			try:
				url = self.tvdb_info_link % (i['tvdb'], lang)
				data = urllib2.urlopen(url, timeout=10).read()
				zip = zipfile.ZipFile(StringIO.StringIO(data))

				result = zip.read('%s.xml' % lang)
				artwork = zip.read('banners.xml')
				actors = zip.read('actors.xml')
				zip.close()

				result = result.split('<Episode>')
				item = [x for x in result if '<EpisodeNumber>' in x]
				item2 = result[0]

				num = [x for x,y in enumerate(item) if re.compile('<SeasonNumber>(.+?)</SeasonNumber>').findall(y)[0] == str(i['snum']) and re.compile('<EpisodeNumber>(.+?)</EpisodeNumber>').findall(y)[0] == str(i['enum'])][-1]
				# TVDb index out of order for Season0 and Episodes now.  This now fails allot getting next episode in index and no simple fix to fetch next episode when we don't know when a season ends. Index based is right way but TVDb fucked us!!
				item = [y for x,y in enumerate(item) if x > num][0]

				artwork = artwork.split('<Banner>')
				artwork = [x for x in artwork if '<Language>en</Language>' in x and '<BannerType>season</BannerType>' in x]
				artwork = [x for x in artwork if not 'seasonswide' in re.findall('<BannerPath>(.+?)</BannerPath>', x)[0]]

				premiered = client.parseDOM(item, 'FirstAired')[0]

				try:
					added = i['added']
				except:
					added = None

				try:
					lastplayed = i['lastplayed']
				except:
					lastplayed = None

				try:
					episodeIDS = i['episodeIDS']
				except:
					episodeIDS = {}

				status = i['status'] or client.parseDOM(item2, 'Status')[0]

				unaired = ''

				if status.lower() == 'ended':
					pass
				elif premiered == '0':
					raise Exception()
				elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
					unaired = 'true'
					if self.showunaired != 'true':
						raise Exception()

				title = client.parseDOM(item, 'EpisodeName')[0]
				title = client.replaceHTMLCodes(title)
				title = title.encode('utf-8')

				season = client.parseDOM(item, 'SeasonNumber')[0]
				season = '%01d' % int(season)

				if control.setting('tv.specials') == 'false' and season == '0':
					raise Exception()

				episode = client.parseDOM(item, 'EpisodeNumber')[0]
				episode = re.sub('[^0-9]', '', '%01d' % int(episode))

				seasoncount = '0'
				# seasoncount = seasons.Seasons.seasonCountParse(season=season, items=result)
				# log_utils.log('seasoncount = %s for title = %s' % (str(seasoncount), str(title)), __name__, log_utils.LOGDEBUG)

				tvshowtitle = i['tvshowtitle']
				year = str(i.get('year'))
				imdb, tmdb, tvdb = i['imdb'], i['tmdb'], i['tvdb']

				poster = client.parseDOM(item2, 'poster')[0]
				if poster and poster != '':
					poster = self.tvdb_image + poster
				else: poster = '0'

				season_poster = [x for x in artwork if client.parseDOM(x, 'Season')[0] == season]
				try:
					season_poster = client.parseDOM(season_poster[0], 'BannerPath')[0]
				except:
					season_poster = ''
				if season_poster != '':
					season_poster = self.tvdb_image + season_poster
				else:
					season_poster = '0'
				season_poster = client.replaceHTMLCodes(season_poster)
				season_poster = season_poster.encode('utf-8')

				banner = client.parseDOM(item2, 'banner')[0]
				if banner and banner != '':
					banner = self.tvdb_image + banner
				else: banner = '0'

				fanart = client.parseDOM(item2, 'fanart')[0]
				if fanart and fanart != '':
					fanart = self.tvdb_image + fanart
				else: fanart = '0'

				thumb = client.parseDOM(item, 'filename')[0]
				if thumb and thumb != '':
					thumb = self.tvdb_image + thumb
				else: thumb = '0'

				if poster != '0':
					pass
				elif fanart != '0':
					poster = fanart
				elif banner != '0':
					poster = banner

				if banner != '0':
					pass
				elif fanart != '0':
					banner = fanart
				elif poster != '0':
					banner = poster

				if thumb != '0':
					pass
				elif fanart != '0':
					thumb = fanart.replace(self.tvdb_image, self.tvdb_poster)
				elif poster != '0':
					thumb = poster

				studio = i['studio'] or client.parseDOM(item2, 'Network')[0]

				genre = client.parseDOM(item2, 'Genre')[0]
				genre = [x for x in genre.split('|') if x != '']
				genre = ' / '.join(genre)

				duration = client.parseDOM(item2, 'Runtime')[0]

				rating = client.parseDOM(item, 'Rating')[0]
				votes = client.parseDOM(item2, 'RatingCount')[0]

				mpaa = client.parseDOM(item2, 'ContentRating')[0]

				director = client.parseDOM(item, 'Director')[0]
				director = [x for x in director.split('|') if x != '']
				director = (' / '.join(director)).encode('utf-8')
				director = client.replaceHTMLCodes(director)

				writer = client.parseDOM(item, 'Writer')[0]
				writer = [x for x in writer.split('|') if x != '']
				writer = (' / '.join(writer)).encode('utf-8')
				writer = client.replaceHTMLCodes(writer)

				import xml.etree.ElementTree as ET
				tree = ET.ElementTree(ET.fromstring(actors))
				root = tree.getroot()
				castandart = []
				for actor in root.iter('Actor'):
					person = [name.text for name in actor]
					image = person[1]
					name = person[2]
					try: name = client.replaceHTMLCodes(person[2])
					except: pass
					role = person[3]
					try: role = client.replaceHTMLCodes(person[3])
					except: pass
					try:
						try:
							castandart.append({'name': name.encode('utf-8'), 'role': role.encode('utf-8'), 'thumbnail': ((self.tvdb_image + image) if image is not None else '0')})
						except:
							castandart.append({'name': name, 'role': role, 'thumbnail': ((self.tvdb_image + image) if image is not None else '0')})
					except:
						castandart = []
					if len(castandart) == 150: break

				plot = client.parseDOM(item, 'Overview')[0]
				if not plot:
					plot = client.parseDOM(item2, 'Overview')[0]
				plot = client.replaceHTMLCodes(plot)
				plot = plot.encode('utf-8')

				values = {'title': title, 'seasoncount': seasoncount, 'season': season, 'episode': episode,
								'year': year, 'tvshowtitle': tvshowtitle, 'tvshowyear': year, 'premiered': premiered,
								'added': added, 'lastplayed': lastplayed, 'status': status, 'studio': studio, 'genre': genre,
								'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'director': director,
								'writer': writer, 'castandart': castandart, 'plot': plot, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb,
								'poster': poster, 'season_poster': season_poster,  'banner': banner, 'fanart': fanart, 'thumb': thumb,
								'snum': i['snum'], 'enum': i['enum'], 'unaired': unaired, 'episodeIDS': episodeIDS, 'traktProgress': True}

				if not direct:
					values['action'] = 'episodes'

				if 'airday' in i and i['airday'] is not None and i['airday'] != '':
					values['airday'] = i['airday']
				if 'airtime' in i and i['airtime'] is not None and i['airtime'] != '':
					values['airtime'] = i['airtime']
				if 'airzone' in i and i['airzone'] is not None and i['airzone'] != '':
					values['airzone'] = i['airzone']
				self.list.append(values)
			except:
				pass

		items = items[:len(items)]
		threads = []
		for i in items:
			threads.append(workers.Thread(items_list, i))
		[i.start() for i in threads]
		[i.join() for i in threads]

		return self.list


	def trakt_list(self, url, user, count=False):
		try:
			for i in re.findall('date\[(\d+)\]', url):
				url = url.replace('date[%s]' % i, (self.datetime - datetime.timedelta(days=int(i))).strftime('%Y-%m-%d'))

			q = dict(urlparse.parse_qsl(urlparse.urlsplit(url).query))
			q.update({'extended': 'full'})
			q = (urllib.urlencode(q)).replace('%2C', ',')
			u = url.replace('?' + urlparse.urlparse(url).query, '') + '?' + q

			itemlist = []
			items = trakt.getTraktAsJson(u)
		except:
			return

		try:
			q = dict(urlparse.parse_qsl(urlparse.urlsplit(url).query))
			if int(q['limit']) != len(items):
				raise Exception()
			q.update({'page': str(int(q['page']) + 1)})
			q = (urllib.urlencode(q)).replace('%2C', ',')
			next = url.replace('?' + urlparse.urlparse(url).query, '') + '?' + q
		except:
			next = ''

		for item in items:
			try:
				if 'show' not in item or 'episode' not in item:
					continue

				try:
					title = (item['episode']['title']).encode('utf-8')
				except:
					title = item['episode']['title']
				if title is None or title == '':
					continue

				season = item['episode']['season']
				season = re.sub('[^0-9]', '', '%01d' % int(season))

				if control.setting('tv.specials') == 'false' and season == '0':
					continue

				episode = item['episode']['number']
				episode = re.sub('[^0-9]', '', '%01d' % int(episode))
				if episode == '0':
					continue

				try:
					tvshowtitle = (item['show']['title']).encode('utf-8')
				except:
					tvshowtitle = item['show']['title']
				if tvshowtitle is None or tvshowtitle == '':
					continue

				year = str(item.get('show').get('year'))

				try:
					progress = max(0, min(1, item['progress'] / 100.0))
				except:
					progress = None

				imdb = item.get('show', {}).get('ids', {}).get('imdb', '0')
				if imdb == '' or imdb is None or imdb == 'None':
					imdb = '0'

				tmdb = str(item.get('show', {}).get('ids', {}).get('tmdb', 0))
				if tmdb == '' or tmdb is None or tmdb == 'None':
					tmdb = '0'

				tvdb = str(item.get('show', {}).get('ids', {}).get('tvdb', 0))
				if tvdb == '' or tvdb is None or tvdb == 'None':
					tvdb = '0'

				episodeIDS = item.get('episode').get('ids', {})

				premiered = item.get('episode').get('first_aired')

				added = item['episode']['updated_at'] or item.get('show').get('updated_at', '0')
				lastplayed = item.get('watched_at', '0')

				studio = item.get('show').get('network')
 
				genre = []
				for i in item['show']['genres']:
					genre.append(i.title())
				if genre == []: genre = 'NA'

				duration = str(item['episode']['runtime']) or str(item.get('show').get('runtime'))

				rating = str(item.get('episode').get('rating'))
				votes = str(format(int(item.get('episode').get('votes')),',d'))

				mpaa = item.get('show').get('certification')

				plot = item['episode']['overview'] or item['show']['overview']
				try:
					plot = plot.encode('utf-8')
				except:
					pass

				trailer = item['show']['trailer']

				values = {'title': title, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle,
							'year': year, 'premiered': premiered, 'added': added, 'lastplayed': lastplayed,
							'status': 'Continuing', 'studio': studio, 'genre': genre, 'duration': duration,
							'rating': rating, 'votes': votes, 'mpaa': mpaa, 'plot': plot, 'imdb': imdb, 'tmdb': tmdb,
							'tvdb': tvdb, 'progress': progress, 'episodeIDS': episodeIDS, 'next': next}

				if 'airday' in item and not item['airday'] is None and item['airday'] != '':
					values['airday'] = item['airday']
				if 'airtime' in item and not item['airtime'] is None and item['airtime'] != '':
					values['airtime'] = item['airtime']
				if 'airzone' in item and not item['airzone'] is None and item['airzone'] != '':
					values['airzone'] = item['airzone']

				try:
					air = item['show']['airs']
					if 'airday' not in item or item['airday'] is None or item['airday'] == '':
						values['airday'] = air['day']
					if 'airtime' not in item or item['airtime'] is None or item['airtime'] == '':
						values['airtime'] = air['time']
					if 'airzone' not in item or item['airzone'] is None or item['airzone'] == '':
						values['airzone'] = air['timezone']
				except:
					log_utils.error()
					pass

				itemlist.append(values)
				if count:
					self.seasonCount(itemlist, len(itemlist) - 1)

			except:
				log_utils.error()
				pass

		if count:
			self.seasonCountWait()

		itemlist = itemlist[::-1]
		return itemlist


	def trakt_episodes_list(self, url, user, lang, direct=True):
		# from resources.lib.menus import seasons

		self.list = []
		items = self.trakt_list(url, user)
		def items_list(i):
			# try:
				# item = [x for x in self.blist if x['tvdb'] == i['tvdb'] and x['season'] == i['season'] and x['episode'] == i['episode']][0]
				# if item['poster'] == '0':
					# raise Exception()
				# self.list.append(item)
				# return
			# except:
				# pass

			try:
				url = self.tvdb_info_link % (i['tvdb'], lang)
				data = urllib2.urlopen(url, timeout=10).read()

				zip = zipfile.ZipFile(StringIO.StringIO(data))
				result = zip.read('%s.xml' % lang)
				artwork = zip.read('banners.xml')
				actors = zip.read('actors.xml')
				zip.close()

				result = result.split('<Episode>')
				item = [(re.findall('<SeasonNumber>%01d</SeasonNumber>' % int(i['season']), x),
						re.findall('<EpisodeNumber>%01d</EpisodeNumber>' % int(i['episode']), x), x) for x in result]
				item = [x[2] for x in item if len(x[0]) > 0 and len(x[1]) > 0][0]
				item2 = result[0]

				artwork = artwork.split('<Banner>')
				artwork = [x for x in artwork if '<Language>en</Language>' in x and '<BannerType>season</BannerType>' in x]
				artwork = [x for x in artwork if not 'seasonswide' in re.findall('<BannerPath>(.+?)</BannerPath>', x)[0]]

				premiered = i['premiered'] or client.parseDOM(item, 'FirstAired')[0]

				status = client.parseDOM(item2, 'Status')[0]
				if not status:
					status = 'Ended'

				title = client.parseDOM(item, 'EpisodeName')[0]
				title = client.replaceHTMLCodes(title)
				title = title.encode('utf-8')

				season = client.parseDOM(item, 'SeasonNumber')[0]
				season = '%01d' % int(season)

				if control.setting('tv.specials') == 'false' and season == '0':
					raise Exception()

				episode = client.parseDOM(item, 'EpisodeNumber')[0]
				episode = re.sub('[^0-9]', '', '%01d' % int(episode))

				seasoncount = '0'
				# seasoncount = seasons.Seasons.seasonCountParse(season=season, items=result)

				tvshowtitle = i['tvshowtitle']
				year = str(i.get('year'))
				imdb, tmdb, tvdb = i['imdb'], i['tmdb'], i['tvdb']

				try:
					progress = i['progress']
				except:
					progress = None

				added = i['added']
				lastplayed = i['lastplayed']
				episodeIDS = i['episodeIDS']

				poster = client.parseDOM(item2, 'poster')[0]
				if poster and poster != '':
					poster = self.tvdb_image + poster
				else: poster = '0'

				banner = client.parseDOM(item2, 'banner')[0]
				if banner and banner != '':
					banner = self.tvdb_image + banner
				else: banner = '0'

				fanart = client.parseDOM(item2, 'fanart')[0]
				if fanart and fanart != '':
					fanart = self.tvdb_image + fanart
				else: fanart = '0'

				thumb = client.parseDOM(item, 'filename')[0]
				if thumb and thumb != '':
					thumb = self.tvdb_image + thumb
				else: thumb = '0'

				season_poster = [x for x in artwork if client.parseDOM(x, 'Season')[0] == season]
				try:
					season_poster = client.parseDOM(season_poster[0], 'BannerPath')[0]
				except:
					season_poster = ''
				if season_poster != '':
					season_poster = self.tvdb_image + season_poster
				else:
					season_poster = '0'
				season_poster = client.replaceHTMLCodes(season_poster)
				season_poster = season_poster.encode('utf-8')

				if poster != '0':
					pass
				elif fanart != '0':
					poster = fanart
				elif banner != '0':
					poster = banner

				if banner != '0':
					pass
				elif fanart != '0':
					banner = fanart
				elif poster != '0':
					banner = poster

				if thumb != '0':
					pass
				elif fanart != '0':
					thumb = fanart.replace(self.tvdb_image, self.tvdb_poster)
				elif poster != '0':
					thumb = poster

				studio = i['studio'] or client.parseDOM(item2, 'Network')[0]

				if 'genre' in i and i['genre'] is not None and i['genre'] != 'NA':
					genre = i['genre'] 
				else:
					genre = client.parseDOM(item2, 'Genre')[0]
					genre = [x for x in genre.split('|') if x != '']
					genre = ' / '.join(genre)

				duration = i['duration'] or client.parseDOM(item2, 'Runtime')[0]

				rating = i['rating'] or client.parseDOM(item, 'Rating')[0]
				votes = i['votes'] or client.parseDOM(item2, 'RatingCount')[0]

				mpaa = i['mpaa'] or client.parseDOM(item2, 'ContentRating')[0]

				director = client.parseDOM(item, 'Director')[0]
				director = [x for x in director.split('|') if x != '']
				director = (' / '.join(director)).encode('utf-8')
				director = client.replaceHTMLCodes(director)

				writer = client.parseDOM(item, 'Writer')[0]
				writer = [x for x in writer.split('|') if x != '']
				writer = (' / '.join(writer)).encode('utf-8')
				writer = client.replaceHTMLCodes(writer)

				import xml.etree.ElementTree as ET
				tree = ET.ElementTree(ET.fromstring(actors))
				root = tree.getroot()
				castandart = []
				for actor in root.iter('Actor'):
					person = [name.text for name in actor]
					image = person[1]
					name = person[2]
					try: name = client.replaceHTMLCodes(person[2])
					except: pass
					role = person[3]
					try: role = client.replaceHTMLCodes(person[3])
					except: pass
					try:
						try:
							castandart.append({'name': name.encode('utf-8'), 'role': role.encode('utf-8'), 'thumbnail': ((self.tvdb_image + image) if image is not None else '0')})
						except:
							castandart.append({'name': name, 'role': role, 'thumbnail': ((self.tvdb_image + image) if image is not None else '0')})
					except:
						castandart = []
					if len(castandart) == 150: break

				plot = client.parseDOM(item, 'Overview')[0]
				if not plot:
					plot = client.parseDOM(item2, 'Overview')[0]
				plot = client.replaceHTMLCodes(plot)
				plot = plot.encode('utf-8')

				values = {'title': title, 'seasoncount': seasoncount, 'season': season, 'episode': episode, 'year': year, 'tvshowtitle': tvshowtitle,
								'tvshowyear': year, 'premiered': premiered, 'status': status, 'studio': studio, 'genre': genre, 'duration': duration,
								'rating': rating, 'votes': votes, 'mpaa': mpaa, 'director': director, 'writer': writer, 'castandart': castandart, 'plot': plot,
								'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'progress': progress, 'added': added, 'lastplayed': lastplayed, 'poster': poster,
								'season_poster': season_poster, 'banner': banner, 'fanart': fanart, 'thumb': thumb, 'episodeIDS': episodeIDS}

				if not direct:
					values['action'] = 'episodes'

				try:
					if 'airday' in i and i['airday'] is not None and i['airday'] != '':
						values['airday'] = i['airday']
					if 'airtime' in i and i['airtime'] is not None and i['airtime'] != '':
						values['airtime'] = i['airtime']
					if 'airzone' in i and i['airzone'] is not None and i['airzone'] != '':
						values['airzone'] = i['airzone']
				except:
					log_utils.error()
					pass

				self.list.append(values)
			except:
				pass

		items = items[:len(items)]

		threads = []
		for i in items:
			threads.append(workers.Thread(items_list, i))
		[i.start() for i in threads]
		[i.join() for i in threads]
		return self.list


	def tvmaze_list(self, url, limit, count=False):
		try:
			result = client.request(url, error=True)
			items = json.loads(result)
		except:
			return

		itemlist = []

		for item in items:
			try:
				if 'english' not in item['show']['language'].lower():
					continue

				if limit is True and 'scripted' not in item['show']['type'].lower():
					continue

				try:
					title = (item.get('name')).encode('utf-8')
				except:
					title = item.get('name')

				season = item['season']
				if season is None:
					continue
				season = re.sub('[^0-9]', '', '%01d' % int(season))

				if control.setting('tv.specials') == 'false' and season == '0':
					continue

				episode = item['number']
				if episode is None:
					continue
				episode = re.sub('[^0-9]', '', '%01d' % int(episode))

				premiered = item.get('airdate', '0')

				year = str(item.get('show').get('premiered', '0'))
				year = re.search(r"(\d{4})", year).group(1)

				try:
					tvshowtitle = (item.get('show', {}).get('name')).encode('utf-8')
				except:
					tvshowtitle = item.get('show', {}).get('name')

				tvshowyear = item.get('show').get('year') or year

				imdb = item.get('show', {}).get('externals', {}).get('imdb', '0')
				if imdb == '' or imdb is None or imdb == 'None':
					imdb = '0'

				# TVMaze does not have tmdb in their api
				tmdb = '0'

				tvdb = str(item.get('show').get('externals').get('thetvdb', '0'))
				if tvdb == '' or tvdb is None or tvdb == 'None':
					tvdb = '0'

				if imdb == '0' or tvdb == '0':
					try:
						trakt_ids = trakt.SearchTVShow(urllib.quote_plus(tvshowtitle), year, full=False)
						if trakt_ids is None:
							raise Exception()
						trakt_ids = trakt_ids[0]['show']['ids']

						if imdb == '0':
							imdb = trakt_ids.get('imdb', '0')
							if imdb == '' or imdb is None or imdb == 'None':
								imdb = '0'

						if tmdb == '0':
							tmdb = str(trakt_ids.get('tmdb', '0'))
							if tmdb == '' or tmdb is None or tmdb == 'None':
								ztmdb = '0'

						if tvdb == '0':
							tvdb = str(trakt_ids.get('tvdb', '0'))
							if tvdb == '' or tvdb is None or tvdb == 'None':
								tvdb = '0'
					except:
						pass

# ### episode IDS
				episodeIDS = {}
				if control.setting('enable.upnext') == 'true':
					episodeIDS = trakt.getEpisodeSummary(imdb, season, episode, full=False) or {}
					if episodeIDS != {}:
						episodeIDS = episodeIDS.get('ids', {})
##------------------

				try:
					poster = item['show']['image']['original']
				except:
					poster = '0'

				try:
					thumb = item['image']['original']
				except:
					thumb = '0'

				studio = item.get('network', {}) or item.get('webChannel', {})
				studio = studio.get('name') or '0'

				genre = []
				for i in item['show']['genres']:
					genre.append(i.title())
				if genre == []: genre = 'NA'

				duration = str(item.get('show', {}).get('runtime', '0'))

				rating = str(item.get('show', {}).get('rating', {}).get('average', '0'))

				try:
					status = str(item.get('show', {}).get('status', '0'))
				except:
					status = 'Continuing'

				try:
					plot = item.get('show', {}).get('summary', '0')
					plot = re.sub('<.+?>|</.+?>|\n', '', plot)
				except:
					plot = '0'

				airday = ''
				airtime = item['airtime'] or ''
				# airtime = item['show']['schedule']['time'] or ''
				try:
					airzone = item['show']['network']['country']['timezone']
				except:
					airzone = ''

				values = {'title': title, 'season': season, 'episode': episode, 'year': year, 'tvshowtitle': tvshowtitle, 'tvshowyear': tvshowyear,
								'premiered': premiered, 'status': status, 'studio': studio, 'genre': genre, 'duration': duration, 'rating': rating, 'plot': plot,
								'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'airday': airday, 'airtime': airtime, 'airzone': airzone, 'poster': poster,
								'season_poster': poster, 'thumb': thumb, 'fanart': thumb, 'episodeIDS': episodeIDS}

				itemlist.append(values)

				# if count:
					# self.seasonCount(itemlist, len(itemlist) - 1)
			except:
				log_utils.error()
				pass

		# if count:
			# self.seasonCountWait()

		def items_list(i):
			self.list = []
			try:
				url = self.tvdb_info_link % (i['tvdb'], self.lang)
				data = urllib2.urlopen(url, timeout=10).read()
				zip = zipfile.ZipFile(StringIO.StringIO(data))

				result = zip.read('%s.xml' % self.lang)
				artwork = zip.read('banners.xml')
				actors = zip.read('actors.xml')
				zip.close()

				result = result.split('<Episode>')
				try:
					item = [(re.findall('<SeasonNumber>%01d</SeasonNumber>' % int(i['season']), x), re.findall('<EpisodeNumber>%01d</EpisodeNumber>' % int(i['episode']), x), x) for x in result]
					item = [x[2] for x in item if len(x[0]) > 0 and len(x[1]) > 0][0]
				except:
					item = None
					pass
				item2 = result[0]

				artwork = artwork.split('<Banner>')
				artwork = [x for x in artwork if '<Language>en</Language>' in x and '<BannerType>season</BannerType>' in x]
				artwork = [x for x in artwork if not 'seasonswide' in re.findall('<BannerPath>(.+?)</BannerPath>', x)[0]]

				status = i['status'] or client.parseDOM(item2, 'Status')[0]
				if not status:
					status = 'Ended'

				title = i['title']
				season = i['season']
				episode = i['episode']

				seasoncount = '0'
				# seasoncount = seasons.Seasons.seasonCountParse(season=season, items=result)

				tvshowtitle = i['tvshowtitle']
				premiered = i['premiered']
				year = i['year']
				imdb, tmdb, tvdb = i['imdb'], i['tmdb'], i['tvdb']

				episodeIDS = i['episodeIDS']

				poster = i['poster']
				poster2 = client.parseDOM(item2, 'poster')[0]
				if poster2 and poster2 != '':
					poster2 = self.tvdb_image + poster2
				else: poster2 = None
				poster = poster2 or poster or '0'

				banner = client.parseDOM(item2, 'banner')[0]
				if banner and banner != '':
					banner = self.tvdb_image + banner
				else: banner = '0'

				fanart = client.parseDOM(item2, 'fanart')[0]
				if fanart and fanart != '':
					fanart = self.tvdb_image + fanart
				else: fanart = '0'

				thumb = i['thumb']
				if item is not None:
					thumb2 = client.parseDOM(item, 'filename')[0]
					if thumb2 and thumb2 != '':
						thumb2 = self.tvdb_image + thumb2
					else: thumb2 = None
					thumb = thumb2 or thumb or '0'

				season_poster = [x for x in artwork if client.parseDOM(x, 'Season')[0] == season]
				try:
					season_poster = client.parseDOM(season_poster[0], 'BannerPath')[0]
				except:
					season_poster = ''
				if season_poster != '':
					season_poster = self.tvdb_image + season_poster
				else:
					season_poster = '0'
				season_poster = client.replaceHTMLCodes(season_poster)
				season_poster = season_poster.encode('utf-8')

				if poster != '0':
					pass
				elif fanart != '0':
					poster = fanart
				elif banner != '0':
					poster = banner

				if banner != '0':
					pass
				elif fanart != '0':
					banner = fanart
				elif poster != '0':
					banner = poster

				if thumb != '0':
					pass
				elif fanart != '0':
					thumb = fanart.replace(self.tvdb_image, self.tvdb_poster)
				elif poster != '0':
					thumb = poster

				studio = i['studio'] or client.parseDOM(item2, 'Network')[0]

				if 'genre' in i and i['genre'] is not None and i['genre'] != 'NA':
					genre = i['genre'] 
				else:
					genre = client.parseDOM(item2, 'Genre')[0]
					genre = [x for x in genre.split('|') if x != '']
					genre = ' / '.join(genre)

				duration = i['duration'] or client.parseDOM(item2, 'Runtime')[0]

				rating = i['rating']
				votes = client.parseDOM(item2, 'RatingCount')[0]

				mpaa = client.parseDOM(item2, 'ContentRating')[0]

				plot = i['plot']
				director = writer = '0'
				if item is not None:
					premiered = premiered or client.parseDOM(item, 'FirstAired')[0] or '0'

					director = client.parseDOM(item, 'Director')[0]
					director = [x for x in director.split('|') if x != '']
					director = (' / '.join(director)).encode('utf-8')
					director = client.replaceHTMLCodes(director)

					writer = client.parseDOM(item, 'Writer')[0]
					writer = [x for x in writer.split('|') if x != '']
					writer = (' / '.join(writer)).encode('utf-8')
					writer = client.replaceHTMLCodes(writer)

					rating = rating or client.parseDOM(item, 'Rating')[0]

					plot2 = client.parseDOM(item, 'Overview')[0]
					if not plot2:
						plot2 = client.parseDOM(item2, 'Overview')[0]
					plot2 = client.replaceHTMLCodes(plot2)
					plot2 = plot2.encode('utf-8')
					plot = plot2 or plot

				import xml.etree.ElementTree as ET
				tree = ET.ElementTree(ET.fromstring(actors))
				root = tree.getroot()
				castandart = []
				for actor in root.iter('Actor'):
					person = [name.text for name in actor]
					image = person[1]
					name = person[2]
					try: name = client.replaceHTMLCodes(person[2])
					except: pass
					role = person[3]
					try: role = client.replaceHTMLCodes(person[3])
					except: pass
					try:
						try:
							castandart.append({'name': name.encode('utf-8'), 'role': role.encode('utf-8'), 'thumbnail': ((self.tvdb_image + image) if image is not None else '0')})
						except:
							castandart.append({'name': name, 'role': role, 'thumbnail': ((self.tvdb_image + image) if image is not None else '0')})
					except:
						castandart = []
					if len(castandart) == 150: break

				airday = i['airday'] or ''
				airtime = i['airtime'] or client.parseDOM(item2, 'Airs_Time')[0] or ''
				airzone = i['airzone'] or ''

				values = {'extended': True, 'title': title, 'seasoncount': seasoncount, 'season': season, 'episode': episode, 'year': year, 'tvshowtitle': tvshowtitle,
								'tvshowyear': year, 'premiered': premiered, 'status': status, 'studio': studio, 'genre': genre, 'duration': duration, 'rating': rating,
								'votes': votes, 'mpaa': mpaa, 'director': director, 'writer': writer, 'castandart': castandart, 'plot': plot, 'airday': airday, 'airtime': airtime,
								'airzone': airzone, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'poster': poster, 'season_poster': season_poster, 'banner': banner,
								'fanart': fanart, 'thumb': thumb, 'episodeIDS': episodeIDS, 'ForceAirEnabled': True}

				if disable_fanarttv != 'true':
					from resources.lib.indexers import fanarttv
					extended_art = cache.get(fanarttv.get_tvshow_art, 168, tvdb)
					if extended_art is not None:
						values.update(extended_art)
						# meta.update(values)

				# values = dict((k,v) for k, v in values.iteritems() if v != '0')
				self.list.append(values)
			except:
				log_utils.error()
				pass

		items = itemlist[:len(itemlist)]
		threads = []
		for i in items:
			threads.append(workers.Thread(items_list, i))
		[i.start() for i in threads]
		[i.join() for i in threads]

		self.list = sorted(self.list, key=lambda k: k['airtime'], reverse=False)
		return self.list


	def episodeDirectory(self, items, unfinished=False, next=True):
		# TotalTime1 = time.time()
		if items is None or len(items) == 0:
			control.idle()
			control.notification(title=32326, message=33049, icon='INFO', sound=notificationSound)
			sys.exit()

		# Retrieve additional metadata if not super info was retireved (eg: Trakt lists, such as Unfinished and History)
		try:
			if 'extended' not in items[0] or not items[0]['extended']:
				from resources.lib.menus import tvshows
				show = tvshows.TVshows(type=self.type)
				show.list = copy.deepcopy(self.list)
				show.worker()
				for i in range(len(self.list)):
					self.list[i] = dict(show.list[i].items() + self.list[i].items())
		except:
			log_utils.error()
			pass

		sysaddon = sys.argv[0]
		syshandle = int(sys.argv[1])

		settingFanart = control.setting('fanart')

		addonPoster = control.addonPoster()
		addonFanart = control.addonFanart()
		addonBanner = control.addonBanner()

		try:
			multi = [i['tvshowtitle'] for i in items]
		except:
			multi = []
		multi = len([x for y, x in enumerate(multi) if x not in multi[:y]])
		multi = True if multi > 1 else False
		try:
			if '/users/me/history/' in items[0]['next']:
				multi = True
		except: pass

		try:
			sysaction = items[0]['action']
		except:
			sysaction = ''

		indicators = playcount.getTVShowIndicators()

		isFolder = False if sysaction != 'episodes' else True

		isPlayable = 'false'
		if 'plugin' not in control.infoLabel('Container.PluginName'):
			isPlayable = 'true'
		elif control.setting('enable.upnext') == 'true' or control.setting('hosts.mode') != '1' :
			isPlayable = 'true'

		unwatchedEnabled = control.setting('tvshows.unwatched.enabled')
		unwatchedLimit = False
		# seasoncountEnabled = control.setting('tvshows.seasoncount.enabled')
		playlistcreate = control.setting('auto.playlistcreate')

		airEnabled = control.setting('tvshows.air.enabled') if 'ForceAirEnabled' not in items[0] else 'true'
		if airEnabled == 'true':
			airZone = control.setting('tvshows.air.zone')
			airLocation = control.setting('tvshows.air.location')
			airFormat = control.setting('tvshows.air.format')
			airFormatDay = control.setting('tvshows.air.day')
			airFormatTime = control.setting('tvshows.air.time')
			airBold = control.setting('tvshows.air.bold')
			airLabel = '[B]' + control.lang(35032).encode('utf-8') + '[/B]' + ': '

		if control.setting('hosts.mode') == '2' or control.setting('enable.upnext') == 'true':
			playbackMenu = control.lang(32063).encode('utf-8')
		else:
			playbackMenu = control.lang(32064).encode('utf-8')

		if trakt.getTraktIndicatorsInfo() is True:
			watchedMenu = control.lang(32068).encode('utf-8')
			unwatchedMenu = control.lang(32069).encode('utf-8')
		else:
			watchedMenu = control.lang(32066).encode('utf-8')
			unwatchedMenu = control.lang(32067).encode('utf-8')

		traktManagerMenu = control.lang(32070).encode('utf-8')

		playlistManagerMenu = control.lang(35522).encode('utf-8')
		queueMenu = control.lang(32065).encode('utf-8')

		traktProgress = False if 'traktProgress' not in items[0] else True
		if traktProgress is True and control.setting('tvshows.direct') == 'false':
			progressMenu = control.lang(32015).encode('utf-8')
		else:
			progressMenu = control.lang(32016).encode('utf-8')

		tvshowBrowserMenu = control.lang(32071).encode('utf-8')
		addToLibrary = control.lang(32551).encode('utf-8')

		for i in items:
			try:
				imdb, tvdb, year, season, episode, premiered = i.get('imdb', '0'), i.get('tvdb', '0'), i['year'], i['season'], i['episode'], i['premiered']
				if 'label' not in i:
					i['label'] = i['title']

				if i['label'] == '0':
					label = '%sx%02d . %s %s' % (i['season'], int(i['episode']), 'Episode', i['episode'])
				else:
					label = '%sx%02d . %s' % (i['season'], int(i['episode']), i['label'])

				# if self.season_special is False and control.setting('tv.specials') == 'true':
					# self.season_special = True if int(season) == 0 else False

				if multi is True:
					label = '%s - %s' % (i['tvshowtitle'], label)

				try:
					labelProgress = label + ' [' + str(int(i['progress'] * 100)) + '%]'
				except:
					labelProgress = label

				try:
					if i['unaired'] == 'true':
						labelProgress = '[COLOR %s][I]%s[/I][/COLOR]' % (self.unairedcolor, labelProgress)
				except:
					pass

				systitle = urllib.quote_plus(i['title'])
				systvshowtitle = urllib.quote_plus(i['tvshowtitle'])
				syspremiered = urllib.quote_plus(i['premiered'])

				try:
					seasoncount = i['seasoncount']
				except:
					seasoncount = None

				meta = dict((k, v) for k, v in i.iteritems() if v != '0' and v != '')
				# meta = dict((k, v) for k, v in i.iteritems())
				meta.update({'mediatype': 'episode'})
				meta.update({'trailer': '%s?action=trailer&name=%s&imdb=%s' % (sysaddon, systvshowtitle, imdb)})

				# Some descriptions have a link at the end that. Remove it.
				try:
					plot = meta['plot']
					index = plot.rfind('See full summary')
					if index >= 0:
						plot = plot[:index]
					plot = plot.strip()
					if re.match('[a-zA-Z\d]$', plot):
						plot += ' ...'
					meta['plot'] = plot
				except:
					pass

				try: meta.update({'duration': str(int(meta['duration']) * 60)})
				except: pass
				try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
				except: pass
				try: meta.update({'title': i['label']})
				except: pass
				try: meta.update({'year': re.findall('(\d{4})', i['premiered'])[0]})
				except: pass

				try:
					# Kodi uses the year (the year the show started) as the year for the episode. Change it from the premiered date.
					meta.update({'tvshowyear': i['year']})
				except: pass

				if airEnabled == 'true':
					air = []
					airday = None
					airtime = None
					if 'airday' in meta and not meta['airday'] is None and meta['airday'] != '':
						airday = meta['airday']
					if 'airtime' in meta and not meta['airtime'] is None and meta['airtime'] != '':
						airtime = meta['airtime']
						if 'airzone' in meta and not meta['airzone'] is None and meta['airzone'] != '':
							if airZone == '1':
								zoneTo = meta['airzone']
							elif airZone == '2':
								zoneTo = 'utc'
							else:
								zoneTo = 'local'

							if airFormatTime == '1':
								formatOutput = '%I:%M'
							elif airFormatTime == '2':
								formatOutput = '%I:%M %p'
							else:
								formatOutput = '%H:%M'

							abbreviate = airFormatDay == '1'
							airtime = tools.Time.convert(stringTime=airtime, stringDay=airday, zoneFrom=meta['airzone'],
														zoneTo=zoneTo, abbreviate=abbreviate, formatOutput=formatOutput)
							if airday:
								airday = airtime[1]
								airtime = airtime[0]
					if airday: air.append(airday)
					if airtime: air.append(airtime)
					if len(air) > 0:
						if airFormat == '0':
							air = airtime
						elif airFormat == '1':
							air = airday
						elif airFormat == '2':
							air = air = ' '.join(air)

						if airLocation == '0' or airLocation == '1':
							air = '[COLOR skyblue][%s][/COLOR]' % air
						if airBold == 'true': air = '[B]%s[/B]' % str(air)
						if airLocation == '0':
							labelProgress = '%s %s' % (air, labelProgress)
						elif airLocation == '1':
							labelProgress = '%s %s' % (labelProgress, air)
						elif airLocation == '2':
							meta['plot'] = '%s%s\r\n%s' % (airLabel, air, meta['plot'])
						elif airLocation == '3':
							meta['plot'] = '%s\r\n%s%s' % (meta['plot'], airLabel, air)

				poster1 = meta.get('poster')
				poster2 = meta.get('poster2')
				poster3 = meta.get('poster3')
				poster = poster3 or poster2 or poster1 or addonPoster

				season_poster = meta.get('season_poster') or poster

				fanart = '0'
				if settingFanart:
					fanart1 = meta.get('fanart')
					fanart2 = meta.get('fanart2')
					fanart3 = meta.get('fanart3')
					fanart = fanart3 or fanart2 or fanart1 or addonFanart

				landscape = meta.get('landscape')
				thumb = meta.get('thumb') or poster or landscape
				icon = meta.get('icon') or poster

				banner1 = meta.get('banner')
				banner2 = meta.get('banner2')
				banner3 = meta.get('banner3')
				banner = banner3 or banner2 or banner1 or addonBanner

				clearlogo = meta.get('clearlogo')
				clearart = meta.get('clearart')

				art = {}
				art.update({'poster': season_poster, 'tvshow.poster': poster, 'season.poster': season_poster, 'fanart': fanart, 'icon': icon,
									'thumb': thumb, 'banner': banner, 'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape})

####-Context Menu and Overlays-####
				cm = []
				if self.traktCredentials is True:
					cm.append((traktManagerMenu, 'RunPlugin(%s?action=traktManager&name=%s&imdb=%s&tvdb=%s&season=%s&episode=%s)' % (
										sysaddon, systvshowtitle, imdb, tvdb, season, episode)))

				try:
					overlay = int(playcount.getEpisodeOverlay(indicators, imdb, tvdb, season, episode))
					watched = (overlay == 7)

					# Skip episodes marked as watched for the unfinished and onDeck lists.
					try:
						if unfinished and watched and not i['progress'] is None: continue
					except: pass

					if watched:
						meta.update({'playcount': 1, 'overlay': 7})
						cm.append((unwatchedMenu, 'RunPlugin(%s?action=episodePlaycount&name=%s&imdb=%s&tvdb=%s&season=%s&episode=%s&query=6)' % (
												sysaddon, systvshowtitle, imdb, tvdb, season, episode)))
					else:
						meta.update({'playcount': 0, 'overlay': 6})
						cm.append((watchedMenu, 'RunPlugin(%s?action=episodePlaycount&name=%s&imdb=%s&tvdb=%s&season=%s&episode=%s&query=7)' % (
												sysaddon, systvshowtitle, imdb, tvdb, season, episode)))
				except:
					pass

				sysmeta = urllib.quote_plus(json.dumps(meta))
				sysart = urllib.quote_plus(json.dumps(art))
				syslabelProgress = urllib.quote_plus(labelProgress)

				url = '%s?action=play&title=%s&year=%s&imdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&t=%s' % (
										sysaddon, systitle, year, imdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta, self.systime)
				sysurl = urllib.quote_plus(url)

				Folderurl = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tvdb=%s&season=%s&episode=%s' % (
										sysaddon, systvshowtitle, year, imdb, tvdb, season, episode)

				if isFolder is True:
					if traktProgress is True:
						if control.setting('hosts.mode') == '1' and control.setting('enable.upnext') != 'true':
							cm.append((progressMenu, 'RunPlugin(%s)' % url))

						elif control.setting('hosts.mode') != '1' or control.setting('enable.upnext') == 'true':
							cm.append((progressMenu, 'PlayMedia(%s)' % url))

					url = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tvdb=%s&season=%s&episode=%s' % (
										sysaddon, systvshowtitle, year, imdb, tvdb, season, episode)

				cm.append((playlistManagerMenu, 'RunPlugin(%s?action=playlistManager&name=%s&url=%s&meta=%s&art=%s)' % (
										sysaddon, syslabelProgress, sysurl, sysmeta, sysart)))
				cm.append((queueMenu, 'RunPlugin(%s?action=queueItem&name=%s)' % (sysaddon, syslabelProgress)))

				if multi is True:
					cm.append((tvshowBrowserMenu, 'Container.Update(%s?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tvdb=%s,return)' % (
										sysaddon, systvshowtitle, year, imdb, tvdb)))

				if isFolder is False:
					if traktProgress is True:
						cm.append((progressMenu, 'Container.Update(%s)' % Folderurl))

					cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))

					if control.setting('hosts.mode') == '1' and control.setting('enable.upnext') != 'true':
						cm.append(('Rescrape Item', 'RunPlugin(%s?action=reScrape&title=%s&year=%s&imdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&t=%s)' % (
											sysaddon, systitle, year, imdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta, self.systime)))

					elif control.setting('hosts.mode') != '1' or control.setting('enable.upnext') == 'true':
						cm.append(('Rescrape Item', 'PlayMedia(%s?action=reScrape&title=%s&year=%s&imdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&t=%s)' % (
											sysaddon, systitle, year, imdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta, self.systime)))

				if control.setting('library.service.update') == 'true':
					cm.append((addToLibrary, 'RunPlugin(%s?action=tvshowToLibrary&tvshowtitle=%s&year=%s&imdb=%s&tvdb=%s)' % (
											sysaddon, systvshowtitle, year, imdb, tvdb)))
				cm.append((control.lang(32610).encode('utf-8'), 'RunPlugin(%s?action=clearAllCache&opensettings=false)' % sysaddon))

				# cm.append(('PlayAll', 'RunPlugin(%s?action=playAll)' % sysaddon))
				cm.append(('[COLOR red]Venom Settings[/COLOR]', 'RunPlugin(%s?action=openSettings)' % sysaddon))
####################################

				item = control.item(label=labelProgress)

				if 'castandart' in i:
					item.setCast(i['castandart'])

				if 'episodeIDS' in i:
					item.setUniqueIDs(i['episodeIDS'])

				if unwatchedEnabled == 'true':
					count = playcount.getShowCount(indicators, imdb, tvdb, unwatchedLimit)
					if count:
						item.setProperty('TotalEpisodes', str(count['total']))
						item.setProperty('WatchedEpisodes', str(count['watched']))
						item.setProperty('UnWatchedEpisodes', str(count['unwatched']))

				# if seasoncountEnabled == 'true':
					# total_seasons = trakt.getSeasons(imdb, full=False)
					# if total_seasons is not None:
						# total_seasons = [i['number'] for i in total_seasons]
						# total_seasons = len(total_seasons)
						# if control.setting('tv.specials') == 'false' or self.season_special is False:
							# total_seasons = total_seasons - 1
						# item.setProperty('TotalSeasons', str(total_seasons))

				item.setArt(art)
				item.setProperty('IsPlayable', isPlayable)
				item.setInfo(type='video', infoLabels=control.metadataClean(meta))
				video_streaminfo = {'codec': 'h264'}
				item.addStreamInfo('video', video_streaminfo)
				item.addContextMenuItems(cm)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)

				if playlistcreate == 'true':
					control.playlist.add(url=url, listitem=item)
			except:
				log_utils.error()
				pass

		if next:
			try:
				url = items[0]['next']
				if url == '':
					raise Exception()

				nextMenu = control.lang(32053).encode('utf-8')
				url_params = dict(urlparse.parse_qsl(url))

				if 'imdb.com' in url:
					start = int(url_params.get('start'))
					# start = int(re.search('start=(.+?)&ref_=', url).group(1))
					page = '  [I](%s)[/I]' % str(((start - 1) / self.count) + 1)
				else:
					page = url_params.get('page')
					page = '  [I](%s)[/I]' % page

				nextMenu = '[COLOR skyblue]' + nextMenu + page + '[/COLOR]'

				if '/users/me/history/' in url:
					url = '%s?action=calendar&url=%s' % (sysaddon, urllib.quote_plus(url))

				item = control.item(label=nextMenu)
				icon = control.addonNext()
				item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon})
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except:
				pass

		# Show multi as show, in order to display unwatched count if enabled.
		if multi is True and unwatchedEnabled == 'true':
			control.content(syshandle, 'tvshows')
			control.directory(syshandle, cacheToDisc=True)
			views.setView('tvshows', {'skin.estuary': 55, 'skin.confluence': 500})
		else:
			control.content(syshandle, 'episodes')
			control.directory(syshandle, cacheToDisc=True)
			views.setView('episodes', {'skin.estuary': 55, 'skin.confluence': 504})

		# TotalTime2 = time.time()
		# log_utils.log('Episode Directory time = %s' % str(TotalTime2 - TotalTime1), __name__, log_utils.LOGDEBUG)


	def addDirectory(self, items, queue=False):
		if items is None or len(items) == 0:
			control.hide()
			control.notification(title=32326, message=33049, icon='INFO', sound=notificationSound)
			sys.exit()

		sysaddon = sys.argv[0]
		syshandle = int(sys.argv[1])

		addonThumb = control.addonThumb()
		artPath = control.artPath()

		queueMenu = control.lang(32065).encode('utf-8')

		for i in items:
			try:
				name = i['name']

				if i['image'].startswith('http'):
					thumb = i['image']
				elif artPath is not None:
					thumb = os.path.join(artPath, i['image'])
				else:
					thumb = addonThumb

				icon = i.get('icon', 0)
				if icon is None:
					icon = 'DefaultFolder.png'

				url = '%s?action=%s' % (sysaddon, i['action'])
				try:
					url += '&url=%s' % urllib.quote_plus(i['url'])
				except:
					pass

				cm = []
				if queue is True:
					cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

				cm.append((control.lang(32610).encode('utf-8'), 'RunPlugin(%s?action=clearAllCache&opensettings=false)' % sysaddon))
				cm.append(('[COLOR red]Venom Settings[/COLOR]', 'RunPlugin(%s?action=openSettings)' % sysaddon))

				item = control.item(label=name)
				item.setArt({'icon': icon, 'poster': thumb, 'thumb': thumb, 'fanart': control.addonFanart(), 'banner': thumb})

				item.addContextMenuItems(cm)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except:
				pass

		control.content(syshandle, 'addons')
		control.directory(syshandle, cacheToDisc=True)
