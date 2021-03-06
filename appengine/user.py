import os
from django.utils import simplejson as json

import hashlib

import re
import datetime

import logging

import gmemsess

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
#from google.appengine.ext.db import stats
from google.appengine.ext.webapp import template
from google.appengine.api import memcache
from google.appengine.api import images
from google.appengine.api import mail

import cStringIO
import csv

from datastore import *
import helper

# number of observations shown per page
PAGE_SIZE = 20

# list data page: /user/data
class UserDataByDatePage(webapp.RequestHandler):
	# display data in table format
	# TODO: page results
	def get(self):
		sess = gmemsess.Session(self)

		# if session is new, user was not logged in, redirect
		if sess.is_new():
			sess['error'] = 'Please log in to view this page.'
			sess['redirect'] = '/user/data'
			sess.save()
			self.redirect('/user/login')
			return
		# if username not set in session, user not logged in, redirect
		if not sess.has_key('username'):
			sess['error'] = 'Please log in to view this page.'
			sess['redirect'] = '/user/data'
			sess.save()
			self.redirect('/user/login')
			return

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

		# form user data cache name
		cache_name = 'data_' + sess['userid']

		helper.get_data_page(template_values, cache_name, 'username =', sess['userid'], bookmark, page)

		template_values['userdata'] = True
		template_values['current_bookmark'] = bookmark
		template_values['current_page'] = page

		path = os.path.join (os.path.dirname(__file__), 'views/user_data.html')
		self.response.out.write (helper.render(self, path, template_values))
	# end get method
# End UserDataByDatePage Class

# map page: /user/map
class UserMapPage(webapp.RequestHandler):
	def get(self):
		sess = gmemsess.Session(self)

		# if session is new, user was not logged in, redirect
		if sess.is_new():
			sess['error'] = 'Please log in to view this page.'
			sess['redirect'] = '/user/map'
			sess.save()
			self.redirect('/user/login')
			return
		# if username not set in session, user not logged in, redirect
		if not sess.has_key('username'):
			sess['error'] = 'Please log in to view this page.'
			sess['redirect'] = '/user/map'
			sess.save()
			self.redirect('/user/login')
			return

		if os.environ.get('HTTP_HOST'):
			base_url = 'http://' + os.environ['HTTP_HOST'] + '/'
		else:
			base_url = 'http://' + os.environ['SERVER_NAME'] + '/'

		# form user data cache name
		cache_name = 'data_' + sess['userid']

		extracted = memcache.get(cache_name)

		if not extracted:
			logging.debug('cache miss, populate')
			# get 5 pages of most recent records and cache
			surveys = SurveyData.all().filter('username =', sess['userid']).order('-timestamp').fetch(PAGE_SIZE*5 + 1)
			extracted = helper.extract_surveys (surveys)
			# if values returned, save in cache
			if surveys is not None:
				memcache.set(cache_name, extracted)

		template_values = { 'surveys' : extracted, 'base_url' : base_url }
		template_values['usermap'] = True
		path = os.path.join (os.path.dirname(__file__), 'views/map.html')
		self.response.out.write (helper.render(self, path, template_values))
	# end get method
# End MapPage Class

# list data page: /user/data
class ClassDataByDatePage(webapp.RequestHandler):
	# display data in table format
	# TODO: page results
	def get(self):
		sess = gmemsess.Session(self)

		# if session is new, user was not logged in, redirect
		if sess.is_new():
			sess['error'] = 'Please log in to view this page.'
			sess['redirect'] = '/user/classdata'
			sess.save()
			self.redirect('/user/login')
			return
		# if username not set in session, user not logged in, redirect
		if not sess.has_key('username'):
			sess['error'] = 'Please log in to view this page.'
			sess['redirect'] = '/user/classdata'
			sess.save()
			self.redirect('/user/login')
			return

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

		# form user data cache name
		cache_name = 'class_' + sess['classid']

		helper.get_data_page(template_values, cache_name, 'classid =', sess['classid'], bookmark, page)

		template_values['classdata'] = True

		path = os.path.join (os.path.dirname(__file__), 'views/class_data.html')
		self.response.out.write (helper.render(self, path, template_values))
	# end get method
