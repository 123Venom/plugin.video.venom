# -*- coding: utf-8 -*-

'''
	Venom Add-on
'''

import os, sys, re, datetime
import urllib, urlparse, json

from resources.lib.modules import cache
from resources.lib.modules import cleangenre
from resources.lib.modules import client
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import metacache
from resources.lib.modules import playcount
from resources.lib.modules import trakt
from resources.lib.modules import views
from resources.lib.modules import workers

sysaddon = sys.argv[0]
syshandle = int(sys.argv[1])

params = dict(urlparse.parse_qsl(sys.argv[2].replace('?',''))) if len(sys.argv) > 1 else dict()
action = params.get('action')
notificationSound = False if control.setting('notification.sound') == 'false' else True


class Collections:
	def __init__(self):
		self.list = []
		self.disable_fanarttv = control.setting('disable.fanarttv')
		self.datetime = (datetime.datetime.utcnow() - datetime.timedelta(hours = 5))
		self.systime = (self.datetime).strftime('%Y%m%d%H%M%S%f')

		self.lang = control.apiLanguage()['trakt']
		self.traktCredentials = trakt.getTraktCredentialsInfo()

		self.imdb_user = control.setting('imdb.user').replace('ur', '')

		self.tmdb_key = control.setting('tm.user')
		if self.tmdb_key == '' or self.tmdb_key is None:
			self.tmdb_key = '3320855e65a9758297fec4f7c9717698'

		# self.user = str(self.imdb_user) + str(self.tmdb_key)
		self.user = str(self.tmdb_key)

		self.tmdb_link = 'https://api.themoviedb.org'
		self.tmdb_poster = 'http://image.tmdb.org/t/p/w300'
		self.tmdb_fanart = 'http://image.tmdb.org/t/p/w1280'
		self.tmdb_api_link = 'https://api.themoviedb.org/4/list/%s?api_key=%s&sort_by=release_date.asc&page=1' % ('%s', self.tmdb_key)

		self.imdb_link = 'https://www.imdb.com'
		self.imdblists_link = 'https://www.imdb.com/user/ur%s/lists?tab=all&sort=mdfd&order=desc&filter=titles' % self.imdb_user
		self.imdblist_link = 'https://www.imdb.com/list/%s/?view=detail&sort=alpha,asc&title_type=movie,short,tvMovie,tvSpecial,video&start=1'
		self.imdbwatchlist_link = 'https://www.imdb.com/user/ur%s/watchlist?sort=alpha,asc' % self.imdb_user


# Martial Arts Movies
		self.martialartsmovies_link = self.tmdb_api_link % '117973'

# Martial Arts Actors
		self.brandonlee_link = self.tmdb_api_link % '117971'
		self.brucelee2_link = self.tmdb_api_link % '118011'
		self.chucknorris_link = self.tmdb_api_link % '118012'
		self.chowyunfat_link = self.tmdb_api_link % '118014'
		self.donnieyen_link = self.tmdb_api_link % '118015'
		self.garydaniels_link = self.tmdb_api_link % '118035'
		self.jackiechan_link = self.tmdb_api_link % '118017'
		self.jasonstatham_link = self.tmdb_api_link % '118016'
		self.vandamme_link = self.tmdb_api_link % '118022'
		self.jetli_link = self.tmdb_api_link % '118023'
		self.markdacascos_link = self.tmdb_api_link % '118024'
		self.michaeljaiwhite_link = self.tmdb_api_link % '118025'
		self.philipng_link = self.tmdb_api_link % '118026'
		self.rain_link = self.tmdb_api_link % '118033'
		self.robinshou_link = self.tmdb_api_link % '118028'
		self.scottadkins_link = self.tmdb_api_link % '118061'
		self.stevenseagal_link = self.tmdb_api_link % '118029'
		self.tigerchen_link = self.tmdb_api_link % '118030'
		self.tonyjaa_link = self.tmdb_api_link % '118031'

# Christmas Movies
		self.xmasmovies_link = self.tmdb_api_link % '32770'

# DC Comics Movies
		self.dcmovies_link = self.tmdb_api_link % '32799'

# Disney Movies
		self.disneymovies_link = self.tmdb_api_link % '32800'

# Kids Movies
		self.kidsmovies_link = self.tmdb_api_link % '32802'

# Marvel Movies
		self.marvelmovies_link = self.tmdb_api_link % '32793'

