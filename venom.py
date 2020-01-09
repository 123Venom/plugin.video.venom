# -*- coding: utf-8 -*-

'''
	Venom Add-on
'''

from urlparse import parse_qsl
from urllib import quote_plus
from sys import argv

from resources.lib.modules import control

params = dict(parse_qsl(argv[2].replace('?','')))
action = params.get('action')

subid = params.get('subid')
name = params.get('name')
title = params.get('title')
year = params.get('year')
imdb = params.get('imdb')
tvdb = params.get('tvdb')
tmdb = params.get('tmdb')
season = params.get('season')
episode = params.get('episode')
tvshowtitle = params.get('tvshowtitle')
premiered = params.get('premiered')
url = params.get('url')
image = params.get('image')
meta = params.get('meta')
art = params.get('art')
select = params.get('select')
query = params.get('query')
source = params.get('source')
content = params.get('content')
table = params.get('table')
list_name = params.get('list_name')

windowedtrailer = params.get('windowedtrailer')
windowedtrailer = int(windowedtrailer) if windowedtrailer in ("0","1") else 0
notificationSound = False if control.setting('notification.sound') == 'false' else True

if action is None:
	from resources.lib.menus import navigator
	from resources.lib.modules import cache
	run = control.setting('first.info')
	if run == '':
		run = 'true' #clean install scenerio
	if cache._find_cache_version():
		run = 'true'
	if run == 'true':
		from resources.lib.modules import changelog
		changelog.get()
		control.setSetting(id='first.info', value='false')
	cache.cache_version_check()
	navigator.Navigator().root()



####################################################
#---News and Updates
####################################################
elif action == 'infoCheck':
	from resources.lib.menus import navigator
	navigator.Navigator().infoCheck('')

elif action == 'ShowNews':
	from resources.lib.modules import newsinfo
	newsinfo.news()

elif action == 'ShowChangelog':
	from resources.lib.modules import changelog
	changelog.get()



####################################################
#---MOVIES
####################################################
elif action == 'movieNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().movies()

elif action == 'movieliteNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().movies(lite=True)

elif action == 'mymovieNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().mymovies()

elif action == 'mymovieliteNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().mymovies(lite=True)

elif action == 'movies':
	from resources.lib.menus import movies
	movies.Movies().get(url)

elif action == 'moviePage':
	from resources.lib.menus import movies
	movies.Movies().get(url)

elif action == 'tmdbmovies':
	from resources.lib.menus import movies
	movies.Movies().getTMDb(url)

elif action == 'tmdbmoviePage':
	from resources.lib.menus import movies
	movies.Movies().getTMDb(url)

elif action == 'newMovies':
	from resources.lib.menus import movies
	movies.Movies().newMovies()

elif action == 'movieSearch':
	from resources.lib.menus import movies
	movies.Movies().search()

elif action == 'movieSearchnew':
	from resources.lib.menus import movies
	movies.Movies().search_new()

elif action == 'movieSearchterm':
	from resources.lib.menus import movies
	movies.Movies().search_term(name)

elif action == 'moviePerson':
	from resources.lib.menus import movies
	movies.Movies().person()

elif action == 'movieGenres':
	from resources.lib.menus import movies
	movies.Movies().genres()

elif action == 'movieLanguages':
	from resources.lib.menus import movies
	movies.Movies().languages()

elif action == 'movieCertificates':
	from resources.lib.menus import movies
	movies.Movies().certifications()

elif action == 'movieYears':
	from resources.lib.menus import movies
	movies.Movies().years()

elif action == 'moviePersons':
	from resources.lib.menus import movies
	movies.Movies().persons(url)

elif action == 'moviesUnfinished':
	from resources.lib.menus import movies
	movies.Movies().unfinished(url)

elif action == 'movieUserlists':
	from resources.lib.menus import movies
	movies.Movies().userlists()



####################################################
#---Collections
####################################################
elif action == 'collectionsNavigator':
	from resources.lib.menus import collections
	collections.Collections().collectionsNavigator()

elif action == 'collectionActors':
	from resources.lib.menus import collections
	collections.Collections().collectionActors()

