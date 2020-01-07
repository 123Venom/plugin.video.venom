# -*- coding: utf-8 -*-

"""
		v344.3a setting clear test Venom
"""
import glob
import os
import re
import traceback

import xbmc
import xbmcgui
import xbmcaddon
import threading
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import trakt
from xbmc import (LOGDEBUG, LOGERROR, LOGFATAL, LOGINFO,
                  LOGNONE, LOGNOTICE, LOGSEVERE, LOGWARNING)

# check on adding while loop here with xbmc.Monitor().abortRequested() vs. inside the service function
control.execute('RunPlugin(plugin://%s)' % control.get_plugin_url({'action': 'service'}))

addon_name = 'Venom'
addon_icon = xbmcaddon.Addon().getAddonInfo('icon')
addon_path = xbmc.translatePath(('special://home/addons/plugin.video.venom')).decode('utf-8')
module_path = xbmc.translatePath(('special://home/addons/plugin.video.venom')).decode('utf-8')
addon_settings = xbmc.translatePath('special://userdata/addon_data/plugin.video.venom/settings.xml')

def main():
    fum_ver = xbmcaddon.Addon(id='plugin.video.venom').getAddonInfo('version')
    updated = xbmcaddon.Addon(id='plugin.video.venom').getSetting('module_base')
    if updated == '' or updated is None:
        updated = '0'

    if str(fum_ver) == str(updated):
        return
    xbmcgui.Dialog().notification(addon_name, 'Clearing Old Settings', addon_icon)

    if os.path.exists(xbmc.translatePath(addon_settings)):
        control.deleteFile(addon_settings)

    xbmcaddon.Addon(id='plugin.video.venom').setSetting('module_base', fum_ver)
    xbmcgui.Dialog().notification(addon_name, 'Settings Cleared', addon_icon)

DEBUGPREFIX = '[COLOR red][ Venom DEBUG ][/COLOR]'


def log(msg, level=LOGNOTICE):

    try:
        if isinstance(msg, unicode):
            msg = '%s (ENCODED)' % (msg.encode('utf-8'))
        print('%s: %s' % (DEBUGPREFIX, msg))
    except Exception as e:
        try:
            xbmc.log('Logging Failure: %s' % (e), level)
        except Exception:
            pass

if __name__ == '__main__':
    main()

traktCredentials = trakt.getTraktCredentialsInfo()

try:
	AddonVersion = control.addon('plugin.video.venom').getAddonInfo('version')
	RepoVersion = control.addon('repository.venom').getAddonInfo('version')
	log_utils.log('################### Venom ######################', log_utils.LOGNOTICE)
	log_utils.log('####### CURRENT Venom VERSIONS REPORT ##########', log_utils.LOGNOTICE)
	log_utils.log('######### Venom PLUGIN VERSION: %s #########' % str(AddonVersion), log_utils.LOGNOTICE)
	log_utils.log('####### Venom REPOSITORY VERSION: %s #######' % str(RepoVersion), log_utils.LOGNOTICE)
	log_utils.log('################################################', log_utils.LOGNOTICE)

except:
	log_utils.log('############################# Venom ############################', log_utils.LOGNOTICE)
	log_utils.log('################# CURRENT Venom VERSIONS REPORT ################', log_utils.LOGNOTICE)
	log_utils.log('# ERROR GETTING Venom VERSION - Missing Repo of failed Install #', log_utils.LOGNOTICE)
	log_utils.log('################################################################', log_utils.LOGNOTICE)


def syncTraktLibrary():
	control.execute('RunPlugin(plugin://%s)' % 'plugin.video.venom/?action=tvshowsToLibrarySilent&url=traktcollection')
	control.execute('RunPlugin(plugin://%s)' % 'plugin.video.venom/?action=moviesToLibrarySilent&url=traktcollection')


def syncTraktWatched():
	control.execute('RunPlugin(plugin://%s)' % 'plugin.video.venom/?action=cachesyncTVShows')
	control.execute('RunPlugin(plugin://%s)' % 'plugin.video.venom/?action=cachesyncMovies')
	# if control.setting('trakt.general.notifications') == 'true':
		# control.notification(title = 'default', message = 'Trakt Watched Status Sync Complete', icon='default', time=1, sound=False)


if traktCredentials is True:
	syncTraktWatched()


if control.setting('autoTraktOnStart') == 'true':
	syncTraktLibrary()


if int(control.setting('schedTraktTime')) > 0:
	log_utils.log('###############################################################', log_utils.LOGNOTICE)
	log_utils.log('#################### STARTING TRAKT SCHEDULING ################', log_utils.LOGNOTICE)
	log_utils.log('#################### SCHEDULED TIME FRAME '+ control.setting('schedTraktTime')  + ' HOURS ###############', log_utils.LOGNOTICE)
	timeout = 3600 * int(control.setting('schedTraktTime'))
	schedTrakt = threading.Timer(timeout, syncTraktLibrary)
	schedTrakt.start()