# End ClassDataByDatePage Class

# map page: /user/classmap
class ClassMapPage(webapp.RequestHandler):
	def get(self):
		sess = gmemsess.Session(self)

		# if session is new, user was not logged in, redirect
		if sess.is_new():
			sess['error'] = 'Please log in to view this page.'
			sess['redirect'] = '/user/classmap'
			sess.save()
			self.redirect('/user/login')
			return
		# if username not set in session, user not logged in, redirect
		if not sess.has_key('username'):
			sess['error'] = 'Please log in to view this page.'
			sess['redirect'] = '/user/classmap'
			sess.save()
			self.redirect('/user/login')
			return

		if os.environ.get('HTTP_HOST'):
			base_url = 'http://' + os.environ['HTTP_HOST'] + '/'
		else:
			base_url = 'http://' + os.environ['SERVER_NAME'] + '/'


		# form user data cache name
		cache_name = 'class_' + sess['classid']

		extracted = memcache.get(cache_name)

		if not extracted:
			logging.debug('cache miss, populate')
			# get 5 pages of most recent records and cache
			surveys = SurveyData.all().filter('classid =', sess['classid']).order('-timestamp').fetch(PAGE_SIZE*5 + 1)
			extracted = helper.extract_surveys (surveys)
			# if values returned, save in cache
			if surveys is not None:
				memcache.set(cache_name, extracted)

		template_values = { 'surveys' : extracted, 'base_url' : base_url }
		template_values['classmap'] = True
		path = os.path.join (os.path.dirname(__file__), 'views/map.html')
		self.response.out.write (helper.render(self, path, template_values))
	# end get method
# End MapPage Class

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
			self.redirect('/user/data')
		else:
			template_values = { 'sess' : sess }

			if sess.has_key('error'):
				template_values['error'] = sess['error']
				del sess['error']
				sess.save()

			path = os.path.join (os.path.dirname(__file__), 'views/login.html')
			self.response.out.write(helper.render(self, path, template_values))
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

		if not self.request.get('username') or not self.request.get('password'):
			sess['error'] = 'Missing username or password'
			sess.save()
			self.redirect('/user/login')
			return
		

		if sess.has_key('username'):
			if sess.has_key('redirect'):
				old_url = sess['redirect']
				del sess['redirect']
				self.redirect(old_url)
			else:
				self.redirect('/user/data')
					
		else:
			hashedval = hashlib.sha1(self.request.get('password'))
			sha1val = hashedval.hexdigest()

			uid = UserTable().check_valid_password(self.request.get('username'), sha1val)

			if not uid:
				sess['error'] = 'Incorrect Username or Password'
				sess.save()
				self.redirect('/user/login')
				return
			else:
				# get official class list from memcache if exists
				classlist = memcache.get('classlist')
				# if not exist, fetch from datastore
				if not classlist:
					cl = ClassList().all()

					classlist = []
					for c in cl:
						classlist.append(c.classid)

					# save to memcache to prevent this lookup from happening everytime
					memcache.set('classlist', classlist)

				# get classid of class, or set to 'tester'

				userclass = UserTable().all().filter('ckey =', uid).get()

				classid = 'testers'
				if userclass is not None:
					if userclass.classid in classlist:
						classid = userclass.classid

				sess['username'] = self.request.get('username')
				sess['userid'] = uid
				sess['classid'] = classid
				classentry = ClassList().all().filter('classid =',classid).get()
				if classentry:
					sess['classname'] = classentry.classname

				logging.debug('class name: ' + str(sess['classname']))
				if userclass.admin:
					sess['admin'] = True
				if userclass.teacher:
					sess['teacher'] = True

				sess['success'] = 'Welcome ' + sess['username']
				sess.save()
				if sess.has_key('redirect'):
					old_url = sess['redirect']
					del sess['redirect']
					self.redirect(old_url)
				else:
					self.redirect('/user/data')
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

