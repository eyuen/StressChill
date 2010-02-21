import cgi
import os
from django.utils import simplejson as json
import oauth
import hashlib
from datastore import *

from time import time

import logging
from google.appengine.api import urlfetch


from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.db import stats
from google.appengine.ext.webapp import template

import cStringIO
import csv
from datastore import *

BASE_URL = "http://stresschill.appspot.com"

def extract_surveys(surveys):
	extracted = []
	for s in surveys:
		item = {}
		item['stressval'] = s.stressval
		item['category'] = s.category
		item['comments'] = s.comments
		item['longitude'] = s.longitude
		item['latitude'] = s.latitude
		item['key'] = str(s.key())
		extracted.append(item)
	return extracted

class Survey(db.Model):
	user = db.UserProperty()
	username = db.StringProperty()
	timestamp =	db.DateTimeProperty(auto_now_add=True)
	longitude =	db.StringProperty()
	latitude =	db.StringProperty()
	stressval =	db.FloatProperty()
	comments =	db.TextProperty()
	category =	db.StringProperty()
	version =	db.StringProperty()
	photo =		db.BlobProperty()

class HomePage(webapp.RequestHandler):
	def get(self):
		path = os.path.join (os.path.dirname(__file__), 'views/home.html')
		self.response.out.write (template.render(path, {}))

class MapPage(webapp.RequestHandler):
	def get(self):
		if os.environ.get('HTTP_HOST'):
			base_url = 'http://' + os.environ['HTTP_HOST'] + '/'
		else:
			base_url = 'http://' + os.environ['SERVER_NAME'] + '/'

		surveys = Survey.all().fetch(1000)
		extracted = extract_surveys (surveys)
		template_values = { 'surveys' : extracted, 'base_url' : base_url }
		path = os.path.join (os.path.dirname(__file__), 'views/map.html')
		self.response.out.write (template.render(path, template_values))

class ClientsPage(webapp.RequestHandler):
	def get(self):
		path = os.path.join (os.path.dirname(__file__), 'views/clients.html')
		self.response.out.write (template.render(path, {}))

class AboutPage(webapp.RequestHandler):
	def get(self):
		path = os.path.join (os.path.dirname(__file__), 'views/about.html')
		self.response.out.write (template.render(path, {}))

class UploadSurvey(webapp.RequestHandler):
	def post(self):
		s = Survey()

		#if users.get_current_user():
		#	s.user = users.get_current_user()
		s.longitude = self.request.get('longitude')
		s.latitude = self.request.get('latitude')
		s.stressval = float(self.request.get('stressval'))
		s.comments = str(self.request.get('comments')).replace('\n', ' ')
		s.category = self.request.get('category')
		s.version = self.request.get('version')

		file_content = self.request.get('file')
		try:
			s.photo = db.Blob(file_content)
		except TypeError:
			s.photo = ''

		s.put()
		self.redirect('/')

class GetPointSummary(webapp.RequestHandler):
	def get(self):
		surveys = db.GqlQuery("SELECT * FROM Survey ORDER BY timestamp DESC LIMIT 1000")
		d = {}
		i = 0
		for s in surveys:
			e = {}
			e['latitude'] = s.latitude
			e['longitude'] = s.longitude
			e['stressval'] = s.stressval
			e['comments'] = s.comments
			e['key'] = str(s.key())
			e['version'] = s.version

			d[i] = e;
			i = i + 1

		self.response.headers['Content-type'] = 'text/plain'
		if i > 0:
			self.response.out.write(json.dumps(d))
		else:
			self.response.out.write("no data so far")

class GetAPoint(webapp.RequestHandler):
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
				surveys = db.GqlQuery("SELECT * FROM Survey WHERE __key__ = :1", db_key)
				for s in surveys:
					e = {}
					e['photo'] = 'http://' + base_url + "/get_image_thumb?key=" + req_key;
					e['latitude'] = s.latitude
					e['longitude'] = s.longitude
					e['stressval'] = s.stressval
					e['category'] = s.category
					e['comments'] = s.comments
					e['key'] = str(s.key())
					e['version'] = s.version
					self.response.out.write(json.dumps(e))
					return
			except (db.Error):
				self.response.out.write("No data has been uploaded :[")
				return
		self.response.out.write("No data has been uploaded :[")

class GetAnImage(webapp.RequestHandler):
	def get(self):
		self.response.headers['Content-type'] = 'image/jpeg'
		req_key = self.request.get('key')
		if req_key != '':
			try :
				db_key = db.Key(req_key)
				surveys = db.GqlQuery("SELECT * FROM Survey WHERE __key__ = :1", db_key)
				for s in surveys:
					self.response.out.write(s.photo)
					return
			except (db.Error):
				return
		return

class GetImageThumb(webapp.RequestHandler):
	def get(self):
		if os.environ.get('HTTP_HOST'):
			base_url = os.environ['HTTP_HOST']
		else:
			base_url = os.environ['SERVER_NAME']

		self.response.headers['Content-type'] = 'text/html'
		req_key = self.request.get('key')
		self.response.out.write("<html><body><img src=\"http://" + base_url + "/get_an_image?key=")
		self.response.out.write(req_key)
		self.response.out.write("\" width=\"180\" height=\"130\"></body></html>")


