import cgi
import os
from django.utils import simplejson as json
import oauth
import hashlib

from collections import deque

import re
import datetime

import logging

from google.appengine.api import urlfetch

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
#from google.appengine.ext.db import stats
from google.appengine.ext.webapp import template
from google.appengine.api import memcache
from google.appengine.api import images
from google.appengine.api import quota

import cStringIO
import csv
from datastore import *

# number of observations shown per page
PAGE_SIZE = 20

def extract_surveys(surveys):
	extracted = []
	for s in surveys:
		item = {}
		item['stressval'] = s.stressval

		if item['stressval'] < 0:
			item['stress'] = True
		else:
			item['stress'] = False

		if not s.category:
			item['category'] = s.category
		else:
			item['category'] = cgi.escape(s.category, True)

		if not s.subcategory:
			item['subcategory'] = s.subcategory
		else:
			item['subcategory'] = cgi.escape(s.subcategory, True)

		if not s.comments:
			item['comments'] = s.comments
		else:
			item['comments'] = cgi.escape(s.comments, True)

		if s.hasphoto:
			item['hasphoto'] = True
			item['photo_key'] = str(s.photo_ref.key())
		else:
			item['hasphoto'] = False
			item['photo_key'] = None

		if not s.timestamp:
			item['timestamp'] = s.timestamp
		else:
			pdt = s.timestamp - datetime.timedelta(hours=7)
			item['timestamp'] = str(pdt).split('.')[0] + " PDT"

		item['realtime'] = s.timestamp

		item['longitude'] = s.longitude
		item['latitude'] = s.latitude
		item['key'] = str(s.key())
		item['version'] = s.version
		extracted.append(item)
	return extracted
# End extract_surveys function


# main page: /
class HomePage(webapp.RequestHandler):
	def get(self):
		path = os.path.join (os.path.dirname(__file__), 'views/home.html')
		self.response.out.write (template.render(path, {}))
	# end get method
# End HomePage Class

# map page: /map
class MapPage(webapp.RequestHandler):
	def get(self):
		if os.environ.get('HTTP_HOST'):
			base_url = 'http://' + os.environ['HTTP_HOST'] + '/'
		else:
			base_url = 'http://' + os.environ['SERVER_NAME'] + '/'

		extracted = memcache.get('saved')

		if not extracted:
			surveys = SurveyData.all().order('-timestamp').fetch(PAGE_SIZE*5+1)
			extracted = extract_surveys (surveys)
			if surveys is not None:
				#memcache.set('saved', extracted, 604800)
				memcache.set('saved', extracted)
		template_values = { 'surveys' : extracted, 'base_url' : base_url }
		path = os.path.join (os.path.dirname(__file__), 'views/map.html')
		self.response.out.write (template.render(path, template_values))
	# end get method
# End MapPage Class

# client link page: /client
class ClientsPage(webapp.RequestHandler):
	def get(self):
		path = os.path.join (os.path.dirname(__file__), 'views/clients.html')
		self.response.out.write (template.render(path, {}))
	# end get method
# End ClientsPage Class

# about page: /about
class AboutPage(webapp.RequestHandler):
	def get(self):
		path = os.path.join (os.path.dirname(__file__), 'views/about.html')
		self.response.out.write (template.render(path, {}))
	# end get method
# End AboutPage Class

# handler for: /get_point_summary
class GetPointSummary(webapp.RequestHandler):
	# returns json string of all survey data
	# TODO: this needs to be changed to return only a subset of the surveys, add paging
	def get(self):
		#surveys = db.GqlQuery("SELECT * FROM SurveyData ORDER BY timestamp DESC LIMIT 50")

		# this should be changed to just use the same extracted format everything else uses...
		d = memcache.get('pointsummary')

		i = 0
		if not d:
			surveys = SurveyData.all().order('-timestamp').fetch(50)
			d = {}
			for s in surveys:
				e = {}
				e['latitude'] = s.latitude
				e['longitude'] = s.longitude
				e['stressval'] = s.stressval
				e['comments'] = s.comments
				e['key'] = str(s.key())
				e['version'] = s.version
				if s.hasphoto:
					e['photo_key'] = str(s.photo_ref.key())
				else:
					e['photo_key'] = None

				d[i] = e
				i = i + 1

			if i > 0:
				#memcache.set('pointsummary', d, 604800)
				memcache.set('pointsummary', d)
		else:
			i = len(d)

		self.response.headers['Content-type'] = 'text/plain'
		if i > 0 :
			self.response.out.write(json.dumps(d))
		else:
			self.response.out.write("no data so far")
	# end get method
# End GetPointSummary Class

# handler for: /get_a_point
class GetAPoint(webapp.RequestHandler):
	# input: key - datastore key from SurveyData 
	# returns survey data associated with given key as json string
	def get(self):
		if os.environ.get('HTTP_HOST'):
			base_url = os.environ['HTTP_HOST']
		else:
			base_url = os.environ['SERVER_NAME']


		self.response.headers['Content-type'] = 'text/plain'
		req_key = self.request.get('key')
		if req_key != '':
			try :
				db_key = db.Key(req_key)
				s = db.GqlQuery("SELECT * FROM SurveyData WHERE __key__ = :1", db_key).get()
				e = {}
				try:
					e['photo'] = 'http://' + base_url + "/get_image_thumb?key=" + str(s.photo_ref.key());
				except (AttributeError):
					e['photo'] = ''
				e['latitude'] = s.latitude
				e['longitude'] = s.longitude
				e['stressval'] = s.stressval
				e['category'] = s.category
				e['subcategory'] = s.subcategory
				e['comments'] = s.comments
				e['key'] = str(s.key())
				e['version'] = s.version
				if s.hasphoto:
					e['photo_key'] = str(s.photo_ref.key())
				else:
					e['photo_key'] = None
				self.response.out.write(json.dumps(e))
				return

			except (db.Error):
				self.response.out.write("No data has been uploaded :[")
				return
		self.response.out.write("No data has been uploaded :[")
	# end get method
# End GetAPoint Class