# handler for: /user/delete
# display confirm delete page
class SetupDelete(webapp.RequestHandler):
	def get(self):
		sess = gmemsess.Session(self)

		bookmark = self.request.get('bookmark')
		page = self.request.get('page')

		# setup redirect strings
		data_redirect_str = '/user/data'
		delete_redirect_str = '/user/delete?key=' + self.request.get('key')
		if bookmark and len(bookmark) != 0:
			data_redirect_str += '?bookmark=' + str(bookmark)
			delete_redirect_str += '&bookmark=' + str(bookmark)
			if page and len(page) != 0:
				data_redirect_str += '&page=' + str(page)
				delete_redirect_str += '&page=' + str(page)
		elif page and len(page) != 0:
				data_redirect_str += '?page=' + str(page)
				delete_redirect_str += '&page=' + str(page)

		logging.debug('data redirect: ' + data_redirect_str)
		logging.debug('delete redirect: ' + delete_redirect_str)

		# redirect to login page if not logged in
		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			#sess['redirect'] = '/user/delete?key=' + self.request.get('key')
			sess['redirect'] = delete_redirect_str
			sess.save()
			self.redirect('/user/login')
			return
		
		# check if key set
		if not self.request.get('key'):
			sess['error'] = 'No observation was selected.'
			sess.save()
			self.redirect(data_redirect_str)
			return

		# check valid key
		try:
			db_key = db.Key(self.request.get('key'))
			if db_key.kind() != 'SurveyData':
				sess['error'] = 'Bad key.'
				sess.save()
				self.redirect(data_redirect_str)
				return

		except:
			sess['error'] = 'Bad key.'
			sess.save()
			self.redirect(data_redirect_str)
			return

		# check if user owns observation
		observation = db.get(self.request.get('key'))

		# if no observation exists with key, error
		if not observation:
			sess['error'] = 'No observation exists with this key or you do not have permission to delete this observation'
			sess.save()
			self.redirect(data_redirect_str)
			return

		# if user not have permission, error
		if observation.username != sess['userid']:
			sess['error'] = 'No observation exists with this key or you do not have permission to delete this observation'
			sess.save()
			self.redirect(data_redirect_str)
			return

		# format data...
		surveys = []
		surveys.append(observation)
		extracted = helper.extract_surveys(surveys)
		observation = extracted[0]

		if os.environ.get('HTTP_HOST'):
			base_url = 'http://' + os.environ['HTTP_HOST'] + '/'
		else:
			base_url = 'http://' + os.environ['SERVER_NAME'] + '/'

		# display delete confirmation page
		template_values = {'observation': observation, 'base_url':base_url}
		template_values['current_bookmark'] = bookmark
		template_values['current_page'] = page

		path = os.path.join (os.path.dirname(__file__), 'views/delete.html')
		self.response.out.write (helper.render(self, path, template_values))
	# end get method
# End SetupDelete Class

