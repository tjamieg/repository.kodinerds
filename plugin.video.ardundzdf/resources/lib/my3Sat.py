# -*- coding: utf-8 -*-
################################################################################
#				my3Sat.py - Teil von Kodi-Addon-ARDundZDF
#							Start Juni 2019
#			Migriert von Plex-Plugin-3Sat_Mediathek, V0.5.9
################################################################################
# 	dieses Modul nutzt die Webseiten der Mediathek ab https://www.3sat.de,
#	Seiten werden im html-format, teils. json ausgeliefert
#	Stand: 15.03.2020
#
#	04.11.2019 Migration Python3  Python3 Modul future
#	18.11.2019 Migration Python3 Modul kodi_six + manuelle Anpassungen
# 	

# Python3-Kompatibilität:
from __future__ import absolute_import		# sucht erst top-level statt im akt. Verz. 
from __future__ import division				# // -> int, / -> float
from __future__ import print_function		# PYTHON2-Statement -> Funktion
from kodi_six import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs

# o. Auswirkung auf die unicode-Strings in PYTHON3:
from kodi_six.utils import py2_encode, py2_decode

import os, sys, subprocess
PYTHON2 = sys.version_info.major == 2
PYTHON3 = sys.version_info.major == 3
if PYTHON2:
	from urllib import quote, unquote, quote_plus, unquote_plus, urlencode, urlretrieve
	from urllib2 import Request, urlopen, URLError 
	from urlparse import urljoin, urlparse, urlunparse, urlsplit, parse_qs
elif PYTHON3:
	from urllib.parse import quote, unquote, quote_plus, unquote_plus, urlencode, urljoin, urlparse, urlunparse, urlsplit, parse_qs
	from urllib.request import Request, urlopen, urlretrieve
	from urllib.error import URLError

# Python
import string, re
import  json, ssl		
import datetime, time

# Addonmodule + Funktionsziele (util_imports.py)
# import ardundzdf reicht nicht für thread_getpic
from ardundzdf import *					# -> get_query, ParseMasterM3u, test_downloads, Parseplaylist, 
										# thread_getpic, ZDF_SlideShow
from resources.lib.util import *


# Globals
ICON_TV3Sat 			= 'tv-3sat.png'
ICON_MAIN_ARD 			= 'ard-mediathek.png'			
ICON_MAIN_TVLIVE 		= 'tv-livestreams.png'		
			
ICON_SEARCH 			= 'ard-suche.png'						
ICON_DIR_FOLDER			= "Dir-folder.png"
ICON_SPEAKER 			= "icon-speaker.png"
ICON_MEHR 				= "icon-mehr.png"

DreiSat_BASE 	= 'https://www.3sat.de'
DreiSat_AZ 		= "https://www.3sat.de/sendungen-a-z"
DreiSat_Verpasst= "https://www.3sat.de/programm?airtimeDate=%s"   		# Format %s: 2019-05-22 (Y-m-d) 
DreiSat_Suche	= "https://www.3sat.de/suche?q=%s&synth=true&attrs=&contentTypes=episode" 	# ganze Sendungen

ADDON_ID      	= 'plugin.video.ardundzdf'
SETTINGS 		= xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    	= SETTINGS.getAddonInfo('name')
SETTINGS_LOC  	= SETTINGS.getAddonInfo('profile')
ADDON_PATH    	= SETTINGS.getAddonInfo('path')	# Basis-Pfad Addon
ADDON_VERSION 	= SETTINGS.getAddonInfo('version')
PLUGIN_URL 		= sys.argv[0]				# plugin://plugin.video.ardundzdf/
HANDLE			= int(sys.argv[1])
FANART = xbmc.translatePath('special://home/addons/' + ADDON_ID + '/fanart.jpg')
ICON = xbmc.translatePath('special://home/addons/' + ADDON_ID + '/icon.png')

ARDStartCacheTime = 300						# 5 Min.	
USERDATA		= xbmc.translatePath("special://userdata")
ADDON_DATA		= os.path.join("%sardundzdf_data") % USERDATA

if 	check_AddonXml('"xbmc.python" version="3.0.0"'):
	ADDON_DATA	= os.path.join("%s", "%s", "%s") % (USERDATA, "addon_data", ADDON_ID)
WATCHFILE		= os.path.join("%s/merkliste.xml") % ADDON_DATA

DICTSTORE 		= os.path.join("%s/Dict") % ADDON_DATA			# hier nur DICTSTORE genutzt
SLIDESTORE 		= os.path.join("%s/slides") % ADDON_DATA
SUBTITLESTORE 	= os.path.join("%s/subtitles") % ADDON_DATA
TEXTSTORE 		= os.path.join("%s/Inhaltstexte") % ADDON_DATA

DEBUG			= SETTINGS.getSetting('pref_info_debug')
NAME			= 'ARD und ZDF'

#----------------------------------------------------------------
# Aufrufer: Haupt-PRG, Menü Main
#
def Main_3Sat(name):
	PLog('Main_3Sat:'); 
	PLog(name)
				
	li = xbmcgui.ListItem()
	li = home(li, ID=NAME)				# Home-Button
	PLog("li:" + str(li))						
			
	title="Suche in 3Sat-Mediathek"		
	fparams="&fparams={'first': 'True','path': ''}" 
	addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Search", fanart=R('3sat.png'), 
		thumb=R('zdf-suche.png'), fparams=fparams)
			
	epg = get_epg()
	if epg:
		epg = 'Jetzt in 3sat: ' + epg
	title = '3Sat-Livestream'
	title=py2_encode(title); epg=py2_encode(epg);
	fparams="&fparams={'name': '%s', 'epg': '%s'}" % (quote(title), quote(epg))
	addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Live", 
		fanart=R('3sat.png'), thumb=R(ICON_MAIN_TVLIVE), tagline=epg, fparams=fparams)
	
	title = 'Verpasst'
	summ = 'aktuelle Beiträge eines Monats - nach Datum geordnet'
	fparams="&fparams={'title': 'Sendung verpasst'}"
	addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Verpasst", 
		fanart=R('3sat.png'), thumb=R('zdf-sendung-verpasst.png'), summary=summ, fparams=fparams)
	
	title = "Sendungen A-Z | 0-9"	
	summ = "Sendereihen - alphabetisch geordnet"
	DreiSat_AZ 		= "https://www.3sat.de/sendungen-a-z"			# geht hier nach epg verloren	
	title=py2_encode(title); DreiSat_AZ=py2_encode(DreiSat_AZ);
	fparams="&fparams={'name': '%s', 'path': '%s'}"	% (quote(title), quote(DreiSat_AZ))
	addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.SendungenAZlist", 
		fanart=R('3sat.png'), thumb=R('zdf-sendungen-az.png'),  summary=summ, fparams=fparams)
												
	title = "Rubriken"
	path = 'https://www.3sat.de/themen'
	summ = "Dokumentation, Film, Gesellschaft, Kabarett, Kultur, Wissen"
	title=py2_encode(title); path=py2_encode(path);
	fparams="&fparams={'name': '%s', 'path': '%s'}"	% (quote(title), quote(path))
	addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Rubriken", 
		fanart=R('3sat.png'), thumb=R('zdf-rubriken.png'), summary=summ, fparams=fparams)

	title = 'Bildgalerien 3sat'	
	fparams="&fparams={}" 
	addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Bilder3sat",
		fanart=R('3sat.png'), thumb=R('zdf-bilderserien.png'), fparams=fparams)

	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)
		 		