# handler for: /get_an_image
class GetAnImage(webapp.RequestHandler):
	# input: key - datastore key from SurveyPhoto 
	# returns image as jpeg
	def get(self):
		req_key = self.request.get('key')
		if req_key != '':
			try :
				db_key = db.Key(req_key)
				s = db.GqlQuery("SELECT * FROM SurveyPhoto WHERE __key__ = :1", db_key).get()
				if s:
					self.response.headers['Content-type'] = 'image/jpeg'
					self.response.headers['Last-Modified'] = s.timestamp.strftime("%a, %d %b %Y %H:%M:%S GMT")
					x = datetime.datetime.utcnow() + datetime.timedelta(days=30)
					self.response.headers['Expires'] = x.strftime("%a, %d %b %Y %H:%M:%S GMT")
					self.response.headers['Cache-Control'] = 'public, max-age=315360000'
					self.response.headers['Date'] = datetime.datetime.utcnow() 
				
					self.response.out.write(s.photo)
				else:
					self.response.set_status(401, 'Image not found.')
			except (db.Error):
				self.response.set_status(401, 'Image not found.')
		else:
			self.response.set_status(401, 'No Image requested.')
	# end get method
# End GetAnImage Class

# handler for: /get_a_thumb
class GetAThumb(webapp.RequestHandler):
	# input: key - datastore key from SurveyPhoto 
	# returns image as jpeg
	def get(self):
		req_key = self.request.get('key')
		if req_key != '':
			try :
				db_key = db.Key(req_key)
				s = db.GqlQuery("SELECT * FROM SurveyPhoto WHERE __key__ = :1", db_key).get()
				if s:
					self.response.headers['Content-type'] = 'image/jpeg'
					self.response.headers['Last-Modified'] = s.timestamp.strftime("%a, %d %b %Y %H:%M:%S GMT")
					x = datetime.datetime.now() + datetime.timedelta(days=30)
					self.response.headers['Expires'] = x.strftime("%a, %d %b %Y %H:%M:%S GMT")
					self.response.headers['Cache-Control'] = 'public, max-age=315360000'
					self.response.headers['Date'] = datetime.datetime.utcnow() 
					self.response.out.write(s.thumb)
				else:
					self.response.set_status(401, 'Image not found.')
			except (db.Error):
				self.response.set_status(401, 'Image not found.')
		else:
			self.response.set_status(401, 'No Image requested.')
	# end get method
# End GetAnImage Class

# handler for: /get_image_thumb
class GetImageThumb(webapp.RequestHandler):
	# input: key - datastore key from SurveyPhoto 
	def get(self):
		if os.environ.get('HTTP_HOST'):
			base_url = os.environ['HTTP_HOST']
		else:
			base_url = os.environ['SERVER_NAME']

		self.response.headers['Content-type'] = 'text/html'
		req_key = self.request.get('key')
		self.response.out.write("<html><body><img src=\"http://" + base_url + "/get_a_thumb?key=")
		self.response.out.write(req_key)
		self.response.out.write("\" width=\"180\" height=\"130\"></body></html>")
	# end get method
# end GetImageThumb Class

