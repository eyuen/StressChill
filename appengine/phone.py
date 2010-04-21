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
			t = db.GqlQuery("SELECT * FROM Token WHERE ckey = :1", req_token).get()

			if not t:
				logging.error('if you got here, token lookup failed.')
				self.error(401)
				return

			s = SurveyData()

			s.username = t.user
			s.longitude = self.request.get('longitude')
			s.latitude = self.request.get('latitude')
			if self.request.get('stressval'):
				s.stressval = float(self.request.get('stressval'))
			else:
				s.stressval = 0
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
			logging.debug('increment stats for category, ' + s.category + ', & subcategory, ' +s.subcategory)
			#catkey = CategoryStat().increment_stats(s.category, s.stressval)
			#subcatkey = SubCategoryStat().increment_stats(s.subcategory, s.category, catkey, s.stressval)
			param = {}

			param['user_category'] = s.category
			param['user_subcategory'] = s.subcategory
			param['value'] = s.stressval

			db.run_in_transaction(helper.update_stats, s.stressval, s.category, s.subcategory)

			# update running daily stats (this should probably be moved to the task queue)
			# TODO: cache key & stats and create transaction
			pdt = s.timestamp - datetime.timedelta(hours=7)
			time_key = str(pdt).split(' ')[0]
			dt = datetime.datetime.strptime(time_key, "%Y-%m-%d")
			date = datetime.date(dt.year, dt.month, dt.day)

			dailycatkey = DailyCategoryStat().increment_stats(s.category, date, s.stressval)
			dailysubcatkey = DailySubCategoryStat().increment_stats(s.subcategory, s.category, dailycatkey, date, s.stressval)

			# update user running stats (this should probably be moved to the task queue)
			# TODO: cache key & stats and create transaction
			usercatkey = UserStat().increment_stats(s.username, s.subcategory, s.category, s.stressval)
				
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

			# form image url
			if s.hasphoto:
				photo_url = 'http://' + base_url + "/get_an_image?key="+str(s.photo_ref.key())

			else:
				photo_url = 'no_image'

			hashedval = hashlib.sha1(str(s.key()))
			sha1val = hashedval.hexdigest()

			userhashedval = hashlib.sha1(s.username)
			usersha1val = hashedval.hexdigest()

			# write csv data row
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

			# add to cache (writes should update this cached value)
			memcache.set('csv', output.getvalue())

			### append to user csv blob

			# this will have to change if multiple pages are ever needed (limits?)
			insert_csv = UserSurveyCSV.all().filter('userid =', s.username).filter('page =', 1).get()

			# write header row if csv blob doesnt exist yet
			if not insert_csv:
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

			# form image url
			if s.hasphoto:
				photo_url = 'http://' + base_url + "/get_an_image?key="+str(s.photo_ref.key())

			else:
				photo_url = 'no_image'

			hashedval = hashlib.sha1(str(s.key()))
			sha1val = hashedval.hexdigest()

			userhashedval = hashlib.sha1(s.username)
			usersha1val = hashedval.hexdigest()

			# write csv data row
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

			# create new blob if one does not exist
			if not insert_csv:
				insert_csv = UserSurveyCSV()
				insert_csv.csv = db.Blob(output.getvalue())
				insert_csv.last_entry_date = s.timestamp
				insert_csv.count = 1
				insert_csv.page = 1
			else:	#if blob exists, append and update
				insert_csv.csv += output.getvalue()
				insert_csv.last_entry_date = s.timestamp
				insert_csv.count += 1

			insert_csv.put()



			try:
				# update data page cache with new value, pop oldest value
				saved = memcache.get('saved')
				if saved is not None:
					s_list = []
					s_list.append(s)
					extract = helper.extract_surveys(s_list)
					d = deque(saved)
					d.pop()
					d.appendleft(extract[0])
					memcache.set('saved', list(d))
			except:
				logging.debug('cache write failed')


			try:
				# update user data page cache with new value, pop oldest value
				cache_name = 'data_' + s.username
				saved = memcache.get(cache_name)
				logging.debug('updating user cache: ' + cache_name)
				if saved is not None:
					s_list = []
					s_list.append(s)
					extract = helper.extract_surveys(s_list)
					d = deque(saved)
					d.pop()
					d.appendleft(extract[0])
					memcache.set(cache_name, list(d))
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

		else:
			logging.error('request token empty')
			self.response.set_status(401, 'request token empty.')
			self.response.out.write('request token empty.')
	# end handle method
# End ProtectedResourceHandler2 Class

# handler for: /confirm_user
# (used by phone registration)
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
		classid = self.request.get('classid')

		if not username or not password or not confirmpassword or not email:
			self.response.set_status(401, 'Missing field')
			self.response.out.write('Missing field')
			logging.error('Missing field')
			return
		if password != confirmpassword:
			self.response.set_status(401, 'Password mismatch')
			self.response.out.write('Password mismatch')
			logging.error('Password mismatch')
			return

		if not classid:
			if not UserTable().create_user(username, password, email):
				self.response.set_status(401, 'Username already in use.')
				self.response.out.write('Username already in use.')
				logging.error('could not create user (taken or db error)')
				return
		else:
			if not UserTable().create_user(username, password, email, classid):
				self.response.set_status(401, 'Username already in use.')
				self.response.out.write('Username already in use.')
				logging.error('could not create user (taken or db error)')
				return

		self.response.out.write('user added')
	# end post method
# End ConfirmUser Class