####################################################################################################
# Hinweis: wir suchen in 3Sat_XML_FULL = alle Mediathekinhalte
#	Die Sucheingabe kann mehrere Wörter enthalten, getrennt durch Blanks (ODER-Suche) 
#	Gesucht wird in Titel + Beschreibung
#
# Suche - Verarbeitung der Eingabe. Mediathek listet Suchergebnisse tageweise
def Search(first, path, query=''):
	PLog('Search:'); PLog(first);	
	if 	query == '':	
		query = get_query(channel='ZDF')
	if  query == None or query.strip() == '':
		return ""
		
	PLog(query)

	name = 'Suchergebnis zu: ' + unquote(query)
		
	if first == 'True':								# query nur beim 1. Aufruf injizieren, nicht bei 'mehr' 
		path =  DreiSat_Suche % quote(py2_encode(query))
		path = path + "&page=1"
	PLog(path); 										# Bsp. https://www.3sat.de/suche?q=brexit&synth=true&attrs=&page=2
	page, msg = get_page(path=path)	
	if page == '':			
		msg1 = "Fehler in Search"
		msg2 = msg
		PLog(msg1)
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, msg2, '')
		return li	
		
	rubriken =  blockextract('<picture class="">', page)	
	cnt = stringextract('class="search-number">', '<', page) # Anzahl Treffer
	
	li = xbmcgui.ListItem()
	li = home(li, ID='3Sat')										# Home-Button

	query_unqoute = (query.replace('%252B', ' ').replace('+', ' ')) # quotiertes ersetzen 
	if len(rubriken) == 0 or cnt == '':						# kein Treffer
		msg1 = 'Leider kein Treffer (mehr) zu '  + unquote(query)
		PLog(msg1)
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, '', '')
		return li	
	
	new_title = "%s Treffer zu >%s<" % (cnt, query)
	li = Sendereihe_Sendungen(li, path=path, title=new_title)
	
	# auf mehr prüfen:
	if test_More(page=page):						# Test auf weitere Seiten (class="loader)
		plist = path.split('&page=')
		pagenr = int(plist[-1])
		new_path = plist[0] + '&page=' + str(pagenr + 1)
		title = "Mehr zu: %s" %  unquote(query)
		summary='Mehr...'
		PLog(new_path)
		
		new_path=py2_encode(new_path); query=py2_encode(query);
		fparams="&fparams={'first': 'False', 'path': '%s', 'query': '%s'}" % (quote(new_path), 
			quote(query))
		addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Search", fanart=R('3sat.png'), 
			thumb=R(ICON_MEHR), summary='Mehr...', fparams=fparams)
		
	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)
		
#------------ 
# A-Z Liste der Buchstaben (mit Markierung 'ohne Beiträge')
def SendungenAZlist(name, path):				# 
	PLog('SendungenAZlist: ' + name)
	DreiSat_AZ 		= "https://www.3sat.de/sendungen-a-z"			# geht hier nach epg verloren	
	
	li = xbmcgui.ListItem()
	li = home(li, ID='3Sat')										# Home-Button

	page, msg = get_page(path)						
	if page == '':			
		msg1 = "Fehler in SendungenAZlist"
		msg2 = msg
		PLog(msg1)
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, msg2, '')
		return li	
	
	liste = blockextract('<ul class="letter-list"', page)  # 1 x
	content = blockextract('class="item', liste[0])
	
	PLog(len(content))
	for rec in content:
		title	= stringextract('title="', '"', rec)
		href	= stringextract('href="', '"', rec)
		href	= DreiSat_BASE + href
		PLog(title)
		if 'link is-disabled' in rec:							# Button inaktiv
			letter = stringextract('true">', '<', rec)
			title= "Sendungen mit " + letter + ' | ' + u'ohne Beiträge'
			title=py2_encode(title); DreiSat_AZ=py2_encode(DreiSat_AZ);
			fparams="&fparams={'name': '%s', 'path': '%s'}"	% (quote(title), quote(DreiSat_AZ))
			addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.SendungenAZlist", 
				fanart=R('3sat.png'), thumb=R('zdf-sendungen-az.png'), fparams=fparams)			
		else:
			title=py2_encode(title); href=py2_encode(href);
			fparams="&fparams={'name': '%s', 'path': '%s'}"	% (quote(title), quote(href))
			addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.SendungenAZ", 
				fanart=R('3sat.png'), thumb=R('Dir-folder.png'), fparams=fparams)			
			
	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)

#------------ 
# A-Z Liste der Beiträge
#	-> Sendereihe_Sendungen -> get_zdfplayer_content
def SendungenAZ(name, path): 
	PLog('SendungenAZ: ' + name)

	li = xbmcgui.ListItem()
	li = home(li, ID='3Sat')										# Home-Button		
	
	page, msg = get_page(path)	
	if page == '':			
		msg1 = "Fehler in SendungenAZ"
		msg2 = msg
		PLog(msg1)
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, msg2, '')
		return li	
		
	content = blockextract('<picture class="">', page)
	PLog(len(content))
	
	for rec in content:
		img_src =  stringextract('data-srcset="', ' ', rec)	
		rubrik 	= stringextract('<span>', '</span>', rec)
		sub_rubrik = stringextract('ellipsis" >', '<', rec)
		title	= stringextract('clickarea-link">', '</p>', rec)
		href	= stringextract('href="', '"', rec)
		href	= DreiSat_BASE + href
		descr	= stringextract('clickarea-link" >', '<', rec)
		tag 	= rubrik
		if sub_rubrik:
			tag = "%s | %s" % (tag, sub_rubrik)
		tag = cleanhtml(tag)

		title = repl_json_chars(title); descr = repl_json_chars(descr); 
		descr_par =	descr.replace('\n', '||')	
		
		PLog('Satz:')
		PLog(img_src); PLog(rubrik); PLog(title);  PLog(href); PLog(descr);
			
		# Aufruf Sendereihe_Sendungen hier ohne Listitem					
		title=py2_encode(title); href=py2_encode(href);  img_src=py2_encode(img_src);
		fparams="&fparams={'li': '', 'title': '%s', 'path': '%s', 'img': '%s'}" % (quote(title),
			 quote(href), quote(img_src))
		addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Sendereihe_Sendungen", 
			fanart=R('3sat.png'), thumb=img_src, summary=descr, tagline=tag, fparams=fparams)
	
	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)
			
#------------
# 25.05.2019 more-Links nicht mehr verfügbar (javascript-generiert) -
#	more-Links müssem vom Aufrufer (z.B. Search) generiert werden.
def test_More(page):						# Test auf weitere Seiten
	PLog('test_More:')
	if page.find('class="loader"') > 0:		# 2. Seite (z.Z. Seite 1: 0-9, A-K, Seite 2: Rest)
		PLog('True')
		return True	
	else:
		PLog('False')
		return False	
	
	
#------------
def Verpasst(title):	# je 1 Tag - passend zum Webdesign
	PLog('Verpasst:')
	
	li = xbmcgui.ListItem()
	li = home(li, ID='3Sat')										# Home-Button
		
	wlist = list(range(0,30))					# Abstand 1 Tage
	now = datetime.datetime.now()
	for nr in wlist:
		rdate = now - datetime.timedelta(days = nr)
		iDate = rdate.strftime("%d.%m.%Y")		# Formate s. man strftime (3)
		SendDate = rdate.strftime("%Y-%m-%d")	# 3Sat-Format 2019-05-22 (Y-m-d)  	
		iWeekday =  rdate.strftime("%A")
		punkte = '.'
		if nr == 0:
			iWeekday = 'Heute'	
		if nr == 1:
			iWeekday = 'Gestern'	
		iWeekday = transl_wtag(iWeekday)
		iPath = DreiSat_Verpasst % SendDate

		# PLog(iPath); PLog(iDate); PLog(iWeekday);
		title =	"%s | %s" % (iDate, iWeekday)
		title =	iDate + ' | ' + iWeekday
		
		PLog('Satz:')	
		PLog(SendDate); PLog(title); 
		title=py2_encode(title); 
		fparams="&fparams={'SendDate': '%s', 'title': '%s'}" % (SendDate, quote(title))
		addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.SendungenDatum", 
			fanart=R('3sat.png'), thumb=R(ICON_DIR_FOLDER), fparams=fparams)
		
	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)
			
#------------

