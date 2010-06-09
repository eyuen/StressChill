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

import cStringIO
import csv

from datastore import *
import helper

# number of observations shown per page
PAGE_SIZE = 20

# list data page: /admin/data
class AdminDataByDatePage(webapp.RequestHandler):
	# display data in table format
	# TODO: page results
	def get(self):
		sess = gmemsess.Session(self)

		# if session is new, user was not logged in, redirect
		if sess.is_new():
			sess['error'] = 'Please log in to view this page.'
			sess['redirect'] = '/admin/data'
			sess.save()
			self.redirect('/user/login')
			return
		# if username not set in session, user not logged in, redirect
		if not sess.has_key('username'):
			sess['error'] = 'Please log in to view this page.'
			sess['redirect'] = '/admin/data'
			sess.save()
			self.redirect('/user/login')
			return

		# if user not have permission, error
		admin_flag = UserTable().all().filter('ckey =', sess['userid']).get()

		if not admin_flag.admin:
			sess['error'] = 'You do not have permission to access this page'
			sess.save()
			self.redirect('/admin/data')
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
		cache_name = 'saved'

		helper.get_data_page(template_values, cache_name, None, None, bookmark, page)

		template_values['admindata'] = True
		template_values['current_bookmark'] = bookmark
		template_values['current_page'] = page

		path = os.path.join (os.path.dirname(__file__), 'views/admin_data.html')
		self.response.out.write (helper.render(self, path, template_values))
	# end get method
# End UserDataByDatePage Class

# handler for: /admin/detail
# display confirm delete page
class SetupQuarantine(webapp.RequestHandler):
	def get(self):
		sess = gmemsess.Session(self)

		# setup redirect strings
		bookmark = self.request.get('bookmark')
		page = self.request.get('page')

		data_redirect_str = '/admin/data'
		detail_redirect_str = '/admin/detail?key=' + self.request.get('key')
		if bookmark and len(bookmark) != 0:
			data_redirect_str += '?bookmark=' + str(bookmark)
			detail_redirect_str += '&bookmark=' + str(bookmark)
			if page and len(page) != 0:
				data_redirect_str += '&page=' + str(page)
				detail_redirect_str += '&page=' + str(page)
		elif page and len(page) != 0:
				data_redirect_str += '?page=' + str(page)
				detail_redirect_str += '&page=' + str(page)

		logging.debug('data direct: ' + data_redirect_str)
		logging.debug('detail direct: ' + detail_redirect_str)


		# redirect to login page if not logged in
		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			#sess['redirect'] = '/admin/detail?key=' + self.request.get('key')
			sess['redirect'] = detail_redirect_str
			sess.save()
			self.redirect('/user/login')
			return

		logging.debug('key: ' + str(self.request.get('key')))
		logging.debug('date: ' + str(self.request.get('date')))
		
		# check if key set or date set
		if not self.request.get('key') and not self.request.get('date'):
			sess['error'] = 'No observation was selected.'
			sess.save()
			self.redirect(data_redirect_str)
			return

		# check valid key
		db_key = None
		try:
			if self.request.get('key'):
				db_key = db.Key(self.request.get('key'))
				if db_key.kind() != 'SurveyData':
					sess['error'] = 'Bad key.'
					sess.save()
					self.redirect(data_redirect_str)
					return
			else:
				m = re.match(r'(.*?)(?:\.(\d+))?(([-+]\d{1,2}):(\d{2}))?$',
					str(self.request.get('date')))
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
				db_key = SurveyData().all().filter('timestamp =', dt).key()
		except:
			sess['error'] = 'Bad key.'
			sess.save()
			self.redirect(data_redirect_str)
			return

		# check if user owns observation
		observation = db.get(db_key)

		# if no observation exists with key, error
		if not observation:
			sess['error'] = 'No observation exists with this key or you do not have permission to delete this observation'
			sess.save()
			self.redirect(data_redirect_str)
			return

		# if user not have permission, error
		admin_flag = UserTable().all().filter('ckey =', sess['userid']).get()

		if not admin_flag.admin:
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

		path = os.path.join (os.path.dirname(__file__), 'views/quarantine_observation.html')
		self.response.out.write (helper.render(self, path, template_values))
	# end get method