# list data page: /data
class DataByDatePage(webapp.RequestHandler):
	# display data in table format
	# TODO: page results
	def get(self):
		if os.environ.get('HTTP_HOST'):
			base_url = 'http://' + os.environ['HTTP_HOST'] + '/'
		else:
			base_url = 'http://' + os.environ['SERVER_NAME'] + '/'

		# get bookmark
		bookmark = self.request.get('bookmark')

		logging.debug(self.request.get('bookmark'))

		template_values = { 'base_url' : base_url }

		forward = True

		page = None

		# check if page set
		if self.request.get('page'):
			page = int(self.request.get('page'))

		# fetch cached values if any
		extracted = None

		if (page is not None and page >= 1 and page <=5) or (not page and not bookmark):
			saved = memcache.get('saved')

		# if in cache, get values
		if saved is not None:
			logging.debug('trying cache')
			saved_len = len(saved)
			logging.debug('saved_len: '+str(saved_len))

			# if no page set, return first page
			if not bookmark and not page: 
				logging.debug('getting first page')
				# if less than PAGE_SIZE values, return all
				if saved_len < PAGE_SIZE:
					logging.debug('less than full page')
					extracted = saved
				else: # else, return first page
					extracted = saved[:PAGE_SIZE-1]
					# if there are more values, then setup next
					if saved_len > PAGE_SIZE: 
						template_values['next'] = str(extracted[-1]['realtime'])
						template_values['nextpage'] = 2
						logging.debug('setup next page')
			elif page is not None:
				# first 5 pages are cached
				if page <= 5 and page >= 1:
					#check page exists
					if (page-1)*PAGE_SIZE <= saved_len:

						# if not PAGE_SIZE number of values, return remaining
						if saved_len-(page-1)*PAGE_SIZE < PAGE_SIZE:
							extracted = saved[(page-1)*PAGE_SIZE:]
						else: # else return page
							extracted = saved[(page-1)*PAGE_SIZE:page*PAGE_SIZE]

							# if there are more values, then setup next
							if saved_len > page*PAGE_SIZE: 
								template_values['next'] = str(extracted[-1]['realtime'])
								template_values['nextpage'] = page + 1

						# if not on first page, setup back  
						if page > 1:
							template_values['back'] = str(extracted[0]['realtime'])
							template_values['backpage'] = page - 1

		# if could not retreive from cache
		if not extracted:
			# if values should be in cache, fetch values for cache

			# if page set, and page in range, get page for cache
			if (not page and not bookmark) or (page > 0 and page <=5): 
				logging.debug('cache miss, populate')
				# get 5 pages of most recent records and cache
				surveys = SurveyData.all().order('-timestamp').fetch(PAGE_SIZE*5 + 1)
				saved = extract_surveys (surveys)
				# if values returned, save in cache
				if surveys is not None:
					#memcache.set('saved', saved, 604800)
					memcache.set('saved', saved)

				saved_len = len(saved)

				# if no page set, return first page
				if not bookmark and not page: 
					if saved_len < PAGE_SIZE:
						extracted = saved
					else:
						extracted = saved[:PAGE_SIZE-1]
						# if there are more values, then setup next
						if saved_len > PAGE_SIZE: 
							template_values['next'] = str(extracted[-1]['realtime'])
							template_values['nextpage'] = 2
				elif (page-1)*PAGE_SIZE <= saved_len:
					if saved_len-(page-1)*PAGE_SIZE < PAGE_SIZE:
						extracted = saved[(page-1)*PAGE_SIZE:saved_len-1]
					else:
						extracted = saved[(page-1)*PAGE_SIZE:page*PAGE_SIZE]

						# if there are more values, then setup next
						if saved_len > page*PAGE_SIZE: 
							template_values['next'] = str(extracted[-1]['realtime'])
							template_values['nextpage'] = page + 1

					# if not on first page, setup back  
					if page > 1:
						template_values['back'] = str(extracted[0]['realtime'])
						template_values['backpage'] = page - 1

			else: # pages beyond 5th not cached
				logging.debug('not using cache')
				# determine direction to retreive records
				# if starts with '-', going backwards
				if bookmark.startswith('-'):
					forward = False
					bookmark = bookmark[1:]
				
				# if bookmark set, retrieve page relative to bookmark
				if bookmark:
					# string to datetime code from:
					#	http://aralbalkan.com/1512
					m = re.match(r'(.*?)(?:\.(\d+))?(([-+]\d{1,2}):(\d{2}))?$',
						str(bookmark))
					datestr, fractional, tzname, tzhour, tzmin = m.groups()
					if tzname is None:
						tz = None
					else:
						tzhour, tzmin = int(tzhour), int(tzmin)
						if tzhour == tzmin == 0:
							tzname = 'UTC'
						tz = FixedOffset(timedelta(hours=tzhour,
												   minutes=tzmin), tzname)
					x = datetime.datetime.strptime(datestr, "%Y-%m-%d %H:%M:%S")
					if fractional is None:
						fractional = '0'
						fracpower = 6 - len(fractional)
						fractional = float(fractional) * (10 ** fracpower)
					dt = x.replace(microsecond=int(fractional), tzinfo=tz)


					if forward:
						surveys = SurveyData.all().filter('timestamp <', dt).order('-timestamp').fetch(PAGE_SIZE+1)
						# if PAGE_SIZE + 1 rows returned, more pages to display
						if len(surveys) == PAGE_SIZE + 1:
							template_values['next'] = str(surveys[-2].timestamp)
							if page is not None:
								logging.debug(page)
								template_values['nextpage'] = page + 1
							surveys = surveys[:PAGE_SIZE]

						# if bookmark set, assume there was a back page
						template_values['back'] = '-'+str(surveys[0].timestamp)
						if page is not None:
							template_values['backpage'] = page - 1
					else:
						surveys = SurveyData.all().filter('timestamp >', dt).order('timestamp').fetch(PAGE_SIZE+1)
						# if PAGE_SIZE + 1 rows returned, more pages to diplay
						if len(surveys) == PAGE_SIZE + 1:
							template_values['back'] = '-'+str(surveys[-2].timestamp)
							if page is not None:
								template_values['backpage'] = page - 1
							surveys = surveys[:PAGE_SIZE]
						# if bookmark set, assume there is a next page
						template_values['next'] = str(surveys[0].timestamp)
						if page is not None:
							template_values['nextpage'] = page + 1
						# reverse order of results since they were returned backwards by query
						surveys.reverse()
				else: # if no bookmark set, retrieve first records
					surveys = SurveyData.all().order('-timestamp').fetch(PAGE_SIZE+1)
					if len(surveys) == PAGE_SIZE + 1:
						template_values['next'] = str(surveys[-2].timestamp)
						template_values['nextpage'] = 2
						surveys = surveys[:PAGE_SIZE]

				extracted = extract_surveys (surveys)


		template_values['surveys'] = extracted 

		path = os.path.join (os.path.dirname(__file__), 'views/data.html')
		self.response.out.write (template.render(path, template_values))
	# end get method
# End DataPage Class

# list data page (this function currently not in use): /data 
# See DataByDatePage above
class DataPage(webapp.RequestHandler):
	# display data in table format
	def get(self):
		if os.environ.get('HTTP_HOST'):
			base_url = 'http://' + os.environ['HTTP_HOST'] + '/'
		else:
			base_url = 'http://' + os.environ['SERVER_NAME'] + '/'

		# get bookmark
		bookmark = self.request.get('bookmark')

		logging.debug(self.request.get('bookmark'))

		template_values = { 'base_url' : base_url }

		forward = True

		# determine direction to retreive records
		# if starts with '-', going backwards
		if bookmark.startswith('-'):
			forward = False
			bookmark = bookmark[1:]
		
		# if bookmark set, retrieve page relative to bookmark
		if bookmark:
			db_key = db.Key(bookmark)
			if forward:
				surveys = SurveyData.all().filter('__key__ >', db_key).order('__key__').fetch(PAGE_SIZE+1)
				# if PAGE_SIZE + 1 rows returned, more pages to display
				if len(surveys) == PAGE_SIZE + 1:
					template_values['next'] = str(surveys[-2].key())
					surveys = surveys[:PAGE_SIZE]

				# if bookmark set, assume there was a back page
				template_values['back'] = '-'+str(surveys[0].key())
			else:
				surveys = SurveyData.all().filter('__key__ <', db_key).order('-__key__').fetch(PAGE_SIZE+1)
				# if PAGE_SIZE + 1 rows returned, more pages to diplay
				if len(surveys) == PAGE_SIZE + 1:
					template_values['back'] = '-'+str(surveys[-2].key())
					surveys = surveys[:PAGE_SIZE]
				# if bookmark set, assume there is a next page
				template_values['next'] = str(surveys[0].key())
				# reverse order of results since they were returned backwards by query
				surveys.reverse()
		else: # if no bookmark set, retrieve first records
			surveys = SurveyData.all().order('__key__').fetch(PAGE_SIZE+1)
			if len(surveys) == PAGE_SIZE + 1:
				template_values['next'] = str(surveys[-2].key())
				surveys = surveys[:PAGE_SIZE]

		extracted = extract_surveys (surveys)
		template_values['surveys'] = extracted 

		path = os.path.join (os.path.dirname(__file__), 'views/data.html')
		self.response.out.write (template.render(path, template_values))
	# end get method
# End DataPage Class