# Liste Sendungen gewählter Tag
def SendungenDatum(SendDate, title):	
	PLog('SendungenDatum: ' + SendDate)
	
	title_org = title
	li = xbmcgui.ListItem()
	li = home(li, ID='3Sat')										# Home-Button
		
	path =  DreiSat_Verpasst % SendDate
	page, msg = get_page(path=path)	
	
	content = blockextract('<picture class="">', page)
	PLog(len(content))
			
	if len(content) == 0:			
		msg1 = u'leider kein Treffer im ausgewählten Zeitraum'
		PLog(msg1)
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, '', '')
		return li	
		
	mediatype='' 		
	if SETTINGS.getSetting('pref_video_direct') == 'true': # Kennz. Video für Sofortstart 
		mediatype='video'

	for rec in content:
		img_src =  stringextract('data-srcset="', ' ', rec)	
		href	= stringextract('href="', '"', rec)
		if href == '' or '#skiplinks' in href:
			continue
		href	= DreiSat_BASE + href
		sendung	= stringextract('level-6', '</', rec)
		sendung	= sendung.replace('">', ''); sendung = sendung.strip()
		descr	= stringextract('teaser-epg-text">', '</p>', rec)		# mehrere Zeilen
		PLog(descr)
		descr	= cleanhtml(descr); 
		zeit	= stringextract('class="time">', '</', rec)
		dauer	= stringextract('class="label">', '</', rec)
		
		sendung = zeit  + ' | ' + sendung
		tagline = title_org +  ' | ' + zeit
		if dauer:
			tagline = tagline + ' | ' + dauer
					
		title = repl_json_chars(title);
		sendung = repl_json_chars(sendung)
		descr	= unescape(descr);  
		descr = repl_json_chars(descr); 
		descr_par =	descr.replace('\n', '||')	

		PLog('Satz:')
		PLog(img_src);  PLog(href); PLog(sendung); PLog(tagline); PLog(descr); PLog(dauer);
			 
		sendung=py2_encode(sendung); href=py2_encode(href);  img_src=py2_encode(img_src);
		descr_par=py2_encode(descr_par); dauer=py2_encode(dauer)
		fparams="&fparams={'title': '%s', 'path': '%s', 'img_src': '%s', 'summ': '%s', 'dauer': '%s', 'duration': ''}" %\
			(quote(sendung), quote(href), quote(img_src), quote(descr_par), quote(dauer))
		addDir(li=li, label=sendung, action="dirList", dirID="resources.lib.my3Sat.SingleBeitrag", fanart=R('3sat.png'), 
			thumb=img_src, summary=descr, tagline=tagline, fparams=fparams, mediatype=mediatype)
			 					 	
	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)
			
#------------
def transl_month(shortmonth):	# Monatsbez. (3-stellig) -> Zahl 
	month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	val = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
	
	mval = shortmonth
	for i in range (len(month)):
		m = month[i]
		if m == shortmonth:
			mval = val[i]
			break
	return mval

#------------
# Aufrufer: Main_3Sat - Liste der 3Sat-Rubriken (wie Webseite)
# 	
def Rubriken(name, path):
	PLog('Rubriken:')
	
	li = xbmcgui.ListItem()
	li = home(li, ID='3Sat')										# Home-Button		
	
	page, msg = get_page(path)	
	if page == '':			
		msg1 = "Fehler in Rubriken"
		msg2 = msg
		PLog(msg1)
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, msg2, '')
		return li	
		
	rubriken =  blockextract('class="dropdown-link js-rb-click js-track-click"', page)
	PLog(len(rubriken))
	
	i=0; rubrik=[]; 							
	for rec in rubriken:					# Rubriken sammeln	
		title	= stringextract('title="', '"', rec)
		if 'A-Z' in title:
			continue
		href	= DreiSat_BASE + stringextract('href="', '"', rec)
		line 	= title + "|" + href	
		rubrik.append(line)
		i=i+1
	
	rubrik.sort()							# Rubriken sortieren
	img_src = R('Dir-folder.png')
	for rec in rubrik:
		title, href = rec.split('|')
		title=py2_encode(title); href=py2_encode(href); 
		fparams="&fparams={'name': '%s', 'path': '%s'}" % (quote(title), quote(href))
		addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Rubrik_Single", 
			fanart=R('3sat.png'), thumb=img_src, summary='Folgeseiten', fparams=fparams)

	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)

#------------
# Aufrufer: Rubrik - Liste der Themen einer 3Sat-Rubrik, z.B. Film
# rekursiv: zweiter Durchlauf mit thema listet die Sendereihen dieser Rubrik
#			dritter Durchlauf nach thema 'Mehr' (Sendereihe, keine Einzelbeiträge) -	
#				Liste der Sendereihen beim 2. Durchlauf.
def Rubrik_Single(name, path, thema=''):	# Liste der Einzelsendungen zu Sendereihen
	PLog('Rubrik_Single: '+ name)
	PLog("thema: " + thema)
	
	li = xbmcgui.ListItem()
	li = home(li, ID='3Sat')										# Home-Button		
	
	page, msg = get_page(path)	
	if page == '':			
		msg1 = "Fehler in Rubrik_Single"
		msg2 = msg
		PLog(msg1)
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, msg2, '')
		return li	
		
	themen =  blockextract('is-uppercase ">', page)	
	PLog(len(themen))											
	
	if thema == '':									# 1. Durchlauf: Themen der Rubrik name	
		PLog('1. Durchlauf, thema: %s' % thema)						
		img_src = R('Dir-folder.png')			
		for rec in themen:
			title	= stringextract('is-uppercase ">', '<', rec)
			PLog(title)
			# ausschließen: Ende Themen, Mehr, Rechtliches, ..
			if title == '':
				PLog('Ende Themen')
				break
				
			title	= up_low(title)
			summ = "Folgeseiten"
			if 'VIDEOTIPP' in title:
				summ = 'Videotipp(s) der Redaktion'
			title = repl_json_chars(py2_decode(title))			
			PLog('Satz: %s' % title)
		
			title=py2_encode(title); path=py2_encode(path); 
			fparams="&fparams={'name': '%s', 'path': '%s', 'thema': '%s'}" % (quote(title),
				 quote(path), quote(title))
			addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Rubrik_Single", 
				fanart=R('3sat.png'), thumb=img_src, summary=summ, fparams=fparams)
				
		xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)	# Ende 1. Durchlauf
	
	PLog('2. Durchlauf, thema: %s' % thema)	
	content =  blockextract('is-uppercase ">', page)	
	for rec in content:										# 2. Durchlauf: Beiträge zu Thema thema		
		title	= stringextract('is-uppercase ">', '<', rec)
		title 	= repl_json_chars(py2_decode(title))		# dto. 1. Durchlauf
		title	= up_low(title)
		if 	py2_decode(name) in py2_decode(title):			# Bsp. VIDEOTIPP "SEIDENSTRASSE"
			PLog('Thema gefunden: %s' % name)
			page = rec
			PLog(len(rec))
			if 'TV-SENDETERMINE' in name:
				msg1 = 'TV-SENDETERMINE'
				msg2 = u'Bitte das Menü Verpasst verwenden'
				xbmcgui.Dialog().ok(ADDON_NAME, msg1, msg2, '')
				xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)	
			break											# -> Sendereihe_Sendungen	
	
	if up_low("Videotipp") in title:						# 1 oder mehrere Videos am Kopf
		if 'video-carousel-item">' in rec:
			li, cnt = get_video_carousel(li, rec) 			# mehrere Videos am Kopf
		else:									
			li, cnt = get_zdfplayer_content(li, content)	# 1 Video
		xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)
	
	# Auswertung weiterer Inhalte (page = rec)				
	# Kennzeichnungen: Mehr, MEHR, ZUM STöBERN
	# Blockmerkmal'<picture class=""> entscheidet über Ziel:
	#	mit 	-> Rubrik_Single (nur 'ZUM STöBERN', Bsp. Kultur) oder Sendereihe_Sendungen
	#	ohne 	-> Sendereihe_Sendungen ('is-medium lazyload'), Bsp. Rubrik Wissen
	if up_low(name) == 'MEHR' or name == u'ZUM STöBERN': 	# Zusätze Mehr/MEHR oder ZUM STöBERN
		rubriken =  blockextract('<picture class="">', page)
		PLog(len(rubriken))
		if len(rubriken) > 0:
			for rec in rubriken:
				img_src =  stringextract('data-srcset="', ' ', rec)	
				title	= stringextract('clickarea-link">', '</p>', rec)
				href	= stringextract('href="', '"', rec)
				if href.startswith('http') == False:
					href	= DreiSat_BASE + href
				descr	= stringextract('clickarea-link" >', '<', rec)
				
				title = repl_json_chars(title); descr = repl_json_chars(descr); 					
				PLog('Satz:')
				PLog(img_src); PLog(title);  PLog(href); PLog(descr);
				
				if name == 'ZUM STöBERN':					# ähnlich mehr, aber Auswertung als Rubrik
					title=py2_encode(title); href=py2_encode(href); 
					fparams="&fparams={'name': '%s', 'path': '%s'}" % (quote(title), quote(href))
					addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Rubrik_Single", 
						fanart=R('3sat.png'), thumb=img_src, summary='Folgeseiten', fparams=fparams)

				else:										# Mehr: Sendereihen -> Sendereihe_Sendungen"
					title=py2_encode(title); href=py2_encode(href);	 img_src=py2_encode(img_src);							
					fparams="&fparams={'li': '', 'title': '%s', 'path': '%s', 'img': '%s'}" % (quote(title),
						 quote(href), quote(img_src))
					addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Sendereihe_Sendungen", 
						fanart=R('3sat.png'), thumb=img_src, summary=descr, fparams=fparams)
				
			xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)		
				
	# Übergabe Seitenausschnitt rec in page, Reihenfolge in Sendereihe_Sendungen:
	#	 <picture class=""> (hier nicht enthalten), 'is-medium lazyload'
	PLog(len(page))

	li = Sendereihe_Sendungen(li, path, title, page=page)
				
	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)