elif action == 'collectionBoxset':
	from resources.lib.menus import collections
	collections.Collections().collectionBoxset()

elif action == 'collectionKids':
	from resources.lib.menus import collections
	collections.Collections().collectionKids()

elif action == 'collectionBoxsetKids':
	from resources.lib.menus import collections
	collections.Collections().collectionBoxsetKids()

elif action == 'collectionSuperhero':
	from resources.lib.menus import collections
	collections.Collections().collectionSuperhero()

elif action == 'collections':
	from resources.lib.menus import collections
	collections.Collections().get(url)


####################################################
#---Martial Arts Collections
####################################################
elif action == 'collection_martial_arts':
	from resources.lib.menus import collections
	collections.Collections().collection_martial_arts()

elif action == 'collection_martial_arts_actors':
	from resources.lib.menus import collections
	collections.Collections().collection_martial_arts_actors()



####################################################
#---Furk
####################################################
elif action == "furkNavigator":
	from resources.lib.menus import navigator
	navigator.Navigator().furk()

elif action == "furkMetaSearch":
	from resources.lib.menus import furk
	furk.Furk().furk_meta_search(url)

elif action == "furkSearch":
	from resources.lib.menus import furk
	furk.Furk().search()

elif action == "furkUserFiles":
	from resources.lib.menus import furk
	furk.Furk().user_files()

elif action == "furkSearchNew":
	from resources.lib.menus import furk
	furk.Furk().search_new()



####################################################
# TV Shows
####################################################
elif action == 'tvNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().tvshows()

elif action == 'tvliteNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().tvshows(lite=True)

elif action == 'mytvNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().mytvshows()

elif action == 'mytvliteNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().mytvshows(lite=True)

elif action == 'channels':
	from resources.lib.menus import channels
	channels.channels().get()

elif action == 'tvshows':
	from resources.lib.menus import tvshows
	tvshows.TVshows().get(url)

elif action == 'tvshowPage':
	from resources.lib.menus import tvshows
	tvshows.TVshows().get(url)

elif action == 'tmdbTvshows':
	from resources.lib.menus import tvshows
	tvshows.TVshows().getTMDb(url)

elif action == 'tmdbTvshowPage':
	from resources.lib.menus import tvshows
	tvshows.TVshows().getTMDb(url)

elif action == 'tvmazeTvshows':
	from resources.lib.menus import tvshows
	tvshows.TVshows().getTVmaze(url)

elif action == 'tvmazeTvshowPage':
	from resources.lib.menus import tvshows
	tvshows.TVshows().getTVmaze(url)

elif action == 'tvSearch':
	from resources.lib.menus import tvshows
	tvshows.TVshows().search()

elif action == 'tvSearchnew':
	from resources.lib.menus import tvshows
	tvshows.TVshows().search_new()

elif action == 'tvSearchterm':
	from resources.lib.menus import tvshows
	tvshows.TVshows().search_term(name)

elif action == 'tvPerson':
	from resources.lib.menus import tvshows
	tvshows.TVshows().person()

elif action == 'tvGenres':
	from resources.lib.menus import tvshows
	tvshows.TVshows().genres()

elif action == 'tvNetworks':
	from resources.lib.menus import tvshows
	tvshows.TVshows().networks()

elif action == 'tvLanguages':
	from resources.lib.menus import tvshows
	tvshows.TVshows().languages()

elif action == 'tvCertificates':
	from resources.lib.menus import tvshows
	tvshows.TVshows().certifications()

elif action == 'tvPersons':
	from resources.lib.menus import tvshows
	tvshows.TVshows().persons(url)

elif action == 'tvUserlists':
	from resources.lib.menus import tvshows
	tvshows.TVshows().userlists()



####################################################
#---SEASONS
####################################################
elif action == 'seasons':
	from resources.lib.menus import seasons
	seasons.Seasons().get(tvshowtitle, year, imdb, tvdb)
	# seasons.Seasons().get(tvshowtitle, year, imdb, tmdb, tvdb)

elif action == 'seasonsUserlists':
	from resources.lib.indexers import seasons
	seasons.Seasons().userlists()