# debugging stuff...
class DataDebugPage(webapp.RequestHandler):
	def get(self):
		if os.environ.get('HTTP_HOST'):
			base_url = 'http://' + os.environ['HTTP_HOST'] + '/'
		else:
			base_url = 'http://' + os.environ['SERVER_NAME'] + '/'

		'''
		#populate daily stats models

		categories = {}
		subcategories = {}

		result = db.GqlQuery("SELECT * FROM SurveyData")

		for row in result:
			pdt = row.timestamp - datetime.timedelta(hours=7)
			time_key = str(pdt).split(' ')[0]

			if not categories.has_key(time_key):
				categories[time_key] = {}

			if categories[time_key].has_key(str(row.category)):
				categories[time_key][str(row.category)]['count'] += 1
				categories[time_key][str(row.category)]['total'] += float(row.stressval)
			else:
				tmp = {'count':1, 'total':float(row.stressval)}
				categories[time_key][str(row.category)] = tmp

			if not subcategories.has_key(time_key):
				subcategories[time_key] = {}

			if subcategories[time_key].has_key(str(row.subcategory)):
				subcategories[time_key][str(row.subcategory)]['count'] += 1
				subcategories[time_key][str(row.subcategory)]['total'] += float(row.stressval)
			else:
				tmp = {	'count':1, 
					'total':float(row.stressval),
					'category':str(row.category)}
				subcategories[time_key][str(row.subcategory)] = tmp

		for date_key in categories.keys():
			for cat_keys in categories[date_key].keys():
				cstat = DailyCategoryStat()
				cstat.category = cat_keys
				cstat.count = categories[date_key][cat_keys]['count']
				cstat.total = categories[date_key][cat_keys]['total']
				datestr = date_key.split('.')[0]
				dt = datetime.datetime.strptime(datestr, "%Y-%m-%d")
				x = datetime.date(dt.year, dt.month, dt.day)
				cstat.date = x
				cstat.put()
				categories[date_key][cat_keys]['db_key'] = cstat.key()
			
		for date_key in categories.keys():
			for subcat_keys in subcategories[date_key].keys():
				scstat = DailySubCategoryStat()
				scstat.category = subcategories[date_key][subcat_keys]['category']

				if categories.has_key(date_key):
					if categories[date_key].has_key(subcategories[date_key][subcat_keys]['category']):
						scstat.category_key = categories[date_key][subcategories[date_key][subcat_keys]['category']]['db_key']
				scstat.subcategory = subcat_keys
				datestr = date_key.split('.')[0]
				dt = datetime.datetime.strptime(datestr, "%Y-%m-%d")
				x = datetime.date(dt.year, dt.month, dt.day)
				scstat.date = x
				scstat.count = subcategories[date_key][subcat_keys]['count']
				scstat.total = subcategories[date_key][subcat_keys]['total']
				scstat.put()
		'''

		'''
		# populate stats models
		for row in result:
			if categories.has_key(str(row.category)):
				categories[str(row.category)]['count'] += 1
				categories[str(row.category)]['total'] += float(row.stressval)
			else:
				tmp = {'count':1, 'total':float(row.stressval)}
				categories[str(row.category)] = tmp

			if subcategories.has_key(str(row.subcategory)):
				subcategories[str(row.subcategory)]['count'] += 1
				subcategories[str(row.subcategory)]['total'] += float(row.stressval)
			else:
				tmp = {	'count':1, 
					'total':float(row.stressval),
					'category':str(row.category)}
				subcategories[str(row.subcategory)] = tmp


		for cat_keys in categories.keys():
			cstat = CategoryStat()
			cstat.category = cat_keys
			cstat.count = categories[cat_keys]['count']
			cstat.total = categories[cat_keys]['total']
			cstat.put()
			categories[cat_keys]['db_key'] = cstat.key()
			
		for subcat_keys in subcategories.keys():
			scstat = SubCategoryStat()
			scstat.category = subcategories[subcat_keys]['category']
			scstat.category_key = categories[subcategories[subcat_keys]['category']]['db_key']
			scstat.subcategory = subcat_keys
			scstat.count = subcategories[subcat_keys]['count']
			scstat.total = subcategories[subcat_keys]['total']
			scstat.put()
		'''	


		'''
		self.response.out.write(datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S UTC")+"<br>\n")
		x = datetime.datetime.utcnow() + datetime.timedelta(days=30)

		self.response.out.write(str(x)+"<br>\n")
		'''


		'''
		# create thumbnails
		imagelist = SurveyPhoto.all().fetch(20, offset=105)

		for i in imagelist:
			img = images.Image(i.photo)
			img.resize(width=180, height=130)
			i.thumb = img.execute_transforms(output_encoding=images.JPEG)
			i.put()
		'''

		'''
		surveys = SurveyData.all().fetch(20)
		extracted = extract_surveys (surveys)
		template_values = { 'surveys' : surveys, 'base_url' : base_url }
		path = os.path.join (os.path.dirname(__file__), 'views/data_debug.html')
		self.response.out.write (template.render(path, template_values))
		'''
		''' #fix database
		for s in surveys:
			if s.photo:
				s.hasphoto = True
				s.put()
		'''
		'''
		#copy database
		for s in surveys:
			new_survey = SurveyData()

			new_survey.username = s.username
			new_survey.timestamp = s.timestamp
			new_survey.longitude = s.longitude
			new_survey.latitude = s.latitude
			new_survey.stressval = s.stressval
			new_survey.comments = s.comments
			new_survey.category = s.category
			new_survey.subcategory = s.subcategory
			new_survey.version = s.version

			if s.photo:
				new_survey.hasphoto = True
				new_photo = SurveyPhoto()
				new_photo.photo = s.photo
				new_photo.put()
				new_survey.photo_ref = new_photo.key()
			else:
				new_survey.hasphoto = False
				new_survey.photo_ref = None

			new_survey.put()
		'''
		#extracted = extract_surveys (surveys)
		#template_values = { 'surveys' : surveys, 'base_url' : base_url }
		#path = os.path.join (os.path.dirname(__file__), 'views/data_debug.html')
		#self.response.out.write (template.render(path, template_values))