# Boxset Collection
		self.rounds_link = self.tmdb_api_link % '13120'
		self.tmdb300_link = self.tmdb_api_link % '13132'
		self.fortyeighthours_link = self.tmdb_api_link % '33259'
		self.aceventura_link = self.tmdb_api_link % '33260'
		self.aceventura_link = self.tmdb_api_link % '33260'
		self.airplane_link = self.tmdb_api_link % '33261'
		self.airport_link = self.tmdb_api_link % '33262'
		self.americangraffiti_link = self.tmdb_api_link % '33263'
		self.anaconda_link = self.tmdb_api_link % '33264'
		self.analyzethis_link = self.tmdb_api_link % '33265'
		self.anchorman_link = self.tmdb_api_link % '33266'
		self.austinpowers_link = self.tmdb_api_link % '33267'
		self.avp_link = self.tmdb_api_link % '13199'
		self.backtothefuture_link = self.tmdb_api_link % '33268'
		self.badass_link = self.tmdb_api_link % '13205'
		self.badboys_link = self.tmdb_api_link % '33269'
		self.badsanta_link = self.tmdb_api_link % '33270'
		self.basicinstinct_link = self.tmdb_api_link % '33271'
		self.bestofthebest_link = self.tmdb_api_link % '13269'
		self.beverlyhillscop_link = self.tmdb_api_link % '33272'
		self.bigmommashouse_link = self.tmdb_api_link % '33273'
		self.bloodsport_link = self.tmdb_api_link % '13281'
		self.bluesbrothers_link = self.tmdb_api_link % '33274'
		self.bourne_link = self.tmdb_api_link % '33275'
		self.brucealmighty_link = self.tmdb_api_link % '33276'
		self.brucelee_link = self.tmdb_api_link % '13295'
		self.caddyshack_link = self.tmdb_api_link % '33277'
		self.catsanddogs_link = self.tmdb_api_link % '16501'
		self.cheaperbythedozen_link = self.tmdb_api_link % '33278'
		self.cheechandchong_link = self.tmdb_api_link % '33420'
		self.childsplay_link = self.tmdb_api_link % '33279'
		self.cityslickers_link = self.tmdb_api_link % '33280'
		self.conan_link = self.tmdb_api_link % '33281'
		self.crank_link = self.tmdb_api_link % '33282'
		self.crocodiledundee_link = self.tmdb_api_link % '33419'
		self.thecrow_link = self.tmdb_api_link % '13294'
		self.davincicode_link = self.tmdb_api_link % '33283'
		self.daddydaycare_link = self.tmdb_api_link % '33284'
		self.deathwish_link = self.tmdb_api_link % '33285'
		self.deltaforce_link = self.tmdb_api_link % '33286'
		self.diehard_link = self.tmdb_api_link % '33287'
		self.dirtydancing_link = self.tmdb_api_link % '33288'
		self.dirtyharry_link = self.tmdb_api_link % '33289'
		self.divergent_link = self.tmdb_api_link % '13311'
		self.dumbanddumber_link = self.tmdb_api_link % '33290'
		self.escapefromnewyork_link = self.tmdb_api_link % '33291'
		self.everywhichwaybutloose_link = self.tmdb_api_link % '33292'
		self.exorcist_link = self.tmdb_api_link % '33293'
		self.theexpendables_link = self.tmdb_api_link % '33294'
		self.fastandthefurious_link = self.tmdb_api_link % '13062'
		self.fatherofthebride_link = self.tmdb_api_link % '33295'
		self.fletch_link = self.tmdb_api_link % '33296'
		self.thefly_link = self.tmdb_api_link % '13303'
		self.friday_link = self.tmdb_api_link % '33297'
		self.fridaythe13th_link = self.tmdb_api_link % '33298'
		self.fugitive_link = self.tmdb_api_link % '33299'
		self.gijoe_link = self.tmdb_api_link % '33300'
		self.getshorty_link = self.tmdb_api_link % '33301'
		self.gettysburg_link = self.tmdb_api_link % '33302'
		self.ghostrider_link = self.tmdb_api_link % '33303'
		self.ghostbusters_link = self.tmdb_api_link % '33201'
		self.godsnotdead_link = self.tmdb_api_link % '33304'
		self.godfather_link = self.tmdb_api_link % '33305'
		self.godzilla_link = self.tmdb_api_link % '33306'
		self.grownups_link = self.tmdb_api_link % '33307'
		self.grumpyoldmen_link = self.tmdb_api_link % '33308'
		self.gunsofnavarone_link = self.tmdb_api_link % '33309'
		self.halloween_link = self.tmdb_api_link % '33310'
		self.hangover_link = self.tmdb_api_link % '33311'
		self.hanniballector_link = self.tmdb_api_link % '33312'
		self.hellraiser_link = self.tmdb_api_link % '33313'
		self.highlander_link = self.tmdb_api_link % '13256'
		self.thehobbit_link = 'https://www.imdb.com/search/title?title=the+hobbit&title_type=feature,tv_movie&num_votes=1000,&countries=us&languages=en&sort=release_date,asc'
		self.hollowman_link = self.tmdb_api_link % '13251'
		self.honeyishrunkthekids_link = self.tmdb_api_link % '33208'
		self.horriblebosses_link = self.tmdb_api_link % '33314'
		self.hostel_link = self.tmdb_api_link % '33315'
		self.hotshots_link = self.tmdb_api_link % '33316'
		self.hungergames_link = 'https://www.imdb.com/search/title?title=hunger+games&title_type=feature&num_votes=1000,&countries=us&languages=en&sort=release_date,asc'
		self.huntsman_link = self.tmdb_api_link % '13235'
		self.independenceday_link = self.tmdb_api_link % '33317'
		self.indianajones_link = self.tmdb_api_link % '113191'
		self.insidious_link = self.tmdb_api_link % '33319'
		self.ironeagle_link = self.tmdb_api_link % '33320'
		self.jackreacher_link = self.tmdb_api_link % '33321'
		self.jackryan_link = self.tmdb_api_link % '33322'
		self.jackass_link = self.tmdb_api_link % '33323'
		self.jamesbond_link = self.tmdb_api_link % '33324'
		self.jaws_link = self.tmdb_api_link % '33325'
		self.jeeperscreepers_link = self.tmdb_api_link % '33326'
		self.johnwick_link = self.tmdb_api_link % '113190'
		self.journeytocenter_link = self.tmdb_api_link % '13216'
		self.judgedredd_link = self.tmdb_api_link % '13215'
		self.jumanji_link = self.tmdb_api_link % '113189'
		self.jumpst_link = self.tmdb_api_link % '13213'
		self.jurassicpark_link = self.tmdb_api_link % '113188'
		self.kickass_link = self.tmdb_api_link % '33329'
		self.killbill_link = self.tmdb_api_link % '33330'
		self.kingkong_link = self.tmdb_api_link % '113082'
		self.laracroft_link = self.tmdb_api_link % '33332'
		self.legallyblonde_link = self.tmdb_api_link % '33333'
		self.lethalweapon_link = self.tmdb_api_link % '33334'
		self.lookwhostalking_link = self.tmdb_api_link % '33335'
		self.lordoftherings_link = 'https://www.imdb.com/search/title?title=the+lord+of+the+rings&title_type=feature&num_votes=1000,&countries=us&languages=en&sort=release_date,asc'
		self.machete_link = self.tmdb_api_link % '33336'
		self.madmax_link = self.tmdb_api_link % '13188'
		self.magicmike_link = self.tmdb_api_link % '33337'
		self.majorleague_link = self.tmdb_api_link % '33338'
		self.manfromsnowyriver_link = self.tmdb_api_link % '33339'
		self.mask_link = self.tmdb_api_link % '33340'
		self.matrix_link = self.tmdb_api_link % '33341'
		self.mazerunner_link = self.tmdb_api_link % '13182'
		self.themechanic_link = self.tmdb_api_link % '33342'
		self.meettheparents_link = self.tmdb_api_link % '33343'
		self.meninblack_link = self.tmdb_api_link % '33344'
		self.mightyducks_link = self.tmdb_api_link % '33345'
		self.misscongeniality_link = self.tmdb_api_link % '33346'
		self.missinginaction_link = self.tmdb_api_link % '33347'
		self.missionimpossible_link = self.tmdb_api_link % '113187'
		self.themummy_link = 'https://www.imdb.com/search/title?title=mummy&title_type=feature&release_date=1999-01-01,&num_votes=1000,&countries=us&languages=en&sort=release_date,asc'
		self.nakedgun_link = self.tmdb_api_link % '33349'
		self.nationallampoon_link = self.tmdb_api_link % '33350'
		self.nationallampoonsvacation_link = self.tmdb_api_link % '33351'
		self.nationaltreasure_link = self.tmdb_api_link % '33352'
		self.neighbors_link = self.tmdb_api_link % '33353'
		self.nightatthemuseum_link = self.tmdb_api_link % '33354'
		self.nightmareonelmstreet_link = self.tmdb_api_link % '33355'
		self.nowyouseeme_link = self.tmdb_api_link % '33356'
		self.nuttyprofessor_link = self.tmdb_api_link % '33357'
		self.oceanseleven_link = self.tmdb_api_link % '33358'
		self.oddcouple_link = self.tmdb_api_link % '33359'
		self.ohgod_link = self.tmdb_api_link % '33360'
		self.olympushasfallen_link = self.tmdb_api_link % '33361'
		self.omen_link = self.tmdb_api_link % '33362'
		self.paulblart_link = self.tmdb_api_link % '33363'
		self.piratesofthecaribbean_link = self.tmdb_api_link % '33364'
		self.pitchperfect_link = self.tmdb_api_link % '123873'
		self.planetoftheapes_link = self.tmdb_api_link % '13141'
		self.policeacademy_link = self.tmdb_api_link % '33366'
		self.poltergeist_link = self.tmdb_api_link % '33367'
		self.porkys_link = self.tmdb_api_link % '33368'
		self.predator_link = self.tmdb_api_link % '13136'
		self.thepurge_link = self.tmdb_api_link % '33370'
		self.rambo_link = self.tmdb_api_link % '33371'
		self.red_link = self.tmdb_api_link % '33372'
		self.revengeofthenerds_link = self.tmdb_api_link % '33373'
		self.riddick_link = self.tmdb_api_link % '33374'
		self.ridealong_link = self.tmdb_api_link % '33375'
		self.thering_link = self.tmdb_api_link % '33418'
		self.robocop_link = self.tmdb_api_link % '13115'
		self.rocky_link = self.tmdb_api_link % '33377'
		self.romancingthestone_link = self.tmdb_api_link % '33378'
		self.rushhour_link = self.tmdb_api_link % '33379'
		self.santaclause_link = self.tmdb_api_link % '33380'
		self.saw_link = self.tmdb_api_link % '33381'
		self.sexandthecity_link = self.tmdb_api_link % '33382'
		self.shaft_link = self.tmdb_api_link % '33383'
		self.shanghainoon_link = self.tmdb_api_link % '33384'
		self.sincity_link = self.tmdb_api_link % '33385'
		self.sinister_link = self.tmdb_api_link % '33386'
		self.sisteract_link = self.tmdb_api_link % '33387'
		self.smokeyandthebandit_link = self.tmdb_api_link % '33388'
		self.speed_link = self.tmdb_api_link % '33389'
		self.stakeout_link = self.tmdb_api_link % '33390'
		self.startrek_link = self.tmdb_api_link % '33391'
		self.starwars_link = self.tmdb_api_link % '113185'
		self.thesting_link = self.tmdb_api_link % '33392'
		self.taken_link = self.tmdb_api_link % '33393'
		self.taxi_link = self.tmdb_api_link % '33394'
		self.ted_link = self.tmdb_api_link % '33395'
		self.teenwolf_link = self.tmdb_api_link % '33396'
		self.terminator_link = self.tmdb_api_link % '33397'
		self.termsofendearment_link = self.tmdb_api_link % '33398'
		self.texaschainsawmassacre_link = self.tmdb_api_link % '33399'
		self.thething_link = self.tmdb_api_link % '33400'
		self.thomascrownaffair_link = self.tmdb_api_link % '33401'
		self.transformers_link = 'https://www.imdb.com/search/title?title=transformers&title_type=feature&num_votes=1000,&countries=us&languages=en&sort=release_date,asc'
		self.transporter_link = self.tmdb_api_link % '33402'
		self.tron_link = 'https://www.imdb.com/search/title?title=tron&title_type=feature&num_votes=1000,&countries=us&languages=en&sort=release_date,asc'
		self.twilight_link = 'https://www.imdb.com/search/title?title=twilight&title_type=feature&num_votes=1000,&countries=us&languages=en&plot=vampire&sort=release_date,asc'
		self.undersiege_link = self.tmdb_api_link % '33403'
		self.underworld_link = 'https://www.imdb.com/search/title?title=Underworld&title_type=feature&num_votes=1000,&genres=action&countries=us&languages=en&sort=release_date,asc'
		self.universalsoldier_link = self.tmdb_api_link % '33404'
		self.wallstreet_link = self.tmdb_api_link % '33405'
		self.waynesworld_link = self.tmdb_api_link % '33406'
		self.weekendatbernies_link = self.tmdb_api_link % '33407'
		self.wholenineyards_link = self.tmdb_api_link % '33408'
		self.xfiles_link = self.tmdb_api_link % '33409'
		self.xxx_link = self.tmdb_api_link % '33410'
		self.youngguns_link = self.tmdb_api_link % '33411'
		self.zoolander_link = self.tmdb_api_link % '33412'
		self.zorro_link = self.tmdb_api_link % '33413'