# End SetupDelete Class

# handler for: /admin/quarantine_observation
# quarantine observation
class QuarantineObservation(webapp.RequestHandler):
	def post(self):
		sess = gmemsess.Session(self)

		bookmark = self.request.get('bookmark')
		page = self.request.get('page')

		data_redirect_str = '/admin/data'
		detail_redirect_str = '/admin/detail?key=' + self.request.get('key')
		if bookmark and len(bookmark) != 0:
			data_redirect_str += '?bookmark=' + str(bookmark)
			detail_redirect_str += '&bookmark=' + str(bookmark)
			if page and len(page) != 0:
				data_redirect_str += '&page=' + str(page)
				detail_redirect_str += '&page=' + str(page)
		elif page and len(page) != 0:
				data_redirect_str += '?page=' + str(page)
				detail_redirect_str += '&page=' + str(page)

		logging.debug('data direct: ' + data_redirect_str)
		logging.debug('detail direct: ' + detail_redirect_str)

		# redirect to login page if not logged in
		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			#sess['redirect'] = '/admin/detail?key=' + self.request.get('key')
			sess['redirect'] = detail_redirect_str
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
		admin_flag = UserTable().all().filter('ckey =', sess['userid']).get()

		if not admin_flag.admin:
			sess['error'] = 'No observation exists with this key or you do not have permission to delete this observation'
			sess.save()
			self.redirect(data_redirect_str)
			return

		logging.debug('quarantine: '+str(observation.key()))
		logging.debug('category: '+str(observation.category))
		logging.debug('subcategory: '+str(observation.subcategory))
		logging.debug('value: '+str(observation.stressval))
		logging.debug('hasphoto: '+str(observation.hasphoto))

		# quarantine any associated photo
		if observation.hasphoto:
			try:
				photo = observation.photo_ref
				logging.debug('quarantine photo: '+str(photo.key()))
				photo.flagged = True
				photo.put()
			except:
				logging.debug('invalid photo reference')

		# decrement subcategory count and subtract from total
		subcatstat = SubCategoryStat().all().filter('category =', observation.category).filter('subcategory =', observation.subcategory).get()

		db.run_in_transaction(SubCategoryStat().decrement_stats, subcatstat.key(), observation.stressval)

		pdt = observation.timestamp - datetime.timedelta(hours=7)
		time_key = str(pdt).split(' ')[0]
		dt = datetime.datetime.strptime(time_key, "%Y-%m-%d")
		date = datetime.date(dt.year, dt.month, dt.day)

		# decrement daily subcategory count and subtract from total
		dailysubcatstat = DailySubCategoryStat().all().filter('category =', observation.category).filter('date =', date).filter('subcategory =', observation.subcategory).get()

		db.run_in_transaction(DailySubCategoryStat().decrement_stats, dailysubcatstat.key(), observation.stressval)

		# decrement user count and subtract from total
		userstat = UserStat().all().filter('category =', observation.category).filter('subcategory =', observation.subcategory).get()

		db.run_in_transaction(UserStat().decrement_stats, userstat.key(), observation.stressval)

		# delete observation from csv blob
		# get csv blob
		csv_store = SurveyCSV.all().filter('page = ', 1).get()
		db.run_in_transaction(SurveyCSV().delete_from_csv, csv_store.key(), observation.key())

		# delete observation from user csv blob
		# get csv blob
		csv_store = UserSurveyCSV.all().filter('page = ', 1).filter('userid =', observation.username).get()
		db.run_in_transaction(UserSurveyCSV().delete_from_csv, csv_store.key(), observation.key())

		# delete observation from class csv blob
		# get csv blob
		csv_store = ClassSurveyCSV.all().filter('page = ', 1).filter('classid =', observation.classid).get()
		db.run_in_transaction(ClassSurveyCSV().delete_from_csv, csv_store.key(), observation.key())

		# invalidate related cached items
		saved = memcache.get('saved')
		if saved is not None:
			oldest_date = saved[-1]['realtime']

			if oldest_date <= observation.timestamp:
				memcache.delete('saved')

		# form user data cache name
		cache_name = 'data_' + str(observation.username)

		usersaved = memcache.get(cache_name)

		if usersaved is not None:
			oldest_date = usersaved[-1]['realtime']

			if oldest_date <= observation.timestamp:
				memcache.delete(cache_name)

		# form class data cache name
		cache_name = 'class_' + str(observation.classid)

		usersaved = memcache.get(cache_name)

		if usersaved is not None:
			oldest_date = usersaved[-1]['realtime']

			if oldest_date <= observation.timestamp:
				memcache.delete(cache_name)

		memcache.delete('csv')

		# move observation to quarantined
		quarantined = QuarantineSurveyData()
		quarantined.username = observation.username
		quarantined.timestamp = observation.timestamp
		quarantined.longitude = observation.longitude
		quarantined.latitude = observation.latitude
		quarantined.stressval = observation.stressval
		quarantined.comments = observation.comments
		quarantined.category = observation.category
		quarantined.subcategory = observation.subcategory
		quarantined.version = observation.version
		quarantined.hasphoto = observation.hasphoto
		quarantined.photo_ref = observation.photo_ref
		quarantined.classid = observation.classid
		quarantined.put()

		db.delete(observation)

		sess['success'] = 'Observation quarantined.'
		sess.save()
		self.redirect(data_redirect_str)
	# end post method