# handler for: /data_download_all.csv
class DownloadAllData(webapp.RequestHandler):
	# returns csv of all data
	def get(self):
		# check cache for csv dump
		# I'm not sure at what point this will become infesible (too large for the cache)
		data = memcache.get('csv')

		# if all data in cache, output and done
		if data is not None:
			self.response.headers['Content-type'] = 'text/csv'
			self.response.out.write(data)
			return

		# if cache miss, check if csv blob exist
		data_csv = SurveyCSV.all().get()

		# if csv blob exist, set in cache and output
		if data_csv is not None:
			# add to cache for 1 week
			#memcache.set('csv', data_csv.csv, 604800)
			memcache.set('csv', data_csv.csv)

			self.response.headers['Content-type'] = 'text/csv'
			self.response.out.write('from blob\n')
			self.response.out.write(data_csv.csv)
			return


		# you should never get here except for the first time this url is called
		# if you need to populate the blob, make sure to call this url
		#	before any requests to write new data or the blob will start from that entry instead
		# NOTE: this will probably only work as long as the number of entries in your survey is low
		#	If there are too many entries already, this will likely time out
		#	I have added page as a property of the model incase we need it in future
		surveys = SurveyData.all().order('timestamp').fetch(1000)

		if os.environ.get('HTTP_HOST'):
			base_url = os.environ['HTTP_HOST']
		else:
			base_url = os.environ['SERVER_NAME']

		counter = 0
		last_entry_date = ''
		page = 1

		# setup csv
		output = cStringIO.StringIO()
		writer = csv.writer(output, delimiter=',')

		header_row = [	'id',
						'timestamp',
						'latitude',
						'longitude',
						'stress_value',
						'category',
						'subcategory',
						'comments',
						'image_url'
						]

		writer.writerow(header_row)
		for s in surveys:
			photo_url = ''
			if s.hasphoto:
				photo_url = 'http://' + base_url + "/get_an_image?key="+str(s.photo_ref.key())

			else:
				photo_url = 'no_image'
			new_row = [
					str(s.key()),
					s.timestamp,
					s.latitude,
					s.longitude,
					s.stressval,
					s.category,
					s.subcategory,
					s.comments,
					photo_url
					]
			writer.writerow(new_row)
			counter += 1
			last_entry_date = s.timestamp

		# write blob csv so we dont have to do this again
		insert_csv = SurveyCSV()
		insert_csv.csv = db.Blob(output.getvalue())
		insert_csv.last_entry_date = last_entry_date
		insert_csv.count = counter
		insert_csv.page = page
		insert_csv.put()

		# add to cache for 1 week (writes should update this cached value)
		#memcache.set('csv', output.getvalue(), 604800)
		memcache.set('csv', output.getvalue())

		self.response.headers['Content-type'] = 'text/csv'
		self.response.out.write(output.getvalue())
	# end get method
# End DownloadAllData

# handler for: /data_download_all_test
class DownloadAllDataTest(webapp.RequestHandler):
	# returns csv of all data
	def get(self):
		output = cStringIO.StringIO()
		writer = csv.writer(output, delimiter=',')

		header_row = [
						'timestamp',
						'latitude',
						'longitude',
						'stress_value',
						'category',
						'subcategory',
						'comments',
						'image_url'
						]

		writer.writerow(header_row)


		#surveys = SurveyData.all().fetch(1000)

		if os.environ.get('HTTP_HOST'):
			base_url = os.environ['HTTP_HOST']
		else:
			base_url = os.environ['SERVER_NAME']

		d = {}
		i = 0
		for s in range(0, 1000):
			photo_url = 'http://' + base_url + "/get_an_image?key="+str(s)

			new_row = [
					s,
					s,
					s,
					s,
					s,
					s,
					s,
					photo_url
					]
			writer.writerow(new_row)

			e = {}
			e['latitude'] = s
			e['longitude'] = s
			e['stressval'] = s
			e['comments'] = s
			e['key'] = s
			e['version'] = s
			e['photo_key'] = None

			d[i] = e;
			i = i + 1

		if i > 0:
			self.response.out.write(json.dumps(d))
		else:
			self.response.out.write("no data so far")
	# end get method

		#self.response.headers['Content-type'] = 'text/csv'
		self.response.out.write(output.getvalue())
	# end get method
# End DownloadAllData

# base class to be extended by other handlers needing oauth
class BaseHandler(webapp.RequestHandler):
	def __init__(self, *args, **kwargs):
		self.oauth_server = oauth.OAuthServer(DataStore())
		self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_PLAINTEXT())
		self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_HMAC_SHA1())
	# end __init__ method

	def send_oauth_error(self, err=None):
		self.response.clear()
		if os.environ.get('HTTP_HOST'):
			base_url = os.environ['HTTP_HOST']
		else:
			base_url = os.environ['SERVER_NAME']

		realm_url = 'http://' + base_url

		header = oauth.build_authenticate_header(realm=realm_url)
		for k,v in header.iteritems():
			self.response.headers.add_header(k, v)
		self.response.set_status(401, str(err.message))
		logging.error(err.message)
	# end send_oauth_error method

	def get(self):
		self.handler()
	# end get method

	def post(self):
		self.handler()
	# end post method

	def handler(self):
		pass
	# end handler method

	# get the request
	def construct_request(self, token_type = ''):
		logging.debug('\n\n' + token_type + 'Token------')
		logging.debug(self.request.method)
		logging.debug(self.request.url)
		logging.debug(self.request.headers)

		# get any extra parameters required by server
		self.paramdict = {}
		for j in self.request.arguments():
			self.paramdict[j] = self.request.get(j)
		logging.debug('parameters received: ' +str(self.paramdict))

		# construct the oauth request from the request parameters
		try:
			oauth_request = oauth.OAuthRequest.from_request(self.request.method, self.request.url, headers=self.request.headers, parameters=self.paramdict)
			return oauth_request
		except oauthOauthError, err:
			self.send_oauth_error(oauth.OAuthError('could not create oauth_request'))
			self.send_oauth_error(err)
			return False

		# extra check... 
		if not oauth_request:
			self.send_oauth_error(oauth.OAuthError('could not create oauth_request'))
			return False
# End BaseHandler class

# handler for: /request_token
class RequestTokenHandler(BaseHandler):
	def handler(self):
		oauth_request = self.construct_request('Request')
		if not oauth_request:
			self.send_oauth_error(oauth.OAuthError('could not create oauth_request'))
			return

		try:
			token = self.oauth_server.fetch_request_token(oauth_request)

			self.response.out.write(token.to_string())
			logging.debug('Request Token created')
		except oauth.OAuthError, err:
			self.send_oauth_error(err)
	# end handler method
# End RequestTokenHandler class