#------------
# Aufrufer: SendungenAZ mit path aber ohne Listitem, Rubrik_Single mit 
#	page (Seitenausschnitt)
#	Search + Rubrik_Single jew. mit Listitem
#	rekursiv möglich - s. is-clickarea-action (keine Rubriken, aber
#		weiterführender Link.
#
# Achtung: hier wird (nochmal) auf video-carousel-item	+ o--stage-brand
#	geprüft - page ev. vorher begrenzen.
#
def Sendereihe_Sendungen(li, path, title, img='', page=''):		# Liste der Einzelsendungen zu Sendereihen
	PLog('Sendereihe_Sendungen: ' + path)
	PLog(len(page))
	title_org = title
	got_page = False
	if page:
		got_page = True
	
	ret = False									# Default Return  o. endOfDirectory
	if not li:
		ret = True
		li = xbmcgui.ListItem()
		li = home(li, ID='3Sat')										# Home-Button
	
	if page == '':								# Seitenausschnitt vom Aufrufer?
		page, msg = get_page(path=path)	
	
	# 1. Strukturen am Seitenanfang (1 Video doppelt möglich):	
	if 'video-carousel-item' in page:		# Bsp. www.3sat.de/kultur/kulturzeit
		# video-carousel-item-Beiträge auswerten, html-Format, Seitenkopf
		PLog('Struktur video-carousel-item')
		content =  blockextract('video-carousel-item">', page)
		PLog(len(content))
		li, cnt = get_zdfplayer_content(li, content=content)
		
	if 'o--stage-brand' in page:		# Bsp. www.3sat.de/wissen/netz-natur (1 Beitrag)
		# "o--stage-brand-Beiträge auswerten, html-Format, Seitenkopf
		PLog('Struktur o--stage-brand')
		content =   stringextract('o--stage-brand">', '</article>', page)	# ausschneiden
		content =  blockextract('class="artdirect">', page)
		PLog(len(content))
		li, cnt = get_zdfplayer_content(li, content=content)		
	
	# 2. Strukturen nach Seitenanfang (1 Video doppelt möglich)
	PLog('Sendereihe_Sendungen2:')	
	rubriken =  blockextract('<picture class="">', page)
	PLog(len(rubriken))
	
	 									# kein Einzelbeitrag, weiterführender Link?
	# Bsp.: Rubriken/Kabarett/35 JAHRE 3SAT - JUBILÄUMSPROGRAMM
	#	-> rekursiv
	if len(rubriken) == 0 and got_page == True:		
		if 'class="is-clickarea-action' in page:
			PLog('is-clickarea-action:')
			img_src = stringextract('data-srcset="', ' ', page)	
			title 	= stringextract('title="', '"', page)	
			title	= unescape(title)
			href	= stringextract('href="', '"', page)
			if href.startswith('http') == False:
				href	= DreiSat_BASE + href
			descr	= stringextract('paragraph-large ">', '</p>', page)
			
			title=py2_encode(title); href=py2_encode(href);	 img_src=py2_encode(img_src);							
			fparams="&fparams={'li': '', 'title': '%s', 'path': '%s', 'img': '%s'}" % (quote(title),
				 quote(href), quote(img_src))
			addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Sendereihe_Sendungen", 
				fanart=R('3sat.png'), thumb=img_src, summary=descr, fparams=fparams)

	mediatype='' 		
	if SETTINGS.getSetting('pref_video_direct') == 'true': # Kennz. Video für Sofortstart 
		mediatype='video'
								
	for rec in rubriken:
		if 'data-playlist-toggle' not in rec:
			continue
		img_src =  stringextract('data-srcset="', ' ', rec)	
		rubrik 	= stringextract('<span>', '</span>', rec)
		rubrik	= cleanhtml(rubrik); rubrik = mystrip(rubrik)
		sub_rubrik = stringextract('ellipsis" >', '<', rec)
		sub_rubrik = mystrip(sub_rubrik)
		title	= stringextract('clickarea-link">', '</p>', rec)
		
		href	= stringextract('href="', '"', rec)
		if href.startswith('http') == False:
			href	= DreiSat_BASE + href
		descr	= stringextract('clickarea-link" >', '<', rec)
		tagline = rubrik + ' | ' +sub_rubrik
		dauer	= stringextract('class="label">', '<', rec)		# label">2 min</span>
		if dauer:
			tagline = tagline + ' | ' + dauer
		duration = ' '				
			
		title = repl_json_chars(title); descr = repl_json_chars(descr); 
		descr_par =	descr.replace('\n', '||')	
				
		PLog('Satz:')
		PLog(img_src); PLog(rubrik); PLog(title);  PLog(href); PLog(tagline); PLog(descr);
		PLog(dauer); PLog(duration);
				
		title=py2_encode(title); href=py2_encode(href);	 img_src=py2_encode(img_src);
		descr_par=py2_encode(descr_par); dauer=py2_encode(dauer); duration=py2_encode(duration);						
		fparams="&fparams={'title': '%s', 'path': '%s', 'img_src': '%s', 'summ': '%s', 'dauer': '%s', 'duration': '%s'}" %\
			(quote(title), quote(href), quote(img_src), quote(descr_par), quote(dauer), quote(duration))
		addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.SingleBeitrag", fanart=R('3sat.png'), 
			thumb=img_src, summary=descr, tagline=tagline, fparams=fparams, mediatype=mediatype)

	if 'is-medium lazyload' in page:							# Test auf Loader-Beiträge, escaped
		li, cnt = get_lazyload(li=li, page=page, ref_path=path)
				

	if ret == True:
		xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)
	else:
		return li	
	