elif action == 'seasonsList':
	from resources.lib.menus import seasons
	seasons.Seasons().seasonList(url)



####################################################
#---EPISODES
####################################################
elif action == 'episodes':
	from resources.lib.menus import episodes
	episodes.Episodes().get(tvshowtitle, year, imdb, tvdb, season, episode)
	# episodes.Episodes().get(tvshowtitle, year, imdb, tmdb, tvdb, season, episode)

elif action == 'episodesPage':
	from resources.lib.menus import episodes
	episodes.Episodes().get(tvshowtitle, year, imdb, tvdb, season, episode)

elif action == 'tvWidget':
	from resources.lib.menus import episodes
	episodes.Episodes().widget()

elif action == 'calendar':
	from resources.lib.menus import episodes
	episodes.Episodes().calendar(url)

elif action == 'calendars':
	from resources.lib.menus import episodes
	episodes.Episodes().calendars()

elif action == 'episodesUnfinished':
	from resources.lib.menus import episodes
	episodes.Episodes().unfinished(url)

elif action == 'episodesUserlists':
	from resources.lib.menus import episodes
	episodes.Episodes().userlists()



####################################################
#---Anime
####################################################
elif action == 'animeNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().anime()

elif action == 'animeMovies':
	from resources.lib.menus import movies
	movies.Movies().get(url)

elif action == 'animeTVshows':
	from resources.lib.menus import tvshows
	tvshows.TVshows().get(url)


####################################################
#---Originals
####################################################
elif action == 'originals':
	from resources.lib.menus import tvshows
	tvshows.TVshows().originals()



####################################################
#---YouTube
####################################################
elif action == 'youtube':
	from resources.lib.menus import youtube
	if subid is None:
		youtube.yt_index().root(action)
	else:
		youtube.yt_index().get(action, subid)



####################################################
#---Tools
####################################################
elif action == 'download':
	import json
	from resources.lib.modules import sources
	from resources.lib.modules import downloader
	try:
		downloader.download(name, image, sources.Sources().sourcesResolve(json.loads(source)[0], True))
	except:
		pass

elif action == 'downloadNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().downloads()

elif action == 'libraryNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().library()

elif action == 'toolNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().tools()

elif action == 'searchNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().search()

elif action == 'viewsNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().views()

elif action == 'resetViewTypes':
	from resources.lib.modules import views
	views.clearViews()

elif action == 'addView':
	from resources.lib.modules import views
	views.addView(content)

elif action == 'refresh':
	control.refresh()

elif action == 'openSettings':
	control.openSettings(query)

elif action == 'open.Settings.CacheProviders':
	control.openSettings(query)

elif action == 'artwork':
	control.artwork()

elif action == 'UpNextSettings':
	control.openSettings('0.0', 'service.upnext')
	if params.get('opensettings') == 'true':
		control.openSettings('0.0', "plugin.video.venom")

elif action == 'openscrapersSettings':
	control.openSettings('0.0', 'script.module.openscrapers')
	if params.get('opensettings') == 'true':
		control.openSettings(query, "plugin.video.venom")

elif action == 'urlResolver':
	try:
		import resolveurl
		resolveurl.display_settings()
	except:
		pass

elif action == 'urlResolverRDTorrent':
	control.openSettings(query, "script.module.resolveurl")



####################################################
#---Playcount
####################################################
elif action == 'moviePlaycount':
	from resources.lib.modules import playcount
	playcount.movies(name, imdb, query)

elif action == 'episodePlaycount':
	from resources.lib.modules import playcount
	playcount.episodes(name, imdb, tvdb, season, episode, query)

elif action == 'tvPlaycount':
	from resources.lib.modules import playcount
	playcount.tvshows(name, imdb, tvdb, season, query)



####################################################
#---Trakt
####################################################
elif action == 'traktManager':
	from resources.lib.modules import trakt
	trakt.manager(name, imdb, tvdb, season, episode)

elif action == 'authTrakt':
	from resources.lib.modules import trakt
	trakt.authTrakt()
	if params.get('opensettings') == 'true':
		control.openSettings(query, "plugin.video.venom")