# handler for: /authorize
# required fields: 
# - username: string 
# - password: string, sha1 of plaintext password
# TODO: Change this back into a normal user authorize....
#	redirect to login page, have user authorize app, and redirect to callback if one provided...
class UserAuthorize(BaseHandler):
	def handler(self):
		oauth_request = self.construct_request('Authorize')
		if not oauth_request:
			self.send_oauth_error(oauth.OAuthError('could not create oauth_request'))
			return
	
		try:
			username = None
			password = None
			# set by construct_request
			if 'username' in self.paramdict:
				username = self.paramdict['username']
			if 'password' in self.paramdict:
				password = self.paramdict['password']

			if not username or not password:
				self.response.set_status(401, 'missing username or password')
				logging.error('missing username or password')
				return

			ukey = UserTable().check_valid_password(username, password)

			if not ukey:
				self.response.set_status(401, 'incorrect username or password')
				logging.error('incorrect username or password')
				return

			# perform user authorize
			token = self.oauth_server.fetch_request_token(oauth_request)
			token = self.oauth_server.authorize_token(token, ukey)
			logging.debug(token)

			logging.debug(token.to_string())

			self.response.out.write(token.get_callback_url())
			logging.debug(token.get_callback_url())
		except oauth.OAuthError, err:
			self.send_oauth_error(err)
	# end handler method
# End UserAuthorize Class

# handler for: /access_token
class AccessTokenHandler(BaseHandler):
	def handler(self):
		oauth_request = self.construct_request('Access')
		if not oauth_request:
			self.send_oauth_error(oauth.OAuthError('could not create oauth_request'))
			return

		try:
			token = self.oauth_server.fetch_access_token(oauth_request)

			self.response.out.write(token.to_string())
		except oauth.OAuthError, err:
			self.send_oauth_error(err)
	# end handler method
# End AccessTokenHandler Class

# handler for: /authorize_access
# cheat for mobile phone so no back and forth with redirects...
# access as if fetching request token
# also send username, sha1 of password
# required fields: 
# - username: string 
# - password: string, sha1 of plaintext password
# returns access token
class AuthorizeAccessHandler(BaseHandler):
	def handler(self):
		oauth_request = self.construct_request('AuthorizeAccess')
		if not oauth_request:
			self.send_oauth_error(oauth.OAuthError('could not create oauth_request'))
			return

		try:
			# request token
			token = self.oauth_server.fetch_request_token(oauth_request)
			logging.debug('Request Token created: ' + token.to_string())

			username = None
			password = None

			# check user 
			if 'username' in self.paramdict:
				username = self.paramdict['username']
			if 'password' in self.paramdict:
				password = self.paramdict['password']

			if not username or not password:
				self.response.set_status(401, 'missing username or password')
				logging.error('missing username or password')
				return

			ukey = UserTable().check_valid_password(username, password)

			if not ukey:
				self.response.set_status(401, 'incorrect username or password')
				logging.error('incorrect username or password')
				return

			# perform user authorize
			token = self.oauth_server.authorize_token(token, ukey)
			logging.debug('Token authorized: ' + token.to_string())

			# create access token
			consumer = Consumer().get_consumer(oauth_request.get_parameter('oauth_consumer_key'))

			oauth_request.set_parameter('oauth_verifier', token.verifier)
			oauth_request.set_parameter('oauth_token', token.key)

			oauth_request.sign_request(oauth.OAuthSignatureMethod_PLAINTEXT(), consumer, token)

			logging.debug('Current OAuth Param: ' + str(oauth_request.parameters))
			token = self.oauth_server.fetch_access_token(oauth_request)

			self.response.out.write(token.to_string())
		except oauth.OAuthError, err:
			self.send_oauth_error(err)
	# end handler method
# End AuthorizeAccessHandler Class

# res1
# currently not used. 
class ProtectedResourceHandler(BaseHandler):
	def handler(self):
		oauth_request = self.construct_request('Protected')
		if not oauth_request:
			self.send_oauth_error(oauth.OAuthError('could not create oauth_request'))
			return

		logging.debug(oauth_request.parameters)
		try:
			consumer, token, params = self.oauth_server.verify_request(oauth_request)

			if not ResourceTable().check_valid_consumer('res1', consumer.key):
				self.send_oauth_error(oauth.OAuthError('consumer may not access this resource'))
				return
			logging.debug('token string: '+token.to_string())

			s = SurveyData()

			# check user 
			if 'username' in params:
				s.username = params['username']

			if 'longitude' in params:
				s.longitude = params['longitude']

			if 'latitude' in params:
				s.latitude = params['latitude']

			if 'stressval' in params:
				s.stressval = float(params['stressval'])

			if 'comments' in params:
				s.comments = params['comments']

			if 'version' in params:
				s.version = params['version']

			if 'file' in params:
				file_content = params['file']
				if file_content:
					try:
						# upload image as blob to SurveyPhoto
						new_photo = SurveyPhoto()
						new_photo.photo = db.Blob(file_content)
						# create a thumbnail of image to store in SurveyPhoto
						tmb = images.Image(new_photo.photo)
						tmb.resize(width=180, height=130)
						# execute resize
						new_photo.thumb = tmb.execute_transforms(output_encoding=images.JPEG)
						# insert
						new_photo.put()
						# set reference to photo for SurveyData
						s.photo_ref = new_photo.key()
						s.hasphoto = True
					except TypeError:
						s.photo_ref = None
						s.hasphoto = False
				else:
					s.photo_ref = None
					s.hasphoto = False

			s.put()

		except oauth.OAuthError, err:
			self.send_oauth_error(err)
	# end handler method
# End ProtectedResourceHandler Class