#-------------
# Loader-Beitrag auswerten, json-Format, 
# keys: style, sourceModuleType, teaserImageId, clusterType, clusterTitle,
#	teasertext, sophoraId, moduleId
# Die Pfade zu den Loader-Beiträgen  werden in einer Json-Beitragsliste außerhalb
#	der Loader-Beiträge ermittelt (mittels sophId).
#
def get_lazyload(li, page, ref_path):
	PLog('get_lazyload:')
	content =  blockextract('is-medium lazyload', page)		# Test auf Loader-Beiträge, escaped
	PLog(len(content))
	dauer	= stringextract('duration": "', '"', page)		# gilt für folgende oader-Beiträge
	img_pre = stringextract('data-srcset="', ' ', page)		# dto.
	PLog("dauer %s, img_pre: %s " % (dauer, img_pre))	
	
	mediatype='' 		
	if SETTINGS.getSetting('pref_video_direct') == 'true': # Kennz. Video für Sofortstart 
		mediatype='video'

	cnt=0
	for rec in content:	
		rec = unescape(rec)
		PLog('loader_Beitrag')
		PLog(rec[:60]); 	
	
		# Ersatz für javascript: Auswertung + Rückgabe aller  
		#	Bestandteile:
		sophId,path,title,descr,img_src,dauer,tag,isvideo = get_teaserElement(rec)
		PLog(descr)
		if img_src == '':										
			if img_pre:
				img_src = img_pre								# Fallback 1: Rubrikbild
			else:
				img_src = R('icon-bild-fehlt.png')				# Fallback 2: Leer-Bild 
		if path == '':
			path	= "%s/%s.html" % (DreiSat_BASE, sophId)		# Zielpfad bauen
			
		tag = tag.strip()
		if tag:
			descr = "%s\n\n%s"   % (tag, descr)
				
		title = repl_json_chars(title); descr = repl_json_chars(descr); 
		descr_par =	descr.replace('\n', '||')	
		
		cnt = cnt+1	
		PLog('Satz: %d' % cnt)
		PLog(sophId); PLog(path); PLog(title);PLog(descr); PLog(img_src); PLog(dauer); PLog(tag); 
		
		if isvideo == 'true':											#  page enthält data-playlist
			title=py2_encode(title); path=py2_encode(path);	img_src=py2_encode(img_src);
			descr_par=py2_encode(descr_par); dauer=py2_encode(dauer);					
			fparams="&fparams={'title': '%s', 'path': '%s', 'img_src': '%s', 'summ': '%s', 'dauer': '%s', 'duration': ''}" %\
				(quote(title), quote(path), quote(img_src), quote(descr_par), quote(dauer))
			addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.SingleBeitrag", fanart=R('3sat.png'), 
				thumb=img_src, summary=descr, tagline=dauer, fparams=fparams, mediatype=mediatype)
		else:
			title=py2_encode(title); path=py2_encode(path);	img_src=py2_encode(img_src);
			fparams="&fparams={'li': '', 'title': '%s', 'path': '%s', 'img': '%s'}" % (quote(title),
				 quote(path), quote(img_src))
			addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Sendereihe_Sendungen", 
				fanart=R('3sat.png'), thumb=img_src, summary=descr, fparams=fparams)

	return li, cnt
	
#------------
# Ersatz für javascript: Ermittlung Icon + Sendedauer
#	rec hier bereits unescaped durch get_lazyload
# Aus Performancegründen (Anzahl der Elemente manchmal 
#	> 30) werden die Elemente in TEXTSTORE gecached, 
#	unabhängig von SETTINGS('pref_load_summary').
# 20.11.2019 Einsetzungselement sophoraId ausreichend für path 
#	(teaserHeadline,teasertext,clusterTitle entfallen)
# Hinweis: Änderungen ev. auch in ardundzdf erforderlich.
#
def get_teaserElement(rec):
	PLog('get_teaserElement:')
	# Reihenfolge Ersetzung: sophoraId, teaserHeadline, teasertext, clusterTitle
	
	sophoraId = stringextract('"sophoraId": "', '"', rec)
	teaserHeadline = stringextract('teaserHeadline": "', ',', rec)
	teaserHeadline = teaserHeadline.replace('"', '')
	teasertext = stringextract('"teasertext": "', '",', rec)
	clusterTitle = stringextract('clusterTitle": "', ',', rec)
	
	sophoraId = transl_json(sophoraId); teaserHeadline = transl_json(teaserHeadline);
	teasertext = transl_json(teasertext); clusterTitle = transl_json(clusterTitle);
	PLog(teaserHeadline)	
	
	sophId = sophoraId; title = teaserHeadline; ctitle = clusterTitle;  # Fallback-Rückgaben
	descr = teasertext; isvideo=''	
		
	sophoraId=quote(py2_encode(sophoraId)); teaserHeadlin =quote(py2_encode(teaserHeadline));
	teasertext = quote(py2_encode(teasertext)); clusterTitle = quote(py2_encode(clusterTitle));
	
	path = "https://www.3sat.de/teaserElement?sophoraId=%s&style=m2&moduleId=mod-2&clusterType=Cluster_S&sourceModuleType=cluster-s" % (sophoraId)
	PLog(path)
	
	fpath = os.path.join(TEXTSTORE, sophoraId)
	PLog('fpath: ' + fpath)
	if os.path.exists(fpath) and os.stat(fpath).st_size == 0: # leer? = fehlerhaft -> entfernen 
		PLog('fpath_leer: %s' % fpath)
		os.remove(fpath)
	if os.path.exists(fpath):				# teaserElement lokal laden
		PLog('lade_lokal:') 
		page =  RLoad(fpath, abs_path=True)
	else:
		page, msg = get_page(path)			# teaserElement holen
		if page:							# 	und in TEXTSTORE speichern
			msg = RSave(fpath, page, withcodec=True)
	PLog(page[:100])
	
	if page:								# 2. teaserElement auswerten
		img_src =  stringextract('data-srcset="', ' ', page)	
		title	= stringextract('clickarea-link">', '</p>', page)
		if title == '':
			title = stringextract('title="', '"', page)			# Ersatz: Titel hinter href-Url
		title	= unescape(title); 
		title	= transl_json(title); 
		ctitle = stringextract('ellipsis" >', '<', page)  		# -> tag (subheadline)
		tag 	= stringextract('<span>', '</span>', page)
		dauer	= stringextract('class="label">', '</', page)
		path	= stringextract('href="', '"', page)
		if path.startswith('http') == False:
			path = DreiSat_BASE + path
		descr	= stringextract('clickarea-link" >', '<', page)
		if descr == '':											# 1. Ersatz: 
			descr	= stringextract('teaser-text" >', '<', page)# wie ardundzdf
		if descr == '':											# 2. Ersatz (Bild-Beschr.): 
			descr	= stringextract('alt="', '"', page)
		if ctitle:
			tag = tag + " | " + ctitle
			
		tag = cleanhtml(tag); descr = unescape(descr)
		if "data-playlist" in page:			# Videobeitrag? - Folgeseiten möglich
			isvideo = 'true'
		
		# sophId s.o.
		return sophId, path, title, descr, img_src, dauer, tag, isvideo	
	else:									#  Fallback-Rückgaben, Bild + Dauer leer
		img_src=''; dauer=''; tag=''; isvideo=''
		return sophId, path, title, descr, img_src, dauer, tag, isvideo
	
#------------
# video-carousel-item-Beiträge auswerten, html-Format, Seitenkopf
def get_video_carousel(li, page):
	PLog('get_video_carousel:')
	content =  blockextract('video-carousel-item">', page)
	PLog(len(content))
	
	mediatype='' 		
	if SETTINGS.getSetting('pref_video_direct') == 'true': # Kennz. Video für Sofortstart 
		mediatype='video'
	cnt=0

	for rec in content:	
		if 'data-module="zdfplayer"' not in rec:		# redakt. Beitrag o. Video
			continue
		videoinfos = stringextract("video-infos='{", '}', rec)
		videoinfos = unescape(videoinfos)
		title 	= stringextract('title":', '",', videoinfos)
		title 	= (title.replace('\\"', '').replace('"', ''))
		dauer 	= stringextract('duration": "', '"', videoinfos)	# 2 min
		path	= stringextract('embed_content": "', '"', rec)
		path 	= "%s%s.html" % (DreiSat_BASE, path)
		img_src	= stringextract('image="{', '}', rec)	# data-zdfplayer-teaser-image=
		img_src	= stringextract('768xauto&quot;:&quot;', '&quot', rec)	# 768xauto	
		img_src	= unescape(img_src); img_src = img_src.replace('\\', '')
	
		tagline = dauer
		subtitle	= stringextract('brand-subtitle">', '<', rec)
		if not subtitle:
			subtitle	= stringextract('subheadline level-7 " >', '<', rec)
		if subtitle:
			tagline = "%s | %s" % (dauer, subtitle)
		descr 	= stringextract('paragraph-large ">', '<', rec)
		descr 	= unescape(descr)
		descr = transl_json(descr); 

		descr = transl_json(descr); 
		PLog('Satz:')
		PLog(img_src); PLog(title); PLog(dauer); PLog(path); 
		title=py2_encode(title); path=py2_encode(path);	 img_src=py2_encode(img_src);
		dauer=py2_encode(dauer);
		fparams="&fparams={'title': '%s', 'path': '%s', 'img_src': '%s', 'summ': '', 'dauer': '%s', 'duration': ''}" %\
			(quote(title), quote(path), quote(img_src), quote(dauer))
		addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.SingleBeitrag", fanart=R('3sat.png'), 
			thumb=img_src, tagline=tagline, fparams=fparams, mediatype=mediatype)			 
			 
		cnt=cnt+1
	return li, cnt

