# -*- coding: utf-8 -*-

'''
	Venom Add-on
'''

import copy
import json
import threading
import time

import requests

from resources.lib.modules import control
from resources.lib.modules import cache
from resources.lib.modules import client
from resources.lib.modules import workers
from resources.lib.modules import trakt
from resources.lib.modules import cleantitle
from resources.lib.modules import log_utils



class TVDBAPI:
	def __init__(self):
		self.apiKey = control.setting('tvdb.user')
		if self.apiKey == '':
			# self.apiKey = "43VPI0R8323FB7TI"
			self.apiKey = "7R8SZZX90UA9YMBU"

		self.baseUrl = 'https://api.thetvdb.com/'
		self.jwToken = control.setting('tvdb.jw')
		self.headers = {'Content-Type': 'application/json'}
		self.art = {}
		self.info = {}
		self.episode_summary = {}
		self.cast = []
		self.baseImageUrl = 'https://www.thetvdb.com/banners/'
		self.threads = []
		self.fanartart = {}

		if self.jwToken is not '':
			self.headers['Authorization'] = 'Bearer %s' % self.jwToken
		else:
			self.newToken()
			self.headers['Authorization'] = 'Bearer %s' % self.jwToken


	def post_request(self, url, postData):
		return cache.get(self._post_request, 12, url, postData)


	def _post_request(self, url, postData):
		postData = json.dumps(postData)
		url = self.baseUrl + url
		response = requests.post(url, data=postData, headers=self.headers).text
		if 'Not Authorized' in response:
			self.renewToken()
			self.headers['Authorization'] = 'Bearer %s' % self.jwToken
			response = requests.post(url, data=postData, headers=self.headers).text
		response = json.loads(response)
		return response


	def get_request(self, url):
		url = self.baseUrl + url
		response = requests.get(url, headers=self.headers).text
		if 'not authorized' in response.lower():
			self.renewToken()
			self.headers['Authorization'] = 'Bearer %s' % self.jwToken
			response = requests.get(url, headers=self.headers).text
		response = json.loads(response)
		return response


	def renewToken(self):
		url = self.baseUrl + 'refresh_token'
		response = requests.post(url, headers=self.headers)
		response = json.loads(response.text)

		if 'Error' in response:
			self.newToken(True)
		else:
			self.jwToken = response['token']
			# tools.tvdb_refresh = self.jwToken
			control.setSetting('tvdb.jw', self.jwToken)
			control.setSetting('tvdb.expiry', str(time.time() + (24 * (60 * 60))))
		return


	def newToken(self, ignore_lock=False):
		url = self.baseUrl + "login"
		postdata = {"apikey": self.apiKey}
		postdata = json.dumps(postdata)
		headers = self.headers
		if 'Authorization' in headers:
			headers.pop('Authorization')
		response = json.loads(requests.post(url, data=postdata, headers=self.headers).text)
		self.jwToken = response['token']
		# tools.tvdb_refresh = self.jwToken
		control.setSetting('tvdb.jw', self.jwToken)
		self.headers['Authorization'] = self.jwToken
		log_utils.log('Refreshed TVDB Token')
		control.setSetting('tvdb.expiry', str(time.time() + (24 * (60 * 60))))
		return response


	def getShowArt(self, tvdbID, keyType, number):
		try:
			url = 'series/{}/images/query?keyType={}'.format(tvdbID, keyType)
			response = self.get_request(url)
			return self._extract_art(response['data'], keyType, number)
		except:
			pass


	def _extract_art(self, response, dict_name, number):
		images = [(self.baseImageUrl + x['fileName'],
				x['ratingsInfo']['average'] if x['ratingsInfo']['count'] >= 5 else 5 + (
							x['ratingsInfo']['average'] - 5) * sin(x['ratingsInfo']['count'] / pi))
				for x in response if x['languageId'] == 7]
		images = sorted(images, key=lambda x: int(x[1]), reverse=True)

        counter = 0
        for i in images[:number]:
            self.art[dict_name if counter == 0 else '{}{}'.format(dict_name, counter)] = i[0]
            counter = counter + 1