# handler for: /protected_upload2
# required fields:
#	- oauth_token: string containing access key
# this is a temporary hack...
class ProtectedResourceHandler2(webapp.RequestHandler):
	def post(self):
		self.handle()
	def get(self):
		self.handle()
	def handle(self):
		logging.debug('\n\nProtected Resource 2------')
		logging.debug(self.request.method)
		logging.debug(self.request.url)
		logging.debug(self.request.headers)

		# get any extra parameters required by server
		self.paramdict = {}
		for j in self.request.arguments():
			self.paramdict[j] = self.request.get(j)
		logging.debug('parameters received: ' +str(self.paramdict))

		req_token = self.request.get('oauth_token')

		if req_token != '':
			try :
				t = db.GqlQuery("SELECT * FROM Token WHERE ckey = :1", req_token).get()

				if not t:
					logging.error('if you got here, token lookup failed.')
					self.error(401)
					return

				s = SurveyData()

				s.username = t.user
				s.longitude = self.request.get('longitude')
				s.latitude = self.request.get('latitude')
				s.stressval = float(self.request.get('stressval'))
				s.comments = str(self.request.get('comments')).replace('\n', ' ')
				s.category = self.request.get('category')
				s.subcategory = self.request.get('subcategory')
				s.version = self.request.get('version')

				file_content = self.request.get('file')

				if file_content:
					try:
						# upload image as blob to SurveyPhoto
						new_photo = SurveyPhoto()
						new_photo.photo = db.Blob(file_content)
						# create a thumbnail of image to store in SurveyPhoto
						tmb = images.Image(new_photo.photo)
						tmb.resize(width=180, height=130)
						# execute resize
						new_photo.thumb = tmb.execute_transforms(output_encoding=images.JPEG)
						# insert
						new_photo.put()
						# set reference to photo for SurveyData
						s.photo_ref = new_photo.key()
						s.hasphoto = True
					except TypeError:
						s.photo_ref = None
						s.hasphoto = False
				else:
					s.photo_ref = None
					s.hasphoto = False

				s.put()

				# update running stats (this should probably be moved to the task queue)
				# TODO: cache key & stats and create transaction
				subcat = SubCategoryStat.all().filter('subcategory =', s.subcategory).get()
				if not subcat:
					cat = CategoryStat.all().filter('category = ', s.category).get()

					if not cat:
						cat = CategoryStat()
						cat.category = s.category
						cat.count = 1
						cat.total = s.stressval
						cat.put()
					else:
						cat.count += 1
						cat.total += s.stressval
						cat.put()

					subcat = SubCategoryStat()
					subcat.category = s.category
					subcat.category_key = cat.key()
					subcat.subcategory = s.subcategory
					subcat.count = 1
					subcat.total = s.stressval
					subcat.put()
				else:
					subcat.count += 1
					subcat.total += s.stressval
					subcat.put()
					
					cat = subcat.category_key

					if not cat:
						cat = CategoryStat()
						cat.category = s.category
						cat.count = 1
						cat.total = s.stressval
						cat.put()
						subcat.category_key = cat.key()
					else:
						cat.count += 1
						cat.total += s.stressval
						cat.put()

				# update running daily stats (this should probably be moved to the task queue)
				# TODO: cache key & stats and create transaction
				pdt = s.timestamp - datetime.timedelta(hours=7)
				time_key = str(pdt).split(' ')[0]
				dt = datetime.datetime.strptime(time_key, "%Y-%m-%d")
				date = datetime.date(dt.year, dt.month, dt.day)

				subcat = DailySubCategoryStat.all().filter('subcategory =', s.subcategory).filter('date =', date).get()
				if not subcat:
					cat = DailyCategoryStat.all().filter('category = ', s.category).filter('date =', date).get()

					if not cat:
						cat = DailyCategoryStat()
						cat.category = s.category
						cat.count = 1
						cat.total = s.stressval
						cat.date = date
						cat.put()
					else:
						cat.count += 1
						cat.total += s.stressval
						cat.put()

					subcat = DailySubCategoryStat()
					subcat.category = s.category
					subcat.category_key = cat.key()
					subcat.subcategory = s.subcategory
					subcat.count = 1
					subcat.total = s.stressval
					subcat.date = date
					subcat.put()
				else:
					subcat.count += 1
					subcat.total += s.stressval
					subcat.put()
					
					cat = subcat.category_key

					if not cat:
						cat = DailyCategoryStat()
						cat.category = s.category
						cat.count = 1
						cat.total = s.stressval
						cat.date = date
						cat.put()
						subcat.category_key = cat.key()
					else:
						cat.count += 1
						cat.total += s.stressval
						cat.put()
					

				#write to csv blob and update memcache

				# init csv writer
				output = cStringIO.StringIO()
				writer = csv.writer(output, delimiter=',')

				base_url = ''
				if os.environ.get('HTTP_HOST'):
					base_url = os.environ['HTTP_HOST']
				else:
					base_url = os.environ['SERVER_NAME']

				# append to csv blob

				# this will have to change if multiple pages are ever needed (limits?)
				insert_csv = SurveyCSV.all().filter('page =', 1).get()

				# write header row if csv blob doesnt exist yet
				if not insert_csv:
					header_row = [	'id',
						'timestamp',
						'latitude',
						'longitude',
						'stress_value',
						'category',
						'subcategory',
						'comments',
						'image_url'
						]
					writer.writerow(header_row)

				# form image url
				if s.hasphoto:
					photo_url = 'http://' + base_url + "/get_an_image?key="+str(s.photo_ref.key())

				else:
					photo_url = 'no_image'

				# write csv data row
				new_row = [
						str(s.key()),
						s.timestamp,
						s.latitude,
						s.longitude,
						s.stressval,
						s.category,
						s.subcategory,
						s.comments,
						photo_url
						]
				writer.writerow(new_row)

				# create new blob if one does not exist
				if not insert_csv:
					insert_csv = SurveyCSV()
					insert_csv.csv = db.Blob(output.getvalue())
					insert_csv.last_entry_date = s.timestamp
					insert_csv.count = 1
					insert_csv.page = 1
				else:	#if blob exists, append and update
					insert_csv.csv += output.getvalue()
					insert_csv.last_entry_date = s.timestamp
					insert_csv.count += 1

				insert_csv.put()

				# add to cache for 1 week (writes should update this cached value)
				#memcache.set('csv', output.getvalue(), 604800)
				memcache.set('csv', output.getvalue())


				try:
					# update data page cache with new value, pop oldest value
					saved = memcache.get('saved')
					if saved is not None:
						s_list = []
						s_list.append(s)
						extract = extract_surveys(s_list)
						d = deque(saved)
						d.pop()
						d.appendleft(extract[0])
						memcache.set('saved', list(d))
				except:
					logging.debug('cache write failed')


				# we should convert the dict to a list so this is easier to do
				try:
					# update point summary cache with new value, pop oldest value
					pointsummary = memcache.get('pointsummary')
					if pointsummary is not None:
						e = {}
						e['latitude'] = s.latitude
						e['longitude'] = s.longitude
						e['stressval'] = s.stressval
						e['comments'] = s.comments
						e['key'] = str(s.key())
						e['version'] = s.version
						if s.hasphoto:
							e['photo_key'] = str(s.photo_ref.key())
						else:
							e['photo_key'] = None

						d = {}
						d[0] = e
						for i in range(1,(50)):
							d[i] = pointsummary[i-1]
					
						memcache.set('pointsummary', d)
				except:
					logging.debug('point summary cache write failed')


			except (db.Error):
				logging.error('error inserting to database')
				self.error(401)
				return
		else:
			logging.error('request token empty')
			self.error(401)
	# end handle method