#------------
# ideo-carousel-item- und o--stage-brand-Beiträge auswerten,
#	html-Format, Seitenkopf - Doppel zu Folgebeiträgen möglich
def get_zdfplayer_content(li, content):
	PLog('get_zdfplayer_content:')
	
	mediatype='' 		
	if SETTINGS.getSetting('pref_video_direct') == 'true': # Kennz. Video für Sofortstart 
		mediatype='video'

	cnt=0
	for rec in content:	
		tag=''; 
		if 'data-module="zdfplayer"' not in rec:		# redakt. Beitrag ohne Video
			continue
		videoinfos = stringextract("video-infos='{", '}', rec)
		videoinfos = unescape(videoinfos)
		title 	= stringextract('title":', '",', videoinfos)
		title 	= (title.replace('\\"', '').replace('"', ''))

		dauer 	= stringextract('duration": "', '"', videoinfos)	# Bsp. 2 min
		path	= stringextract('embed_content": "', '"', rec)
		path 	= DreiSat_BASE + path + ".html"
		img_src	= stringextract('data-srcset="', '"', rec)			
		img_src	= img_src.split(' ')[0]								# kann mit Blank enden
		if img_src == '':
			img_src = stringextract('teaser-image-overwrite', 'quot;}', rec)	# Bsp. Wissen/#Erklärt
			PLog(img_src)
			img_src =stringextract('https:', '&', img_src)
			PLog(img_src)
			img_src = 'https:' + img_src.replace('\\/', '/')	 
		
		tagline = dauer
		subtitle	= stringextract('brand-subtitle">', '<', rec)
		if subtitle:
			tag = dauer + ' | ' + subtitle

		descr 	= stringextract('paragraph-large ">', '<', rec)
		descr 	= unescape(descr)
		descr = transl_json(descr); 
		title = transl_json(title); title = repl_json_chars(title);
	
		PLog('Satz:')
		PLog(img_src); PLog(title); PLog(path); 
		title=py2_encode(title); path=py2_encode(path);	img_src=py2_encode(img_src);
		dauer=py2_encode(dauer);
		fparams="&fparams={'title': '%s', 'path': '%s', 'img_src': '%s', 'summ': '', 'dauer': '%s', 'duration': ''}" %\
			(quote(title), quote(path), quote(img_src), quote(dauer))
		addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.SingleBeitrag", fanart=R('3sat.png'), 
			thumb=img_src, summary=descr, fparams=fparams, mediatype=mediatype)
			 	
		cnt=cnt+1

	PLog("Anzahl Beiträge: %s" % cnt)
	return li, cnt

#------------

# 16.05.2017: Design neu, Videoquellen nicht mehr auf der Webseite vorhanden - (Ladekette ähnlich ZDF-Mediathek)
# 22.05.2019: Design neu, Ladekette noch ähnlich ZDF-Mediathek, andere Parameter, Links + zusätzl. apiToken
#
# SingleBeitrag für Verpasst + A-Z
#	hier auch m3u8-Videos verfügbar. 
def SingleBeitrag(title, path, img_src, summ, dauer, duration, Merk='false'):
	PLog('Funktion SingleBeitrag: ' + title)
	PLog(dauer);PLog(duration);PLog(summ);PLog(path)
	
	Plot	 = title
	Plot_par = summ										# -> PlayVideo
	if Plot_par == '':			
		Plot_par = title
	tag_org = dauer
	thumb	= img_src; title_org = title

	li = xbmcgui.ListItem()
	li = home(li, ID='3Sat')							# Home-Button
			
	page, msg = get_page(path=path)						# 1. Basisdaten von Webpage holen
	if page == '':			
		msg1 = "SingleBeitrag1: Abruf fehlgeschlagen"
		msg2 = msg
		msg3=path
		PLog(msg1)
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, msg2, msg3)
		return li	
	
	content = stringextract('window.zdfsite', 'tracking', page)  			
	content = stringextract('data-module="zdfplayer"', 'teaser-image=', page)  			
	appId	= stringextract('zdfplayer-id="', '"', content)
	apiToken= stringextract('apiToken": "', '"', content)
	profile_url= stringextract('content": "', '"', content)		# profile_url
	PLog(appId); PLog(profile_url); PLog("apiToken: " + apiToken); 
	
	if 	apiToken == '' or profile_url == '':
		if '<time datetime="' in page:
			termin = stringextract('<time datetime="', '"', page)
			termin = time_translate(termin)
			msg1 = "(noch) kein Video gefunden, Sendetermin: " + termin
		else:
			msg1 = "keine Videoquelle gefunden. Seite:\n" + path
			PLog(msg1)
			PLog(apiToken)		# zur Kontrolle
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, '', '')
		return li	
	
	headers = "{'Api-Auth': 'Bearer %s','Host': 'api.zdf.de'}" % apiToken 
	page,msg = get_page3sat(path=profile_url, apiToken=apiToken)	# 2. Playerdaten mit neuer Video-ID	
	
	if page == '':			
		msg1 = "SingleBeitrag2: Abruf fehlgeschlagen"
		msg2 = msg
		msg3=path
		PLog(msg1)
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, msg2, msg3)
		return li	
	
	page = page.replace('\\', '')
	PLog(page[:100])

	videodat	= blockextract('ptmd-template":"',page)		# mehrfach möglich
	videodat	= videodat[-1]								# letzte ist relevant
	videodat_url= stringextract('ptmd-template":"', '"', videodat)
	video_ID = videodat_url.split('/')[-1]					#  ID z.B. 190521_sendung_nano
	videodat_url = 'https://api.3sat.de/tmd/2/ngplayer_2_3/vod/ptmd/3sat/' + video_ID
	PLog("videodat_url: " + videodat_url)
	page,msg = get_page3sat(path=videodat_url, apiToken=apiToken)
	if page == '':			
		msg1 = "SingleBeitrag3: Abruf fehlgeschlagen"
		PLog(msg1); PLog(msg)
		msg2 = msg
	
	if page == '':											# Alternative mediathek statt 3sat
		videodat_url = 'https://api.3sat.de/tmd/2/ngplayer_2_3/vod/ptmd/mediathek/' + video_ID
		page = get_page3sat(path=videodat_url, apiToken=apiToken)
		page = str(page)									# <type 'tuple'> möglich
		PLog(page[:100])

	PLog(type(page)); 
	if 	"formitaeten" not in page:
		msg1 = "keine Videoquelle gefunden. Seite:\n" + path
		PLog(msg1)
		PLog(videodat_url)		# zur Kontrolle
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, '', '')
		return li	

	if page:
		formitaeten = blockextract('formitaeten', page)		# 4. einzelne Video-URL's ermitteln 
		geoblock =  stringextract('geoLocation',  '}', page) 
		geoblock =  stringextract('"value" : "',  '"', geoblock).strip()
		PLog('geoblock: ' + geoblock);
		if 	geoblock == 'none':								# i.d.R. "none", sonst "de" - wie bei ARD verwenden
			geoblock = ' | ohne Geoblock'
		else:
			if geoblock == 'de':			# Info-Anhang für summary 
				geoblock = ' | Geoblock DE!'
			if geoblock == 'dach':			# Info-Anhang für summary 
				geoblock = ' | Geoblock DACH!'
			
	download_list = []
	tagline = title + " | " + dauer + " " + geoblock
	Plot_par = tagline + "||||" + Plot_par
	
	thumb=img_src
	for rec in formitaeten:									# Datensätze gesamt
		# PLog(rec)		# bei Bedarf
		typ = stringextract('\"type\" : \"', '\"', rec)
		facets = stringextract('\"facets\" : ', ',', rec)	# Bsp.: "facets": ["progressive"]
		facets = facets.replace('\"', '').replace('\n', '').replace(' ', '')  
		PLog('typ: ' + typ); PLog('facets: ' + facets)
		if typ == "h264_aac_f4f_http_f4m_http":				# manifest.f4m auslassen
			continue
		audio = blockextract('\"audio\" :', rec)			# Datensätze je Typ
		# PLog(audio)	# bei Bedarf
		
		for audiorec in audio:					
			url = stringextract('\"uri\" : \"',  '\"', audiorec)			# URL
			quality = stringextract('\"quality\" : \"',  '\"', audiorec)
			if quality == 'high':							# high bisher identisch mit auto 
				continue
			PLog(url); PLog(quality); 
			
			PLog('Mark0')
			if url:		
				if url.find('master.m3u8') > 0:			# m3u8 enthält alle Auflösungen					
					title = quality + ' [m3u8]'
					# Sofortstart - direkt, falls Listing nicht Playable			
					if SETTINGS.getSetting('pref_video_direct') == 'true': # or Merk == 'true'
						PLog('Sofortstart: SingleBeitrag')
						PLog(xbmc.getInfoLabel('ListItem.Property(IsPlayable)')) 
						# sub_path=''	# fehlt bei ARD - entf. ab 1.4.2019
						PlayVideo(url=url, title=title_org, thumb=thumb, Plot=Plot_par, sub_path='')
						return									

					#  "auto"-Button + Ablage master.m3u8:
					# Da 3Sat 2 versch. m3u8-Qualitäten zeigt,verzichten wir (wie bei ZDF_getVideoSources)
					#	auf Einzelauflösungen via Parseplaylist
					#	
					li = ParseMasterM3u(li=li, url_m3u8=url, thumb=thumb, title=title, descr=Plot_par)
			
				else:									# m3u8 enthält Auflösungen high + med
					title = 'Qualitaet: ' + quality + ' | Typ: ' + typ + ' ' + facets 

					download_list.append(title + '#' + url)			# Download-Liste füllen	
					tagline	= tagline.replace('||','\n')			# s. tagline in ZDF_get_content				
					summ	= summ.replace('||','\n')				# 
					tag	= 	tagline + '\n\n' + summ	
					
					title=py2_encode(title); url=py2_encode(url); thumb=py2_encode(thumb);
					Plot_par=py2_encode(Plot_par);
					fparams="&fparams={'url': '%s', 'title': '%s', 'thumb': '%s', 'Plot': '%s', 'sub_path': '', 'Merk': ''}" %\
						(quote_plus(url), quote_plus(title), quote_plus(thumb), quote_plus(Plot_par))	
					addDir(li=li, label=title, action="dirList", dirID="PlayVideo", fanart=thumb, thumb=thumb, fparams=fparams, 
						mediatype='video', tagline=tag) # summary=summ) 
												
	if SETTINGS.getSetting('pref_use_downloads'):
		# high=0: 	1. Video bisher höchste Qualität:  [progressive] veryhigh
		tagline=tag_org
		li = test_downloads(li,download_list,title_org,Plot_par,tag,thumb,high=0)  # Downloadbutton(s)
					
	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)

