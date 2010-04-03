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

# list data page: /user/data
class UserDataByDatePage(webapp.RequestHandler):
	# display data in table format
	# TODO: page results
	def get(self):
		sess = gmemsess.Session(self)

		# if session is new, user was not logged in, redirect
		if sess.is_new():
			sess['redirect'] = '/user/data'
			sess.save()
			self.redirect('/user/login')
			return
		# if username not set in session, user not logged in, redirect
		if not sess.has_key('username'):
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

		# fetch cached values if any
		saved = None
		extracted = None

		# form user data cache name
		cache_name = 'data_' + sess['userid']

		# if page set, and page in range, get page for cache
		if page > 0 and page <=5: 
			saved = memcache.get(cache_name)

			# if not in cache, try fetching from datastore
			if not saved:
				logging.debug('cache miss, populate')
				# get 5 pages of most recent records and cache
				surveys = SurveyData.all().filter('username =', sess['userid']).order('-timestamp').fetch(PAGE_SIZE*5 + 1)
				saved = helper.extract_surveys (surveys)
				# if values returned, save in cache
				if surveys is not None:
					memcache.set(cache_name, saved)

			# if it could not be fetched, error
			if not saved:
				logging.debug('problem fetching pages for cache')
				self.error(401)
				return

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
					surveys = SurveyData.all().filter('username =', sess['userid']).filter('timestamp <', dt).order('-timestamp').fetch(PAGE_SIZE+1)
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
					surveys = SurveyData.all().filter('username =', sess['userid']).filter('timestamp >', dt).order('timestamp').fetch(PAGE_SIZE+1)
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
				surveys = SurveyData.all().filter('username =', sess['userid']).order('-timestamp').fetch(PAGE_SIZE+1)
				if len(surveys) == PAGE_SIZE + 1:
					template_values['next'] = str(surveys[-2].timestamp)
					template_values['nextpage'] = 2
					surveys = surveys[:PAGE_SIZE]

			extracted = helper.extract_surveys (surveys)

		template_values['surveys'] = extracted 

		path = os.path.join (os.path.dirname(__file__), 'views/user_data.html')
		self.response.out.write (template.render(path, template_values))
	# end get method
# End UserDataByDatePage Class

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
				sess['username'] = self.request.get('username')
				sess['userid'] = uid
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

application = webapp.WSGIApplication(
									 [
									  ('/user/data', UserDataByDatePage),
									  ('/user/login', DisplayLogin),
									  ('/user/confirmlogin', ConfirmLogin),
									  ('/user/logout', LogoutHandler)],
									 debug=True)

def main():
	logging.getLogger().setLevel(logging.DEBUG)
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