# Boxset Collection Kids
		self.onehundredonedalmations_link = self.tmdb_api_link % '33182'
		self.addamsfamily_link = self.tmdb_api_link % '33183'
		self.aladdin_link = self.tmdb_api_link % '33184'
		self.alvinandthechipmunks_link = self.tmdb_api_link % '33185'
		self.atlantis_link = self.tmdb_api_link % '33186'
		self.babe_link = self.tmdb_api_link % '33187'
		self.balto_link = self.tmdb_api_link % '33188'
		self.bambi_link = self.tmdb_api_link % '33189'
		self.beautyandthebeast_link = self.tmdb_api_link % '33190'
		self.beethoven_link = self.tmdb_api_link % '33191'
		self.brotherbear_link = self.tmdb_api_link % '33192'
		self.cars_link = self.tmdb_api_link % '33193'
		self.cinderella_link = self.tmdb_api_link % '33194'
		self.cloudywithachanceofmeatballs_link = self.tmdb_api_link % '33195'
		self.despicableme_link = self.tmdb_api_link % '33197'
		self.findingnemo_link = self.tmdb_api_link % '33198'
		self.foxandthehound_link = self.tmdb_api_link % '33199'
		self.freewilly_link = self.tmdb_api_link % '33200'
		self.ghostbusters_link = self.tmdb_api_link % '33201'
		self.gremlins_link =  self.tmdb_api_link % '33202'
		self.happyfeet_link = self.tmdb_api_link % '33204'
		self.harrypotter_link = self.tmdb_api_link % '33205'
		self.homealone_link = self.tmdb_api_link % '33206'
		self.homewardbound_link = self.tmdb_api_link % '33207'
		self.honeyishrunkthekids_link = self.tmdb_api_link % '33208'
		self.hoteltransylvania_link = self.tmdb_api_link % '33209'
		self.howtotrainyourdragon_link = self.tmdb_api_link % '33210'
		self.hunchbackofnotredame_link = self.tmdb_api_link % '33211'
		self.iceage_link = self.tmdb_api_link % '33212'
		self.jurassicpark_link = self.tmdb_api_link % '113188'
		self.kungfupanda_link = self.tmdb_api_link % '33218'
		self.ladyandthetramp_link = self.tmdb_api_link % '33219'
		self.liloandstitch_link = self.tmdb_api_link % '33220'
		self.madagascar_link = self.tmdb_api_link % '33221'
		self.monstersinc_link = self.tmdb_api_link % '33222'
		self.mulan_link = self.tmdb_api_link % '33223'
		self.narnia_link = self.tmdb_api_link % '33224'
		self.newgroove_link = self.tmdb_api_link % '33225'
		self.openseason_link = self.tmdb_api_link % '33226'
		self.planes_link = self.tmdb_api_link % '33227'
		self.pocahontas_link = self.tmdb_api_link % '33228'
		self.problemchild_link = self.tmdb_api_link % '33229'
		self.rio_link = self.tmdb_api_link % '33230'
		self.sammysadventures_link = self.tmdb_api_link % '33231'
		self.scoobydoo_link = self.tmdb_api_link % '33232'
		self.shortcircuit_link = self.tmdb_api_link % '33233'
		self.shrek_link = self.tmdb_api_link % '33234'
		self.spongebobsquarepants_link = self.tmdb_api_link % '33235'
		self.spykids_link = self.tmdb_api_link % '33236'
		self.starwars_link = self.tmdb_api_link % '113185'
		self.stuartlittle_link = self.tmdb_api_link % '33238'
		self.tarzan_link = self.tmdb_api_link % '33239'
		self.teenagemutantninjaturtles_link = self.tmdb_api_link % '33240'
		self.thejunglebook_link = self.tmdb_api_link % '33216'
		self.thekaratekid_link = self.tmdb_api_link % '33241'
		self.thelionking_link = self.tmdb_api_link % '33242'
		self.thelittlemermaid_link = self.tmdb_api_link % '33243'
		self.theneverendingstory_link = self.tmdb_api_link % '33248'
		self.thesmurfs_link = self.tmdb_api_link % '33249'
		self.toothfairy_link = self.tmdb_api_link % '33251'
		self.tinkerbell_link = self.tmdb_api_link % '33252'
		self.tomandjerry_link = self.tmdb_api_link % '33253'
		self.toystory_link = self.tmdb_api_link % '33254'
		self.veggietales_link = self.tmdb_api_link % '33255'
		self.winniethepooh_link = self.tmdb_api_link % '33257'
		self.wizardofoz_link = self.tmdb_api_link % '33258'