####################################################################################################
# 3Sat - TV-Livestream mit EPG
#	summ = epg (s. Main_3Sat)
def Live(name, epg='', Merk='false'):	
	PLog('Live: ' + name)
	title2 = name
	
	li = xbmcgui.ListItem()
	li = home(li, ID='3Sat')						# Home-Button
	
	url = 'https://zdfhls18-i.akamaihd.net/hls/live/744751/dach/high/master.m3u8'
	# epg_url = 'https://programm.ard.de/TV/ARD-Mediathek/Programmkalender/?sender=28007'	# entf. 
	epgname = 'ARD'; listname = '3sat'
	summary = u'automatische Auflösung';				
	title = 'Bandbreite und Auflösung automatisch'
	img	= R(ICON_TV3Sat)
	
	if not epg:
		epg = get_epg()

	if SETTINGS.getSetting('pref_video_direct') == 'true': # or Merk == 'true'	# Sofortstart
		PLog('Sofortstart: Live')
		Plot	 = 'Live: ' + name + '\n\n' + epg + '\n\n' + summary
		PlayVideo(url=url, title='3Sat Live TV', thumb=img, Plot=Plot, Merk=Merk)
		return	
							
	Plot	 = 'Live: ' + name + '\n\n' + epg
	Plot_par = Plot.replace('\n', '||')
	title=py2_encode(title); url=py2_encode(url); img=py2_encode(img);
	Plot_par=py2_encode(Plot_par);
	fparams="&fparams={'url': '%s', 'title': '%s', 'thumb': '%s', 'Plot': '%s', 'sub_path': '', 'Merk': 'false'}" %\
		(quote_plus(url), quote_plus(title), quote_plus(img), quote_plus(Plot_par))
	addDir(li=li, label=title, action="dirList", dirID="PlayVideo", fanart=img, thumb=img, fparams=fparams, 
		mediatype='video', tagline=Plot) 		
	
	li = Parseplaylist(li, url, img, geoblock='', descr=Plot)	
	
	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)
	
#-----------------------------
def get_epg():		# akt. PRG-Hinweis von 3Sat-Startseite holen
	PLog('get_epg:')
	# 03.08-2017: get_epg_ARD entfällt - akt. PRG-Hinweis auf DreiSat_BASE eingeblendet
	# epg_date, epg_title, epg_text = get_epg_ARD(epg_url, listname)
	page, msg = get_page(path=DreiSat_BASE)	
	if page == '':	
		msg1 = "Fehler in get_epg:"
		msg2 = msg
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, msg2, '')	
		return ''
	
	epg = stringextract('>Jetzt live<', '</div>', page)
	epg = stringextract("class='time'>", '</h3>', epg)
	epg = epg.replace('</span>', ' | ')		# Bsp.: class='time'>10:15</span> Kölner Treff</h3>
	epg = cleanhtml(epg)		
	PLog(epg)
	return epg
	
####################################################################################################
# 3Sat - Bild-Galerien/-Serien
#	Übersichtsseiten - 3sat zeigt 12 Beiträge pro Seite
#		path für weitere Seiten: class="load-more-container"
#
def Bilder3sat(path=''):
	PLog('Bilder3sat:')
	if path == '':
		path="https://www.3sat.de/suche?q=bilderserie&synth=true&attrs=&page=1"
	
	page, msg = get_page(path)	
	if page == '':
		msg1 = 'Bilder3sat: Seite kann nicht geladen werden.'
		msg2 = msg
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, msg2, '')
		return
	
	li = xbmcgui.ListItem()
	li = home(li, ID='3Sat')						# Home-Button

	content = blockextract('class="is-clickarea panel">', page)
	PLog("content: " + str(len(content)))
	if len(content) == 0:										
		msg1 = 'Bilder3sat: keine Bilder (mehr) gefunden.'
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, '', '')
		return li
		
	for rec in content:
		if 'class="icon-gallery"' not in rec:					# Bildsymbol 
			continue
		
		img_set = stringextract('data-srcset="', '"', rec) # Format 16-9
		img_list= img_set.split(',')
		img = img_list[-1]										# 384x216
		PLog(img)
		img_src = 'https:' + stringextract('https:', ' ', img)
		if img == '':
			continue
		
		href = 'https://www.3sat.de' + stringextract('href="', '"', rec)
		
		headline = stringextract('medium-6   ">', '</h3>', rec)		# headline + Subtitel -> Tagline
		title = stringextract('clickarea-link">', '</p>', headline) # Titel -> Ordnername
		title = cleanhtml(title); title = mystrip(title)
		headline = cleanhtml(headline); headline = mystrip(headline)
		stitle= stringextract('ellipsis" >', '</', rec)
		stitle = cleanhtml(stitle); stitle = mystrip(stitle)
		tag = "%s | %s" % (headline, stitle)
		
		summ = stringextract('class="label">', '</', rec)
		
		PLog('Satz:')
		PLog(img_src); PLog(title); PLog(tag);  		
			
		href=py2_encode(href); title=py2_encode(title);
		fparams="&fparams={'path': '%s', 'title': '%s'}" % (quote(href), quote(title))
		addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Bilder3satSingle", 
			fanart=img_src, thumb=img_src, fparams=fparams, tagline=tag, summary=summ)
			
	if 'class="load-more-container">' in page:
		href = stringextract('class="load-more-container">', '</div>', page)
		href = stringextract('href="', '"', href)
		if href:
			title = u'weitere Bilderserien laden'
			href = 'https://www.3sat.de' + href
			PLog('more_url: ' + href)
			href = decode_url(href); href=py2_encode(href); 	# ..&amp;attrs=&amp;page=2
			fparams="&fparams={'path': '%s'}" % (quote(href))
			addDir(li=li, label=title, action="dirList", dirID="resources.lib.my3Sat.Bilder3sat", 
				fanart=R('zdf-bilderserien.png'), thumb=R(ICON_MEHR), tagline='Mehr...', fparams=fparams)	

	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)  # ohne Cache, um Neuladen zu verhindern
		
