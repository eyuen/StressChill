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
import displaydata

# number of observations shown per page
PAGE_SIZE = 20

# main page: /
class HomePage(webapp.RequestHandler):
	def get(self):
		path = os.path.join (os.path.dirname(__file__), 'views/home.html')
		template_values = { 'home' : True }
		self.response.out.write (helper.render(self, path, template_values))
	# end get method
# End HomePage Class

# client link page: /client
class ClientsPage(webapp.RequestHandler):
	def get(self):
		path = os.path.join (os.path.dirname(__file__), 'views/clients.html')
		template_values = { 'client' : True }
		self.response.out.write (helper.render(self, path, template_values))
	# end get method
# End ClientsPage Class

# about page: /about
class AboutPage(webapp.RequestHandler):
	def get(self):
		path = os.path.join (os.path.dirname(__file__), 'views/about.html')
		template_values = { 'about' : True }
		self.response.out.write (helper.render(self, path, template_values))
	# end get method
# End AboutPage Class

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
	classid: <input name="classid" type="text"><br />
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
		classid = self.request.get('classid')

		if not username or not password or not confirmpassword:
			self.response.set_status(401, 'Missing field')
			logging.error('Missing field')
			return
		if password != confirmpassword:
			self.response.set_status(401, 'Password mismatch')
			logging.error('Password mismatch')
			return

		if not classid:
			if not UserTable().create_user(username, password, email):
				self.response.set_status(401, 'could not create user')
				logging.error('could not create user')
				return
		else:
			if not UserTable().create_user(username, password, email, classid):
				self.response.set_status(401, 'could not create user')
				logging.error('could not create user')
				return

		self.response.out.write('user added')
	# end post method
# End ConfirmUser Class


application = webapp.WSGIApplication(
									 [('/', HomePage),
									  ('/map', displaydata.MapPage),
									  ('/clients', ClientsPage),
									  ('/about', AboutPage),
									  ('/get_point_summary', displaydata.GetPointSummary),
									  ('/get_a_point', displaydata.GetAPoint),
									  ('/get_an_image', displaydata.GetAnImage),
									  ('/get_a_thumb', displaydata.GetAThumb),
									  ('/get_image_thumb', displaydata.GetImageThumb),
									  ('/data', displaydata.DataByDatePage),
									  ('/data_download_all.csv', displaydata.DownloadAllData),
									  ('/request_token', phone.RequestTokenHandler),
									  ('/authorize', phone.UserAuthorize),
									  ('/access_token', phone.AccessTokenHandler),
									  ('/authorize_access', phone.AuthorizeAccessHandler),
									  ('/protected_upload', phone.ProtectedResourceHandler),
									  ('/protected_upload2', phone.ProtectedResourceHandler2),
									  ('/summary', displaydata.SummaryHandler),
									  ('/create_user', CreateUser),
									  ('/confirm_user', ConfirmUser),
									  ],
									 debug=True)

def main():
	logging.getLogger().setLevel(logging.DEBUG)
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
