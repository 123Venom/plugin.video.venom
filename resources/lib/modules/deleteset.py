# -*- coding: utf-8 -*-

"""
	Bj
"""
import glob
import os
import re
import traceback

import xbmc
import xbmcgui
import xbmcaddon
import threading
from resources.lib.modules import log_utils
from resources.lib.modules import control
from xbmc import (LOGDEBUG, LOGERROR, LOGFATAL, LOGINFO,
                  LOGNONE, LOGNOTICE, LOGSEVERE, LOGWARNING)


addon_name = 'Venom'
addon_icon = xbmcaddon.Addon().getAddonInfo('icon')
addon_path = xbmc.translatePath(('special://home/addons/plugin.video.venom')).decode('utf-8')
addon_settings = xbmc.translatePath('special://userdata/addon_data/plugin.video.venom/settings.xml')

def deleteset():

    xbmcgui.Dialog().notification(addon_name, 'Clearing Old Settings', addon_icon)

    if os.path.exists(xbmc.translatePath(addon_settings)):
        control.deleteFile(addon_settings)

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

if __name__ == '__deleteset__':
    deleteset()