####################################################################################################
def Bilder3satSingle(title, path):
	PLog('Bilder3satSingle:')
	
	page, msg = get_page(path)	
	if page == '':
		msg1 = 'Bilder3satSingle: Seite kann nicht geladen werden.'
		msg2 = msg
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, msg2, '')
		return
	
	li = xbmcgui.ListItem()
	li = home(li, ID='3Sat')						# Home-Button

	content = blockextract('class="img-container">', page)
	PLog("content: " + str(len(content)))
	if len(content) == 0:										
		msg1 = 'Bilder3satSingle: keine Bilder gefunden.'
		msg2 = title
		xbmcgui.Dialog().ok(ADDON_NAME, msg1, msg2, '')
		return li
	
	fname = make_filenames(title)			# Ordnername: Titel 
	fpath = '%s/%s' % (SLIDESTORE, fname)
	PLog(fpath)
	if os.path.isdir(fpath) == False:
		try:  
			os.mkdir(fpath)
		except OSError:  
			msg1 = 'Bildverzeichnis konnte nicht erzeugt werden:'
			msg2 = "%s/%s" % (SLIDESTORE, fname)
			PLog(msg1); PLog(msg2)
			xbmcgui.Dialog().ok(ADDON_NAME, msg1, msg2, '')
			return li	
	
	image=0; background=False; path_url_list=[]; text_list=[]
	for rec in content:
		img_src =  stringextract('data-srcset="', ' ', rec)	
		img_src = img_src.replace('384x216', '1280x720')			
		title 	= stringextract('level-3   ">', '</h2>', rec) 
		stitle 	= stringextract('level-2">', '</span>', rec)
		title=cleanhtml(title); title=mystrip(title);  
		stitle=cleanhtml(stitle); stitle=mystrip(stitle.strip()); 
		
		descr 	= stringextract('paragraph-large ">', '</p', rec) 	# Bildtext
		urh	= stringextract('teaser-info is-small">', '</dd', rec)	# Urheber
		urh=mystrip(urh.strip()); 
		
		tag = "%s | %s" % (stitle, title)
		summ = "%s\n%s" % (descr, urh)
		
		PLog('Satz:')
		PLog(img_src); PLog(tag[:60]); PLog(summ[:60]);	
		tag=repl_json_chars(tag) 
		title=repl_json_chars(title); summ=repl_json_chars(summ); 		
			
		#  Kodi braucht Endung für SildeShow; akzeptiert auch Endungen, die 
		#	nicht zum Imageformat passen
		pic_name 	= 'Bild_%04d.jpg' % (image+1)		# Bildname
		local_path 	= "%s/%s" % (fpath, pic_name)
		PLog("local_path: " + local_path)
		title = "Bild %03d" % (image+1)
		PLog("Bildtitel: " + title)
		
		local_path 	= os.path.abspath(local_path)
		thumb = local_path
		if os.path.isfile(local_path) == False:			# schon vorhanden?
			# path_url_list (int. Download): Zieldatei_kompletter_Pfad|Bild-Url, 
			#	Zieldatei_kompletter_Pfad|Bild-Url ..
			path_url_list.append('%s|%s' % (local_path, img_src))

			if SETTINGS.getSetting('pref_watermarks') == 'true':
				lable=''
				txt = "%s\n%s\n%s\n%s\n%s\n" % (fname,title,lable,tag,summ)
				text_list.append(txt)	
			background	= True											
								
		title=repl_json_chars(title); summ=repl_json_chars(summ)
		PLog('neu:');PLog(title);PLog(thumb);PLog(summ[0:40]);
		if thumb:	
			local_path=py2_encode(local_path);
			fparams="&fparams={'path': '%s', 'single': 'True'}" % quote(local_path)
			addDir(li=li, label=title, action="dirList", dirID="ZDF_SlideShow", 
				fanart=thumb, thumb=local_path, fparams=fparams, summary=summ, tagline=tag)

		image += 1
			
	if background and len(path_url_list) > 0:				# Thread-Call mit Url- und Textliste
		PLog("background: " + str(background))
		from threading import Thread						# thread_getpic
		folder = fname 
		background_thread = Thread(target=thread_getpic,
			args=(path_url_list, text_list, folder))
		background_thread.start()

	PLog("image: " + str(image))
	if image > 0:	
		fpath=py2_encode(fpath);	
		fparams="&fparams={'path': '%s'}" % quote(fpath) 	# fpath: SLIDESTORE/fname
		addDir(li=li, label="SlideShow", action="dirList", dirID="ZDF_SlideShow", 
			fanart=R('icon-stream.png'), thumb=R('icon-stream.png'), fparams=fparams)
				
		lable = u"Alle Bilder löschen"						# 2. Löschen
		tag = 'Bildverzeichnis: ' + fname 
		summ= u'Bei Problemen: Bilder löschen, Wasserzeichen ausschalten,  neu einlesen'
		fparams="&fparams={'dlpath': '%s', 'single': 'False'}" % quote(fpath)
		addDir(li=li, label=lable, action="dirList", dirID="DownloadsDelete", fanart=R(ICON_DELETE), 
			thumb=R(ICON_DELETE), fparams=fparams, summary=summ, tagline=tag)

	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)  # ohne Cache, um Neuladen zu verhindern

####################################################################################################
#	Hilfsfunktionen
#----------------------------------------------------------------  
# 1. Format timecode '01:30' oder '00:30', Rest (Min, min o.ä.) wird abgeschnitten
# 2. Format: 'P0Y0M0DT5H50M0.000S', T=hours, H=min, M=sec
def HourToMinutes(timecode):	
	if timecode.find('P0Y0M0D') >= 0:			# 1. Format: 'P0Y0M0DT5H50M0.000S', T=hours, H=min, M=sec
		d = re.search('T([0-9]{1,2})H([0-9]{1,2})M([0-9]{1,2}).([0-9]{1,3})S', timecode)
		if(None != d):
			hours = int ( d.group(1) )
			minutes = int ( d.group(2) )
	else:
		timecode =  timecode[0:5]
		if timecode.find(':') < 0:
			return timecode
		t =  timecode.split(':')
		hours = int(t[0])
		minutes = int(t[1])
	
	if hours > 0:
		minutes = (hours * 60) + minutes
	
	return str(minutes)
#----------------------------------------------------------------  
# nur für Anford. Videodaten mittels apiToken 	
def get_page3sat(path, apiToken):
	PLog("get_page3sat: " + path) 
	PLog('Api-Auth: Bearer %s' % apiToken)
	msg=''
	try:
		PLog(type(path))	
		req = Request(path)
		req.add_header('Api-Auth', 'Bearer ' + apiToken)
		gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)  
		gcontext.check_hostname = False	
		r = urlopen(req, context=gcontext)
		page = r.read()
		PLog(page[:100])
	except Exception as exception:
		page = ''
		msg = str(exception)
		PLog(msg)
	PLog(len(page))
	
	page = page.decode('utf-8')	
	return page, msg