# handler for: /user/confirm_delete
# delete observation
class ConfirmDelete(webapp.RequestHandler):
	def post(self):
		sess = gmemsess.Session(self)

		bookmark = self.request.get('bookmark')
		page = self.request.get('page')

		# setup redirect strings
		data_redirect_str = '/user/data'
		delete_redirect_str = '/user/delete?key=' + self.request.get('key')
		if bookmark and len(bookmark) != 0:
			data_redirect_str += '?bookmark=' + str(bookmark)
			delete_redirect_str += '&bookmark=' + str(bookmark)
			if page and len(page) != 0:
				data_redirect_str += '&page=' + str(page)
				delete_redirect_str += '&page=' + str(page)
		elif page and len(page) != 0:
				data_redirect_str += '?page=' + str(page)
				delete_redirect_str += '&page=' + str(page)

		logging.debug('data redirect: ' + data_redirect_str)
		logging.debug('delete redirect: ' + delete_redirect_str)


		# redirect to login page if not logged in
		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			#sess['redirect'] = '/user/delete?key=' + self.request.get('key')
			sess['redirect'] = delete_redirect_str
			sess.save()
			self.redirect('/user/login')
			return

		# check if key set
		if not self.request.get('key'):
			sess['error'] = 'No observation was selected.'
			sess.save()
			self.redirect(data_redirect_str)
			return

		# check valid key
		try:
			db_key = db.Key(self.request.get('key'))
			if db_key.kind() != 'SurveyData':
				sess['error'] = 'Bad key.'
				sess.save()
				self.redirect(data_redirect_str)
				return
		except:
			sess['error'] = 'Bad key.'
			sess.save()
			self.redirect(data_redirect_str)
			return

		# check if user owns observation
		observation = db.get(self.request.get('key'))

		# if no observation exists with key, error
		if not observation:
			sess['error'] = 'No observation exists with this key or you do not have permission to delete this observation'
			sess.save()
			self.redirect(data_redirect_str)
			return

		# if user not have permission, error
		if observation.username != sess['userid']:
			sess['error'] = 'No observation exists with this key or you do not have permission to delete this observation'
			sess.save()
			self.redirect(data_redirect_str)
			return

		logging.debug('can delete: '+str(observation.key()))
		logging.debug('category: '+str(observation.category))
		logging.debug('subcategory: '+str(observation.subcategory))
		logging.debug('value: '+str(observation.stressval))
		logging.debug('hasphoto: '+str(observation.hasphoto))

		# delete any associated photo
		if observation.hasphoto:
			try:
				photo = observation.photo_ref
				logging.debug('delete photo: '+str(photo.key()))
				db.delete(photo)
			except:
				logging.debug('invalid photo reference')

		# decrement subcategory count and subtract from total
		subcatstat = SubCategoryStat().all().filter('category =', observation.category).filter('subcategory =', observation.subcategory).get()

		if subcatstat is not None:
			db.run_in_transaction(SubCategoryStat().decrement_stats, subcatstat.key(), observation.stressval)

		pdt = observation.timestamp - datetime.timedelta(hours=7)
		time_key = str(pdt).split(' ')[0]
		dt = datetime.datetime.strptime(time_key, "%Y-%m-%d")
		date = datetime.date(dt.year, dt.month, dt.day)

		# decrement daily subcategory count and subtract from total
		dailysubcatstat = DailySubCategoryStat().all().filter('category =', observation.category).filter('date =', date).filter('subcategory =', observation.subcategory).get()

		if dailysubcatstat is not None:
			db.run_in_transaction(DailySubCategoryStat().decrement_stats, dailysubcatstat.key(), observation.stressval)

		# decrement user count and subtract from total
		userstat = UserStat().all().filter('category =', observation.category).filter('subcategory =', observation.subcategory).filter('user_id =', sess['userid']).get()

		if userstat is not None:
			db.run_in_transaction(UserStat().decrement_stats, userstat.key(), observation.stressval)

		# decrement user total count
		userstat = UserTotalStat().all().filter('user_id =', sess['userid']).get()

		if userstat is not None:
			db.run_in_transaction(UserTotalStat().decrement_stats, userstat.key())

		# delete observation from csv blob
		# get csv blob
		csv_store = SurveyCSV.all().filter('page = ', 1).get()
		if csv_store is not None:
			db.run_in_transaction(SurveyCSV().delete_from_csv, csv_store.key(), observation.key())

		# delete observation from user csv blob
		# get csv blob
		csv_store = UserSurveyCSV.all().filter('page = ', 1).filter('userid =', sess['userid']).get()
		if csv_store is not None:
			db.run_in_transaction(UserSurveyCSV().delete_from_csv, csv_store.key(), observation.key())

		csv_store = ClassSurveyCSV.all().filter('page = ', 1).filter('classid =', sess['classid']).get()
		if csv_store is not None:
			db.run_in_transaction(ClassSurveyCSV().delete_from_csv, csv_store.key(), observation.key())
		
		# remove from clean csv if class member
		if sess['classid'] != 'testers':
			csv_store = CleanSurveyCSV.all().filter('page = ', 1).get()
			if csv_store is not None:
				db.run_in_transaction(CleanSurveyCSV().delete_from_csv, csv_store.key(), observation.key())

		# invalidate related cached items
		saved = memcache.get('saved')
		if saved is not None:
			oldest_date = saved[-1]['realtime']

			if oldest_date <= observation.timestamp:
				memcache.delete('saved')

		# form user data cache name
		cache_name = 'data_' + sess['userid']

		usersaved = memcache.get(cache_name)

		if usersaved is not None:
			oldest_date = usersaved[-1]['realtime']

			if oldest_date <= observation.timestamp:
				memcache.delete(cache_name)

		# form class data cache name
		cache_name = 'class_' + sess['classid']

		usersaved = memcache.get(cache_name)

		if usersaved is not None:
			oldest_date = usersaved[-1]['realtime']

			if oldest_date <= observation.timestamp:
				memcache.delete(cache_name)

		memcache.delete('csv')

		db.delete(observation)

		sess['success'] = 'Observation deleted.'
		sess.save()
		self.redirect(data_redirect_str)
	# end post method
