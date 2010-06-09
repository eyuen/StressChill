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

import helper
import phone
from datastore import *

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
				if s.hasphoto and s.photo_ref is not None:
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
				if s is not None:
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
				else:
					self.response.out.write("No data has been uploaded")
					return

			except (db.Error):
				self.response.out.write("No data has been uploaded")
				return
		self.response.out.write("No data has been uploaded")
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
					if s.flagged:
						self.redirect('/images/blocked.jpg')
					else:
						self.response.headers['Content-type'] = 'image/jpeg'
						self.response.headers['Last-Modified'] = s.timestamp.strftime("%a, %d %b %Y %H:%M:%S GMT")
						x = datetime.datetime.utcnow() + datetime.timedelta(days=30)
						#self.response.headers['Expires'] = x.strftime("%a, %d %b %Y %H:%M:%S GMT")
						#self.response.headers['Cache-Control'] = 'public, max-age=315360000'
						# forcing download due to quarantining images...
						self.response.headers['Cache-Control'] = 'no-cache, must-revalidate'
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
					if s.flagged:
						self.redirect('/images/blocked.jpg')
					else:
						self.response.headers['Content-type'] = 'image/jpeg'
						self.response.headers['Last-Modified'] = s.timestamp.strftime("%a, %d %b %Y %H:%M:%S GMT")
						x = datetime.datetime.now() + datetime.timedelta(days=30)
						#self.response.headers['Expires'] = x.strftime("%a, %d %b %Y %H:%M:%S GMT")
						#self.response.headers['Cache-Control'] = 'public, max-age=315360000'
						# forcing download due to quarantining images...
						self.response.headers['Cache-Control'] = 'no-cache, must-revalidate'
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

		helper.get_data_page(template_values, 'saved', None, None, bookmark, page)
		template_values['current_bookmark'] = bookmark
		template_values['current_page'] = page

		#template_values['surveys'] = extracted 
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
		data_csv = SurveyCSV.all().filter('page =', 1).get()

		# if csv blob exist, set in cache and output
		if data_csv is not None:
			# add to cache for 1 week
			#memcache.set('csv', data_csv.csv, 604800)
			memcache.set('csv', data_csv.csv)

			self.response.headers['Content-type'] = 'text/csv'
			self.response.out.write(data_csv.csv)
			return
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
				if categories[row.category]['count'] != 0:
					categories[row.category]['average'] = \
						categories[row.category]['total'] / categories[row.category]['count']

			if not categories[row.category]['subcategories'].has_key(row.subcategory):
				subavg = 0
				if row.count != 0:
					subavg = row.total / row.count
				categories[row.category]['subcategories'][row.subcategory] = { 
						'subcategory':row.subcategory, 
						'count':row.count,
						'total':row.total,
						'average':subavg 
						}
			else:
				categories[row.category]['subcategories'][row.subcategory]['count'] += row.count
				categories[row.category]['subcategories'][row.subcategory]['total'] += row.total
				if categories[row.category]['subcategories'][row.subcategory]['count'] != 0:
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

# displays count of each category
class ScoreBoard(webapp.RequestHandler):
	def get(self):
		ulist = UserTotalStat().all().order('-count')
		
		count = 0
		top_thirty = []

		for k in ulist:
			if count > 30:
				break

			count += 1
			
			row = {}
			row['username'] = k.username
			row['count'] = k.count

			top_thirty.append(row)

		template_values = {}
		template_values['topthirty'] = top_thirty
		template_values['scoreboard'] = True
		logging.debug(template_values)

		path = os.path.join (os.path.dirname(__file__), 'views/topscore.html')
		self.response.out.write (helper.render(self, path, template_values))
