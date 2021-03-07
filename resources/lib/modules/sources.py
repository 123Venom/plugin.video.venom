# -*- coding: utf-8 -*-
"""
	Venom Add-on
"""

from datetime import datetime, timedelta
from json import dumps as jsdumps, loads as jsloads
import re
# import _strptime to workaround python 2 bug with threads
import _strptime
import sys
import time
try: #Py2
	from urllib import quote_plus, unquote
	from urlparse import parse_qsl
except ImportError: #Py3
	from urllib.parse import quote_plus, parse_qsl, unquote
from resources.lib.modules import cleantitle
from resources.lib.modules import control
from resources.lib.modules import debrid
from resources.lib.modules import log_utils
from resources.lib.modules import metacache
from resources.lib.modules import providerscache
from resources.lib.modules import source_utils
from resources.lib.modules import trakt
from resources.lib.modules import workers
from resources.lib.debrid import alldebrid
from resources.lib.debrid import premiumize
from resources.lib.debrid import realdebrid
try: from sqlite3 import dbapi2 as database
except ImportError: from pysqlite2 import dbapi2 as database

from fenomscrapers import sources as fs_sources


class Sources:
	def __init__(self):
		self.time = datetime.now()
		self.single_expiry = timedelta(hours=6)
		self.season_expiry = timedelta(hours=48)
		self.show_expiry = timedelta(hours=48)
		self.getConstants()
		self.sources = []
		self.scraper_sources = []
		self.uncached_sources = []
		self.sourceFile = control.providercacheFile
		self.dev_mode = control.setting('dev.mode.enable') == 'true'
		self.dev_disable_single = control.setting('dev.disable.single') == 'true'
		# self.dev_disable_single_filter = control.setting('dev.disable.single.filter') == 'true'
		self.dev_disable_season_packs = control.setting('dev.disable.season.packs') == 'true'
		self.dev_disable_season_filter = control.setting('dev.disable.season.filter') == 'true'
		self.dev_disable_show_packs = control.setting('dev.disable.show.packs') == 'true'
		self.dev_disable_show_filter = control.setting('dev.disable.show.filter') == 'true'
		self.extensions = source_utils.supported_video_extensions()
		self.highlight_color = control.getColor(control.setting('highlight.color'))


	def play(self, title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered, meta, select, rescrape=None):
		gdriveEnabled = control.addon('script.module.fenomscrapers').getSetting('gdrive.cloudflare_url') != ''
		if not self.debrid_resolvers and not gdriveEnabled:
			control.sleep(200)
			control.hide()
			control.notification(message=33034)
			return
		try:
			control.homeWindow.clearProperty(self.metaProperty)
			control.homeWindow.setProperty(self.metaProperty, meta)
			control.homeWindow.clearProperty(self.seasonProperty)
			control.homeWindow.setProperty(self.seasonProperty, season)
			control.homeWindow.clearProperty(self.episodeProperty)
			control.homeWindow.setProperty(self.episodeProperty, episode)
			control.homeWindow.clearProperty(self.titleProperty)
			control.homeWindow.setProperty(self.titleProperty, title)
			control.homeWindow.clearProperty(self.imdbProperty)
			control.homeWindow.setProperty(self.imdbProperty, imdb)
			control.homeWindow.clearProperty(self.tmdbProperty)
			control.homeWindow.setProperty(self.tmdbProperty, tmdb)
			control.homeWindow.clearProperty(self.tvdbProperty)
			control.homeWindow.setProperty(self.tvdbProperty, tvdb)
			p_label = '[COLOR %s]%s (%s)[/COLOR]' % (self.highlight_color, title, year) if tvshowtitle is None else \
			'[COLOR %s]%s (S%02dE%02d)[/COLOR]' % (self.highlight_color, tvshowtitle, int(season), int(episode))
			control.homeWindow.clearProperty(self.labelProperty)
			control.homeWindow.setProperty(self.labelProperty, p_label)

			url = None
			self.mediatype = 'movie'

			#check IMDB for year since TMDB and Trakt differ on a ratio of 1 in 20 and year is off by 1 and some meta titles mismatch
			if tvshowtitle is None and control.setting('imdb.year.check') == 'true':
				year, title = self.movie_chk_imdb(imdb, title, year)

			# get "total_season" to satisfy showPack scrapers. 1st=passed meta, 2nd=matacache check, 3rd=trakt.getSeasons() request
			# also get "is_airing" status of season for showPack scrapers. 1st=passed meta, 2nd=matacache check, 3rd=tvdb v1 xml request
			if tvshowtitle is not None:
				self.mediatype = 'episode'
				self.total_seasons, self.is_airing = self.get_season_info(imdb, tvdb, meta, season)
			if rescrape :
				self.clr_item_providers(title, year, imdb, tvdb, season, episode, tvshowtitle, premiered)
			items = providerscache.get(self.getSources, 48, title, year, imdb, tvdb, season, episode, tvshowtitle, premiered)
			if not items:
				self.url = url
				return self.errorForSources()

			filter = []
			if control.setting('torrent.remove.uncached') == 'true':
				filter += [i for i in items if not re.match(r'^uncached.*torrent', i['source'])]
				if filter:
					for i in range(len(filter)):
						filter[i].update({'label': re.sub(r'(\d+)', '%02d' % int(i + 1), filter[i]['label'], 1)})
				elif not filter:
					if control.yesnoDialog('No cached torrents returned. Would you like to view the uncached torrents to cache yourself?', '', ''):
						control.cancelPlayback()
						select = '1'
						filter += [i for i in items if re.match(r'^uncached.*torrent', i['source'])]
				items = filter
				if not items:
					self.url = url
					return self.errorForSources()

			if select is None:
				if episode is not None and control.setting('enable.upnext') == 'true': select = '2'
				else: select = control.setting('hosts.mode')
			else: select = select

			if select == '1':
				if control.condVisibility("Window.IsActive(script.extendedinfo-DialogVideoInfo.xml)") or \
				control.condVisibility("Window.IsActive(script.extendedinfo-DialogVideoInfo-Aura.xml)") or \
				control.condVisibility("Window.IsActive(script.extendedinfo-DialogVideoInfo-Estuary.xml)") or \
				control.condVisibility("Window.IsActive(script.extendedinfo-DialogVideoInfo-Netflix.xml)") or \
				control.condVisibility("Window.IsActive(DialogVideoInfo.xml)"):
					select = '0'

			title = tvshowtitle if tvshowtitle is not None else title
			if len(items) > 0:
				if select == '1' and 'plugin' in control.infoLabel('Container.PluginName'):
					control.homeWindow.clearProperty(self.itemProperty)
					control.homeWindow.setProperty(self.itemProperty, jsdumps(items))
					control.sleep(200)
					return control.execute('Container.Update(%s?action=addItem&title=%s)' % (sys.argv[0], quote_plus(title)))
				elif select == '0' or select == '1': url = self.sourcesDialog(items)
				else:
					url = self.sourcesAutoPlay(items)

			if url == 'close://' or url is None:
				self.url = url
				return self.errorForSources()

			try: meta = jsloads(unquote(meta.replace('%22', '\\"')))
			except: pass
			from resources.lib.modules import player
			control.sleep(200)
			control.hide()
			player.Player().play_source(title, year, season, episode, imdb, tmdb, tvdb, url, meta, select)
		except:
			log_utils.error()
			control.cancelPlayback()


	def addItem(self, title):
		control.hide()

		def sourcesDirMeta(metadata):
			if not metadata: return metadata
			allowed = ['poster', 'season_poster', 'fanart', 'thumb', 'title', 'year', 'tvshowtitle', 'season', 'episode']
			#return {k: v for k, v in metadata.iteritems() if k in allowed}
			try: return {k: v for k, v in metadata.iteritems() if k in allowed}
			except: return {k: v for k, v in metadata.items() if k in allowed}

		control.playlist.clear()
		items = control.homeWindow.getProperty(self.itemProperty)
		items = jsloads(items)

		if not items:
			control.sleep(200)
			control.hide()
			sys.exit()

		meta = jsloads(unquote(control.homeWindow.getProperty(self.metaProperty).replace('%22', '\\"')))
		meta = sourcesDirMeta(meta)

		sysaddon = sys.argv[0]
		syshandle = int(sys.argv[1])
		systitle = sysname = quote_plus(title)

		downloads = True if control.setting('downloads') == 'true' and (control.setting(
			'movie.download.path') != '' or control.setting('tv.download.path') != '') else False
		poster = meta.get('poster') or control.addonPoster()
		if 'tvshowtitle' in meta and 'season' in meta and 'episode' in meta:
			poster = meta.get('season_poster') or poster or control.addonPoster()
			sysname += quote_plus(' S%02dE%02d' % (int(meta['season']), int(meta['episode'])))
		elif 'year' in meta:
			sysname += quote_plus(' (%s)' % meta['year'])

		fanart = meta.get('fanart')
		if control.setting('fanart') != 'true': fanart = '0'

		resquality_icons = control.setting('enable.resquality.icons') == 'true'
		artPath = control.artPath()
		# sysimage = quote_plus(poster.encode('utf-8'))
		sysimage = quote_plus(poster)
		downloadMenu = control.lang(32403)

		for i in range(len(items)):
			try:
				label = str(items[i]['label'])
				syssource = quote_plus(jsdumps([items[i]]))
				sysurl = '%s?action=playItem&title=%s&source=%s' % (sysaddon, systitle, syssource)

				cm = []
				link_type = 'pack' if 'package' in items[i] else 'single'
				isCached = True if re.match(r'^cached.*torrent', items[i]['source']) else False
				if downloads and (isCached or items[i]['direct'] == True or (items[i]['debridonly'] == True and 'magnet:' not in items[i]['url'])):
					try: new_sysname = quote_plus(items[i]['name'])
					except: new_sysname = sysname
					cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&source=%s&caller=sources&title=%s)' %
										(sysaddon, new_sysname, sysimage, syssource, sysname)))

				if link_type == 'pack' and isCached:
					cm.append(('[B]Browse Debrid Pack[/B]', 'RunPlugin(%s?action=showDebridPack&caller=%s&name=%s&url=%s&source=%s)' %
									(sysaddon, quote_plus(items[i]['debrid']), quote_plus(items[i]['name']), quote_plus(items[i]['url']), quote_plus(items[i]['hash']))))

				if not isCached and 'magnet:' in items[i]['url']:
					d = self.debrid_abv(items[i]['debrid'])
					if d in ('PM', 'RD', 'AD'):
						try: seeders = items[i]['seeders']
						except: seeders = '0'
						cm.append(('[B]Cache to %s Cloud (seeders=%s)[/B]' % (d, seeders), 'RunPlugin(%s?action=cacheTorrent&caller=%s&type=%s&title=%s&url=%s&source=%s)' %
											(sysaddon, d, link_type, sysname, quote_plus(items[i]['url']), syssource)))

				cm.append(('[B]Additional Link Info[/B]', 'RunPlugin(%s?action=sourceInfo&source=%s)' %
									(sysaddon, syssource)))

				if resquality_icons:
					quality = items[i]['quality']
					thumb = '%s%s' % (quality, '.png')
					thumb = control.joinPath(artPath, thumb) if artPath else ''
				else:
					thumb = meta.get('thumb') or poster or fanart or control.addonThumb()

				item = control.item(label=label)
				item.setArt({'icon': thumb, 'thumb': thumb, 'poster': poster, 'fanart': fanart})
				video_streaminfo = {'codec': 'h264'}
				item.addStreamInfo('video', video_streaminfo)
				item.addContextMenuItems(cm)

				# item.setProperty('IsPlayable', 'true') # test
				item.setProperty('IsPlayable', 'false')

				item.setInfo(type='video', infoLabels=control.metadataClean(meta))
				control.addItem(handle=syshandle, url=sysurl, listitem=item, isFolder=False)
			except:
				log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)


	def playItem(self, title, source):
		try:
			meta = jsloads(unquote(control.homeWindow.getProperty(self.metaProperty).replace('%22', '\\"')))
			year = meta['year'] if 'year' in meta else None
			if 'tvshowtitle' in meta:
				year = meta['tvshowyear'] if 'tvshowyear' in meta else year #year was changed to year of premiered in episodes module so can't use that, need original shows year.
			season = meta['season'] if 'season' in meta else None
			episode = meta['episode'] if 'episode' in meta else None
			imdb = meta['imdb'] if 'imdb' in meta else None
			tmdb = meta['tmdb'] if 'tmdb' in meta else None
			tvdb = meta['tvdb'] if 'tvdb' in meta else None

			next = [] ; prev = [] ; total = []
			for i in range(1, 1000):
				try:
					u = control.infoLabel('ListItem(%s).FolderPath' % str(i))
					if u in total: raise Exception()
					total.append(u)
					u = dict(parse_qsl(u.replace('?', '')))
					u = jsloads(u['source'])[0]
					next.append(u)
				except: break
			for i in range(-1000, 0)[::-1]:
				try:
					u = control.infoLabel('ListItem(%s).FolderPath' % str(i))
					if u in total: raise Exception()
					total.append(u)
					u = dict(parse_qsl(u.replace('?', '')))
					u = jsloads(u['source'])[0]
					prev.append(u)
				except: break

			items = jsloads(source)
			items = [i for i in items + next + prev][:40]

			header = control.homeWindow.getProperty(self.labelProperty) + ': Resolving...'
			progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
			progressDialog.create(header, '')

			block = None
			for i in range(len(items)):
				try:
					label = re.sub(r' {2,}', ' ', str(items[i]['label']))
					label = re.sub(r'\n', '', label)
					try:
						if progressDialog.iscanceled(): break
						progressDialog.update(int((100 / float(len(items))) * i), label)
					except: progressDialog.update(int((100 / float(len(items))) * i), '[COLOR %s]Resolving...[/COLOR]%s' % (self.highlight_color, items[i]['name']))

					if items[i]['source'] == block: raise Exception()
					w = workers.Thread(self.sourcesResolve, items[i])
					w.start()

					if 'torrent' in items[i].get('source'): offset = float('inf')
					else: offset = 0
					m = ''
					for x in range(3600):
						try:
							if control.monitor.abortRequested(): return sys.exit()
							if progressDialog.iscanceled(): return progressDialog.close()
						except: pass

						k = control.condVisibility('Window.IsActive(virtualkeyboard)')
						if k: m += '1' ; m = m[-1]
						if (not w.is_alive() or x > 30 + offset) and not k: break
						k = control.condVisibility('Window.IsActive(yesnoDialog)')
						if k: m += '1' ; m = m[-1]
						if (not w.is_alive() or x > 30 + offset) and not k: break
						time.sleep(0.5)

					for x in range(30):
						try:
							if control.monitor.abortRequested(): return sys.exit()
							if progressDialog.iscanceled(): return progressDialog.close()
						except: pass

						if m == '': break
						if not w.is_alive(): break
						time.sleep(0.5)

					if w.is_alive(): block = items[i]['source']
					if not self.url: raise Exception()
					if not any(x in self.url.lower() for x in self.extensions):
						log_utils.log('Playback not supported for: %s' % self.url, __name__, log_utils.LOGDEBUG)
						raise Exception()

					try: progressDialog.close()
					except: pass
					control.sleep(200)
					control.execute('Dialog.Close(virtualkeyboard)')
					control.execute('Dialog.Close(yesnoDialog)')

					from resources.lib.modules import player
					control.sleep(200)
					control.hide()
					player.Player().play_source(title, year, season, episode, imdb, tmdb, tvdb, self.url, meta, select='1')
					return self.url
				except:
					log_utils.error()
			try: progressDialog.close()
			except: pass
			del progressDialog

			self.errorForSources()
		except:
			log_utils.error()


	def getSources(self, title, year, imdb, tvdb, season, episode, tvshowtitle, premiered, quality='HD', timeout=30):
		progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
		header = control.homeWindow.getProperty(self.labelProperty) + ': Scraping...'
		progressDialog.create(header, '')

		self.prepareSources()
		sourceDict = self.sourceDict
		progressDialog.update(0, control.lang(32600))

		content = 'movie' if tvshowtitle is None else 'episode'
		if content == 'movie':
			sourceDict = [(i[0], i[1], getattr(i[1], 'movie', None)) for i in sourceDict]
		else:
			sourceDict = [(i[0], i[1], getattr(i[1], 'tvshow', None)) for i in sourceDict]
		sourceDict = [(i[0], i[1]) for i in sourceDict if i[2] is not None]
		if control.setting('cf.disable') == 'true':
			sourceDict = [(i[0], i[1]) for i in sourceDict if not any(x in i[0] for x in self.sourcecfDict)]

		sourceDict = [(i[0], i[1], i[1].priority) for i in sourceDict]
		sourceDict = sorted(sourceDict, key=lambda i: i[2]) # sorted by scraper priority num

		threads = []
		if content == 'movie':
			title = self.getTitle(title)
			aliases = self.getAliasTitles(imdb, content)
			for i in sourceDict:
				threads.append(workers.Thread(self.getMovieSource, title, aliases, year, imdb, i[0], i[1]))
		else:
			from fenomscrapers import pack_sources
			self.packDict = providerscache.get(pack_sources, 192)
			tvshowtitle = self.getTitle(tvshowtitle)
			aliases = self.getAliasTitles(imdb, content)
			for i in sourceDict:
				threads.append(workers.Thread(self.getEpisodeSource, title, year, imdb, tvdb, season,
											episode, tvshowtitle, aliases, premiered, i[0], i[1]))

		s = [i[0] + (i[1],) for i in zip(sourceDict, threads)]
		s = [(i[3].getName(), i[0], i[2]) for i in s]
		sourcelabelDict = dict([(i[0], i[1].upper()) for i in s])
		[i.start() for i in threads]

		sdc = control.getColor(control.setting('scraper.dialog.color'))
		string1 = control.lang(32404) # msgid "[COLOR cyan]Time elapsed:[/COLOR]  %s seconds"
		# string2 = control.lang(32405) # msgid "%s seconds"
		string3 = control.lang(32406) # msgid "[COLOR cyan]Remaining providers:[/COLOR] %s"
		string4 = control.lang(32601) # msgid "[COLOR cyan]Total:[/COLOR]"

		try: timeout = int(control.setting('scrapers.timeout'))
		except: pass
		start_time = time.time()
		end_time = start_time + timeout

		quality = control.setting('hosts.quality')
		if quality == '': quality = '0'
		line1 = line2 = line3 = ""

		pre_emp = str(control.setting('preemptive.termination'))
		pre_emp_limit = int(control.setting('preemptive.limit'))
		pre_emp_res = str(control.setting('preemptive.res'))
		source_4k = source_1080 = source_720 = source_sd = total = 0
		total_format = '[COLOR %s][B]%s[/B][/COLOR]'
		pdiag_format = '4K:  %s  |  1080p:  %s  |  720p:  %s  |  SD:  %s'

		control.hide()
		while True:
			try:
				if control.monitor.abortRequested(): return sys.exit()
				try:
					if progressDialog.iscanceled(): break
				except: pass
				try:
					if progressDialog.isFinished(): break
				except: pass

				if pre_emp == 'true':
					if pre_emp_res == '0':
						if (source_4k) >= pre_emp_limit: break
					elif pre_emp_res == '1':
						if (source_1080) >= pre_emp_limit: break
					elif pre_emp_res == '2':
						if (source_720) >= pre_emp_limit: break
					elif pre_emp_res == '3':
						if (source_sd) >= pre_emp_limit: break
					else:
						if (source_sd) >= pre_emp_limit: break

				if quality == '0':
					source_4k = len([e for e in self.scraper_sources if e['quality'] == '4K'])
					source_1080 = len([e for e in self.scraper_sources if e['quality'] == '1080p'])
					source_720 = len([e for e in self.scraper_sources if e['quality'] in ['720p', 'HD']])
					source_sd = len([e for e in self.scraper_sources if e['quality'] in ['SD', 'SCR', 'CAM']])
				elif quality == '1':
					source_1080 = len([e for e in self.scraper_sources if e['quality'] == '1080p'])
					source_720 = len([e for e in self.scraper_sources if e['quality'] in ['720p', 'HD']])
					source_sd = len([e for e in self.scraper_sources if e['quality'] in ['SD', 'SCR', 'CAM']])
				elif quality == '2':
					source_720 = len([e for e in self.scraper_sources if e['quality'] in ['720p', 'HD']])
					source_sd = len([e for e in self.scraper_sources if e['quality'] in ['SD', 'SCR', 'CAM']])
				else:
					source_sd = len([e for e in self.scraper_sources if e['quality'] in ['SD', 'SCR', 'CAM']])
				total = source_4k + source_1080 + source_720 + source_sd

				source_4k_label = total_format % ('red', source_4k) if source_4k == 0 else total_format % (sdc, source_4k)
				source_1080_label = total_format % ('red', source_1080) if source_1080 == 0 else total_format % (sdc, source_1080)
				source_720_label = total_format % ('red', source_720) if source_720 == 0 else total_format % (sdc, source_720)
				source_sd_label = total_format % ('red', source_sd) if source_sd == 0 else total_format % (sdc, source_sd)
				source_total_label = total_format % ('red', total) if total == 0 else total_format % (sdc, total)

				try:
					info = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() == True]
					line1 = pdiag_format % (source_4k_label, source_1080_label, source_720_label, source_sd_label)
					line2 = string4 % source_total_label + '     ' + string1 % round(time.time() - start_time, 1)
					if len(info) > 6: line3 = string3 % str(len(info))
					elif len(info) > 0: line3 = string3 % (', '.join(info))
					else: break
					current_time = time.time()
					current_progress = current_time - start_time
					percent = int((current_progress / float(timeout)) * 100)
					# if progressDialog != control.progressDialogBG: progressDialog.update(max(1, percent), line1, line2, line3)
					if progressDialog != control.progressDialogBG: progressDialog.update(max(1, percent), line1 + '[CR]' + line2 + '[CR]' + line3)

					else: progressDialog.update(max(1, percent), line1 + '  ' + string3 % str(len(info)))
					# if len(info) == 0: break
					if end_time < current_time: break
				except:
					log_utils.error()
					break
				control.sleep(100)
			except:
				log_utils.error()
		try: progressDialog.close()
		except: pass
		del progressDialog
		del threads[:] # Make sure any remaining providers are stopped.
		self.sources.extend(self.scraper_sources)
		if len(self.sources) > 0:
			self.sourcesFilter()
		return self.sources


	def prepareSources(self):
		try:
			control.makeFile(control.dataPath)
			dbcon = database.connect(self.sourceFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''CREATE TABLE IF NOT EXISTS rel_url (source TEXT, imdb_id TEXT, season TEXT, episode TEXT, rel_url TEXT, UNIQUE(source, imdb_id, season, episode));''')
			dbcur.execute('''CREATE TABLE IF NOT EXISTS rel_src (source TEXT, imdb_id TEXT, season TEXT, episode TEXT, hosts TEXT, added TEXT, UNIQUE(source, imdb_id, season, episode));''')
			dbcur.connection.commit()
		except:
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()


	def getMovieSource(self, title, aliases, year, imdb, source, call):
		try:
			dbcon = database.connect(self.sourceFile, timeout=60)
			dbcur = dbcon.cursor()
		except: pass
		''' Fix to stop items passed with a 0 IMDB id pulling old unrelated sources from the database. '''
		if imdb == '0':
			try:
				for table in ["rel_src", "rel_url"]: dbcur.execute('''DELETE FROM {} WHERE (source=? AND imdb_id='0' AND season='' AND episode='')'''.format(table), (source, ))
				dbcur.connection.commit()
			except:
				log_utils.error()
		try:
			sources = []
			db_movie = dbcur.execute('''SELECT * FROM rel_src WHERE (source=? AND imdb_id=? AND season='' AND episode='')''', (source, imdb)).fetchone()
			if db_movie:
				timestamp = control.datetime_workaround(str(db_movie[5]), '%Y-%m-%d %H:%M:%S.%f', False)
				db_movie_valid = abs(self.time - timestamp) < self.single_expiry
				if db_movie_valid:
					# sources = eval(db_movie[4].encode('utf-8'))
					sources = eval(db_movie[4])
					return self.scraper_sources.extend(sources)
		except:
			log_utils.error()
		try:
			url = None
			url = dbcur.execute('''SELECT * FROM rel_url WHERE (source=? AND imdb_id=? AND season='' AND episode='')''', (source, imdb)).fetchone()
			# if url: url = eval(url[4].encode('utf-8'))
			if url: url = eval(url[4])
		except:
			log_utils.error()
		try:
			if not url: url = call.movie(imdb, title, aliases, year)
			if url:
				dbcur.execute('''INSERT OR REPLACE INTO rel_url Values (?, ?, ?, ?, ?)''', (source, imdb, '', '', repr(url)))
				dbcur.connection.commit()
		except:
			log_utils.error()
		try:
			sources = []
			sources = call.sources(url, self.hostprDict)
			if sources:
				sources = [jsloads(t) for t in set(jsdumps(d, sort_keys=True) for d in sources)]
				self.scraper_sources.extend(sources)
				dbcur.execute('''INSERT OR REPLACE INTO rel_src Values (?, ?, ?, ?, ?, ?)''', (source, imdb, '', '', repr(sources), datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
				dbcur.connection.commit()
		except:
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()


	def getEpisodeSource(self, title, year, imdb, tvdb, season, episode, tvshowtitle, aliases, premiered, source, call):
		try:
			dbcon = database.connect(self.sourceFile, timeout=60)
			dbcur = dbcon.cursor()
		except: pass
		''' Fix to stop items passed with a 0 IMDB id pulling old unrelated sources from the database. '''
		if imdb == '0':
			try:
				for table in ["rel_src", "rel_url"]: dbcur.execute('''DELETE FROM {} WHERE (source=? AND imdb_id='0' AND season=? AND episode=?)'''.format(table), (source, season, episode))
				dbcur.execute('''DELETE FROM rel_src WHERE (source = ? AND imdb_id = '0' AND season = ? AND episode = '')''', (source, season))
				for table in ["rel_src", "rel_url"]: dbcur.execute('''DELETE FROM {} WHERE (source=? AND imdb_id='0' AND season='' AND episode='')'''.format(table), (source, ))
				dbcur.connection.commit()
			except:
				log_utils.error()
		try: # singleEpisodes db check
			db_singleEpisodes_valid = False
			if self.dev_mode and self.dev_disable_single: raise Exception()
			sources = []
			db_singleEpisodes = dbcur.execute('''SELECT * FROM rel_src WHERE (source=? AND imdb_id=? AND season=? AND episode=?)''', (source, imdb, season, episode)).fetchone()
			if db_singleEpisodes:
				timestamp = control.datetime_workaround(str(db_singleEpisodes[5]), '%Y-%m-%d %H:%M:%S.%f', False)
				db_singleEpisodes_valid = abs(self.time - timestamp) < self.single_expiry
				if db_singleEpisodes_valid:
					# sources = eval(db_singleEpisodes[4].encode('utf-8'))
					sources = eval(db_singleEpisodes[4])
					self.scraper_sources.extend(sources)
		except:
			log_utils.error()
		try: # seasonPacks db check
			db_seasonPacks_valid = False
			if self.is_airing: raise Exception()
			if self.dev_mode and self.dev_disable_season_packs: raise Exception()
			sources = []
			db_seasonPacks = dbcur.execute('''SELECT * FROM rel_src WHERE (source=? AND imdb_id=? AND season=? AND episode='')''', (source, imdb, season)).fetchone()
			if db_seasonPacks:
				timestamp = control.datetime_workaround(str(db_seasonPacks[5]), '%Y-%m-%d %H:%M:%S.%f', False)
				db_seasonPacks_valid = abs(self.time - timestamp) < self.season_expiry
				if db_seasonPacks_valid:
					# sources = eval(db_seasonPacks[4].encode('utf-8'))
					sources = eval(db_seasonPacks[4])
					self.scraper_sources.extend(sources)
		except:
			log_utils.error()
		try: # showPacks db check
			db_showPacks_valid = False
			if self.dev_mode and self.dev_disable_show_packs: raise Exception()
			sources = []
			db_showPacks = dbcur.execute('''SELECT * FROM rel_src WHERE (source=? AND imdb_id=? AND season='' AND episode='')''', (source, imdb)).fetchone()
			if db_showPacks:
				timestamp = control.datetime_workaround(str(db_showPacks[5]), '%Y-%m-%d %H:%M:%S.%f', False)
				db_showPacks_valid = abs(self.time - timestamp) < self.show_expiry
				if db_showPacks_valid:
					# sources = eval(db_showPacks[4].encode('utf-8'))
					sources = eval(db_showPacks[4])
					sources = [i for i in sources if i.get('last_season') >= int(season)] # filter out range items that do not apply to current season
					self.scraper_sources.extend(sources)
					if db_singleEpisodes_valid and db_seasonPacks_valid:
						return self.scraper_sources
		except:
			log_utils.error()
		try:
			url = None
			url = dbcur.execute('''SELECT * FROM rel_url WHERE (source=? AND imdb_id=? AND season='' AND episode='')''', (source, imdb)).fetchone()
			# if url: url = eval(url[4].encode('utf-8'))
			if url: url = eval(url[4])
		except:
			log_utils.error()
		try:
			if not url: url = call.tvshow(imdb, tvdb, tvshowtitle, aliases, year)
			if url:
				dbcur.execute('''INSERT OR REPLACE INTO rel_url Values (?, ?, ?, ?, ?)''', (source, imdb, '', '', repr(url)))
				dbcur.connection.commit()
		except:
			log_utils.error()
		try:
			ep_url = None
			ep_url = dbcur.execute('''SELECT * FROM rel_url WHERE (source=? AND imdb_id=? AND season=? AND episode=?)''', (source, imdb, season, episode)).fetchone()
			# if ep_url: ep_url = eval(ep_url[4].encode('utf-8'))
			if ep_url: ep_url = eval(ep_url[4])
		except:
			log_utils.error()
		try:
			if url:
				if not ep_url: ep_url = call.episode(url, imdb, tvdb, title, premiered, season, episode)
				if ep_url:
					dbcur.execute('''INSERT OR REPLACE INTO rel_url Values (?, ?, ?, ?, ?)''', (source, imdb, season, episode, repr(ep_url)))
					dbcur.connection.commit()
		except:
			log_utils.error()
		try: # singleEpisodes scraper call
			if self.dev_mode and self.dev_disable_single: raise Exception()
			if db_singleEpisodes_valid: raise Exception()
			sources = []
			sources = call.sources(ep_url, self.hostprDict)
			if sources:
				sources = [jsloads(t) for t in set(jsdumps(d, sort_keys=True) for d in sources)]
				self.scraper_sources.extend(sources)
				dbcur.execute('''INSERT OR REPLACE INTO rel_src Values (?, ?, ?, ?, ?, ?)''', (source, imdb, season, episode, repr(sources), datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
				dbcur.connection.commit()
		except:
			log_utils.error()
		try: # seasonPacks scraper call
			if self.dev_mode and self.dev_disable_season_packs: raise Exception()
			if self.is_airing: raise Exception()
			if self.packDict and source in self.packDict:
				if db_seasonPacks_valid: raise Exception()
				sources = []
				sources = call.sources_packs(ep_url, self.hostprDict, bypass_filter=self.dev_disable_season_filter)
				if sources:
					sources = [jsloads(t) for t in set(jsdumps(d, sort_keys=True) for d in sources)]
					self.scraper_sources.extend(sources)
					dbcur.execute('''INSERT OR REPLACE INTO rel_src Values (?, ?, ?, ?, ?, ?)''', (source, imdb, season,'', repr(sources), datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
					dbcur.connection.commit()
		except:
			log_utils.error()
		try: # showPacks scraper call
			if self.dev_mode and self.dev_disable_show_packs: raise Exception()
			if self.packDict and source in self.packDict:
				if db_showPacks_valid: raise Exception()
				sources = []
				sources = call.sources_packs(ep_url, self.hostprDict, search_series=True, total_seasons=self.total_seasons, bypass_filter=self.dev_disable_show_filter)
				if sources:
					sources = [jsloads(t) for t in set(jsdumps(d, sort_keys=True) for d in sources)]
					sources = [i for i in sources if i.get('last_season') >= int(season)] # filter out range items that do not apply to current season
					self.scraper_sources.extend(sources)
					dbcur.execute('''INSERT OR REPLACE INTO rel_src Values (?, ?, ?, ?, ?, ?)''', (source, imdb, '', '', repr(sources), datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
					dbcur.connection.commit()
		except:
			log_utils.error()
		finally:
			dbcon.close() ; dbcon.close()


	def alterSources(self, url, meta):
		try:
			if control.setting('hosts.mode') == '2' or (control.setting('enable.upnext') == 'true' and 'episode' in meta): url += '&select=1'
			else: url += '&select=2'
			# control.execute('RunPlugin(%s)' % url)
			control.execute('PlayMedia(%s)' % url)
		except:
			log_utils.error()


	def sourcesFilter(self):
		control.busy()
		quality = control.setting('hosts.quality')
		if quality == '': quality = '0'
		if control.setting('remove.duplicates') == 'true':
			self.sources = self.filter_dupes()
		if self.mediatype == 'episode':
			self.sources = self.calc_pack_size()
		if control.setting('source.enablesizelimit') == 'true':
			self.sources = [i for i in self.sources if i.get('size', 0) <= int(control.setting('source.sizelimit'))]
		if control.setting('remove.hevc') == 'true':
			self.sources = [i for i in self.sources if 'HEVC' not in i.get('info', '')] # scrapers write HEVC to info
		if control.setting('remove.CamSd.sources') == 'true':
			if any(i for i in self.sources if any(value in i['quality'] for value in ['4K', '1080p', '720p'])): #only remove CAM and SD if better quality does exist
				self.sources = [i for i in self.sources if not any(value in i['quality'] for value in ['CAM', 'SD'])]
		if control.setting('remove.3D.sources') == 'true':
			self.sources = [i for i in self.sources if '3D' not in i.get('info', '')]

		local = [i for i in self.sources if 'local' in i and i['local'] is True] # for library and videoscraper (skips cache check)
		self.sources = [i for i in self.sources if not i in local]
		direct = [i for i in self.sources if i['direct'] == True] # acct scrapers (skips cache check)
		self.sources = [i for i in self.sources if not i in direct]

		from copy import deepcopy
		deepcopy_sources = deepcopy(self.sources)
		deepcopy_sources = [i for i in deepcopy_sources if 'magnet:' in i['url']]
		threads = []
		self.filter = []
		valid_hosters = set([i['source'] for i in self.sources])

		def checkStatus(function, debrid_name, valid_hoster):
			try:
				cached = None
				if deepcopy_sources: cached = function(deepcopy_sources)
				# if cached: self.filter += [dict(i.items() + [('debrid', debrid_name)]) for i in cached if 'magnet:' in i['url']]
				if cached: self.filter += [dict(list(i.items()) + [('debrid', debrid_name)]) for i in cached if 'magnet:' in i['url']]
				# self.filter += [dict(i.items() + [('debrid', debrid_name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]
				self.filter += [dict(list(i.items()) + [('debrid', debrid_name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]
			except:
				log_utils.error()

		for d in self.debrid_resolvers:
			if d.name == 'Premiumize.me' and control.setting('premiumize.enable') == 'true':
				try:
					valid_hoster = [i for i in valid_hosters if d.valid_url(i)]
					threads.append(workers.Thread(checkStatus, self.pm_cache_chk_list, d.name, valid_hoster))
				except:
					log_utils.error()
			if d.name == 'Real-Debrid' and control.setting('realdebrid.enable') == 'true':
				try:
					valid_hoster = [i for i in valid_hosters if d.valid_url(i)]
					threads.append(workers.Thread(checkStatus, self.rd_cache_chk_list, d.name, valid_hoster))
				except:
					log_utils.error()
			if d.name == 'AllDebrid' and control.setting('alldebrid.enable') == 'true':
				try:
					valid_hoster = [i for i in valid_hosters if d.valid_url(i)]
					threads.append(workers.Thread(checkStatus, self.ad_cache_chk_list, d.name, valid_hoster))
				except:
					log_utils.error()
		if threads:
			[i.start() for i in threads]
			[i.join() for i in threads]
		self.filter += direct
		self.filter += local
		self.sources = self.filter

		if control.setting('sources.group.sort') == '1':
			torr_filter = []
			torr_filter += [i for i in self.sources if 'torrent' in i['source']]  #torrents first
			if control.setting('sources.size.sort') == 'true':
				torr_filter.sort(key=lambda k: k.get('size', 0), reverse=True)
			aact_filter = []
			aact_filter += [i for i in self.sources if i['direct'] == True]  #account scrapers and local/library next
			if control.setting('sources.size.sort') == 'true':
				aact_filter.sort(key=lambda k: k.get('size', 0), reverse=True)
			prem_filter = []
			prem_filter += [i for i in self.sources if 'torrent' not in i['source'] and i['debridonly'] is True]  #prem.hosters last
			if control.setting('sources.size.sort') == 'true':
				prem_filter.sort(key=lambda k: k.get('size', 0), reverse=True)
			self.sources = torr_filter
			self.sources += aact_filter
			self.sources += prem_filter

		elif control.setting('sources.size.sort') == 'true':
			filter = []
			filter += [i for i in self.sources]
			filter.sort(key=lambda k: k.get('size', 0), reverse=True)
			self.sources = filter

		filter = []
		if quality in ['0']:
			filter += [i for i in self.sources if i['quality'] == '4K']
		if quality in ['0', '1']:
			filter += [i for i in self.sources if i['quality'] == '1080p']
		if quality in ['0', '1', '2']:
			filter += [i for i in self.sources if i['quality'] == '720p']
		filter += [i for i in self.sources if i['quality'] == 'SCR']
		filter += [i for i in self.sources if i['quality'] == 'SD']
		filter += [i for i in self.sources if i['quality'] == 'CAM']
		self.sources = filter
		self.sources = self.sources[:4000]

		cached_color = control.getColor(control.setting('sources.cached.color'))
		uncached_color = control.getColor(control.setting('sources.uncached.color'))
		prem_color = control.getColor(control.setting('sources.prem.color'))
		line2_color = control.getColor(control.setting('sources.sec.color'))
		line2_type = control.setting('sources.sec.type')

		for i in range(len(self.sources)):
			t = ''
			if line2_type == 'link title' and 'name' in self.sources[i]:
				t = self.sources[i]['name']
			else:
				try: f = (' / '.join(['%s ' % info.strip() for info in self.sources[i]['info'].split('|')]))
				except: f = ''
				if 'name_info' in self.sources[i]:
					t = source_utils.getFileType(name_info=self.sources[i]['name_info'])
				else:
					t = source_utils.getFileType(url=self.sources[i]['url'])
				t = '%s / %s' % (f, t) if (f != '' and f != '0 ' and f != ' ') else t
			if t == '':
				t = source_utils.getFileType(url=self.sources[i]['url'])

			try:
				size = self.sources[i]['info'].split('|', 1)[0]
				if any(value in size for value in ['HEVC', '3D']): size = ''
			except: size = ''

			u = self.sources[i]['url']
			q = self.sources[i]['quality']
			p = self.sources[i]['provider'].upper()
			s = self.sources[i]['source'].upper().rsplit('.', 1)[0]

			if 'debrid' in self.sources[i]: d = self.debrid_abv(self.sources[i]['debrid'])
			else: d = self.sources[i]['debrid'] = ''
			if d:
				if 'UNCACHED' in s and uncached_color != 'nocolor':
					color = uncached_color
					sec_color = uncached_color
				elif 'CACHED' in s and cached_color != 'nocolor':
					color = cached_color
					sec_color = line2_color
				elif 'TORRENT' not in s and prem_color != 'nocolor':
					color = prem_color
					sec_color = line2_color
			else:
				sec_color = line2_color

			if d != '':
				if size: line1 = '[COLOR %s]%02d  |  [B]%s[/B]  |  %s  |  %s  |  %s  |  [B]%s[/B][/COLOR]' % (color, int(i + 1), q, d, p, s, size)
				else: line1 = '[COLOR %s]%02d  |  [B]%s[/B]  |  %s  |  %s  |  %s[/COLOR]' % (color, int(i + 1), q, d, p, s)
			else:
				if size: line1 = '%02d  |  [B]%s[/B]  |  %s  |  %s  |  [B]%s[/B]' % (int(i + 1), q, p, s, size)
				else: line1 = '%02d  |  [B]%s[/B]  |  %s  |  %s' % (int(i + 1), q, p, s)
			line1_len = len(line1)-20

			if t != '': line2 = '\n       [COLOR %s][I]%s[/I][/COLOR]' % (sec_color, t)
			else: line2 = ''
			line2_len = len(line2)

			if line2_len > line1_len:
				adjust = line2_len - line1_len
				line1 = line1.ljust(line1_len+30+adjust)
			label = line1 + line2

			self.sources[i]['label'] = label
		control.hide()
		return self.sources


	def filter_dupes(self):
		filter = []
		log_dupes = control.setting('remove.duplicates.logging') == 'false'
		for i in self.sources:
			a = i['url'].lower()
			for sublist in filter:
				try:
					b = sublist['url'].lower()
					if 'magnet:' in a:
						if i['hash'].lower() in b:
							filter.remove(sublist)
							if log_dupes:
								log_utils.log('Removing %s - %s (DUPLICATE TORRENT) ALREADY IN :: %s' % (sublist['provider'], b, i['provider']), level=log_utils.LOGDEBUG)
							break
					elif a == b:
						filter.remove(sublist)
						if log_dupes:
							log_utils.log('Removing %s - %s (DUPLICATE LINK) ALREADY IN :: %s' % (sublist['source'], i['url'], i['provider']), level=log_utils.LOGDEBUG)
						break
				except:
					log_utils.error()
			filter.append(i)
		header = control.homeWindow.getProperty(self.labelProperty)
		control.notification(title=header, message='Removed %s duplicate sources from list' % (len(self.sources) - len(filter)))
		log_utils.log('Removed %s duplicate sources for (%s) from list' % (len(self.sources) - len(filter), control.homeWindow.getProperty(self.labelProperty)), level=log_utils.LOGDEBUG)
		return filter


	def sourcesResolve(self, item):
		url = item['url']
		self.url = None
		debrid_provider = item['debrid']
		if 'magnet:' in url:
			if not 'uncached' in item['source']:
				try:
					meta = control.homeWindow.getProperty(self.metaProperty)
					if meta:
						meta = jsloads(unquote(meta.replace('%22', '\\"')))
						season = meta.get('season')
						episode = meta.get('episode')
						title = meta.get('title')
					else:
						season = control.homeWindow.getProperty(self.seasonProperty)
						episode = control.homeWindow.getProperty(self.episodeProperty)
						title = control.homeWindow.getProperty(self.titleProperty)
					if debrid_provider == 'Real-Debrid':
						from resources.lib.debrid.realdebrid import RealDebrid as debrid_function
					elif debrid_provider == 'Premiumize.me':
						from resources.lib.debrid.premiumize import Premiumize as debrid_function
					elif debrid_provider == 'AllDebrid':
						from resources.lib.debrid.alldebrid import AllDebrid as debrid_function
					else: return
					url = debrid_function().resolve_magnet(url, item['hash'], season, episode, title)
					self.url = url
					return url
				except:
					log_utils.error()
					return
		else:
			direct = item['direct']
			call = [i[1] for i in self.sourceDict if i[0] == item['provider']][0]
			if direct:
				self.url = call.resolve(url)
				return url
			else:
				try:
					if debrid_provider == 'Real-Debrid':
						from resources.lib.debrid.realdebrid import RealDebrid as debrid_function
					elif debrid_provider == 'Premiumize.me':
						from resources.lib.debrid.premiumize import Premiumize as debrid_function
					elif debrid_provider == 'AllDebrid':
						from resources.lib.debrid.alldebrid import AllDebrid as debrid_function
					u = url = call.resolve(url)
					url = debrid_function().unrestrict_link(url)
					self.url = url
					return url
				except:
					log_utils.error()
					return


	def sourcesDialog(self, items):
		try:
			labels = [i['label'] for i in items]
			select = control.selectDialog(labels)
			if select == -1: return 'close://'
			next = [y for x, y in enumerate(items) if x >= select]
			prev = [y for x, y in enumerate(items) if x < select][::-1]
			items = [items[select]]
			items = [i for i in items + next + prev][:40]
			header = control.homeWindow.getProperty(self.labelProperty) + ': Resolving...'
			progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
			progressDialog.create(header, '')

			block = None
			control.hide()
			for i in range(len(items)):
				try:
					if items[i]['source'] == block: raise Exception()
					w = workers.Thread(self.sourcesResolve, items[i])
					w.start()
					label = re.sub(r' {2,}', ' ', str(items[i]['label']))
					label = re.sub(r'\n', '', label)
					try:
						if progressDialog.iscanceled(): break
						progressDialog.update(int((100 / float(len(items))) * i), label)
					except: progressDialog.update(int((100 / float(len(items))) * i), '[COLOR %s]Resolving...[/COLOR]%s' % (self.highlight_color, items[i]['name']))

					if 'torrent' in items[i].get('source'): offset = float('inf')
					else: offset = 0
					m = ''
					for x in range(3600):
						try:
							if control.monitor.abortRequested():
								control.notification(message=32400)
								return sys.exit()
							if progressDialog.iscanceled():
								control.notification(message=32400)
								return progressDialog.close()
						except: pass

						k = control.condVisibility('Window.IsActive(virtualkeyboard)')
						if k: m += '1' ; m = m[-1]
						if (not w.is_alive() or x > 30 + offset) and not k: break
						k = control.condVisibility('Window.IsActive(yesnoDialog)')
						if k: m += '1' ; m = m[-1]
						if (not w.is_alive() or x > 30 + offset) and not k: break
						time.sleep(0.5)

					for x in range(30):
						try:
							if control.monitor.abortRequested():
								control.notification(message=32400)
								return sys.exit()
							if progressDialog.iscanceled():
								control.notification(message=32400)
								return progressDialog.close()
						except: pass

						if m == '': break
						if not w.is_alive(): break
						time.sleep(0.5)

					if w.is_alive(): block = items[i]['source']
					if not self.url: raise Exception()
					if not any(x in self.url.lower() for x in self.extensions):
						log_utils.log('Playback not supported for: %s' % self.url, __name__, log_utils.LOGDEBUG)
						raise Exception()

					try: progressDialog.close()
					except: pass
					control.execute('Dialog.Close(virtualkeyboard)')
					control.execute('Dialog.Close(yesnoDialog)')
					return self.url
				except:
					log_utils.error()

			try: progressDialog.close()
			except: pass
			del progressDialog

		except Exception as e:
			try: progressDialog.close()
			except: pass
			del progressDialog
			log_utils.log('Error %s' % str(e), __name__, log_utils.LOGDEBUG)


	def sourcesAutoPlay(self, items):
		if control.setting('autoplay.sd') == 'true':
			items = [i for i in items if not i['quality'] in ['4K', '1080p', '720p', 'HD']]
		u = None
		header = control.homeWindow.getProperty(self.labelProperty) + ': Resolving...'
		try:
			control.sleep(500)
			if control.setting('progress.dialog') == '0': progressDialog = control.progressDialog
			else: progressDialog = control.progressDialogBG
			progressDialog.create(header, '')
		except: pass

		control.hide()
		for i in range(len(items)):
			label = re.sub(r' {2,}', ' ', str(items[i]['label']))
			label = re.sub(r'\n', '', label)
			try:
				if progressDialog.iscanceled(): break
				progressDialog.update(int((100 / float(len(items))) * i), label)
			except: progressDialog.update(int((100 / float(len(items))) * i), '[COLOR %s]Resolving...[/COLOR]%s' % (self.highlight_color, items[i]['name']))
			try:
				if control.monitor.abortRequested(): return sys.exit()
				url = self.sourcesResolve(items[i])
				if not u: u = url
				if url: break
			except: pass
		try: progressDialog.close()
		except: pass
		del progressDialog
		return u


	def debridPackDialog(self, provider, name, magnet_url, info_hash):
		try:
			if provider == 'Real-Debrid':
				from resources.lib.debrid.realdebrid import RealDebrid as debrid_function
			elif provider == 'Premiumize.me':
				from resources.lib.debrid.premiumize import Premiumize as debrid_function
			elif provider == 'AllDebrid':
				from resources.lib.debrid.alldebrid import AllDebrid as debrid_function
			else: return
			debrid_files = None
			control.busy()
			try: debrid_files = debrid_function().display_magnet_pack(magnet_url, info_hash)
			except: pass
			if not debrid_files:
				control.hide()
				return control.notification(message=32399)
			debrid_files = sorted(debrid_files, key=lambda k: k['filename'].lower())
			display_list = ['%02d | [B]%.2f GB[/B] | [I]%s[/I]' % \
							(count, i['size'], i['filename'].upper()) for count, i in enumerate(debrid_files, 1)]
			control.hide()
			chosen = control.selectDialog(display_list, heading=name)
			if chosen < 0: return None
			control.busy()
			chosen_result = debrid_files[chosen]
			if provider	 == 'Real-Debrid':
				self.url = debrid_function().unrestrict_link(chosen_result['link'])
			elif provider == 'Premiumize.me':
				self.url = debrid_function().add_headers_to_url(chosen_result['link'])
			elif provider == 'AllDebrid':
				self.url = debrid_function().unrestrict_link(chosen_result['link'])
			from resources.lib.modules import player
			from resources.lib.modules.source_utils import seas_ep_filter
			meta = jsloads(unquote(control.homeWindow.getProperty(self.metaProperty).replace('%22', '\\"')))
			title = meta['tvshowtitle']
			year = meta['year'] if 'year' in meta else None

			if 'tvshowtitle' in meta:
				year = meta['tvshowyear'] if 'tvshowyear' in meta else year
			season = meta['season'] if 'season' in meta else None
			episode = meta['episode'] if 'episode' in meta else None
			imdb = meta['imdb'] if 'imdb' in meta else None
			tmdb = meta['tmdb'] if 'tmdb' in meta else None
			tvdb = meta['tvdb'] if 'tvdb' in meta else None
			release_title = chosen_result['filename']
			control.hide()
			if seas_ep_filter(season, episode, release_title):
				return player.Player().play_source(title, year, season, episode, imdb, tmdb, tvdb, self.url, meta, select='1')
			else:
				return player.Player().play(self.url)
		except Exception as e:
			control.hide()
			log_utils.log('Error debridPackDialog %s' % str(e), __name__, log_utils.LOGDEBUG)


	def sourceInfo(self, info):
		try:
			platform = sys.platform
			supported_platform = any(value in platform for value in ['win32', 'linux2'])
			source = jsloads(info)[0]
			try: f = ' / '.join(['%s' % info.strip() for info in source.get('info').split('|')])
			except: f = ''
			if 'name_info' in source:
				t = source_utils.getFileType(name_info=source.get('name_info'))
			else:
				t = source_utils.getFileType(url=source.get('url'))
			t = '%s /%s' % (f, t) if (f != '' and f != '0 ' and f != ' ') else t
			if t == '':
				t = source_utils.getFileType(url=source.get('url'))
			list = [('[COLOR %s]url:[/COLOR]  %s' % (self.highlight_color, source.get('url')), source.get('url'))]
			# "&" in magnets causes copy2clip to fail
			if 'magnet:' not in source.get('url') and not source.get('direct'):
				if supported_platform: list += [('[COLOR %s]  -- Copy url To Clipboard[/COLOR]' % self.highlight_color, ' ')]
			list += [('[COLOR %s]name:[/COLOR]  %s' % (self.highlight_color, source.get('name')), source.get('name'))]
			if supported_platform: list += [('[COLOR %s]  -- Copy name To Clipboard[/COLOR]' % self.highlight_color, ' ')]
			list += [('[COLOR %s]info:[/COLOR]  %s' % (self.highlight_color, t), ' ')]
			if 'magnet:' in source.get('url'):
				list += [('[COLOR %s]hash:[/COLOR]  %s' % (self.highlight_color, source.get('hash')), source.get('hash'))]
				if supported_platform: list += [('[COLOR %s]  -- Copy hash To Clipboard[/COLOR]' % self.highlight_color, ' ')]
				list += [('[COLOR %s]seeders:[/COLOR]  %s' % (self.highlight_color, source.get('seeders')), ' ')]
			select = control.selectDialog([i[0] for i in list], 'Source Info')
			if any(x in list[select][0] for x in ['Copy url To Clipboard', 'Copy name To Clipboard', 'Copy hash To Clipboard']):
				control.copy2clip(list[select - 1][1])
			return
		except:
			log_utils.error()


	def errorForSources(self):
		try:
			control.sleep(200) # added 5/14
			control.hide()
			if self.url == 'close://': control.notification(message=32400)
			else: control.notification(message=32401)
			control.cancelPlayback()
		except:
			log_utils.error()


	def getAliasTitles(self, imdb, content):
		lang = 'en'
		try:
			t = trakt.getMovieAliases(imdb) if content == 'movie' else trakt.getTVShowAliases(imdb)
			if not t: return []
			t = [i for i in t if i.get('country', '').lower() in [lang, '', 'us']]
			return jsdumps(t)
		except:
			log_utils.error()
			return []


	def getTitle(self, title):
		title = cleantitle.normalize(title)
		return title


	def getConstants(self): # gets initialized multiple times
		self.itemProperty = 'plugin.video.venom.container.items'
		self.metaProperty = 'plugin.video.venom.container.meta'
		self.seasonProperty = 'plugin.video.venom.container.season'
		self.episodeProperty = 'plugin.video.venom.container.episode'
		self.titleProperty = 'plugin.video.venom.container.title'
		self.imdbProperty = 'plugin.video.venom.container.imdb'
		self.tmdbProperty = 'plugin.video.venom.container.tmdb'
		self.tvdbProperty = 'plugin.video.venom.container.tvdb'
		self.labelProperty = 'plugin.video.venom.container.label'

		self.sourceDict = fs_sources()
		# add cloud scrapers to sourceDict

		from resources.lib.modules import premium_hosters
		self.debrid_resolvers = debrid.debrid_resolvers()
		def cache_prDict():
			try:
				hosts = []
				for d in self.debrid_resolvers:
					hosts += d.get_hosts()[d.name]
				return list(set(hosts))
			except:
				return premium_hosters.hostprDict

		self.hostprDict = providerscache.get(cache_prDict, 192)
		self.sourcecfDict = premium_hosters.sourcecfDict


	def calc_pack_size(self):
		seasoncount = None
		counts = None
		try:
			meta = control.homeWindow.getProperty(self.metaProperty)
			if meta:
				meta = jsloads(unquote(meta.replace('%22', '\\"')))
				seasoncount = meta.get('seasoncount', None)
				counts = meta.get('counts', None)
		except:
			log_utils.error()
		# check metacache, 2nd fallback
		if not seasoncount or not counts:
			try:
				imdb_user = control.setting('imdb.user').replace('ur', '')
				tvdb_key = control.setting('tvdb.api.key')

				user = str(imdb_user) + str(tvdb_key)
				meta_lang = control.apiLanguage()['tvdb']
				if meta:
					imdb = meta.get('imdb')
					tmdb = meta.get('tmdb')
					tvdb = meta.get('tvdb')
				else:
					imdb = control.homeWindow.getProperty(self.imdbProperty)
					tmdb = control.homeWindow.getProperty(self.tmdbProperty)
					tvdb = control.homeWindow.getProperty(self.tvdbProperty)
				ids = [{'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb}]

				meta2 = metacache.fetch(ids, meta_lang, user)[0]
				if not seasoncount: seasoncount = meta2.get('seasoncount', None)
				if not counts: counts = meta2.get('counts', None)
			except:
				log_utils.error()
		# make request, 3rd fallback
		if not seasoncount or not counts:
			try:
				if meta: season = meta.get('season')
				else: season = control.homeWindow.getProperty(self.seasonProperty)
				from resources.lib.indexers import tvdb_v1
				counts = tvdb_v1.get_counts(tvdb)
				seasoncount = counts[season]
			except:
				log_utils.error()
				return self.sources
		for i in self.sources:
			try:
				if 'package' in i:
					dsize = i.get('size')
					if not dsize: continue
					if i['package'] == 'season':
						divider = int(seasoncount)
						if not divider: continue
					else:
						if not counts: continue
						season_count = 1
						divider = 0
						while season_count <= int(i['last_season']):
							divider += int(counts[str(season_count)])
							season_count += 1
					float_size = float(dsize) / divider
					if round(float_size, 2) == 0: continue
					str_size = '%.2f GB' % float_size
					info = i['info']
					try: info = [i['info'].split(' | ', 1)[1]]
					except: info = []
					info.insert(0, str_size)
					info = ' | '.join(info)
					i.update({'size': float_size, 'info': info})
				else:
					continue
			except:
				log_utils.error()
				continue
		return self.sources


	def ad_cache_chk_list(self, torrent_List):
		if len(torrent_List) == 0: return
		try:
			hashList = [i['hash'] for i in torrent_List]
			cached = alldebrid.AllDebrid().check_cache(hashList)
			if not cached: return None
			cached = cached['magnets']
			count = 0
			for i in torrent_List:
				if 'error' in cached[count]:
					count += 1
					continue
				if cached[count]['instant'] is False:
					if 'package' in i: i.update({'source': 'uncached (pack) torrent'})
					else: i.update({'source': 'uncached torrent'})
				else:
					if 'package' in i: i.update({'source': 'cached (pack) torrent'})
					else: i.update({'source': 'cached torrent'})
				count += 1
			return torrent_List
		except:
			log_utils.error()


	def pm_cache_chk_list(self, torrent_List):
		if len(torrent_List) == 0: return
		try:
			hashList = [i['hash'] for i in torrent_List]
			cached = premiumize.Premiumize().check_cache_list(hashList)
			if not cached: return None
			count = 0
			for i in torrent_List:
				if cached[count] is False:
					if 'package' in i: i.update({'source': 'uncached (pack) torrent'})
					else: i.update({'source': 'uncached torrent'})
				else:
					if 'package' in i: i.update({'source': 'cached (pack) torrent'})
					else: i.update({'source': 'cached torrent'})
				count += 1
			return torrent_List
		except:
			log_utils.error()


	def rd_cache_chk_list(self, torrent_List):
		if len(torrent_List) == 0: return
		def base32_to_hex(hash):
			from base64 import b32decode
			from resources.lib.modules import py_tools
			log_utils.log('base32 hash: %s' % hash, __name__, log_utils.LOGDEBUG)
			if py_tools.isPY3:
				hex = b32decode(hash).hex()
			else:
				hex = b32decode(hash).encode('hex') 
			log_utils.log('base32_to_hex: %s' % hex, __name__, log_utils.LOGDEBUG)
			return hex
		try:
			hashList = [i['hash'] if len(i['hash']) == 40 else base32_to_hex(i['hash']) for i in torrent_List] # RD can not handle BASE32 encoded hashes, hex 40 only (AD and PM convert)
			cached = realdebrid.RealDebrid().check_cache_list(hashList)
			# log_utils.log('hashList = %s' % len(hashList), __name__, log_utils.LOGDEBUG)
			# log_utils.log('cached = %s' % len(cached), __name__, log_utils.LOGDEBUG)
			if not cached: return None
			for i in torrent_List:
				if 'rd' not in cached.get(i['hash'].lower(), {}):
					if 'package' in i: i.update({'source': 'uncached (pack) torrent'})
					else: i.update({'source': 'uncached torrent'})
					continue
				elif len(cached[i['hash'].lower()]['rd']) >= 1:
					if 'package' in i: i.update({'source': 'cached (pack) torrent'})
					else: i.update({'source': 'cached torrent'})
				else:
					if 'package' in i: i.update({'source': 'uncached (pack) torrent'})
					else: i.update({'source': 'uncached torrent'})
			return torrent_List
		except:
			log_utils.error()


	def clr_item_providers(self, title, year, imdb, tvdb, season, episode, tvshowtitle, premiered):
		providerscache.remove(self.getSources, title, year, imdb, tvdb, season, episode, tvshowtitle, premiered) # function cache removal of selected item ONLY
		try:
			dbcon = database.connect(self.sourceFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''SELECT count(name) FROM sqlite_master WHERE type='table' AND name='rel_src';''') # table exists so both all will
			if dbcur.fetchone()[0] == 1:
				dbcur.execute('''DELETE FROM rel_src WHERE imdb_id=?''', (imdb,)) # DEL the "rel_src" list of cached links
				if not tvshowtitle:
					dbcur.execute('''DELETE FROM rel_url WHERE imdb_id=?''', (imdb,)) #only DEL movies "rel_url" so imdb year check may update for setting change
				dbcur.connection.commit()
		except:
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()


	def movie_chk_imdb(self, imdb, title, year):
		try:
			if not imdb or imdb == '0': return year, title
			from resources.lib.modules.client import _basic_request
			result = _basic_request('https://v2.sg.media-imdb.com/suggestion/t/{}.json'.format(imdb))
			if not result: return year, title
			result = jsloads(result)['d'][0]
			year_ck = str(result['y'])
			title_ck = result['l']
			if not year_ck or not title_ck: return year, title
			if year != year_ck: year = year_ck
			if title != title_ck: title = title_ck
			return year, title
		except:
			log_utils.error()
			return year, title


	def get_season_info(self, imdb, tvdb, meta, season):
		total_seasons = None
		is_airing = None
		try:
			meta = jsloads(unquote(meta.replace('%22', '\\"')))
			total_seasons = meta.get('total_seasons', None)
			is_airing = meta.get('is_airing', None)
		except: pass
		# check metacache, 2nd fallback
		if not total_seasons or not is_airing:
			try:
				imdb_user = control.setting('imdb.user').replace('ur', '')
				tvdb_key = control.setting('tvdb.api.key')
				user = str(imdb_user) + str(tvdb_key)
				meta_lang = control.apiLanguage()['tvdb']
				ids = [{'imdb': imdb, 'tvdb': tvdb}]
				meta2 = metacache.fetch(ids, meta_lang, user)[0]
				if not total_seasons:
					total_seasons = meta2.get('total_seasons', None)
				if not is_airing:
					is_airing = meta2.get('is_airing', None)
			except:
				log_utils.error()
		# make request, 3rd fallback
		if not total_seasons:
			try:
				total_seasons = trakt.getSeasons(imdb, full=False)
				if total_seasons:
					total_seasons = [i['number'] for i in total_seasons]
					season_special = True if 0 in total_seasons else False
					total_seasons = len(total_seasons)
					if season_special:
						total_seasons = total_seasons - 1
			except:
				log_utils.error()
		if not is_airing:
			try:
				from resources.lib.indexers import tvdb_v1
				is_airing = tvdb_v1.get_is_airing(tvdb, season)
			except:
				log_utils.error()
		return total_seasons, is_airing


	def debrid_abv(self, debrid):
		try:
			d_dict = {'AllDebrid': 'AD', 'Premiumize.me': 'PM', 'Real-Debrid': 'RD'}
			d = d_dict[debrid]
		except:
			log_utils.error()
			d = ''
		return d