# End ConfirmDelete Class

# handler for: /user/user_data_download.csv
class DownloadUserData(webapp.RequestHandler):
	# returns csv of all data
	def get(self):
		sess = gmemsess.Session(self)

		# redirect to login page if not logged in
		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			sess.save()
			self.redirect('/user/login')
			return

		# check if csv blob exist
		data_csv = UserSurveyCSV.all().filter('userid =', sess['userid']).get()

		# if csv blob exist, output
		if data_csv is not None:
			self.response.headers['Content-type'] = 'text/csv'
			self.response.out.write(data_csv.csv)
			return
	# end get method
# End DownloadAllData

# handler for: /user/summary
# displays count of each category
class UserSummaryHandler(webapp.RequestHandler):
	def get(self):
		self.handle()
	# end get method

	def post(self):
		self.handle()
	# end post method

	def handle(self):
		sess = gmemsess.Session(self)

		# redirect to login page if not logged in
		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			sess['redirect'] = '/user/summary'
			sess.save()
			self.redirect('/user/login')
			return

		result = UserStat().all().filter('user_id =', sess['userid'])

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

# handler for: /user/user_data_download.csv
class DownloadClassData(webapp.RequestHandler):
	# returns csv of all data
	def get(self):
		sess = gmemsess.Session(self)

		# redirect to login page if not logged in
		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			sess.save()
			self.redirect('/user/login')
			return

		# check if csv blob exist
		data_csv = ClassSurveyCSV.all().filter('classid =', sess['classid']).get()

		# if csv blob exist, output
		if data_csv is not None:
			self.response.headers['Content-type'] = 'text/csv'
			self.response.out.write(data_csv.csv)
			return

	# end get method
# End DownloadAllData

# displays users with highest observation count
class ClassScoreBoard(webapp.RequestHandler):
	def get(self):
		sess = gmemsess.Session(self)

		# redirect to login page if not logged in
		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			sess['redirect'] = '/user/class_score_board'
			sess.save()
			self.redirect('/user/login')
			return

		# get user stats
		result = UserStat().all().filter('user_id =', sess['userid'])

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


		template_values = { 'summary' : data }
		logging.debug(template_values)

		# get user's class scoreboard
		ulist = UserTotalStat().all().filter('class_id =', sess['classid']).order('-count')
		
		count = 0
		top_thirty = []

		for k in ulist:
			if count > 50:
				break

			count += 1
			
			row = {}
			row['rank'] = count
			row['username'] = k.username
			row['count'] = k.count
			if k.username == sess['username']:
				row['highlight'] = True
			else:
				row['highlight'] = False

			top_thirty.append(row)

		#template_values = {}
		# This now has more than 30 records in it...
		template_values['topthirty'] = top_thirty
		template_values['classscoreboard'] = True
		logging.debug(template_values)

		path = os.path.join (os.path.dirname(__file__), 'views/user_summary_score.html')
		self.response.out.write (helper.render(self, path, template_values))
	# end get method
