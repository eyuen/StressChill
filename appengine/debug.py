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

# debugging stuff...
class DataDebugPage(webapp.RequestHandler):
	def get(self):
		if os.environ.get('HTTP_HOST'):
			base_url = 'http://' + os.environ['HTTP_HOST'] + '/'
		else:
			base_url = 'http://' + os.environ['SERVER_NAME'] + '/'

		'''
		csv_store = SurveyCSV.all().filter('page = ', 1).get()
		if csv_store is not None:
			# init csv reader
			csv_file = csv.DictReader(cStringIO.StringIO(str(csv_store.csv)))

			self.response.out.write("fieldnames: "+str(csv_file.fieldnames))
			header_keys = []
			for row in csv_file:
				self.response.out.write('rowkeys: '+str(row.keys()))
				header_keys = row.keys()
				break
			self.response.out.write('<br>fn: '+str(csv_file.fieldnames))
			# init csv writer
			output = cStringIO.StringIO()
			writer = csv.DictWriter(output, csv_file.fieldnames)

			self.response.out.write('<br>fn: '+str(csv_file.fieldnames))
			# output csv header
			header = {}
			for h in csv_file.fieldnames:
				header[h] = h
			writer.writerow(header)

			self.response.out.write(output.getvalue())
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
<form action="/debug/get_consumer" METHOD="POST">
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

# handler for: /test_session
# displays count of each category
class TestSession(webapp.RequestHandler):
	def get(self):
		sess = gmemsess.Session(self)

		if sess.is_new():
			self.response.out.write('New session - setting counter to 0.<br>')
			sess['myCounter']=0
			sess.save()
		else:
			sess['myCounter'] += 1
			self.response.out.write('Session counter is %d.'%(sess['myCounter']))
			if sess['myCounter'] < 3:
				sess.save()
			else:
				self.response.out.write('Invalidating cookie.')
				sess.invalidate()
	# end get method
# End TestSession

# handler for: /login
# display login page
class DisplayLogin(webapp.RequestHandler):
	def get(self):
		self.handler()
	def post(self):
		self.handler()
	def handler(self):
		sess = gmemsess.Session(self)

		if sess.has_key('username'):
			self.response.out.write('hello '+str(sess['username']))
			self.response.out.write('<br><a href="/debug/logout">logout</a>')
		else:
			template_values = { 'sess' : sess }
			path = os.path.join (os.path.dirname(__file__), 'views/login.html')
			self.response.out.write(template.render(path, template_values))
	#end handler method
# End DisplayLogin Class

# handler for: /confirmlogin
# display login page
class ConfirmLogin(webapp.RequestHandler):
	def get(self):
		self.handler()
	def post(self):
		self.handler()
	def handler(self):
		sess = gmemsess.Session(self)

		sess['username'] = self.request.get('username')
		sess.save()
		self.redirect('/debug/login')
	#end handler method
# End ConfirmLogin Class

# handler for: /logout
# destroy session and redirect to home page
class LogoutHandler(webapp.RequestHandler):
	def get(self):
		self.handler()
	def post(self):
		self.handler()
	def handler(self):
		sess = gmemsess.Session(self)
		sess.invalidate()

		self.redirect("/")
	#end handler method
# End ConfirmLogin Class

# Populates the daily stats Datastore
# this should only be run once to populate the datastore with existing values
class PopulateDailyStat(webapp.RequestHandler):
	def get(self):
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

# Populates the stats Datastore
# this should only be run once to populate the datastore with existing values
class PopulateStat(webapp.RequestHandler):
	def get(self):
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

# Populates the user stats Datastore
# this should only be run once to populate the datastore with existing values
class PopulateUserStat(webapp.RequestHandler):
	def get(self):
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

# Populates the user csv
# this should only be run once to populate the datastore with existing values
class PopulateUserCSV(webapp.RequestHandler):
	def get(self):
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


application = webapp.WSGIApplication(
									 [
									  ('/debug/create_consumer', CreateConsumer),
									  ('/debug/get_consumer', GetConsumer),
									  ('/debug/test_session', TestSession),
									  ('/debug/login', DisplayLogin),
									  ('/debug/confirmlogin', ConfirmLogin),
									  ('/debug/logout', LogoutHandler),
									  ('/debug/data_debug', DataDebugPage),
									  ('/debug/populate_daily_stat', PopulateDailyStat),
									  ('/debug/populate_stat', PopulateStat),
									  ('/debug/populate_user_stat', PopulateUserStat),
									  ('/debug/populate_user_csv', PopulateUserCSV)
									  ],
									 debug=True)

def main():
	logging.getLogger().setLevel(logging.DEBUG)
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