# Superhero Collection
		self.avengers_link = self.tmdb_api_link % '33128'
		self.batman_link = self.tmdb_api_link % '33129'
		self.captainamerica_link =self.tmdb_api_link % '33130'
		self.darkknight_link = self.tmdb_api_link % '33132'
		self.fantasticfour_link = self.tmdb_api_link % '33133'
		self.hulk_link = self.tmdb_api_link % '33134'
		self.ironman_link = self.tmdb_api_link % '33135'
		self.spiderman_link = self.tmdb_api_link % '33126'
		self.superman_link = self.tmdb_api_link % '33136'
		self.thor_link = 'https://www.imdb.com/search/title?title=thor&title_type=feature&num_votes=1000,&genres=action&countries=us&languages=en&sort=release_date,asc'
		self.xmen_link = self.tmdb_api_link % '33137'


	def collectionsNavigator(self, lite=False):
		self.addDirectoryItem('Movies', 'collectionBoxset', 'boxsets.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Martial Arts', 'collection_martial_arts', 'boxsets.png', 'DefaultVideoPlaylists.png')

		if control.getMenuEnabled('navi.xmascollections'):
			self.addDirectoryItem('Christmas Collections', 'collections&url=xmasmovies', 'boxsets.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('DC Comics', 'collections&url=dcmovies', 'boxsets.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Marvel Comics', 'collections&url=marvelmovies', 'boxsets.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Superheroes', 'collectionSuperhero', 'boxsets.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Kids Collections', 'collectionKids', 'boxsets.png', 'DefaultVideoPlaylists.png')
		self.endDirectory()


	def collectionBoxset(self):
		self.addDirectoryItem('12 Rounds (2009-2015)', 'collections&url=rounds', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('300 (2007-2014)', 'collections&url=tmdb300', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('48 Hrs. (1982-1990)', 'collections&url=fortyeighthours', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Ace Ventura (1994-1995)', 'collections&url=aceventura', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Airplane (1980-1982)', 'collections&url=airplane', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Airport (1970-1979)', 'collections&url=airport', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('American Graffiti (1973-1979)', 'collections&url=americangraffiti', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Anaconda (1997-2004)', 'collections&url=anaconda', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Analyze This (1999-2002)', 'collections&url=analyzethis', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Anchorman (2004-2013)', 'collections&url=anchorman', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Austin Powers (1997-2002)', 'collections&url=austinpowers', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('AVP (2004-2007)', 'collections&url=avp', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Back to the Future (1985-1990)', 'collections&url=backtothefuture', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bad Ass (2012-2014)', 'collections&url=badass', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bad Boys (1995-2003)', 'collections&url=badboys', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bad Santa (2003-2016)', 'collections&url=badsanta', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Basic Instinct (1992-2006)', 'collections&url=basicinstinct', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Best Of The Best (1989-1998)', 'collections&url=bestofthebest', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Beverly Hills Cop (1984-1994)', 'collections&url=beverlyhillscop', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Big Mommas House (2000-2011)', 'collections&url=bigmommashouse', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bloodsport (1988-2010)', 'collections&url=bloodsport', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Blues Brothers (1980-1998)', 'collections&url=bluesbrothers', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bourne (2002-2016)', 'collections&url=bourne', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bruce Almighty (2003-2007)', 'collections&url=brucealmighty', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bruce Lee (1965-2017)', 'collections&url=brucelee', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Caddyshack (1980-1988)', 'collections&url=caddyshack', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Cheaper by the Dozen (2003-2005)', 'collections&url=cheaperbythedozen', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Cheech and Chong (1978-1984)', 'collections&url=cheechandchong', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Childs Play (1988-2004)', 'collections&url=childsplay', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('City Slickers (1991-1994)', 'collections&url=cityslickers', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Conan (1982-2011)', 'collections&url=conan', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Crank (2006-2009)', 'collections&url=crank', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Crocodile Dundee (1986-2001)', 'collections&url=crocodiledundee', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Crow (1994-2005)', 'collections&url=thecrow', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Da Vinci Code (2006-2017)', 'collections&url=davincicode', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Daddy Day Care (2003-2007)', 'collections&url=daddydaycare', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Death Wish (1974-1994)', 'collections&url=deathwish', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Delta Force (1986-1990)', 'collections&url=deltaforce', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Die Hard (1988-2013)', 'collections&url=diehard', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Dirty Dancing (1987-2004)', 'collections&url=dirtydancing', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Dirty Harry (1971-1988)', 'collections&url=dirtyharry', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Divergent (2014-2016)', 'collections&url=divergent', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Dumb and Dumber (1994-2014)', 'collections&url=dumbanddumber', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Escape from New York (1981-1996)', 'collections&url=escapefromnewyork', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Every Which Way But Loose (1978-1980)', 'collections&url=everywhichwaybutloose', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Exorcist (1973-2005)', 'collections&url=exorcist', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Expendables (2010-2014)', 'collections&url=theexpendables', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Fast and the Furious (2001-2021)', 'collections&url=fastandthefurious', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Father of the Bride (1991-1995)', 'collections&url=fatherofthebride', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Fletch (1985-1989)', 'collections&url=fletch', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Fly (1986-1989)', 'collections&url=thefly', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Friday (1995-2002)', 'collections&url=friday', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Friday the 13th (1980-2009)', 'collections&url=fridaythe13th', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Fugitive (1993-1998)', 'collections&url=fugitive', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('G.I. Joe (2009-2013)', 'collections&url=gijoe', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Get Shorty (1995-2005)', 'collections&url=getshorty', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Gettysburg (1993-2003)', 'collections&url=gettysburg', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Ghost Rider (2007-2011)', 'collections&url=ghostrider', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Ghostbusters (1984-2016)', 'collections&url=ghostbusters', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Gods Not Dead (2014-2016)', 'collections&url=godsnotdead', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Godfather (1972-1990)', 'collections&url=godfather', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Godzilla (1956-2016)', 'collections&url=godzilla', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Grown Ups (2010-2013)', 'collections&url=grownups', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Grumpy Old Men (2010-2013)', 'collections&url=grumpyoldmen', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Guns of Navarone (1961-1978)', 'collections&url=gunsofnavarone', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Halloween (1978-2009)', 'collections&url=halloween', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hangover (2009-2013)', 'collections&url=hangover', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hannibal Lector (1986-2007)', 'collections&url=hanniballector', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hellraiser (1987-1996)', 'collections&url=hellraiser', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Highlander', 'collections&url=highlander', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Hobbit (1977-2014)', 'collections&url=thehobbit', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hollow Man (2000-2006)', 'collections&url=hollowman', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Honey I Shrunk the Kids (1989-1995)', 'collections&url=honeyishrunkthekids', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Horrible Bosses (2011-2014)', 'collections&url=horriblebosses', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hostel (2005-2011)', 'collections&url=hostel', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hot Shots (1991-1996)', 'collections&url=hotshots', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hunger Games (2012-2015)', 'collections&url=hungergames', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Huntsman (2012-2016)', 'collections&url=huntsman', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Independence Day (1996-2016)', 'collections&url=independenceday', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Indiana Jones (1981-2021)', 'collections&url=indianajones', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Insidious (2010-2015)', 'collections&url=insidious', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Iron Eagle (1986-1992)', 'collections&url=ironeagle', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jack Reacher (2012-2016)', 'collections&url=jackreacher', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jack Ryan (1990-2014)', 'collections&url=jackryan', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jackass (2002-2013)', 'collections&url=jackass', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('James Bond (1963-2015)', 'collections&url=jamesbond', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jaws (1975-1987)', 'collections&url=jaws', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jeepers Creepers (2001-2017)', 'collections&url=jeeperscreepers', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('John Wick (2014-2021)', 'collections&url=johnwick', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Journey to the Center of the Earth (2008-2012)', 'collections&url=journeytocenter', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Judge Dredd (1995-2012)', 'collections&url=judgedredd', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jumanji (1995-2019)', 'collections&url=jumanji', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jump Street (2012-2014)', 'collections&url=jumpst', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jurassic Park (1993-2021)', 'collections&url=jurassicpark', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Kick-Ass (2010-2013)', 'collections&url=kickass', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Kill Bill (2003-2004)', 'collections&url=killbill', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('King Kong (1933-2020)', 'collections&url=kingkong', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Lara Croft (2001-2003)', 'collections&url=laracroft', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Legally Blonde (2001-2003)', 'collections&url=legallyblonde', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Lethal Weapon (1987-1998)', 'collections&url=lethalweapon', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Look Whos Talking (1989-1993)', 'collections&url=lookwhostalking', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Lord of The Rings (1978-2003)', 'collections&url=lordoftherings', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Machete (2010-2013)', 'collections&url=machete', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Mad Max (1979-2015)', 'collections&url=madmax', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Magic Mike (2012-2015)', 'collections&url=magicmike', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Major League (1989-1998)', 'collections&url=majorleague', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Man from Snowy River (1982-1988)', 'collections&url=manfromsnowyriver', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Mask (1994-2005)', 'collections&url=mask', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Matrix (1999-2003)', 'collections&url=matrix', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Maze Runner(2014-2018)', 'collections&url=mazerunner', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Mechanic (2011-2016)', 'collections&url=themechanic', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Meet the Parents (2000-2010)', 'collections&url=meettheparents', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Men in Black (1997-2012)', 'collections&url=meninblack', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Mighty Ducks (1995-1996)', 'collections&url=mightyducks', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Miss Congeniality (2000-2005)', 'collections&url=misscongeniality', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Missing in Action (1984-1988)', 'collections&url=missinginaction', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Mission Impossible (1996-2021)', 'collections&url=missionimpossible', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Mummy (1999-2017)', 'collections&url=themummy', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Naked Gun (1988-1994)', 'collections&url=nakedgun', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('National Lampoon (1978-2006)', 'collections&url=nationallampoon', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('National Lampoons Vacation (1983-2015)', 'collections&url=nationallampoonsvacation', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('National Treasure (2004-2007)', 'collections&url=nationaltreasure', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Neighbors (2014-2016)', 'collections&url=neighbors', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Night at the Museum (2006-2014)', 'collections&url=nightatthemuseum', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Nightmare on Elm Street (1984-2010)', 'collections&url=nightmareonelmstreet', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Now You See Me (2013-2016)', 'collections&url=nowyouseeme', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Nutty Professor (1996-2000)', 'collections&url=nuttyprofessor', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Oceans Eleven (2001-2007)', 'collections&url=oceanseleven', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Odd Couple (1968-1998)', 'collections&url=oddcouple', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Oh, God (1977-1984)', 'collections&url=ohgod', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Olympus Has Fallen (2013-2016)', 'collections&url=olympushasfallen', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Omen (1976-1981)', 'collections&url=omen', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Paul Blart Mall Cop (2009-2015)', 'collections&url=paulblart', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Pirates of the Caribbean (2003-2017)', 'collections&url=piratesofthecaribbean', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Pitch Perfect (2012-2015)', 'collections&url=pitchperfect', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Planet of the Apes (1968-2017)', 'collections&url=planetoftheapes', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Police Academy (1984-1994)', 'collections&url=policeacademy', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Poltergeist (1982-1988)', 'collections&url=poltergeist', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Porkys (1981-1985)', 'collections&url=porkys', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Predator (1987-2018)', 'collections&url=predator', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Purge (2013-2016)', 'collections&url=thepurge', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Rambo (1982-2008)', 'collections&url=rambo', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('RED (2010-2013)', 'collections&url=red', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Revenge of the Nerds (1984-1987)', 'collections&url=revengeofthenerds', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Riddick (2000-2013)', 'collections&url=riddick', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Ride Along (2014-2016)', 'collections&url=ridealong', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Ring (2002-2017)', 'collections&url=thering', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('RoboCop (1987-1993)', 'collections&url=robocop', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Rocky (1976-2015)', 'collections&url=rocky', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Romancing the Stone (1984-1985)', 'collections&url=romancingthestone', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Rush Hour (1998-2007)', 'collections&url=rushhour', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Santa Clause (1994-2006)', 'collections&url=santaclause', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Saw (2004-2010)', 'collections&url=saw', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Sex and the City (2008-2010)', 'collections&url=sexandthecity', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Shaft (1971-2000)', 'collections&url=shaft', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Shanghai Noon (2000-2003)', 'collections&url=shanghainoon', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Sin City (2005-2014)', 'collections&url=sincity', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Sinister (2012-2015)', 'collections&url=sinister', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Sister Act (1995-1993)', 'collections&url=sisteract', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Smokey and the Bandit (1977-1986)', 'collections&url=smokeyandthebandit', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Speed (1994-1997)', 'collections&url=speed', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Stakeout (1987-1993)', 'collections&url=stakeout', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Star Trek (1979-2016)', 'collections&url=startrek', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Star Wars (1977-2019)', 'collections&url=starwars', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Sting (1973-1983)', 'collections&url=thesting', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Taken (2008-2014)', 'collections&url=taken', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Taxi (1998-2007)', 'collections&url=taxi', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Ted (2012-2015)', 'collections&url=ted', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Teen Wolf (1985-1987)', 'collections&url=teenwolf', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Terminator (1984-2015)', 'collections&url=terminator', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Terms of Endearment (1983-1996)', 'collections&url=termsofendearment', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Texas Chainsaw Massacre (1974-2013)', 'collections&url=texaschainsawmassacre', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Thing (1982-2011)', 'collections&url=thething', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Thomas Crown Affair (1968-1999)', 'collections&url=thomascrownaffair', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Transformers (2002-2017)', 'collections&url=transformers', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Transporter (2002-2015)', 'collections&url=transporter', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Tron (1982-2010)', 'collections&url=tron', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Twilight (2008-2012)', 'collections&url=twilight', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Under Siege (1992-1995)', 'collections&url=undersiege', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Underworld (2003-2016)', 'collections&url=underworld', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Universal Soldier (1992-2012)', 'collections&url=universalsoldier', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Wall Street (1987-2010)', 'collections&url=wallstreet', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Waynes World (1992-1993)', 'collections&url=waynesworld', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Weekend at Bernies (1989-1993)', 'collections&url=weekendatbernies', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Whole Nine Yards (2000-2004)', 'collections&url=wholenineyards', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('X-Files (1998-2008)', 'collections&url=xfiles', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('xXx (2002-2005)', 'collections&url=xxx', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Young Guns (1988-1990)', 'collections&url=youngguns', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Zoolander (2001-2016)', 'collections&url=zoolander', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Zorro (1998-2005)', 'collections&url=zorro', 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.endDirectory()


	def collection_martial_arts(self):
		self.addDirectoryItem('All Movies', 'collections&url=martialartsmovies', 'boxsets.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('By Actors', 'collection_martial_arts_actors', 'people.png', 'DefaultVideoPlaylists.png')
		self.endDirectory()


	def collection_martial_arts_actors(self):
		self.addDirectoryItem('Brandon Lee', 'collections&url=brandonlee', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Bruce Lee', 'collections&url=brucelee2', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Chuck Norris', 'collections&url=chucknorris', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Chow Yun-Fat', 'collections&url=chowyunfat', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Donnie Yen', 'collections&url=donnieyen', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Gary Daniels', 'collections&url=garydaniels', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Jackie Chan', 'collections&url=jackiechan', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Jason Statham', 'collections&url=jasonstatham', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Jean-Claude Van Damme', 'collections&url=vandamme', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Jet Li', 'collections&url=jetli', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Mark Dacascos', 'collections&url=markdacascos', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Michael Jai White', 'collections&url=michaeljaiwhite', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Philip Ng', 'collections&url=philipng', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Rain', 'collections&url=rain', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Robin Shou', 'collections&url=robinshou', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Scott Adkins', 'collections&url=scottadkins', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Steven Seagal', 'collections&url=stevenseagal', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Tiger Chen', 'collections&url=tigerchen', 'people.png', 'DefaultActor.png')
		self.addDirectoryItem('Tony Jaa', 'collections&url=tonyjaa', 'people.png', 'DefaultActor.png')
		self.endDirectory()


	def collectionKids(self):
		self.addDirectoryItem('Disney Collection', 'collections&url=disneymovies', 'collectiondisney.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Kids Boxset Collection', 'collectionBoxsetKids', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Kids Movie Collection', 'collections&url=kidsmovies', 'collectionkids.png', 'DefaultVideoPlaylists.png')
		self.endDirectory()


	def collectionBoxsetKids(self):
		self.addDirectoryItem('101 Dalmations (1961-2003)', 'collections&url=onehundredonedalmations', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Addams Family (1991-1998)', 'collections&url=addamsfamily', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Aladdin (1992-1996)', 'collections&url=aladdin', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Alvin and the Chipmunks (2007-2015)', 'collections&url=alvinandthechipmunks', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Atlantis (2001-2003)', 'collections&url=atlantis', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Babe (1995-1998)', 'collections&url=babe', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Balto (1995-1998)', 'collections&url=balto', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bambi (1942-2006)', 'collections&url=bambi', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Beauty and the Beast (1991-2017)', 'collections&url=beautyandthebeast', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Beethoven (1992-2014)', 'collections&url=beethoven', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Brother Bear (2003-2006)', 'collections&url=brotherbear', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Cars (2006-2017)', 'collections&url=cars', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Cats & Dogs (2001-2010)', 'collections&url=catsanddogs', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Cinderella (1950-2007)', 'collections&url=cinderella', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Cloudy With a Chance of Meatballs (2009-2013)', 'collections&url=cloudywithachanceofmeatballs', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Despicable Me (2010-2015)', 'collections&url=despicableme', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Finding Nemo (2003-2016)', 'collections&url=findingnemo', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Fox and the Hound (1981-2006)', 'collections&url=foxandthehound', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Free Willy (1993-2010)', 'collections&url=freewilly', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Ghostbusters (1984-2016)', 'collections&url=ghostbusters', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Gremlins (1984-2016)', 'collections&url=gremlins', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Happy Feet (2006-2011)', 'collections&url=happyfeet', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Harry Potter (2001-2011)', 'collections&url=harrypotter', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Home Alone (1990-2012)', 'collections&url=homealone', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Homeward Bound (1993-1996)', 'collections&url=homewardbound', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Honey, I Shrunk the Kids (1989-1997)', 'collections&url=honeyishrunkthekids', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hotel Transylvania (2012-2015)', 'collections&url=hoteltransylvania', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('How to Train Your Dragon (2010-2014)', 'collections&url=howtotrainyourdragon', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hunchback of Notre Dame (1996-2002)', 'collections&url=hunchbackofnotredame', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Ice Age (2002-2016)', 'collections&url=iceage', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jurassic Park (1993-2021)', 'collections&url=jurassicpark', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Kung Fu Panda (2008-2016)', 'collections&url=kungfupanda', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Lady and the Tramp (1955-2001)', 'collections&url=ladyandthetramp', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Lilo and Stitch (2002-2006)', 'collections&url=liloandstitch', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Madagascar (2005-2014)', 'collections&url=madagascar', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Monsters Inc (2001-2013)', 'collections&url=monstersinc', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Mulan (1998-2004)', 'collections&url=mulan', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Narnia (2005-2010)', 'collections&url=narnia', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('New Groove (2000-2005)', 'collections&url=newgroove', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Open Season (2006-2015)', 'collections&url=openseason', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Planes (2013-2014)', 'collections&url=planes', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Pocahontas (1995-1998)', 'collections&url=pocahontas', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Problem Child (1990-1995)', 'collections&url=problemchild', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Rio (2011-2014)', 'collections&url=rio', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Sammys Adventures (2010-2012)', 'collections&url=sammysadventures', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Scooby-Doo (2002-2014)', 'collections&url=scoobydoo', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Short Circuit (1986-1988)', 'collections&url=shortcircuit', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Shrek (2001-2011)', 'collections&url=shrek', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('SpongeBob SquarePants (2004-2017)', 'collections&url=spongebobsquarepants', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Spy Kids (2001-2011)', 'collections&url=spykids', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Stuart Little (1999-2002)', 'collections&url=stuartlittle', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Tarzan (1999-2016)', 'collections&url=tarzan', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Teenage Mutant Ninja Turtles (1978-2009)', 'collections&url=teenagemutantninjaturtles', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Jungle Book (1967-2003)', 'collections&url=thejunglebook', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Karate Kid (1984-2010)', 'collections&url=thekaratekid', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Lion King (1994-2016)', 'collections&url=thelionking', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Little Mermaid (1989-1995)', 'collections&url=thelittlemermaid', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Neverending Story (1984-1994)', 'collections&url=theneverendingstory', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Smurfs (2011-2013)', 'collections&url=thesmurfs', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Tooth Fairy (2010-2012)', 'collections&url=toothfairy', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Tinker Bell (2008-2014)', 'collections&url=tinkerbell', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Tom and Jerry (1992-2013)', 'collections&url=tomandjerry', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Toy Story (1995-2014)', 'collections&url=toystory', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('VeggieTales (2002-2008)', 'collections&url=veggietales', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Winnie the Pooh (2000-2005)', 'collections&url=winniethepooh', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Wizard of Oz (1939-2013)', 'collections&url=wizardofoz', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.endDirectory()


	def collectionSuperhero(self):
		self.addDirectoryItem('Avengers (2008-2017)', 'collections&url=avengers', 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Batman (1989-2016)', 'collections&url=batman', 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Captain America (2011-2016)', 'collections&url=captainamerica', 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Dark Knight Trilogy (2005-2013)', 'collections&url=darkknight', 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Fantastic Four (2005-2015)', 'collections&url=fantasticfour', 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hulk (2003-2008)', 'collections&url=hulk', 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Iron Man (2008-2013)', 'collections&url=ironman', 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Spider-Man (2002-2017)', 'collections&url=spiderman', 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Thor (2011-2017)', 'collections&url=thor', 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Superman (1978-2016)', 'collections&url=superman', 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('X-Men (2000-2016)', 'collections&url=xmen', 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.endDirectory()


	def get(self, url, idx=True):
		try:
			try: url = getattr(self, url + '_link')
			except: pass
			try: u = urlparse.urlparse(url).netloc.lower()
			except:
				pass

			if u in self.tmdb_link and '/list/' in url:
				from resources.lib.indexers import tmdb
				self.list = cache.get(tmdb.Movies().tmdb_collections_list, 168, url)
				# self.sort()
				self.list = sorted(self.list, key = lambda k: k['premiered'], reverse = False)

			elif u in self.tmdb_link and not '/list/' in url:
				from resources.lib.indexers import tmdb
				self.list = cache.get(tmdb.Movies().tmdb_list, 168, url)
				# self.sort()
				self.list = sorted(self.list, key = lambda k: k['premiered'], reverse = False)

			elif u in self.imdb_link and ('/user/' in url or '/list/' in url):
				self.list = cache.get(self.imdb_list, 168, url)
				if idx is True:
					self.worker()
				# self.sort()

			elif u in self.imdb_link:
				self.list = cache.get(self.imdb_list, 168, url)
				if idx is True:
					self.worker()
				# self.sort()

			if idx is True:
				self.movieDirectory(self.list)
			return self.list
		except:
			log_utils.error()
			pass


	def sort(self):
		try:
			attribute = int(control.setting('sort.movies.type'))
			reverse = (int(control.setting('sort.movies.order')) == 1)
			if attribute == 0:
				reverse = False
			if attribute > 0:
				if attribute == 1:
					try:
						self.list = sorted(self.list, key = lambda k: re.sub('(^the |^a |^an )', '', k['title'].lower()), reverse = reverse)
					except:
						self.list = sorted(self.list, key = lambda k: k['title'].lower(), reverse = reverse)
				elif attribute == 2:
					self.list = sorted(self.list, key = lambda k: float(k['rating']), reverse = reverse)
				elif attribute == 3:
					self.list = sorted(self.list, key = lambda k: int(k['votes'].replace(',', '')), reverse = reverse)
				elif attribute == 4:
					for i in range(len(self.list)):
						if 'premiered' not in self.list[i]:
							self.list[i]['premiered'] = ''
							self.list = sorted(self.list, key = lambda k: k['year'], reverse = reverse)
						else:
							self.list = sorted(self.list, key = lambda k: k['premiered'], reverse = reverse)
				elif attribute == 5:
					for i in range(len(self.list)):
						if 'added' not in self.list[i]:
							self.list[i]['added'] = ''
					self.list = sorted(self.list, key = lambda k: k['added'], reverse = reverse)
				elif attribute == 6:
					for i in range(len(self.list)):
						if 'lastplayed' not in self.list[i]:
							self.list[i]['lastplayed'] = ''
					self.list = sorted(self.list, key = lambda k: k['lastplayed'], reverse = reverse)
			elif reverse:
				self.list = reversed(self.list)
		except:
			log_utils.error()
			pass


	def tmdb_sort(self):
		sort = int(control.setting('sort.movies.type'))
		tmdb_sort = 'original_order'
		if sort == 1:
			tmdb_sort = 'title'
		if sort in [2, 3]:
			tmdb_sort = 'vote_average'
		if sort in [4, 5, 6]:
			tmdb_sort = 'release_date'

		tmdb_sort_order = '.asc' if int(control.setting('sort.movies.order')) == 0 else '.desc'
		sort_string = tmdb_sort + tmdb_sort_order
		return sort_string


	def imdb_list(self, url):
		list = []
		try:
			for i in re.findall('date\[(\d+)\]', url):
				url = url.replace('date[%s]' % i, (self.datetime - datetime.timedelta(days = int(i))).strftime('%Y-%m-%d'))

			def imdb_watchlist_id(url):
				return client.parseDOM(client.request(url).decode('iso-8859-1').encode('utf-8'), 'meta', ret='content', attrs = {'property': 'pageId'})[0]

			if url == self.imdbwatchlist_link:
				url = cache.get(imdb_watchlist_id, 8640, url)
				url = self.imdblist_link % url

			result = client.request(url, error=True)
			# result = client.request(url, output = 'extended', error = True)

			result = result.replace('\n', ' ')
			# result = result[0].replace('\n','')
			result = result.decode('iso-8859-1').encode('utf-8')

			items = client.parseDOM(result, 'div', attrs = {'class': '.+? lister-item'}) + client.parseDOM(result, 'div', attrs = {'class': 'lister-item .+?'})
			items += client.parseDOM(result, 'div', attrs = {'class': 'list_item.+?'})
		except:
			return

		next = ''
		try:
			# HTML syntax error, " directly followed by attribute name. Insert space in between. parseDOM can otherwise not handle it.
			result = result.replace('"class="lister-page-next', '" class="lister-page-next')
			# next = client.parseDOM(result, 'a', ret='href', attrs = {'class': 'lister-page-next.+?'})
			next = client.parseDOM(result, 'a', ret='href', attrs = {'class': '.*?lister-page-next.*?'})

			if len(next) == 0:
				next = client.parseDOM(result, 'div', attrs = {'class': 'pagination'})[0]
				next = zip(client.parseDOM(next, 'a', ret='href'), client.parseDOM(next, 'a'))
				next = [i[0] for i in next if 'Next' in i[1]]

			next = url.replace(urlparse.urlparse(url).query, urlparse.urlparse(next[0]).query)
			next = client.replaceHTMLCodes(next)
			next = next.encode('utf-8')
		except:
			next = ''

		for item in items:
			try:
				title = client.parseDOM(item, 'a')[1]
				title = client.replaceHTMLCodes(title)
				try: title = title.encode('utf-8')
				except: pass

				year = client.parseDOM(item, 'span', attrs = {'class': 'lister-item-year.+?'})
				year = re.findall('(\d{4})', year[0])[0]
				year = year.encode('utf-8')

				if int(year) > int((self.datetime).strftime('%Y')): raise Exception()

				try:
					show = '–'.decode('utf-8') in str(year).decode('utf-8') or '-'.decode('utf-8') in str(year).decode('utf-8')
				except:
					show = False
				if show or 'Episode:' in item:
					raise Exception() # Some lists contain TV shows.

				try: mpaa = client.parseDOM(item, 'span', attrs = {'class': 'certificate'})[0]
				except: mpaa = '0'
				if mpaa == '' or mpaa == 'NOT_RATED': mpaa = '0'
				mpaa = mpaa.replace('_', '-')
				mpaa = client.replaceHTMLCodes(mpaa)
				mpaa = mpaa.encode('utf-8')

				imdb = client.parseDOM(item, 'a', ret='href')[0]
				imdb = re.findall('(tt\d*)', imdb)[0]
				imdb = imdb.encode('utf-8')

				# parseDOM cannot handle elements without a closing tag.
				# try: poster = client.parseDOM(item, 'img', ret='loadlate')[0]
				# except: poster = '0'
				try:
					from bs4 import BeautifulSoup
					html = BeautifulSoup(item, "html.parser")
					poster = html.find_all('img')[0]['loadlate']
				except:
					poster = '0'

				if '/nopicture/' in poster: poster = '0'
				poster = re.sub('(?:_SX|_SY|_UX|_UY|_CR|_AL)(?:\d+|_).+?\.', '_SX500.', poster)
				poster = client.replaceHTMLCodes(poster)
				poster = poster.encode('utf-8')

				try:
					genre = client.parseDOM(item, 'span', attrs = {'class': 'genre'})[0]
				except:
					genre = '0'
				genre = ' / '.join([i.strip() for i in genre.split(',')])
				if genre == '': genre = '0'
				genre = client.replaceHTMLCodes(genre)
				genre = genre.encode('utf-8')

				try:
					duration = re.findall('(\d+?) min(?:s|)', item)[-1]
				except:
					duration = '0'
				duration = duration.encode('utf-8')

				rating = '0'
				try: rating = client.parseDOM(item, 'span', attrs = {'class': 'rating-rating'})[0]
				except:
					try: rating = client.parseDOM(rating, 'span', attrs = {'class': 'value'})[0]
					except:
						try: rating = client.parseDOM(item, 'div', ret='data-value', attrs = {'class': '.*?imdb-rating'})[0]
						except: pass
				if rating == '' or rating == '-': rating = '0'
				if rating == '0':
					try:
						rating = client.parseDOM(item, 'span', attrs = {'class': 'ipl-rating-star__rating'})[0]
						if rating == '' or rating == '-': rating = '0'
					except: pass
				rating = client.replaceHTMLCodes(rating)
				rating = rating.encode('utf-8')

				votes = '0'
				try: votes = client.parseDOM(item, 'span', attrs = {'name': 'nv'})[0]
				except:
					try: votes = client.parseDOM(item, 'div', ret='title', attrs = {'class': '.*?rating-list'})[0]
					except:
						try: votes = re.findall('\((.+?) vote(?:s|)\)', votes)[0]
						except: pass
				if votes == '': votes = '0'
				votes = client.replaceHTMLCodes(votes)
				votes = votes.encode('utf-8')

				try:
					director = re.findall('Director(?:s|):(.+?)(?:\||</div>)', item)[0]
				except:
					director = '0'
				director = client.parseDOM(director, 'a')
				director = ' / '.join(director)
				if director == '':
					director = '0'
				director = client.replaceHTMLCodes(director)
				director = director.encode('utf-8')

				plot = '0'
				try:
					plot = client.parseDOM(item, 'p', attrs = {'class': 'text-muted'})[0]
				except:
					try:
						plot = client.parseDOM(item, 'div', attrs = {'class': 'item_description'})[0]
					except:
						pass
				plot = plot.rsplit('<span>', 1)[0].strip()
				plot = re.sub('<.+?>|</.+?>', '', plot)
				if plot == '':
					plot = '0'
				if plot == '0':
					try:
						plot = client.parseDOM(item, 'div', attrs = {'class': 'lister-item-content'})[0]
						plot = re.sub('<p\s*class="">', '<p class="plot_">', plot)
						plot = client.parseDOM(plot, 'p', attrs = {'class': 'plot_'})[0]
						plot = re.sub('<.+?>|</.+?>', '', plot)
						if plot == '': plot = '0'
					except:
						pass
				plot = client.replaceHTMLCodes(plot)
				plot = plot.encode('utf-8')

				list.append({'title': title, 'originaltitle': title, 'year': year, 'genre': genre, 'duration': duration, 'rating': rating,
											'votes': votes, 'mpaa': mpaa, 'director': director, 'writer': '0', 'plot': plot, 'tagline': '0', 'imdb': imdb,
											'tmdb': '0', 'tvdb': '0', 'poster': poster, 'fanart': '0', 'next': next})
			except:
				log_utils.error()
				pass

		return list


	def worker(self, level=1):
		try:
			if self.list is None or self.list == []:
				return
			self.meta = []
			total = len(self.list)

			for i in range(0, total):
				self.list[i].update({'metacache': False})

			self.list = metacache.fetch(self.list, self.lang, self.user)

			for r in range(0, total, 40):
				threads = []
				for i in range(r, r + 40):
					# if i <= total: # this is wrong loop counts 0 but len() does not
					if i < total:
						threads.append(workers.Thread(self.super_imdb_info, i))
				[i.start() for i in threads]
				[i.join() for i in threads]

			if self.meta:
				metacache.insert(self.meta)

			self.list = [i for i in self.list if (i['imdb'] and i['tmdb'] != '0')]
		except:
			log_utils.error()


	def super_imdb_info(self, i):
		try:
			if self.list[i]['metacache'] is True:
				return

			imdb = self.list[i]['imdb'] or '0'
			tmdb = self.list[i]['tmdb'] or '0'
			id = (self.list[i]['title'].lower() + '-' + self.list[i]['year']) if imdb == '0' else imdb

# look into getting rid of this and replace with tmdb.Movies().get_details() to cut down from 2 api calls to 1
# maybe issue with using tmdb_id vs. imdb as some list do not contain tmdb_id
			# item = trakt.getMovieSummary(id=imdb)
			item = trakt.getMovieSummary(id)

			title = item.get('title')

			originaltitle = title

			if 'year' not in self.list[i] or self.list[i]['year'] == '0':
				year = str(item.get('year', '0'))
			else:
				year = self.list[i]['year']

			if imdb == '0' or imdb is None:
				imdb = item.get('ids', {}).get('imdb', '0')
				if imdb == '' or imdb is None or imdb == 'None':
					imdb = '0'

			if tmdb == '0' or tmdb is None:
				tmdb = str(item.get('ids', {}).get('tmdb', 0))
				if tmdb == '' or tmdb is None or tmdb == 'None':
					tmdb = '0'

			if 'premiered' not in self.list[i] or self.list[i]['premiered'] == '0':
				premiered = item.get('released', '0')
			else:
				premiered = self.list[i]['premiered']

			if 'genre' not in self.list[i] or self.list[i]['genre'] == '0' or self.list[i]['genre'] == 'NA':
				genre = []
				for x in item['genres']:
					genre.append(x.title())
				if genre == []: genre = 'NA'
			else:
				genre = self.list[i]['genre']

			if 'duration' not in self.list[i] or self.list[i]['duration'] == '0':
				duration = str(item.get('runtime', '0'))
			else:
				duration = self.list[i]['duration']

			if 'rating' not in self.list[i] or self.list[i]['rating'] == '0':
				rating = str(item.get('rating', '0'))
			else:
				rating = self.list[i]['rating']

			if 'votes' not in self.list[i] or self.list[i]['votes'] == '0':
				votes = str(format(int(item.get('votes', '0')),',d'))
			else:
				votes = self.list[i]['votes']

			if 'mpaa' not in self.list[i] or self.list[i]['mpaa'] == '0' or self.list[i]['mpaa'] == 'NR':
				mpaa = item.get('certification', '0')
			else:
				mpaa = self.list[i]['mpaa']

			if 'tagline' not in self.list[i] or self.list[i]['tagline'] == '0':
				tagline = item.get('tagline', '0')
			else:
				tagline = self.list[i]['tagline']

			if 'plot' not in self.list[i] or self.list[i]['plot'] == '0':
				plot = item.get('overview', '0')
			else:
				plot = self.list[i]['plot']
			try: plot = plot.encode('utf-8')
			except: pass

#########################################
			from resources.lib.indexers.tmdb import Movies
			tmdb_Item = cache.get(Movies().get_details, 168, tmdb, imdb)

			castandart = []
			director = writer = '0'
			poster3 = fanart3 = '0'
			try:
				if tmdb_Item is None:
					raise Exception()
				for person in tmdb_Item['credits']['cast']:
					try:
						try:
							castandart.append({'name': person['name'].encode('utf-8'), 'role': person['character'].encode('utf-8'), 'thumbnail': ((self.tmdb_poster + person.get('profile_path')) if person.get('profile_path') is not None else '0')})
						except:
							castandart.append({'name': person['name'], 'role': person['character'], 'thumbnail': ((self.tmdb_poster + person.get('profile_path')) if person.get('profile_path') is not None else '0')})
					except:
						castandart = []
					if len(castandart) == 150: break

				for person in tmdb_Item['credits']['crew']:
					if 'Director' in person['job']:
						director = ', '.join([director['name'].encode('utf-8') for director in tmdb_Item['credits']['crew'] if director['job'].lower() == 'director'])
					if person['job'] in ['Writer', 'Screenplay', 'Author', 'Novel']:
						writer = ', '.join([writer['name'].encode('utf-8') for writer in tmdb_Item['credits']['crew'] if writer['job'].lower() in ['writer', 'screenplay', 'author', 'novel']])

				poster3 = '%s%s' % (self.tmdb_poster, tmdb_Item['poster_path']) if tmdb_Item['poster_path'] else '0'
				fanart3 = '%s%s' % (self.tmdb_fanart, tmdb_Item['backdrop_path']) if tmdb_Item['backdrop_path'] else '0'
			except:
				pass
########################################

			try:
				if self.lang == 'en' or self.lang not in item.get('available_translations', [self.lang]):
					raise Exception()
				trans_item = trakt.getMovieTranslation(imdb, self.lang, full = True)

				title = trans_item.get('title') or title
				tagline = trans_item.get('tagline') or tagline
				plot = trans_item.get('overview') or plot
			except:
				log_utils.error()
				pass

			item = {'title': title, 'originaltitle': originaltitle, 'year': year, 'imdb': imdb, 'tmdb': tmdb, 'premiered': premiered,
						'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'director': director,
						'writer': writer, 'castandart': castandart, 'plot': plot, 'tagline': tagline, 'poster2': '0', 'poster3': poster3,
						'banner': '0', 'banner2': '0', 'fanart2': '0', 'fanart3': fanart3, 'clearlogo': '0', 'clearart': '0', 'landscape': '0',
						'discart': '0', 'metacache': False}

			meta = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': '0', 'lang': self.lang, 'user': self.user, 'item': item}

			if self.disable_fanarttv != 'true':
				from resources.lib.indexers import fanarttv
				extended_art = cache.get(fanarttv.get_movie_art, 168, imdb, tmdb)
				if extended_art is not None:
					item.update(extended_art)
					meta.update(item)

			if item.get('landscape', '0') == '0':
				item.update({'landscape': fanart3})
				meta.update(item)

			item = dict((k, v) for k, v in item.iteritems() if v != '0')
			self.list[i].update(item)
			self.meta.append(meta)
		except:
			pass


	def movieDirectory(self, items, next=True):
		if items is None or len(items) == 0: 
			control.idle()
			control.notification(title = 32000, message = 33049, icon = 'INFO', sound=notificationSound)
			sys.exit()

		settingFanart = control.setting('fanart')

		addonPoster = control.addonPoster()
		addonFanart = control.addonFanart()
		addonBanner = control.addonBanner()

		indicators = playcount.getMovieIndicators()

		isPlayable = 'false'
		if 'plugin' not in control.infoLabel('Container.PluginName'):
			isPlayable = 'true'
		elif control.setting('hosts.mode') != '1' :
			isPlayable = 'true'

		if control.setting('hosts.mode') == '2':
			playbackMenu = control.lang(32063).encode('utf-8')
		else:
			playbackMenu = control.lang(32064).encode('utf-8')

		if trakt.getTraktIndicatorsInfo() is True:
			watchedMenu = control.lang(32068).encode('utf-8')
			unwatchedMenu = control.lang(32069).encode('utf-8')
		else:
			watchedMenu = control.lang(32066).encode('utf-8')
			unwatchedMenu = control.lang(32067).encode('utf-8')

		playlistManagerMenu = control.lang(35522).encode('utf-8')
		queueMenu = control.lang(32065).encode('utf-8')
		traktManagerMenu = control.lang(32070).encode('utf-8')
		addToLibrary = control.lang(32551).encode('utf-8')

		for i in items:
			try:
				imdb, tmdb, title, year = i.get('imdb', '0'), i.get('tmdb', '0'), i['title'], i.get('year', '0')
				# try:
					# title = i['originaltitle']
				# except:
					# title = i['title']

				label = '%s (%s)' % (title, year)

				sysname = urllib.quote_plus(label)
				systitle = urllib.quote_plus(title)

				meta = dict((k,v) for k, v in i.iteritems() if v != '0')
				meta.update({'code': imdb, 'imdbnumber': imdb, 'imdb_id': imdb})
				meta.update({'tmdb_id': tmdb})
				meta.update({'mediatype': 'movie'})
				meta.update({'trailer': '%s?action=trailer&name=%s' % (sysaddon, sysname)})

				# Some descriptions have a link at the end that. Remove it.
				try:
					plot = meta['plot']
					index = plot.rfind('See full summary')
					if index >= 0:
						plot = plot[:index]
					plot = plot.strip()
					if re.match('[a-zA-Z\d]$', plot): plot += ' ...'
					meta['plot'] = plot
				except:
					pass

				try: meta.update({'duration': str(int(meta['duration']) * 60)})
				except: pass
				try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
				except: pass
				try: meta.update({'year': int(meta['year'])})
				except: pass

				poster1 = meta.get('poster')
				poster2 = meta.get('poster2')
				poster3 = meta.get('poster3')
				poster = poster3 or poster2 or poster1 or addonPoster

				fanart = ''
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
				discart = meta.get('discart')

				art = {}
				art.update({'icon': icon, 'thumb': thumb, 'banner': banner, 'poster': poster, 'fanart': fanart,
								'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape, 'discart': discart})

####-Context Menu and Overlays-####
				cm = []
				if self.traktCredentials is True:
					cm.append((traktManagerMenu, 'RunPlugin(%s?action=traktManager&name=%s&imdb=%s)' % (sysaddon, sysname, imdb)))

				try:
					overlay = int(playcount.getMovieOverlay(indicators, imdb))
					watched = (overlay == 7)

					if watched:
						cm.append((unwatchedMenu, 'RunPlugin(%s?action=moviePlaycount&name=%s&imdb=%s&query=6)' % (sysaddon, sysname, imdb)))
						meta.update({'playcount': 1, 'overlay': 7})
						# lastplayed = trakt.watchedMoviesTime(imdb)
						# meta.update({'lastplayed': lastplayed})
					else:
						cm.append((watchedMenu, 'RunPlugin(%s?action=moviePlaycount&name=%s&imdb=%s&query=7)' % (sysaddon, sysname, imdb)))
						meta.update({'playcount': 0, 'overlay': 6})
				except:
					pass

				sysmeta = urllib.quote_plus(json.dumps(meta))
				sysart = urllib.quote_plus(json.dumps(art))

				url = '%s?action=play&title=%s&year=%s&imdb=%s&meta=%s&t=%s' % (sysaddon, systitle, year, imdb, sysmeta, self.systime)
				sysurl = urllib.quote_plus(url)

				cm.append((playlistManagerMenu, 'RunPlugin(%s?action=playlistManager&name=%s&url=%s&meta=%s&art=%s)' % (sysaddon, sysname, sysurl, sysmeta, sysart)))
				cm.append((queueMenu, 'RunPlugin(%s?action=queueItem&name=%s)' % (sysaddon, sysname)))
				cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))

				if control.setting('hosts.mode') == '1':
					cm.append(('Rescrape Item', 'RunPlugin(%s?action=reScrape&title=%s&year=%s&imdb=%s&meta=%s&t=%s)' % (sysaddon, systitle, year, imdb, sysmeta, self.systime)))

				elif control.setting('hosts.mode') != '1':
					cm.append(('Rescrape Item', 'PlayMedia(%s?action=reScrape&title=%s&year=%s&imdb=%s&meta=%s&t=%s)' % (sysaddon, systitle, year, imdb, sysmeta, self.systime)))

				if control.setting('library.service.update') == 'true':
					cm.append((addToLibrary, 'RunPlugin(%s?action=movieToLibrary&name=%s&title=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, sysname, systitle, year, imdb, tmdb)))
				cm.append(('Find similar', 'ActivateWindow(10025,%s?action=movies&url=https://api.trakt.tv/movies/%s/related,return)' % (sysaddon, imdb)))
				cm.append((control.lang(32610).encode('utf-8'), 'RunPlugin(%s?action=clearAllCache&opensettings=false)' % sysaddon))
				cm.append(('[COLOR red]Venom Settings[/COLOR]', 'RunPlugin(%s?action=openSettings)' % sysaddon))
####################################

				item = control.item(label=label)

				if 'castandart' in i:
					item.setCast(i['castandart'])

				item.setArt(art)
				item.setProperty('IsPlayable', isPlayable)
				item.setInfo(type='video', infoLabels=control.metadataClean(meta))
				video_streaminfo = {'codec': 'h264'}
				item.addStreamInfo('video', video_streaminfo)
				item.addContextMenuItems(cm)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
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
					page = '  [I](%s)[/I]' % str(((start - 1) / self.count) + 1)
				else:
					page = url_params.get('page')
					page = '  [I](%s)[/I]' % page

				nextMenu = '[COLOR skyblue]' + nextMenu + page + '[/COLOR]'

				url = '%s?action=collections&url=%s' % (sysaddon, urllib.quote_plus(url))

				item = control.item(label=nextMenu)
				icon = control.addonNext()
				item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon})
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except:
				log_utils.error()
				pass

		control.content(syshandle, 'movies')
		control.directory(syshandle, cacheToDisc=True)
		views.setView('movies', {'skin.estuary': 55, 'skin.confluence': 500})


	def addDirectoryItem(self, name, query, thumb, icon, context=None, queue=False, isAction=True, isFolder=True):
		try:
			if type(name) is str or type(name) is unicode:
				name = str(name)
			if type(name) is int:
				name = control.lang(name).encode('utf-8')
		except:
			log_utils.error()

		url = '%s?action=%s' % (sysaddon, query) if isAction else query

		artPath = control.artPath()
		thumb = os.path.join(artPath, thumb) if artPath is not None else icon

		cm = []
		if queue is True:
			cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

		if context is not None:
			cm.append((control.lang(context[0]).encode('utf-8'), 'RunPlugin(%s?action=%s)' % (sysaddon, context[1])))

		cm.append((control.lang(32610).encode('utf-8'), 'RunPlugin(%s?action=clearAllCache&opensettings=false)' % sysaddon))
		cm.append(('[COLOR red]Venom Settings[/COLOR]', 'RunPlugin(%s?action=openSettings)' % sysaddon))

		item = control.item(label=name)
		item.setArt({'icon': icon, 'poster': thumb, 'thumb': thumb, 'fanart': control.addonFanart(), 'banner': thumb})

		item.addContextMenuItems(cm)
		control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)


	def endDirectory(self):
		control.content(syshandle, 'addons')
		control.directory(syshandle, cacheToDisc=True)