class TestPost(webapp.RequestHandler):
	def get(self):
		path = os.path.join (os.path.dirname(__file__), 'views/testpost.html')
		self.response.out.write (template.render(path, {}))

class TestUpload(webapp.RequestHandler):
	def post(self):
		s = Survey()

		s.longitude = self.request.get('longitude')
		s.latitude = self.request.get('latitude')
		s.stressval = float(self.request.get('stressval'))
		s.comments = self.request.get('comments')
		s.version = self.request.get('version')

		file_content = self.request.get('file')
		try:
			s.photo = db.Blob(file_content)
		except TypeError:
			s.photo = ''

		s.put()
		self.redirect('/')

class DataPage(webapp.RequestHandler):
	def get(self):

		if os.environ.get('HTTP_HOST'):
			base_url = 'http://' + os.environ['HTTP_HOST'] + '/'
		else:
			base_url = 'http://' + os.environ['SERVER_NAME'] + '/'

		surveys = Survey.all().fetch(50)
		template_values = { 'surveys' : surveys, 'base_url' : base_url }
		path = os.path.join (os.path.dirname(__file__), 'views/data.html')
		self.response.out.write (template.render(path, template_values))


class DownloadAllData(webapp.RequestHandler):
	def get(self):
		output = cStringIO.StringIO()
		writer = csv.writer(output, delimiter=',')

		header_row = [
						'timestamp',
						'latitude',
						'longitude',
						'stress_value',
						'category',
						'comments',
						'image_url'
						]

		writer.writerow(header_row)


		surveys = Survey.all().fetch(1000)

		if os.environ.get('HTTP_HOST'):
			base_url = os.environ['HTTP_HOST']
		else:
			base_url = os.environ['SERVER_NAME']

		for s in surveys:
			new_row = [
					s.timestamp,
					s.latitude,
					s.longitude,
					s.stressval,
					s.category,
					s.comments,
					'http://' + base_url + "/get_an_image?key="+str(s.key())
					]
			writer.writerow(new_row)

		self.response.headers['Content-type'] = 'text/csv'
		self.response.out.write(output.getvalue())

# base clase to be extended by other handlers needing oauth
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

# cheat for mobile phone so no back and forth with redirects...
# access as if fetching request token
# also send username, sha1 of password
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

			s = Survey()

			# check user 
			if 'username' in params:
				username = params['username']

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
				try:
					s.photo = db.Blob(file_content)
				except TypeError:
					s.photo = ''

			s.put()
			self.redirect('/')

		except oauth.OAuthError, err:
			self.send_oauth_error(err)
	# end handler method
# End ProtectedResourceHandler Class

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
				tokens = db.GqlQuery("SELECT * FROM Token WHERE ckey = :1", req_token)
				for t in tokens:
					s = Survey()

					s.username = t.user
					s.longitude = self.request.get('longitude')
					s.latitude = self.request.get('latitude')
					s.stressval = float(self.request.get('stressval'))
					s.comments = str(self.request.get('comments')).replace('\n', ' ')
					s.category = self.request.get('category')
					s.version = self.request.get('version')

					file_content = self.request.get('file')
					try:
						s.photo = db.Blob(file_content)
					except TypeError:
						s.photo = ''

					s.put()
					self.error(200)
					return
				logging.error('if you got here, token lookup failed.')
			except (db.Error):
				logging.error('error inserting to database')
				self.error(401)
				return
		logging.error('request token empty')
		self.error(401)



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
# End CreateConsumer class

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
		

# End GetConsumer class

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
# End CreateUser class

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


application = webapp.WSGIApplication(
									 [('/', HomePage),
									  ('/map', MapPage),
									  ('/clients', ClientsPage),
									  ('/about', AboutPage),
									  ('/upload_survey', UploadSurvey),
									  ('/get_point_summary', GetPointSummary),
									  ('/get_a_point', GetAPoint),
									  ('/get_an_image', GetAnImage),
									  ('/get_image_thumb', GetImageThumb),
									  ('/testpost', TestPost),
									  ('/testupload', TestUpload),
									  ('/data', DataPage),
									  ('/data_download_all.csv', DownloadAllData),
									  ('/request_token', RequestTokenHandler),
									  ('/authorize', UserAuthorize),
									  ('/access_token', AccessTokenHandler),
									  ('/authorize_access', AuthorizeAccessHandler),
									  ('/protected_upload', ProtectedResourceHandler),
									  ('/protected_upload2', ProtectedResourceHandler2),
									  ('/create_consumer', CreateConsumer),
									  ('/get_consumer', GetConsumer),
									  ('/create_user', CreateUser),
									  ('/confirm_user', ConfirmUser)],
									 debug=True)

def main():
	logging.getLogger().setLevel(logging.DEBUG)
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