elif action == 'cachesyncMovies':
	from resources.lib.modules import trakt
	trakt.cachesyncMovies()

elif action == 'cachesyncTVShows':
	from resources.lib.modules import trakt
	trakt.cachesyncTVShows()



####################################################
#---TMDb
####################################################
elif action == 'authTMDb':
	from resources.lib.indexers import tmdb
	tmdb.Auth().create_session_id()
	if params.get('opensettings') == 'true':
		control.openSettings(query, "plugin.video.venom")

elif action == 'revokeTMDb':
	from resources.lib.indexers import tmdb
	tmdb.Auth().revoke_session_id()
	if params.get('opensettings') == 'true':
		control.openSettings(query, "plugin.video.venom")



####################################################
#---Playlist
####################################################
elif action == 'playlistManager':
	from resources.lib.modules import playlist
	playlist.playlistManager(name, url, meta, art)

elif action == 'showPlaylist':
	from resources.lib.modules import playlist
	playlist.playlistShow()

elif action == 'clearPlaylist':
	from resources.lib.modules import playlist
	playlist.playlistClear()

elif action == 'queueItem':
	control.queueItem()
	if name is None:
		control.notification(title = 35515, message = 35519, icon = 'INFO', sound = notificationSound)
	else:
		control.notification(title = name, message = 35519, icon = 'INFO', sound = notificationSound)



####################################################
#---Player
####################################################
elif action == 'play':
	# playlistStarted = False
	# try:
		# import xbmc
		# if not xbmc.Player().isPlayingVideo():
			# r = argv[0]+"?action=playAll"
			# control.execute('RunPlugin(%s)' % r)
			# playlistStarted = True
	# except:
		# pass
	# if playlistStarted == False:

	from resources.lib.modules import sources
	sources.Sources().play(title, year, imdb, tvdb, season, episode, tvshowtitle, premiered, meta, select, rescrape=False)

elif action == 'playAll':
	control.player2().play(control.playlist)

elif action == 'playItem':
	from resources.lib.modules import sources
	sources.Sources().playItem(title, source)

elif action == 'reScrape':
	from resources.lib.modules import sources
	sources.Sources().play(title, year, imdb, tvdb, season, episode, tvshowtitle, premiered, meta, select, rescrape=True)

elif action == 'addItem':
	from resources.lib.modules import sources
	sources.Sources().addItem(title)

elif action == 'alterSources':
	from resources.lib.modules import sources
	sources.Sources().alterSources(url, meta)

elif action == 'trailer':
	from resources.lib.modules import trailer
	trailer.Trailer().play(name, url, windowedtrailer)

elif action == 'random':
	rtype = params.get('rtype')

	if rtype == 'movie':
		from resources.lib.menus import movies
		rlist = movies.Movies().get(url, idx=False)
		r = argv[0]+"?action=play"

	elif rtype == 'episode':
		from resources.lib.menus import episodes
		rlist = episodes.Episodes().get(tvshowtitle, year, imdb, tvdb, season, idx=False)
		r = argv[0]+"?action=play"

	elif rtype == 'season':
		from resources.lib.menus import seasons
		rlist = seasons.Seasons().get(tvshowtitle, year, imdb, tvdb, idx=False)
		r = argv[0]+"?action=random&rtype=episode"

	elif rtype == 'show':
		from resources.lib.menus import tvshows
		rlist = tvshows.TVshows().get(url, idx=False)
		r = argv[0]+"?action=random&rtype=season"

	from random import randint
	import json

	try:
		rand = randint(1,len(rlist))-1

		for p in ['title','year','imdb','tvdb','season','episode','tvshowtitle','premiered','select']:

			if rtype == "show" and p == "tvshowtitle":
				try:
					r += '&'+p+'='+quote_plus(rlist[rand]['title'])
				except:
					pass
			else:
				try:
					r += '&'+p+'='+quote_plus(rlist[rand][p])
				except:
					pass

		try:
			r += '&meta='+quote_plus(json.dumps(rlist[rand]))
		except:
			r += '&meta='+quote_plus("{}")

		if rtype == "movie":
			try:
				control.infoDialog(rlist[rand]['title'], control.lang(32536).encode('utf-8'), time=30000)
			except:
				pass

		elif rtype == "episode":
			try:
				control.infoDialog(rlist[rand]['tvshowtitle']+" - Season "+rlist[rand]['season']+" - "+rlist[rand]['title'], control.lang(32536).encode('utf-8'), time=30000)
			except:
				pass
		control.execute('RunPlugin(%s)' % r)
	except:
		control.infoDialog(control.lang(32537).encode('utf-8'), time=8000)



