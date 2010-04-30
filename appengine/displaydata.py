import cgi
import os
from django.utils import simplejson as json
import oauth
import hashlib

from collections import deque

import re
import datetime

import logging

import gmemsess

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
import helper
import phone

# number of observations shown per page
PAGE_SIZE = 20

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
			extracted = helper.extract_surveys (surveys)
			if surveys is not None:
				#memcache.set('saved', extracted, 604800)
				memcache.set('saved', extracted)
		template_values = { 'surveys' : extracted, 'base_url' : base_url }
		template_values['map'] = True
		path = os.path.join (os.path.dirname(__file__), 'views/map.html')
		self.response.out.write (helper.render(self, path, template_values))
	# end get method
# End MapPage Class

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
		elif not bookmark:
			page = 1

		# fetch cached values if any
		saved = None
		extracted = None

		# if page set, and page in range, get page for cache
		if page > 0 and page <=5: 
			saved = memcache.get('saved')

			# if not in cache, try fetching from datastore
			if not saved:
				logging.debug('cache miss, populate')
				# get 5 pages of most recent records and cache
				surveys = SurveyData.all().order('-timestamp').fetch(PAGE_SIZE*5 + 1)
				saved = helper.extract_surveys (surveys)
				# if values returned, save in cache
				if surveys is not None:
					memcache.set('saved', saved)

			# if data, setup display
			if saved:
				# get page
				extracted = helper.get_page_from_cache(saved, page, PAGE_SIZE)

				logging.debug(len(extracted))

				# if got page
				if extracted is not None:
					if len(extracted) == PAGE_SIZE + 1:
						template_values['next'] = str(extracted[-1]['realtime'])
						template_values['nextpage'] = page + 1
						extracted = extracted[:PAGE_SIZE-1]

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

			extracted = helper.extract_surveys (surveys)

		template_values['surveys'] = extracted 
		template_values['data'] = True

		path = os.path.join (os.path.dirname(__file__), 'views/data.html')
		self.response.out.write (helper.render(self, path, template_values))
	# end get method
# End DataPage Class

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
						'userid', 
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
				try:
					photo_url = 'http://' + base_url + "/get_an_image?key="+str(s.photo_ref.key())
				except:
					photo_url = 'no_image'

			else:
				photo_url = 'no_image'

			hashedval = hashlib.sha1(str(s.key()))
			sha1val = hashedval.hexdigest()

			usersha1val = ''
			if s.username is not None:
				userhashedval = hashlib.sha1(s.username)
				usersha1val = userhashedval.hexdigest()
			else:
				usersha1val = 'none'

			new_row = [
					sha1val,
					usersha1val,
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
		result = SubCategoryStat().all()

		categories = {}

		for row in result:
			if not categories.has_key(row.category):
				categories[row.category] = {
						'category':row.category,
						'count':row.count,
						'total':row.total
						}
				if row.count != 0:
					categories[row.category]['average'] = row.total/row.count
				else:
					categories[row.category]['average'] = 0

				categories[row.category]['subcategories'] = {}
			else:
				categories[row.category]['count'] += row.count
				categories[row.category]['total'] += row.total
				if categories[row.category]['total'] != 0:
					categories[row.category]['average'] = \
						categories[row.category]['total'] / categories[row.category]['count']

			if not categories[row.category]['subcategories'].has_key(row.subcategory):
				subavg = 0
				if row.count != 0:
					subavg = row.total / row.count
				categories[row.category]['subcategories'][row.subcategory] = { 
						'subcategory':row.category, 
						'count':row.count,
						'total':row.total,
						'average':subavg 
						}
			else:
				categories[row.category]['subcategories'][row.subcategory]['count'] += row.count
				categories[row.category]['subcategories'][row.subcategory]['total'] += row.total
				if categories[row.category]['subcategories'][row.subcategory]['total'] != 0:
					categories[row.category]['subcategories'][row.subcategory]['average'] = \
						categories[row.category]['subcategories'][row.subcategory]['total'] / categories[row.category]['subcategories'][row.subcategory]['count']

		data = []
		for key,cat in categories.items():
			cat['subcatlist'] = []

			for skey,scat in cat['subcategories'].items():
				cat['subcatlist'].append(scat)

			del cat['subcategories']
			del cat['total']
			data.append(cat)
			#newrow = {}

			#ewrow['category'] = cat['category']
			#newrow['count'] = cat['count']
			#newrow['average'] = cat['average']


		template_values = { 'summary' : data }
		template_values['datasummary'] = True
		template_values['divstyle'] = ['span-11 colborder','span-12 last']

		logging.debug(template_values)

		path = os.path.join (os.path.dirname(__file__), 'views/summary.html')
		self.response.out.write (helper.render(self, path, template_values))
	# end handle method
# End SummaryHandler Class
