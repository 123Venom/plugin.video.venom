# -*- coding: utf-8 -*-

import sys, time, datetime, os
import xbmc, xbmcgui
import re, urllib, urlparse, random, json

from resources.lib.modules import client, cleantitle, control, workers
from resources.lib.modules import trakt, source_utils, log_utils
from resources.lib.modules import debrid, cache

try:
	from sqlite3 import dbapi2 as database
except:
	from pysqlite2 import dbapi2 as database

try:
	import resolveurl
except:
	pass


class Sources:
	def __init__(self):
		self.getConstants()
		self.sources = []


	def play(self, title, year, imdb, tvdb, season, episode, tvshowtitle, premiered, meta, select, rescrape=False):
		try:
			url = None

			if rescrape:
				items = self.getSources(title, year, imdb, tvdb, season, episode, tvshowtitle, premiered)
			else:
				if 'plugin' not in control.infoLabel('Container.PluginName'):
					items = self.getSources(title, year, imdb, tvdb, season, episode, tvshowtitle, premiered)
				else:
					items = cache.get(self.getSources, 48, title, year, imdb, tvdb, season, episode, tvshowtitle, premiered)

			if items is None:
				self.url = url
				return self.errorForSources()

			if select is None:
				if episode is not None and control.setting('enable.upnext') == 'true':
					select = '2'
				else:
					select = control.setting('hosts.mode')
					# if control.window.getProperty('extendedinfo_running') or control.window.getProperty('infodialogs.active') and select == '1':
					if xbmc.getCondVisibility("Window.IsActive(script.extendedinfo-DialogVideoInfo-Netflix.xml)") or \
							xbmc.getCondVisibility("Window.IsActive(script.extendedinfo-DialogVideoInfo-Estuary.xml)") or \
							xbmc.getCondVisibility("Window.IsActive(script.extendedinfo-DialogVideoInfo-Aura.xml)") or \
							xbmc.getCondVisibility("Window.IsActive(script.extendedinfo-DialogVideoInfo.xml)") and select == '1':
						select = '0'
			else:
				select = select

			title = tvshowtitle if tvshowtitle is not None else title

			if len(items) > 0:
				if select == '1' and 'plugin' in control.infoLabel('Container.PluginName'):
					control.window.clearProperty(self.itemProperty)
					control.window.setProperty(self.itemProperty, json.dumps(items))

					control.window.clearProperty(self.metaProperty)
					control.window.setProperty(self.metaProperty, meta)

					control.sleep(200)

					return control.execute('Container.Update(%s?action=addItem&title=%s)' % (sys.argv[0], urllib.quote_plus(title)))

				elif select == '0' or select == '1':
					url = self.sourcesDialog(items)
				else:
					url = self.sourcesDirect(items)

			if url == 'close://' or url is None:
				self.url = url
				return self.errorForSources()

			try:
				meta = json.loads(meta)
			except:
				pass

			from resources.lib.modules import player
			player.Player().play_source(title, year, season, episode, imdb, tvdb, url, meta, select)

		except:
			log_utils.error()
			pass


	def addItem(self, title):
		def sourcesDirMeta(metadata):
			if metadata is None:
				return metadata
			allowed = ['poster', 'poster2', 'poster3', 'season_poster', 'fanart', 'fanart2', 'fanart3', 'thumb', 'title', 'year', 'tvshowtitle', 'season', 'episode', 'rating', 'director', 'plot', 'trailer', 'mediatype']
			return {k: v for k, v in metadata.iteritems() if k in allowed}

		control.playlist.clear()

		items = control.window.getProperty(self.itemProperty)
		items = json.loads(items)

		if items is None or len(items) == 0:
			control.idle()
			sys.exit()

		meta = control.window.getProperty(self.metaProperty)
		meta = json.loads(meta)
		meta = sourcesDirMeta(meta)

		sysaddon = sys.argv[0]
		syshandle = int(sys.argv[1])

		downloads = True if control.setting('downloads') == 'true' and (control.setting(
			'movie.download.path') != '' or control.setting('tv.download.path') == '') else False

		systitle = sysname = urllib.quote_plus(title)

		if 'tvshowtitle' in meta and 'season' in meta and 'episode' in meta:
			sysname += urllib.quote_plus(' S%02dE%02d' % (int(meta['season']), int(meta['episode'])))
		elif 'year' in meta:
			sysname += urllib.quote_plus(' (%s)' % meta['year'])

		poster1 = meta.get('poster')
		poster2 = meta.get('poster2')
		poster3 = meta.get('poster3')
		poster4 = meta.get('season_poster')
		poster = poster4 or poster3 or poster2 or poster1 or control.addonPoster()

		fanart1 = meta.get('fanart')
		fanart2 = meta.get('fanart2')
		fanart3 = meta.get('fanart3')
		fanart = fanart3 or fanart2 or fanart1 or control.addonFanart()
		if control.setting('fanart') != 'true':
			fanart = '0'

		# thumb = meta.get('thumb')
		# thumb = thumb or poster or fanart or control.addonThumb()

		sysimage = urllib.quote_plus(poster.encode('utf-8'))
		downloadMenu = control.lang(32403).encode('utf-8')

		multiline = control.setting('sourcelist.multiline')

		for i in range(len(items)):
			try:
				if multiline == 'true':
					label = str(items[i]['multiline_label'])
				else:
					label = str(items[i]['label'])

				syssource = urllib.quote_plus(json.dumps([items[i]]))
				sysurl = '%s?action=playItem&title=%s&source=%s' % (sysaddon, systitle, syssource)

				cm = []
				if downloads is True:
					cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&source=%s)' %
							(sysaddon, sysname, sysimage, syssource)))

				quality = items[i]['quality']
				# if quality == 'SCR': quality = 'CAM'
				thumb = quality + '.png'
				artPath = control.artPath()
				thumb = os.path.join(artPath, thumb) if artPath is not None else ''

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
				pass

		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)


	def playItem(self, title, source):
		try:
			meta = control.window.getProperty(self.metaProperty)
			meta = json.loads(meta)

			year = meta['year'] if 'year' in meta else None
			season = meta['season'] if 'season' in meta else None
			episode = meta['episode'] if 'episode' in meta else None

			imdb = meta['imdb'] if 'imdb' in meta else None
			tvdb = meta['tvdb'] if 'tvdb' in meta else None

			next = []
			prev = []
			total = []

			for i in range(1, 1000):
				try:
					u = control.infoLabel('ListItem(%s).FolderPath' % str(i))
					if u in total:
						raise Exception()
					total.append(u)
					u = dict(urlparse.parse_qsl(u.replace('?', '')))
					u = json.loads(u['source'])[0]
					next.append(u)
				except:
					break

			for i in range(-1000, 0)[::-1]:
				try:
					u = control.infoLabel('ListItem(%s).FolderPath' % str(i))
					if u in total:
						raise Exception()
					total.append(u)
					u = dict(urlparse.parse_qsl(u.replace('?', '')))
					u = json.loads(u['source'])[0]
					prev.append(u)
				except:
					break

			items = json.loads(source)

			# items = [i for i in items + next + prev][:40]
			items = [i for i in items + next + prev][:1000]

			header = control.addonInfo('name')
			header2 = header.upper()

			progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
			progressDialog.create(header, '')
			progressDialog.update(0)

			block = None

			for i in range(len(items)):
				try:
					try:
						if progressDialog.iscanceled():
							break
						progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label']), str(' '))
						# progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label']).replace('\n    ', ' | '))
					except:
						progressDialog.update(int((100 / float(len(items))) * i), str(header2), str(items[i]['label']))

					if items[i]['source'] == block:
						raise Exception()

					w = workers.Thread(self.sourcesResolve, items[i])
					w.start()

					if items[i].get('source').lower() in self.hostcapDict:
						offset = 60 * 2
					elif items[i].get('source').lower() == 'torrent':
						offset = float('inf')
					else:
						offset = 0

					m = ''
					for x in range(3600):
						try:
							if xbmc.abortRequested is True:
								return sys.exit()
							if progressDialog.iscanceled():
								return progressDialog.close()
						except:
							pass

						k = control.condVisibility('Window.IsActive(virtualkeyboard)')
						if k:
							m += '1'
							m = m[-1]
						if (w.is_alive() is False or x > 30 + offset) and not k:
							break
						k = control.condVisibility('Window.IsActive(yesnoDialog)')
						if k:
							m += '1'
							m = m[-1]
						if (w.is_alive() is False or x > 30 + offset) and not k:
							break
						time.sleep(0.5)

					for x in range(30):
						try:
							if xbmc.abortRequested is True:
								return sys.exit()
							if progressDialog.iscanceled():
								return progressDialog.close()
						except:
							pass

						if m == '':
							break
						if w.is_alive() is False:
							break
						time.sleep(0.5)

					if w.is_alive() is True:
						block = items[i]['source']

					if self.url is None:
						raise Exception()

					try:
						progressDialog.close()
					except:
						pass

					control.sleep(200)
					control.execute('Dialog.Close(virtualkeyboard)')
					control.execute('Dialog.Close(yesnoDialog)')

					from resources.lib.modules import player
					player.Player().play_source(title, year, season, episode, imdb, tvdb, self.url, meta, select='1')

					return self.url
				except:
					pass

			try:
				progressDialog.close()
			except:
				pass

			self.errorForSources()
		except:
			log_utils.error()
			pass


	def getSources(self, title, year, imdb, tvdb, season, episode, tvshowtitle, premiered, quality='HD', timeout=30):
		progressDialog = control.progressDialog if control.setting(
			'progress.dialog') == '0' else control.progressDialogBG
		progressDialog.create(control.addonInfo('name'), '')
		progressDialog.update(0)

		self.prepareSources()
		sourceDict = self.sourceDict
		progressDialog.update(0, control.lang(32600).encode('utf-8'))

		content = 'movie' if tvshowtitle is None else 'episode'
		if content == 'movie':
			sourceDict = [(i[0], i[1], getattr(i[1], 'movie', None)) for i in sourceDict]
			genres = trakt.getGenre('movie', 'imdb', imdb)
		else:
			sourceDict = [(i[0], i[1], getattr(i[1], 'tvshow', None)) for i in sourceDict]
			genres = trakt.getGenre('show', 'tvdb', tvdb)

		sourceDict = [(i[0], i[1], i[2]) for i in sourceDict if not hasattr(i[1], 'genre_filter') or not i[1].genre_filter or any(
								x in i[1].genre_filter for x in genres)]
		sourceDict = [(i[0], i[1]) for i in sourceDict if i[2] is not None]

		language = self.getLanguage()

		sourceDict = [(i[0], i[1], i[1].language) for i in sourceDict]
		sourceDict = [(i[0], i[1]) for i in sourceDict if any(x in i[2] for x in language)]

		try:
			sourceDict = [(i[0], i[1], control.setting('provider.' + i[0])) for i in sourceDict]
		except:
			sourceDict = [(i[0], i[1], 'true') for i in sourceDict]

		sourceDict = [(i[0], i[1]) for i in sourceDict if i[2] != 'false']
		sourceDict = [(i[0], i[1], i[1].priority) for i in sourceDict]

		random.shuffle(sourceDict)

		sourceDict = sorted(sourceDict, key=lambda i: i[2])

		threads = []
		if content == 'movie':
			title = self.getTitle(title)
			localtitle = self.getLocalTitle(title, imdb, tvdb, content)
			aliases = self.getAliasTitles(imdb, localtitle, content)

			for i in sourceDict:
				threads.append(workers.Thread(self.getMovieSource, title, localtitle, aliases, year, imdb, i[0], i[1]))
		else:
			tvshowtitle = self.getTitle(tvshowtitle)
			localtvshowtitle = self.getLocalTitle(tvshowtitle, imdb, tvdb, content)
			aliases = self.getAliasTitles(imdb, localtvshowtitle, content)

			for i in sourceDict:
				threads.append(workers.Thread(self.getEpisodeSource, title, year, imdb, tvdb, season,
											episode, tvshowtitle, localtvshowtitle, aliases, premiered, i[0], i[1]))

		s = [i[0] + (i[1],) for i in zip(sourceDict, threads)]
		s = [(i[3].getName(), i[0], i[2]) for i in s]

		mainsourceDict = [i[0] for i in s if i[2] == 0]
		sourcelabelDict = dict([(i[0], i[1].upper()) for i in s])

		[i.start() for i in threads]

		pdpc = control.setting('progress.dialog.prem.color')
		pdpc = self.getPremColor(pdpc)

		pdfc = control.setting('progress.dialog.free.color')
		pdfc = self.getPremColor(pdfc)

		string1 = control.lang(32404).encode('utf-8')
		string2 = control.lang(32405).encode('utf-8')
		string3 = control.lang(32406).encode('utf-8')
		string4 = control.lang(32601).encode('utf-8')
		string5 = control.lang(32602).encode('utf-8')
		string6 = (control.lang(32606) % pdpc).encode('utf-8')
		string7 = (control.lang(32607) % pdfc).encode('utf-8')

		try:
			timeout = int(control.setting('scrapers.timeout.1'))
		except:
			pass

		quality = control.setting('hosts.quality')
		if quality == '':
			quality = '0'

		line1 = line2 = line3 = ""

		pre_emp = str(control.setting('preemptive.termination'))
		pre_emp_limit = int(control.setting('preemptive.limit'))
		pre_emp_res = str(control.setting('preemptive.res'))

		source_4k = d_source_4k = 0
		source_1080 = d_source_1080 = 0
		source_720 = d_source_720 = 0
		source_sd = d_source_sd = 0
		total = d_total = 0

		debrid_list = debrid.debrid_resolvers
		debrid_status = debrid.status()

		total_format = '[COLOR %s][B]%s[/B][/COLOR]'
		pdiag_format = ' 4K: %s | 1080p: %s | 720p: %s | SD: %s | %s: %s'.split('|')
		pdiag_bg_format = '4K:%s(%s)|1080p:%s(%s)|720p:%s(%s)|SD:%s(%s)|T:%s(%s)'.split('|')

		for i in range(0, 4 * timeout):
			if pre_emp == 'true':
				if pre_emp_res in ['0','1']:
					if (source_4k + d_source_4k) >= pre_emp_limit:
						break
				elif pre_emp_res in ['2']:
					if (source_1080 + d_source_1080) >= pre_emp_limit:
						break
				elif pre_emp_res in ['3']:
					if (source_720 + d_source_720) >= pre_emp_limit:
						break
				elif pre_emp_res in ['4']:
					if (source_sd + d_source_sd) >= pre_emp_limit:
						break
				else:
					if (source_sd + d_source_sd) >= pre_emp_limit:
						break
			try:
				if xbmc.abortRequested is True:
					return sys.exit()

				try:
					if progressDialog.iscanceled():
						break
				except:
					pass

				if len(self.sources) > 0:
					if quality in ['0']:
						source_4k = len([e for e in self.sources if e['quality'] == '4K' and e['debridonly'] is False])
						source_1080 = len([e for e in self.sources if e['quality'] in ['1440p', '1080p'] and e['debridonly'] is False])
						source_720 = len([e for e in self.sources if e['quality'] in ['720p', 'HD'] and e['debridonly'] is False])
						source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])

					elif quality in ['1']:
						source_1080 = len([e for e in self.sources if e['quality'] in ['1440p', '1080p'] and e['debridonly'] is False])
						source_720 = len([e for e in self.sources if e['quality'] in ['720p', 'HD'] and e['debridonly'] is False])
						source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])

					elif quality in ['2']:
						source_1080 = len([e for e in self.sources if e['quality'] in ['1080p'] and e['debridonly'] is False])
						source_720 = len([e for e in self.sources if e['quality'] in ['720p', 'HD'] and e['debridonly'] is False])
						source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])

					elif quality in ['3']:
						source_720 = len([e for e in self.sources if e['quality'] in ['720p', 'HD'] and e['debridonly'] is False])
						source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])

					else:
						source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])

					total = source_4k + source_1080 + source_720 + source_sd

					if debrid_status:
						if quality in ['0']:
							for d in debrid_list:
								d_source_4k = len([e for e in self.sources if e['quality'] == '4K' and d.valid_url(e['url'], e['source'])])
								d_source_1080 = len([e for e in self.sources if e['quality'] in ['1440p', '1080p'] and d.valid_url(e['url'], e['source'])])
								d_source_720 = len([e for e in self.sources if e['quality'] in ['720p', 'HD'] and d.valid_url(e['url'], e['source'])])
								d_source_sd = len([e for e in self.sources if e['quality'] == 'SD' and d.valid_url(e['url'], e['source'])])

						elif quality in ['1']:
							for d in debrid_list:
								d_source_1080 = len([e for e in self.sources if e['quality'] in ['1440p', '1080p'] and d.valid_url(e['url'], e['source'])])
								d_source_720 = len([e for e in self.sources if e['quality'] in ['720p', 'HD'] and d.valid_url(e['url'], e['source'])])
								d_source_sd = len([e for e in self.sources if e['quality'] == 'SD' and d.valid_url(e['url'], e['source'])])

						elif quality in ['2']:
							for d in debrid_list:
								d_source_1080 = len([e for e in self.sources if e['quality'] in ['1080p'] and d.valid_url(e['url'], e['source'])])
								d_source_720 = len([e for e in self.sources if e['quality'] in ['720p', 'HD'] and d.valid_url(e['url'], e['source'])])
								d_source_sd = len([e for e in self.sources if e['quality'] == 'SD' and d.valid_url(e['url'], e['source'])])

						elif quality in ['3']:
							for d in debrid_list:
								d_source_720 = len([e for e in self.sources if e['quality'] in ['720p', 'HD'] and d.valid_url(e['url'], e['source'])])
								d_source_sd = len([e for e in self.sources if e['quality'] == 'SD' and d.valid_url(e['url'], e['source'])])

						else:
							for d in debrid_list:
								d_source_sd = len([e for e in self.sources if e['quality'] == 'SD' and d.valid_url(e['url'], e['source'])])

						d_total = d_source_4k + d_source_1080 + d_source_720 + d_source_sd

				if debrid_status:
					d_4k_label = total_format % ('red', d_source_4k) if d_source_4k == 0 else total_format % (pdpc, d_source_4k)
					d_1080_label = total_format % ('red', d_source_1080) if d_source_1080 == 0 else total_format % (pdpc, d_source_1080)
					d_720_label = total_format % ('red', d_source_720) if d_source_720 == 0 else total_format % (pdpc, d_source_720)
					d_sd_label = total_format % ('red', d_source_sd) if d_source_sd == 0 else total_format % (pdpc, d_source_sd)
					d_total_label = total_format % ('red', d_total) if d_total == 0 else total_format % (pdpc, d_total)

				source_4k_label = total_format % ('red', source_4k) if source_4k == 0 else total_format % (pdfc, source_4k)
				source_1080_label = total_format % ('red', source_1080) if source_1080 == 0 else total_format % (pdfc, source_1080)
				source_720_label = total_format % ('red', source_720) if source_720 == 0 else total_format % (pdfc, source_720)
				source_sd_label = total_format % ('red', source_sd) if source_sd == 0 else total_format % (pdfc, source_sd)
				source_total_label = total_format % ('red', total) if total == 0 else total_format % (pdfc, total)

				if (i / 2) < timeout:
					try:
						mainleft = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() is True and x.getName() in mainsourceDict]
						info = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() is True]
						if i >= timeout and len(mainleft) == 0 and len(self.sources) >= 100 * len(info):
							break

						if debrid_status:
							if quality in ['0']:
								if progressDialog != control.progressDialogBG:
									line1 = ('%s:' + '|'.join(pdiag_format)) % (string6, d_4k_label, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
									line2 = ('%s:' + '|'.join(pdiag_format)) % (string7, source_4k_label, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
									print line1, line2
								else:
									control.idle()
									line1 = '|'.join(pdiag_bg_format[:-1]) % (source_4k_label, d_4k_label, source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label)

							elif quality in ['1']:
								if progressDialog != control.progressDialogBG:
									line1 = ('%s:' + '|'.join(pdiag_format[1:])) % (string6, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
									line2 = ('%s:' + '|'.join(pdiag_format[1:])) % (string7, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
								else:
									control.idle()
									line1 = '|'.join(pdiag_bg_format[1:]) % (source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)

							elif quality in ['2']:
								if progressDialog != control.progressDialogBG:
									line1 = ('%s:' + '|'.join(pdiag_format[1:])) % (string6, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
									line2 = ('%s:' + '|'.join(pdiag_format[1:])) % (string7, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
								else:
									control.idle()
									line1 = '|'.join(pdiag_bg_format[1:]) % (source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)

							elif quality in ['3']:
								if progressDialog != control.progressDialogBG:
									line1 = ('%s:' + '|'.join(pdiag_format[2:])) % (string6, d_720_label, d_sd_label, str(string4), d_total_label)
									line2 = ('%s:' + '|'.join(pdiag_format[2:])) % (string7, source_720_label, source_sd_label, str(string4), source_total_label)
								else:
									control.idle()
									line1 = '|'.join(pdiag_bg_format[2:]) % (source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)

							else:
								if progressDialog != control.progressDialogBG:
									line1 = ('%s:' + '|'.join(pdiag_format[3:])) % (string6, d_sd_label, str(string4), d_total_label)
									line2 = ('%s:' + '|'.join(pdiag_format[3:])) % (string7, source_sd_label, str(string4), source_total_label)
								else:
									control.idle()
									line1 = '|'.join(pdiag_bg_format[3:]) % (source_sd_label, d_sd_label, source_total_label, d_total_label)
						else:
							if quality in ['0']:
								line1 = '|'.join(pdiag_format) % (source_4k_label, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)

							elif quality in ['1']:
								line1 = '|'.join(pdiag_format[1:]) % (source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)

							elif quality in ['2']:
								line1 = '|'.join(pdiag_format[1:]) % (source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)

							elif quality in ['3']:
								line1 = '|'.join(pdiag_format[2:]) % (source_720_label, source_sd_label, str(string4), source_total_label)

							else:
								line1 = '|'.join(pdiag_format[3:]) % (source_sd_label, str(string4), source_total_label)

						if debrid_status:
							if len(info) > 6:
								line3 = string3 % (str(len(info)))
							elif len(info) > 0:
								line3 = string3 % (', '.join(info))
							else:
								break
							percent = int(100 * float(i) / (2 * timeout) + 0.5)

							if progressDialog != control.progressDialogBG:
								progressDialog.update(max(1, percent), line1, line2, line3)
							else:
								progressDialog.update(max(1, percent), line1, line3)

						else:
							if len(info) > 6:
								line2 = string3 % (str(len(info)))
							elif len(info) > 0:
								line2 = string3 % (', '.join(info))
							else:
								break
							percent = int(100 * float(i) / (2 * timeout) + 0.5)
							progressDialog.update(max(1, percent), line1, line2)
					except Exception as e:
						log_utils.log('Exception Raised: %s' % str(e), log_utils.LOGERROR)
				else:
					try:
						mainleft = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() is True and x.getName() in mainsourceDict]
						info = mainleft

						if debrid_status:
							if len(info) > 6:
								line3 = 'Waiting for: %s' % (str(len(info)))
							elif len(info) > 0:
								line3 = 'Waiting for: %s' % (', '.join(info))
							else:
								break

							percent = int(100 * float(i) / (2 * timeout) + 0.5) % 100

							if progressDialog != control.progressDialogBG:
								progressDialog.update(max(1, percent), line1, line2, line3)
							else:
								progressDialog.update(max(1, percent), line1, line3)

						else:
							if len(info) > 6:
								line2 = 'Waiting for: %s' % (str(len(info)))
							elif len(info) > 0:
								line2 = 'Waiting for: %s' % (', '.join(info))
							else:
								break
							percent = int(100 * float(i) / (2 * timeout) + 0.5) % 100
							progressDialog.update(max(1, percent), line1, line2)
					except:
						break
				time.sleep(0.5)
			except:
				log_utils.error()
				pass

		try:
			progressDialog.close()
		except:
			pass

		self.sourcesFilter()
		return self.sources


	def preScrape(self, title, year, imdb, tvdb, season, episode, tvshowtitle, premiered):
		return cache.get(self.silentScrape, 48, title, year, imdb, tvdb, season, episode, tvshowtitle, premiered)


	# def silentScrape(self, title, year, imdb, tvdb, season, episode, tvshowtitle, premiered, quality='HD', timeout=30):
		# self.prepareSources()
		# sourceDict = self.sourceDict

		# content = 'movie' if tvshowtitle is None else 'episode'
		# if content == 'movie':
			# sourceDict = [(i[0], i[1], getattr(i[1], 'movie', None)) for i in sourceDict]
			# genres = trakt.getGenre('movie', 'imdb', imdb)
		# else:
			# sourceDict = [(i[0], i[1], getattr(i[1], 'tvshow', None)) for i in sourceDict]
			# genres = trakt.getGenre('show', 'tvdb', tvdb)

		# sourceDict = [(i[0], i[1], i[2]) for i in sourceDict if not hasattr(i[1], 'genre_filter') or not i[1].genre_filter or any(
								# x in i[1].genre_filter for x in genres)]
		# sourceDict = [(i[0], i[1]) for i in sourceDict if i[2] is not None]

		# language = self.getLanguage()

		# sourceDict = [(i[0], i[1], i[1].language) for i in sourceDict]
		# sourceDict = [(i[0], i[1]) for i in sourceDict if any(x in i[2] for x in language)]

		# try:
			# sourceDict = [(i[0], i[1], control.setting('provider.' + i[0])) for i in sourceDict]
		# except:
			# sourceDict = [(i[0], i[1], 'true') for i in sourceDict]

		# sourceDict = [(i[0], i[1]) for i in sourceDict if i[2] != 'false']
		# sourceDict = [(i[0], i[1], i[1].priority) for i in sourceDict]

		# random.shuffle(sourceDict)

		# sourceDict = sorted(sourceDict, key=lambda i: i[2])

		# threads = []

		# if content == 'movie':
			# title = self.getTitle(title)
			# localtitle = self.getLocalTitle(title, imdb, tvdb, content)
			# aliases = self.getAliasTitles(imdb, localtitle, content)

			# for i in sourceDict:
				# threads.append(workers.Thread(self.getMovieSource, title, localtitle, aliases, year, imdb, i[0], i[1]))
		# else:
			# tvshowtitle = self.getTitle(tvshowtitle)
			# localtvshowtitle = self.getLocalTitle(tvshowtitle, imdb, tvdb, content)
			# aliases = self.getAliasTitles(imdb, localtvshowtitle, content)

			# for i in sourceDict:
				# threads.append(workers.Thread(self.getEpisodeSource, title, year, imdb, tvdb, season,
											# episode, tvshowtitle, localtvshowtitle, aliases, premiered, i[0], i[1]))

		# s = [i[0] + (i[1],) for i in zip(sourceDict, threads)]
		# s = [(i[3].getName(), i[0], i[2]) for i in s]

		# mainsourceDict = [i[0] for i in s if i[2] == 0]
		# sourcelabelDict = dict([(i[0], i[1].upper()) for i in s])






	def prepareSources(self):
		try:
			control.makeFile(control.dataPath)
			self.sourceFile = control.providercacheFile
			dbcon = database.connect(self.sourceFile)
			dbcur = dbcon.cursor()
			dbcur.execute(
				"CREATE TABLE IF NOT EXISTS rel_url (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""rel_url TEXT, ""UNIQUE(source, imdb_id, season, episode)"");")
			dbcur.execute(
				"CREATE TABLE IF NOT EXISTS rel_src (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""hosts TEXT, ""added TEXT, ""UNIQUE(source, imdb_id, season, episode)"");")
			dbcur.connection.commit()
			dbcon.close()
		except:
			log_utils.error()
			pass


	def getMovieSource(self, title, localtitle, aliases, year, imdb, source, call):
		try:
			dbcon = database.connect(self.sourceFile)
			dbcur = dbcon.cursor()
		except:
			pass

		''' Fix to stop items passed with a 0 IMDB id pulling old unrelated sources from the database. '''
		if imdb == '0':
			try:
				dbcur.execute(
					"DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (
					source, imdb, '', ''))
				dbcur.execute(
					"DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (
					source, imdb, '', ''))
				dbcur.connection.commit()
			except:
				log_utils.error()
				pass
		''' END '''

		try:
			sources = []
			dbcur.execute(
				"SELECT * FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (
				source, imdb, '', ''))
			match = dbcur.fetchone()
			if match is not None:
				t1 = int(re.sub('[^0-9]', '', str(match[5])))
				t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
				update = abs(t2 - t1) > 60
				if update is False:
					sources = eval(match[4].encode('utf-8'))
					return self.sources.extend(sources)
		except:
			log_utils.error()
			pass

		try:
			url = None
			dbcur.execute(
				"SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (
				source, imdb, '', ''))
			url = dbcur.fetchone()
			if url is not None:
				url = eval(url[4].encode('utf-8'))
		except:
			log_utils.error()
			pass

		try:
			if url is None:
				url = call.movie(imdb, title, localtitle, aliases, year)
			if url is not None:
				dbcur.execute(
					"DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (
					source, imdb, '', ''))
				dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, '', '', repr(url)))
				dbcur.connection.commit()
		except:
			log_utils.error()
			pass

		try:
			sources = []
			sources = call.sources(url, self.hostDict, self.hostprDict)
			if sources is not None and sources != []:
				sources = [json.loads(t) for t in set(json.dumps(d, sort_keys=True) for d in sources)]
				for i in sources:
					i.update({'provider': source})
				self.sources.extend(sources)
				dbcur.execute(
					"DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (
					source, imdb, '', ''))
				dbcur.execute("INSERT INTO rel_src Values (?, ?, ?, ?, ?, ?)",
							(source, imdb, '', '', repr(sources), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
				dbcur.connection.commit()
			# dbcon.close()
		except:
			log_utils.error()
			# dbcon.close()
			pass
		dbcon.close()


	def getEpisodeSource(self, title, year, imdb, tvdb, season, episode, tvshowtitle, localtvshowtitle, aliases, premiered, source, call):
		try:
			dbcon = database.connect(self.sourceFile)
			dbcur = dbcon.cursor()
		except:
			pass

		try:
			sources = []
			dbcur.execute(
				"SELECT * FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (
				source, imdb, season, episode))
			match = dbcur.fetchone()
			if match is not None:
				t1 = int(re.sub('[^0-9]', '', str(match[5])))
				t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
				update = abs(t2 - t1) > 60
				if update is False:
					sources = eval(match[4].encode('utf-8'))
					return self.sources.extend(sources)
		except:
			log_utils.error()
			pass

		try:
			url = None
			dbcur.execute(
				"SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
			url = dbcur.fetchone()
			if url is not None:
				url = eval(url[4].encode('utf-8'))
		except:
			log_utils.error()
			pass

		try:
			if url is None:
				url = call.tvshow(imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year)
			if url is not None:
				dbcur.execute(
					"DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (
					source, imdb, '', ''))

				dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, '', '', repr(url)))
				dbcur.connection.commit()
		except:
			log_utils.error()
			pass

		try:
			ep_url = None
			dbcur.execute(
				"SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (
				source, imdb, season, episode))
			ep_url = dbcur.fetchone()
			if ep_url is not None:
				ep_url = eval(ep_url[4].encode('utf-8'))
		except:
			log_utils.error()
			pass

		try:
			if url is not None:
				if ep_url is None:
					ep_url = call.episode(url, imdb, tvdb, title, premiered, season, episode)
				if ep_url is not None:
					dbcur.execute(
						"DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (
						source, imdb, season, episode))
					dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)",
								(source, imdb, season, episode, repr(ep_url)))
					dbcur.connection.commit()
		except:
			log_utils.error()
			pass

		try:
			sources = []
			sources = call.sources(ep_url, self.hostDict, self.hostprDict)
			if sources is not None and sources != []:
				sources = [json.loads(t) for t in set(json.dumps(d, sort_keys=True) for d in sources)]
				for i in sources:
					i.update({'provider': source})
				self.sources.extend(sources)
				dbcur.execute(
					"DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (
					source, imdb, season, episode))
				dbcur.execute("INSERT INTO rel_src Values (?, ?, ?, ?, ?, ?)", (
				source, imdb, season, episode, repr(sources), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
				dbcur.connection.commit()
			# dbcon.close()
		except:
			log_utils.error()
			# dbcon.close()
			pass
		dbcon.close()


	def alterSources(self, url, meta):
		try:
			if control.setting('hosts.mode') == '2' or (control.setting('enable.upnext') == 'true' and 'episode' in meta):
				url += '&select=1'
			else:
				url += '&select=2'
			# control.execute('RunPlugin(%s)' % url)
			control.execute('PlayMedia(%s)' % url)
		except:
			pass


	def sourcesFilter(self):
		provider = control.setting('hosts.sort.provider')
		if provider == '':
			provider = 'false'

		debrid_only = control.setting('debrid.only')
		if debrid_only == '':
			debrid_only = 'false'

		sortthemup = control.setting('torrent.sort.them.up')
		if sortthemup == '':
			sortthemup = 'false'

		quality = control.setting('hosts.quality')
		if quality == '':
			quality = '0'

		captcha = control.setting('hosts.captcha')
		if captcha == '':
			captcha = 'true'

		###---Filter out duplicates
		if control.setting('remove.duplicates') == 'true':
			filter = []
			for i in self.sources:
				a = i['url'].lower()
				for sublist in filter:
					b = sublist['url'].lower()
					if 'magnet:' in a and debrid.status() is True:
						info_hash = re.search('magnet:.+?urn:\w+:([a-z0-9]+)', a)
						if info_hash:
							if info_hash.group(1) in b:
								filter.remove(sublist)
								log_utils.log('Removing %s - %s (DUPLICATE TORRENT) ALREADY IN :: %s' % (
													i['provider'], info_hash.group(1), sublist['provider']), log_utils.LOGDEBUG)
								break
					elif a == b:
						filter.remove(sublist)
						log_utils.log('Removing %s - %s (DUPLICATE LINK) ALREADY IN :: %s' % (
											i['provider'], i['url'], sublist['source']), log_utils.LOGDEBUG)
						break
				filter.append(i)
			log_utils.log('Removed %s duplicate sources from list' % (len(self.sources) - len(filter)), log_utils.LOGDEBUG)
			self.sources = filter
		###---------


		# # ---Filter out uncached torrents
		# pm_filter = self.sources
		# log_utils.log('self.sources = %s' % len(self.sources), __name__, log_utils.LOGDEBUG)
		# from resources.lib.modules import premiumize
		# try:
			# # list = []
			# # paged_sources = self.paginate_sources(sources=self.sources, page=1, limit=40)
			# # for i in paged_sources:
				# # list.append(i['url'])
			# # log_utils.log('list = %s' % list, __name__, log_utils.LOGDEBUG)

			# log_utils.log('self.sources = %s' % len(self.sources), __name__, log_utils.LOGDEBUG)

			# for i in pm_filter:
				# if 'torrent' in i['source'].lower():
				# # if 'magnet:' in a and debrid.status() is True:
					# cached = str(premiumize.PremiumizeMe().check_cache(i['url'].lower()))
					# # log_utils.log('cached = %s - %s - %s - %s' % (cached, i['debrid'].upper(), i['provider'].upper(), i['url']), __name__, log_utils.LOGDEBUG)
					# log_utils.log('cached = %s - %s - %s' % (cached, i['provider'].upper(), i['url']), __name__, log_utils.LOGDEBUG)
					# if cached == 'False' or cached is False:
						# pm_filter.remove(i) # seems to also be removing from self.sources
						# # log_utils.log('Removing (%s uncached TORRENT) %s - %s' % (i['debrid'].upper(), i['provider'].upper(), i['url']), __name__, log_utils.LOGDEBUG)
						# log_utils.log('Removing (PM uncached TORRENT) %s - %s' % (i['provider'].upper(), i['url']), __name__, log_utils.LOGDEBUG)

			# log_utils.log('self.sources = %s' % len(self.sources), __name__, log_utils.LOGDEBUG)
			# log_utils.log('pm_filter = %s' % len(pm_filter), __name__, log_utils.LOGDEBUG)
			# log_utils.log('Removed %s PM uncached TORRENT sources from list' % (len(self.sources) - len(pm_filter)), log_utils.LOGDEBUG)

			# self.sources = pm_filter
		# except:
			# log_utils.error()
			# pass
		# # ###---------


		if control.setting('HEVC') != 'true':
			self.sources = [i for i in self.sources if not any(value in i['url'].lower() for value in ['hevc', 'h265', 'h.265', 'x265', 'x.265'])]

		if source_utils.ck_CamSd():
			if any(i for i in self.sources if any(value in i['quality'] for value in ['4k', '1080p', '720p'])):
				self.sources = [i for i in self.sources if not any(value in i['quality'].upper() for value in ['CAM', 'SD'])]

		if control.setting('remove.3D.sources') == 'true':
			try:
				self.sources = [i for i in self.sources if '3D' not in i.get('info', '')]
			except:
				log_utils.error()
				pass

		random.shuffle(self.sources)

		if provider == 'true':
			self.sources = sorted(self.sources, key=lambda k: k['provider'])

		local = [i for i in self.sources if 'local' in i and i['local'] is True]
		for i in local:
			i.update({'language': self._getPrimaryLang() or 'en'})
		self.sources = [i for i in self.sources if not i in local]

		filter = []
		for d in debrid.debrid_resolvers:
			valid_hoster = set([i['source'] for i in self.sources])
			valid_hoster = [i for i in valid_hoster if d.valid_url('', i)]

			if sortthemup == 'true':
				filter += [dict(i.items() + [('debrid', d.name)]) for i in self.sources if 'magnet:' in i['url']]
				filter += [dict(i.items() + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]
			else:
				filter += [dict(i.items() + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster or 'magnet:' in i['url']]

		if debrid_only == 'false' or debrid.status() is False:
			filter += [i for i in self.sources if not i['source'].lower() in self.hostprDict and i['debridonly'] is False]
		self.sources = filter

		# log_utils.log('self.sources = %s' % str(len(self.sources)), __name__, log_utils.LOGDEBUG)

		for i in range(len(self.sources)):
			q = self.sources[i]['quality']
			if q == 'HD':
				self.sources[i].update({'quality': '720p'})

		filter = []
		filter += local

		if quality in ['0']: filter += [i for i in self.sources if i['quality'] == '4K' and 'debrid' in i]
		if quality in ['0']: filter += [i for i in self.sources if i['quality'] == '4K' and not 'debrid' in i and 'memberonly' in i]
		if quality in ['0']: filter += [i for i in self.sources if i['quality'] == '4K' and not 'debrid' in i and not 'memberonly' in i]

		if quality in ['0', '1']: filter += [i for i in self.sources if i['quality'] == '1440p' and 'debrid' in i]
		if quality in ['0', '1']: filter += [i for i in self.sources if i['quality'] == '1440p' and not 'debrid' in i and 'memberonly' in i]
		if quality in ['0', '1']: filter += [i for i in self.sources if i['quality'] == '1440p' and not 'debrid' in i and not 'memberonly' in i]

		if quality in ['0', '1', '2']: filter += [i for i in self.sources if i['quality'] == '1080p' and 'debrid' in i]
		if quality in ['0', '1', '2']: filter += [i for i in self.sources if i['quality'] == '1080p' and not 'debrid' in i and 'memberonly' in i]
		if quality in ['0', '1', '2']: filter += [i for i in self.sources if i['quality'] == '1080p' and not 'debrid' in i and not 'memberonly' in i]

		if quality in ['0', '1', '2', '3']: filter += [i for i in self.sources if i['quality'] == '720p' and 'debrid' in i]
		if quality in ['0', '1', '2', '3']: filter += [i for i in self.sources if i['quality'] == '720p' and not 'debrid' in i and 'memberonly' in i]
		if quality in ['0', '1', '2', '3']: filter += [i for i in self.sources if i['quality'] == '720p' and not 'debrid' in i and not 'memberonly' in i]

		filter += [i for i in self.sources if i['quality'] in ['SD', 'SCR', 'CAM']]
		self.sources = filter

		if captcha != 'true':
			filter = [i for i in self.sources if i['source'].lower() in self.hostcapDict and not 'debrid' in i]
			self.sources = [i for i in self.sources if not i in filter]

		filter = [i for i in self.sources if i['source'].lower() in self.hostblockDict and not 'debrid' in i]
		self.sources = [i for i in self.sources if not i in filter]

		multi = [i['language'] for i in self.sources]
		multi = [x for y, x in enumerate(multi) if x not in multi[:y]]
		multi = True if len(multi) > 1 else False

		if multi is True:
			self.sources = [i for i in self.sources if i['language'] != 'en'] + [i for i in self.sources if i['language'] == 'en']

		self.sources = self.sources[:4000]

		extra_info = control.setting('sources.extrainfo')

		prem_identify = control.setting('prem.identify')
		prem_identify = self.getPremColor(prem_identify)

		torr_identify = control.setting('torrent.identify')
		torr_identify = self.getPremColor(torr_identify)

		sec_color = control.setting('sec.identify')
		sec_identify = self.getPremColor(sec_color)

		for i in range(len(self.sources)):
			if extra_info == 'true':
				t = source_utils.getFileType(self.sources[i]['url'])
			else:
				t = ''

			u = self.sources[i]['url']
			q = self.sources[i]['quality']
			p = self.sources[i]['provider'].upper()
			s = self.sources[i]['source'].upper()
			s = s.rsplit('.', 1)[0]
			l = self.sources[i]['language']

			try:
				f = (' / '.join(['%s ' % info.strip() for info in self.sources[i]['info'].split('|')]))
			except:
				f = ''

			try:
				d = self.sources[i]['debrid']
			except:
				d = self.sources[i]['debrid'] = ''
			if d.lower() == 'alldebrid':
				d = 'AD'
			if d.lower() == 'linksnappy':
				d = 'LS'
			if d.lower() == 'megadebrid':
				d = 'MD'
			if d.lower() == 'premiumize.me':
				d = 'PM'
			if d.lower() == 'real-debrid':
				d = 'RD'
			if d.lower() == 'simply-debrid':
				d = 'SD'

			prem_color = 'nocolor'
			if d:
				if 'torrent' in s.lower() and torr_identify != 'nocolor':
					prem_color = torr_identify
				elif 'torrent' not in s.lower() and prem_identify != 'nocolor':
					prem_color = prem_identify

			if d != '':
				label = '[COLOR %s]%02d  |  [B]%s[/B]  |  %s  |  %s  |  [B]%s[/B][/COLOR]' % (prem_color, int(i + 1), q, d, p, s)
			else:
				label = '%02d  |  %s  |  %s  |  %s' % (int(i + 1), q, p, s)

			# if multi is True and l != 'en':
			if l != self.getLanguage()[0]:
				label += '[COLOR %s]  |  [B]%s[/B][/COLOR]' % (prem_color, l.upper())

			multiline_label = label

			if t != '':
				if f != '' and f != '0 ' and f != ' ':
					multiline_label += '\n       [COLOR %s][I]%s / %s[/I][/COLOR]' % (sec_identify, f, t)
					label += '[COLOR %s] / %s / %s[/COLOR]' % (prem_color, f, t)
				else:
					multiline_label += '\n       [COLOR %s][I]%s[/I][/COLOR]' % (sec_identify, t)
					label += '[COLOR %s] / %s[/COLOR]' % (prem_color, t)
			else:
				if f != '' and f != '0 ' and f != ' ':
					multiline_label += '\n       [COLOR %s][I]%s[/I][/COLOR]' % (sec_identify, f)
					label += '[COLOR %s] / %s[/COLOR]' % (prem_color, f)

			self.sources[i]['multiline_label'] = multiline_label
			self.sources[i]['label'] = label

		self.sources = [i for i in self.sources if 'label' or 'multiline_label' in i['label']]
		return self.sources


	def sourcesResolve(self, item, info=False):
		try:
			self.url = None
			u = url = item['url']
			d = item['debrid']
			direct = item['direct']
			local = item.get('local', False)
			provider = item['provider']
			call = [i[1] for i in self.sourceDict if i[0] == provider][0]
			u = url = call.resolve(url)

			if url is None or ('://' not in url and not local and 'magnet:' not in url):
				raise Exception()

			if not local:
				url = url[8:] if url.startswith('stack:') else url

				urls = []
				for part in url.split(' , '):
					u = part
					if d != '':
						part = debrid.resolver(part, d)

					elif direct is not True:
						hmf = resolveurl.HostedMediaFile(url=u, include_disabled=True, include_universal=False)
						if hmf.valid_url() is True:
							part = hmf.resolve()
					urls.append(part)

				url = 'stack://' + ' , '.join(urls) if len(urls) > 1 else urls[0]

			if url is False or url is None:
				raise Exception()

			ext = url.split('?')[0].split('&')[0].split('|')[0].rsplit('.')[-1].replace('/', '').lower()
			if ext == 'rar':
				raise Exception()

			try:
				headers = url.rsplit('|', 1)[1]
			except:
				headers = ''

			headers = urllib.quote_plus(headers).replace('%3D', '=') if ' ' in headers else headers
			headers = dict(urlparse.parse_qsl(headers))

			if url.startswith('http') and '.m3u8' in url:
				result = client.request(url.split('|')[0], headers=headers, output='geturl', timeout='20')
				if result is None:
					raise Exception()

			elif url.startswith('http'):
				result = client.request(url.split('|')[0], headers=headers, output='chunk', timeout='20')
				if result is None:
					raise Exception()

			self.url = url
			return url
		except:
			if info is True:
				self.errorForSources()
			return


	def sourcesDialog(self, items):
		try:
			labels = [i['label'] for i in items]

			select = control.selectDialog(labels)
			if select == -1:
				return 'close://'

			tot_items = len(items)
			next = [y for x, y in enumerate(items) if x >= select]
			prev = [y for x, y in enumerate(items) if x < select][::-1]

			items = [items[select]]

			# items = [i for i in items + next + prev][:40]
			items = [i for i in items + next + prev][:tot_items]

			header = control.addonInfo('name')
			header2 = header.upper()

			progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
			progressDialog.create(header, '')
			progressDialog.update(0)

			block = None

			for i in range(len(items)):
				try:
					if items[i]['source'] == block:
						raise Exception()

					w = workers.Thread(self.sourcesResolve, items[i])
					w.start()

					try:
						if progressDialog.iscanceled():
							break
						progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label']), str(' '))
					except:
						progressDialog.update(int((100 / float(len(items))) * i), str(header2), str(items[i]['label']))

					if items[i].get('source').lower() in self.hostcapDict:
						offset = 60 * 2
					elif items[i].get('source').lower() == 'torrent':
						offset = float('inf')
					else:
						offset = 0

					m = ''

					for x in range(3600):
						try:
							if xbmc.abortRequested is True:
								control.infoDialog('Sources Cancelled', sound=False, icon='INFO')
								return sys.exit()
							if progressDialog.iscanceled():
								control.infoDialog('Sources Cancelled', sound=False, icon='INFO')
								return progressDialog.close()
						except:
							pass

						k = control.condVisibility('Window.IsActive(virtualkeyboard)')
						if k:
							m += '1'
							m = m[-1]
						if (w.is_alive() == False or x > 30 + offset) and not k:
							break

						k = control.condVisibility('Window.IsActive(yesnoDialog)')
						if k:
							m += '1'
							m = m[-1]
						if (w.is_alive() == False or x > 30 + offset) and not k:
							break
						time.sleep(0.5)

					for x in range(30):
						try:
							if xbmc.abortRequested is True:
								control.infoDialog('Sources Cancelled', sound=False, icon='INFO')
								return sys.exit()
							if progressDialog.iscanceled():
								control.infoDialog('Sources Cancelled', sound=False, icon='INFO')
								return progressDialog.close()
						except:
							pass

						if m == '':
							break

						if w.is_alive() is False:
							break
						time.sleep(0.5)

					if w.is_alive() is True:
						block = items[i]['source']

					if self.url is None:
						raise Exception()

					self.selectedSource = items[i]['label']

					try:
						progressDialog.close()
					except:
						pass

					control.execute('Dialog.Close(virtualkeyboard)')
					control.execute('Dialog.Close(yesnoDialog)')
					return self.url
				except:
					pass

			try:
				progressDialog.close()
			except:
				pass

		except Exception as e:
			try:
				progressDialog.close()
			except:
				pass
			log_utils.log('Error %s' % str(e), log_utils.LOGNOTICE)


	def sourcesDirect(self, items):
		filter = [i for i in items if i['source'].lower() in self.hostcapDict and i['debrid'] == '']
		items = [i for i in items if not i in filter]

		filter = [i for i in items if i['source'].lower() in self.hostblockDict and i['debrid'] == '']
		items = [i for i in items if not i in filter]

		items = [i for i in items if ('autoplay' in i and i['autoplay'] is True) or not 'autoplay' in i]

		if control.setting('autoplay.sd') == 'true':
			items = [i for i in items if not i['quality'] in ['4K', '1440p', '1080p', 'HD']]

		u = None

		header = control.addonInfo('name')
		header2 = header.upper()

		try:
			control.sleep(1000)
			if control.setting('progress.dialog') == '0':
				progressDialog = control.progressDialog
			else:
				progressDialog = control.progressDialogBG
			progressDialog.create(header, '')
			progressDialog.update(0)
		except:
			pass

		for i in range(len(items)):
			try:
				if progressDialog.iscanceled():
					break
				progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label']), str(' '))
			except:
				progressDialog.update(int((100 / float(len(items))) * i), str(header2), str(items[i]['label']))
				pass
			try:
				if xbmc.abortRequested is True:
					return sys.exit()

				url = self.sourcesResolve(items[i])
				if u is None:
					u = url
				if url is not None:
					break
			except:
				pass
		try:
			progressDialog.close()
		except:
			pass

		return u


	def errorForSources(self):
		if self.url == 'close://':
			control.infoDialog('Sources Cancelled', sound=False, icon='INFO')
		else:
			control.infoDialog(control.lang(32401).encode('utf-8'), sound=False, icon='INFO')
		control.cancelPlayback()


	def getLanguage(self):
		langDict = {
			'English': ['en'],
			'German': ['de'],
			'German+English': ['de', 'en'],
			'French': ['fr'],
			'French+English': ['fr', 'en'],
			'Portuguese': ['pt'],
			'Portuguese+English': ['pt', 'en'],
			'Polish': ['pl'],
			'Polish+English': ['pl', 'en'],
			'Korean': ['ko'],
			'Korean+English': ['ko', 'en'],
			'Russian': ['ru'],
			'Russian+English': ['ru', 'en'],
			'Spanish': ['es'],
			'Spanish+English': ['es', 'en'],
			'Greek': ['gr'],
			'Italian': ['it'],
			'Italian+English': ['it', 'en'],
			'Greek+English': ['gr', 'en']}
		name = control.setting('providers.lang')
		return langDict.get(name, ['en'])


	def getLocalTitle(self, title, imdb, tvdb, content):
		lang = self._getPrimaryLang()
		if not lang:
			return title

		if content == 'movie':
			t = trakt.getMovieTranslation(imdb, lang)
		else:
			from resources.lib.modules import tvmaze
			t = tvmaze.tvMaze().getTVShowTranslation(tvdb, lang)

		return t or title


	def getAliasTitles(self, imdb, localtitle, content):
		lang = self._getPrimaryLang()

		try:
			t = trakt.getMovieAliases(imdb) if content == 'movie' else trakt.getTVShowAliases(imdb)
			t = [i for i in t if i.get('country', '').lower() in [lang, '', 'us'] and i.get('title', '').lower() != localtitle.lower()]
			return t
		except:
			return []


	def _getPrimaryLang(self):
		langDict = {'English': 'en', 'German': 'de', 'German+English': 'de', 'French': 'fr', 'French+English': 'fr',
						'Portuguese': 'pt', 'Portuguese+English': 'pt', 'Polish': 'pl', 'Polish+English': 'pl', 'Korean': 'ko',
						'Korean+English': 'ko', 'Russian': 'ru', 'Russian+English': 'ru', 'Spanish': 'es', 'Spanish+English': 'es',
						'Italian': 'it', 'Italian+English': 'it', 'Greek': 'gr', 'Greek+English': 'gr'}
		name = control.setting('providers.lang')
		lang = langDict.get(name)
		return lang


	def getTitle(self, title):
		title = cleantitle.normalize(title)
		return title


	def getConstants(self):
		self.itemProperty = 'plugin.video.venom.container.items'
		self.metaProperty = 'plugin.video.venom.container.meta'
		from openscrapers import sources

		self.sourceDict = sources()

		try:
			self.hostDict = resolveurl.relevant_resolvers(order_matters=True)
			self.hostDict = [i.domains for i in self.hostDict if not '*' in i.domains]
			self.hostDict = [i.lower() for i in reduce(lambda x, y: x+y, self.hostDict)]
			self.hostDict = [x for y, x in enumerate(self.hostDict) if not x in self.hostDict[:y]]
		except:
			self.hostDict = []

		self.hostprDict = ['1fichier.com', 'filefactory.com', 'multiup.org', 'nitroflare.com', 'oboom.com', 'rapidgator.net', 'rg.to', 'turbobit.net',
									'uploaded.net', 'uploaded.to', 'uploadgig.com', 'ul.to', 'uploadrocket.net']

		self.hostcapDict = ['flashx.tv', 'flashx.to', 'flashx.sx', 'flashx.bz', 'flashx.cc', 'hugefiles.net', 'kingfiles.net', 'streamin.to',
									'thevideo.me', 'torba.se', 'vidup.me', 'vidup.tv', 'vshare.eu', 'vshare.io', 'vev.io']

		self.hosthqDict = ['gvideo', 'google.com', 'thevideo.me', 'rapidvideo.com', 'raptu.com', 'filez.tv', 'uptobox.com', 'uptostream.com',
									'xvidstage.com', 'xstreamcdn.com', 'idtbox.com', 'streamvid.co']


		self.hostblockDict = ['divxme.com', 'divxstage.eu', 'estream.to', 'facebook.com', 'oload.download', 'oload.fun', 'oload.icu', 'oload.info',
									'oload.life', 'oload.space', 'oload.stream', 'oload.tv', 'oload.win', 'openload.co', 'openload.io', 'openload.pw', 'rapidvideo.com',
									'rapidvideo.is', 'rapidvid.to', 'streamango.com', 'streamcherry.com', 'twitch.tv', 'youtube.com', 'zippyshare.com']


	def getPremColor(self, n):
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


	def color_quality(self, quality):
		color = 'darkred'
		if quality == '4K':
			color = 'lime'
		if quality == '1080p':
			color = 'greenyellow'
		if quality == '720p':
			color = 'sandybrown'
		if quality == 'SD':
			color = 'red'
		return color


	def paginate_sources(self, sources, page, limit):
		pages = [sources[i:i + limit] for i in xrange(0, len(sources), limit)]
		# log_utils.log('pages = %s' % str(pages), __name__, log_utils.LOGDEBUG)
		# log_utils.log('sources = %s' % str(len(sources)), __name__, log_utils.LOGDEBUG)
		return pages[page - 1]