####################################################
#---Library Actions
####################################################
elif action == 'movieToLibrary':
	from resources.lib.modules import libtools
	libtools.libmovies().add(name, title, year, imdb, tmdb)

elif action == 'moviesToLibrary':
	from resources.lib.modules import libtools
	xbmc.log('url=%s' % url, 2)
	xbmc.log('list_name=%s' % list_name, 2)
	libtools.libmovies().range(url, list_name)

elif action == 'moviesListToLibrary':
	from resources.lib.menus import movies
	movies.Movies().moviesListToLibrary(url)

elif action == 'moviesToLibrarySilent':
	from resources.lib.modules import libtools
	libtools.libmovies().silent(url)

elif action == 'tvshowToLibrary':
	from resources.lib.modules import libtools
	libtools.libtvshows().add(tvshowtitle, year, imdb, tvdb)

elif action == 'tvshowsToLibrary':
	from resources.lib.modules import libtools
	libtools.libtvshows().range(url, list_name)

elif action == 'tvshowsListToLibrary':
	from resources.lib.menus import tvshows
	tvshows.TVshows().tvshowsListToLibrary(url)

elif action == 'tvshowsToLibrarySilent':
	from resources.lib.modules import libtools
	libtools.libtvshows().silent(url)

elif action == 'updateLibrary':
	from resources.lib.modules import libtools
	libtools.libepisodes().update()
	libtools.libmovies().list_update()
	libtools.libtvshows().list_update()

elif action == 'cleanLibrary':
	from resources.lib.modules import libtools
	libtools.lib_tools().clean()

elif action == 'librarySetup':
	from resources.lib.modules import libtools
	libtools.lib_tools().total_setup()

elif action == 'service':
	from resources.lib.modules import libtools
	libtools.lib_tools().service()


####################################################
#---Clear Cache actions
####################################################
elif action == 'cfNavigator':
	from resources.lib.menus import navigator
	navigator.Navigator().cf()

elif action == 'clearAllCache':
	from resources.lib.menus import navigator
	navigator.Navigator().clearCacheAll()
	if params.get('opensettings') == 'true':
		control.openSettings(query, 'plugin.video.venom')

elif action == 'clearSources':
	from resources.lib.menus import navigator
	navigator.Navigator().clearCacheProviders()
	if params.get('opensettings') == 'true':
		control.openSettings(query, 'plugin.video.venom')

elif action == 'clearMetaCache':
	from resources.lib.menus import navigator
	navigator.Navigator().clearCacheMeta()
	if params.get('opensettings') == 'true':
		control.openSettings(query, 'plugin.video.venom')

elif action == 'clearCache':
	from resources.lib.menus import navigator
	navigator.Navigator().clearCache()
	if params.get('opensettings') == 'true':
		control.openSettings(query, 'plugin.video.venom')

elif action == 'clearCacheSearch':
	from resources.lib.menus import navigator
	navigator.Navigator().clearCacheSearch() 
	if params.get('opensettings') == 'true':
		control.openSettings(query, 'plugin.video.venom')

elif action == 'clearSearchPhrase':
	from resources.lib.menus import navigator
	navigator.Navigator().clearCacheSearchPhrase(table, name)

elif action == 'clearBookmarks':
	from resources.lib.menus import navigator
	navigator.Navigator().clearBookmarks()
	if params.get('opensettings') == 'true':
		control.openSettings(query, 'plugin.video.venom')

elif action == 'clearResolveURLcache':
	if control.condVisibility('System.HasAddon(script.module.resolveurl)'):
		control.execute('RunPlugin(plugin://script.module.resolveurl/?mode=reset_cache)')