# End ProtectedResourceHandler2 Class

# handler for /create_consumer
# form to create a consumer key & setup permissions to access resources
class CreateConsumer(webapp.RequestHandler):
	def get(self):
		self.handle()
	def post(self):
		self.handle()
	def handle(self):
		self.response.out.write('''
<html>
<body>
<form action="/get_consumer" METHOD="POST">
	Select resources:
	resource 1 (read test): <input name="res1" type="checkbox" value="res1"><br />
	resource 2 (write test): <input name="res2" type="checkbox" value="res2"><br />
	resource 3 (some other resource): <input name="res3" type="checkbox" value="res3"><br />
	<input type="submit" name="submitted">
</form>
</body>
</html>
		''')
	# end handle method
# End CreateConsumer class

# handler for: /get_consumer
# create consumer key/secret & add to resource table
class GetConsumer(webapp.RequestHandler):
	def get(self):
		self.handle()
	def post(self):
		self.handle()
	def handle(self):
		if not self.request.get('submitted'):
			self.response.out.write('no')
			return

		allowed_res = ['res1', 'res2', 'res3']
		consumer = Consumer().insert_consumer('tester1')
		self.response.out.write('key: '+consumer.key+'<br />\n')
		self.response.out.write('pass: '+consumer.secret+'<br />\n')

		if self.request.get('res1') in allowed_res:
			if ResourceTable().create_resource(self.request.get('res1'), consumer.key):
				self.response.out.write('has permission on res 1<br />')
			else:
				self.response.out.write('could not grant on res 1<br />')
		if self.request.get('res2') in allowed_res:
			if ResourceTable().create_resource(self.request.get('res2'), consumer.key):
				self.response.out.write('has permission on res 2<br />')
			else:
				self.response.out.write('could not grant on res 2<br />')
		if self.request.get('res3') in allowed_res:
			if ResourceTable().create_resource(self.request.get('res3'), consumer.key):
				self.response.out.write('has permission on res 3<br />')
			else:
				self.response.out.write('could not grant on res 3<br />')
	# end handle
# End GetConsumer class
		
# handler for: /create_user
# form to set up new user
class CreateUser(webapp.RequestHandler):
	def get(self):
		self.handle()
	def post(self):
		self.handle()
	def handle(self):
		self.response.out.write('''
<html>
<body>
<form action="/confirm_user" METHOD="POST">
	username: <input name="username" type="text"><br />
	password: <input name="password" type="password"><br />
	confirm password: <input name="confirmpassword" type="password"><br />
	email: <input name="email" type="text"><br />
	<input type="submit">
</form>
</body>
</html>
		''')
	# end handle method
# End CreateUser class

# handler for: /confirm_user
# adds user
# required fields:
#	- username: string
#	- password: string
#	- confirmpassword: string - must match password
# optional:
#	- email: string
class ConfirmUser(webapp.RequestHandler):
	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')
		confirmpassword = self.request.get('confirmpassword')
		email = self.request.get('email')

		if not username or not password or not confirmpassword:
			self.response.set_status(401, 'Missing field')
			logging.error('Missing field')
			return
		if password != confirmpassword:
			self.response.set_status(401, 'Password mismatch')
			logging.error('Password mismatch')
			return

		if not UserTable().create_user(username, password, email):
			self.response.set_status(401, 'could not create user')
			logging.error('could not create user')
			return

		self.response.out.write('user added')
	# end post method
# End ConfirmUser Class

# handler for: /summary
# displays count of each category
class SummaryHandler(webapp.RequestHandler):
	def get(self):
		self.handle()
	# end get method

	def post(self):
		self.handle()
	# end post method

	def handle(self):
		result = db.GqlQuery("SELECT * FROM SurveyData")

		categories = []

		for row in result:
			if row.category not in categories:
				categories.append(row.category)

		summary = []
		data = []

		for cat in categories:
			cnt = db.GqlQuery("SELECT * FROM SurveyData WHERE category = :1", cat).count()
			row = { 'category':str(cat), 'count':str(cnt) }
			data.append(row)

		template_values = { 'summary' : data }
		path = os.path.join (os.path.dirname(__file__), 'views/summary.html')
		self.response.out.write (template.render(path, template_values))
	# end handle method
# End SummaryHandler Class

application = webapp.WSGIApplication(
									 [('/', HomePage),
									  ('/map', MapPage),
									  ('/clients', ClientsPage),
									  ('/about', AboutPage),
									  ('/get_point_summary', GetPointSummary),
									  ('/get_a_point', GetAPoint),
									  ('/get_an_image', GetAnImage),
									  ('/get_a_thumb', GetAThumb),
									  ('/get_image_thumb', GetImageThumb),
									  ('/data', DataByDatePage),
									  ('/data_download_all.csv', DownloadAllData),
									  ('/data_download_all_test', DownloadAllDataTest),
									  ('/request_token', RequestTokenHandler),
									  ('/authorize', UserAuthorize),
									  ('/access_token', AccessTokenHandler),
									  ('/authorize_access', AuthorizeAccessHandler),
									  ('/protected_upload', ProtectedResourceHandler),
									  ('/protected_upload2', ProtectedResourceHandler2),
									  ('/create_consumer', CreateConsumer),
									  ('/get_consumer', GetConsumer),
									  ('/create_user', CreateUser),
									  ('/confirm_user', ConfirmUser),
									  ('/summary', SummaryHandler),
									  ('/data_debug', DataDebugPage)],
									 debug=True)

def main():
	logging.getLogger().setLevel(logging.DEBUG)
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