# End QuarantineObservation Class

# handler for: /admin/quarantine_image
# quarantine image
class QuarantineImage(webapp.RequestHandler):
	def post(self):
		sess = gmemsess.Session(self)

		bookmark = self.request.get('bookmark')
		page = self.request.get('page')

		data_redirect_str = '/admin/data'
		detail_redirect_str = '/admin/detail?key=' + self.request.get('key')
		if bookmark and len(bookmark) != 0:
			data_redirect_str += '?bookmark=' + str(bookmark)
			detail_redirect_str += '&bookmark=' + str(bookmark)
			if page and len(page) != 0:
				data_redirect_str += '&page=' + str(page)
				detail_redirect_str += '&page=' + str(page)
		elif page and len(page) != 0:
				data_redirect_str += '?page=' + str(page)
				detail_redirect_str += '&page=' + str(page)

		logging.debug('data direct: ' + data_redirect_str)
		logging.debug('detail direct: ' + detail_redirect_str)

		# redirect to login page if not logged in
		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			#sess['redirect'] = '/admin/detail?key=' + self.request.get('key')
			sess['redirect'] = detail_redirect_str
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
		admin_flag = UserTable().all().filter('ckey =', sess['userid']).get()

		if not admin_flag.admin:
			sess['error'] = 'No observation exists with this key or you do not have permission to delete this observation'
			sess.save()
			self.redirect(data_redirect_str)
			return

		logging.debug('quarantine image for: '+str(observation.key()))
		logging.debug('category: '+str(observation.category))
		logging.debug('subcategory: '+str(observation.subcategory))
		logging.debug('value: '+str(observation.stressval))
		logging.debug('hasphoto: '+str(observation.hasphoto))

		# quarantine any associated photo
		if observation.hasphoto:
			try:
				photo = observation.photo_ref
				logging.debug('quarantine photo: '+str(photo.key()))
				photo.flagged = True
				photo.put()
				sess['success'] = 'Observation quarantined.'
				sess.save()
			except:
				logging.debug('invalid photo reference')
				sess['error'] = 'Image could not be quarantined.'
				sess.save()
		else:
			sess['error'] = 'Observation has no photo flag set. Please contact.'
			sess.save()
			logging.debug('observation has no photo flag set: ' + str(observation.key()))

		self.redirect(data_redirect_str)

	# end put method
# End QuarantineImage Class

application = webapp.WSGIApplication(
									 [
									  ('/admin/data', AdminDataByDatePage),
									  ('/admin/detail', SetupQuarantine),
									  ('/admin/quarantine_observation', QuarantineObservation),
									  ('/admin/quarantine_image', QuarantineImage)
									 ],
									 debug=True)

def main():
	logging.getLogger().setLevel(logging.DEBUG)
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