# End ScoreBoard Class

class Contact(webapp.RequestHandler):
	def get(self):
		sess = gmemsess.Session(self)

		# redirect to login page if not logged in
		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			sess['redirect'] = '/user/contact'
			sess.save()
			self.redirect('/user/login')
			return

		template_values = {}

		path = os.path.join (os.path.dirname(__file__), 'views/contact.html')
		self.response.out.write (helper.render(self, path, template_values))

	def post(self):
		sess = gmemsess.Session(self)

		# redirect to login page if not logged in
		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			sess['redirect'] = '/user/contact'
			sess.save()
			self.redirect('/user/login')
			return

		if not self.request.get('teacher'):
			sess['error'] = 'Please enter your Teacher\'s last name'
			sess.save()
			self.redirect('/user/contact')
			return

		msgbody='User:' + sess['username'] + ' has requested to become part of class: ' + self.request.get('teacher') + '.\n'

		if self.request.get('additional'):
			msgbody+='Note:\n' + self.request.get('additional')


		mail.send_mail(sender="eric.m.yuen@gmail.com",
				to="eric.m.yuen@gmail.com",
				subject="Class Change Request",
				body=msgbody)
		
		sess['success'] = 'Your message has been sent. The admin will correct this as soon as possible'
		self.redirect('/')
		
# handler for: /user/data_download_clean.csv
class DownloadCleanData(webapp.RequestHandler):
	# returns csv of all data
	def get(self):
		# redirect to login page if not logged in
		sess = gmemsess.Session(self)

		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			sess['redirect'] = '/user/show_data_download'
			sess.save()
			self.redirect('/user/login')
			return

		data_csv = CleanSurveyCSV.all().filter('page =', 1).get()

		self.response.headers['Content-type'] = 'text/csv'
		self.response.out.write(data_csv.csv)
		return
	# end get method
# End DownloadAllData

# handler for: /user/show_data_download
class ShowDownload(webapp.RequestHandler):
	# show donwload link for clean data
	def get(self):
		# redirect to login page if not logged in
		sess = gmemsess.Session(self)

		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			sess['redirect'] = '/user/show_data_download'
			sess.save()
			self.redirect('/user/login')
			return

		path = os.path.join (os.path.dirname(__file__), 'views/show_download.html')
		self.response.out.write (helper.render(self, path, {}))



application = webapp.WSGIApplication(
									 [
									  ('/user/data', UserDataByDatePage),
									  ('/user/map', UserMapPage),
									  ('/user/classdata', ClassDataByDatePage),
									  ('/user/classmap', ClassMapPage),
									  ('/user/login', DisplayLogin),
									  ('/user/confirmlogin', ConfirmLogin),
									  ('/user/logout', LogoutHandler),
									  ('/user/delete', SetupDelete),
									  ('/user/confirm_delete', ConfirmDelete),
									  ('/user/summary', UserSummaryHandler),
									  ('/user/user_data_download.csv', DownloadUserData),
									  ('/user/class_data_download.csv', DownloadClassData),
									  ('/user/class_score_board', ClassScoreBoard),
									  ('/user/contact', Contact),
									  ('/user/data_download_clean.csv', DownloadCleanData),
									  ('/user/show_data_download', ShowDownload)
									 ],
									 debug=True)

def main():
	logging.getLogger().setLevel(logging.DEBUG)
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
