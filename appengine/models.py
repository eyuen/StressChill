#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#	 http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import oauth
import hmac
import hashlib
import binascii
import string
import random
from time import time


from google.appengine.ext import db
from google.appengine.api import urlfetch

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

KEY_LEN = 16
SECRET_LEN = 16

SOMEVAL= 'somerAndomStr123!'

# Consumer Class
class Consumer(db.Model):
	ckey = db.StringProperty()
	secret = db.StringProperty()
	name = db.StringProperty()

	timestamp = db.IntegerProperty(default=long(time()))

	# insert new consumer with random ckey and secret, and given name
	def insert_consumer(self, name):
		ckey = generateString(KEY_LEN)
		secret = generateString(SECRET_LEN)

		while self.gql('WHERE ckey = :1', ckey).count():
			ckey = generateString(KEY_LEN)

		self.ckey = ckey
		self.secret = secret
		self.name = name.lower()

		self.put()
		if not self.is_saved():
			return None
		return oauth.OAuthConsumer(self.ckey, self.secret)
	# end insert_token

	# return consumer object by ckey
	#
	# returns OAuthConsumer object if exist, False otherwise
	def get_consumer(self, ckey):
		res = self.gql("WHERE ckey = :1", ckey).get()

		if not res:
			return False
		else:
			return oauth.OAuthConsumer(res.ckey, res.secret)
	# end get_consumer
# End Consumer Class

# Token class
class Token(db.Model):
	ckey = db.StringProperty()
	secret = db.StringProperty()

	callback = db.StringProperty()
	callback_confirmed = db.BooleanProperty(default=False)
	verifier = db.StringProperty()

	consumer_key = db.StringProperty()

	timestamp = db.IntegerProperty(default=long(time()))

	token_type = db.StringProperty(choices=set(['request', 'access']))

	is_approved = db.BooleanProperty(default=False)
	user = db.StringProperty()

	# insert new request token with given consumer_key and callback, random ckey and secret
	def insert_request_token(self, consumer_key = None, callback = None):
		ckey = generateString(KEY_LEN)
		secret = generateString(SECRET_LEN)

		while self.gql('WHERE ckey = :1', ckey).count():
			ckey = generateString(KEY_LEN)

		self.ckey = ckey
		self.secret = secret
		self.token_type = 'request'
		self.consumer_key = consumer_key

		#assumes callback confirmed already
		if callback:
			self.callback = callback
			self.callback_confirmed = True
			

		self.put()
		if not self.is_saved():
			return None

		tok = oauth.OAuthToken(self.ckey, self.secret)

		if callback:
			tok.set_callback(self.callback)

		return tok
	# end insert_token

	# insert new access token with random ckey and secret, given 
	def insert_access_token(self, consumer_key, verifier, user):
		ckey = generateString(KEY_LEN)
		secret = generateString(SECRET_LEN)

		while self.gql('WHERE ckey = :1', ckey).count():
			ckey = generateString(KEY_LEN)

		self.ckey = ckey
		self.secret = secret
		self.token_type = 'access'
		self.consumer_key = consumer_key
		self.verifier = verifier
		self.is_approved = True
		self.user = user

		self.put()
		if not self.is_saved():
			return None

		tok = oauth.OAuthToken(self.ckey, self.secret)

		if verifier:
			tok.set_verifier(verifier)

		return tok
	# end insert_token


	# return token object by ckey
	#
	# return OAuthToken object if exist, False otherwise
	def get_token(self, ckey):
		res = self.gql("WHERE ckey = :1", ckey).get()

		if not res:
			return False
		else:
			tok = oauth.OAuthToken(res.ckey, res.secret)
			if res.callback:
				tok.set_callback(res.callback)
			if res.verifier:
				tok.set_verifier(res.verifier)
			return tok
	# end get_token

	# update token callback url by ckey and type
	def update_token_callback(self, ckey, callback_url):
		res = self.gql("WHERE ckey = :1", ckey).get()

		if not res:
			return False
		else:
			res.callback = callback_url
			res.callback_confirmed = True
			res.put()
			tok = oauth.OAuthToken(res.ckey, res.secret)
			tok.set_callback(res.callback)
			return tok

		return False

	# approve token by ckey, save user key
	def approve_token(self, ckey, user):
		res = self.gql("WHERE ckey = :1", ckey).get()

		if not res:
			return False
		else:
			res.user = user
			res.is_approved = True
			res.verifier = generateString(KEY_LEN)
			res.put()
			tok = oauth.OAuthToken(res.ckey, res.secret)
			tok.set_callback(res.callback)
			tok.set_verifier(res.verifier)
			return tok

		return False
	#end update_token_callback

	# get user key
	def get_user_key(self, ckey):
		res = self.gql("WHERE ckey = :1", ckey).get()

		if not res:
			return False
		else:
			return res.user
	# end get_user_key class

	# get user name
	def get_username(self, ckey):
		res = self.gql("WHERE ckey = :1", ckey).get()

		if not res:
			return False

		res = UserTable().gql("WHERE ckey = :1", res.user).get()

		if not res:
			return False
		else:
			return res.username
	# end get_username class

# End Token class


# Nonce class
class Nonce(db.Model):
	token_key = db.StringProperty()
	consumer_key = db.StringProperty()
	ckey = db.StringProperty()
	# insert new nonce with random ckey and given token_key and consumer_key
	def insert_nonce(self, ckey, token_key, consumer_key):
		'''
		ckey = generateString(KEY_LEN)

		while self.gql('WHERE ckey = :1', ckey).count():
			ckey = generateString(KEY_LEN)
		'''
		self.ckey = ckey
		self.token_key = token_key
		self.consumer_key = consumer_key

		self.put()
		if not self.is_saved():
			return None
		return self.ckey
	# end insert_token


	# return token object by ckey, token_key, and consumer_key
	#
	# return ckey if exist, False otherwise
	def get_nonce_key(self, ckey, token_key, consumer_key):
		res = self.gql("WHERE ckey = :1 AND token_key = :2 AND consumer_key = :3",
								ckey, 
								token_key,
								consumer_key).get()

		if not res:
			return False
		else:
			return res.ckey
	# end get_nonce
# End Nonce class

class UserTable(db.Model):
	username = db.StringProperty()
	password = db.StringProperty()
	email = db.StringProperty()
	ckey = db.StringProperty()
	classid = db.StringProperty()
	created= db.IntegerProperty(default=long(time()))
	admin = db.BooleanProperty(default=False)

	# username: proposed username, string
	# password: plaintext password, string
	# email: email, string
	def create_user(self, username, password, email, classid = None):
		if not username or not password or not email:
			return False

		lowered_username = username.lower()
		lowered_email = email.lower()
		# if username exists, do not create user
		if self.gql('WHERE username = :1', lowered_username).count():
			return False

		hashedpass = hashlib.sha1(password)
		sha1pass = hashedpass.hexdigest()

		hashedval = hashlib.sha1(sha1pass + SOMEVAL)
		sha1val = hashedval.hexdigest()

		ckey = generateString(SECRET_LEN)

		while self.gql('WHERE ckey = :1', ckey).count():
			ckey = generateString(KEY_LEN)

		self.username = lowered_username
		self.password = sha1val
		self.email = lowered_email
		self.ckey = ckey

		if classid is not None:
			self.classid = classid

		self.put()

		if not self.is_saved():
			return False
		return True
	# end create_user

	def update_user(self, username, password):
		if not username or not password:
			return False

		lowered_username = username.lower()
		# if username not exists, error
		res = self.gql('WHERE username = :1', lowered_username).get()

		if not res:
			return False
		else:
			hashedpass = hashlib.sha1(password)
			sha1pass = hashedpass.hexdigest()

			hashedval = hashlib.sha1(sha1pass + SOMEVAL)
			sha1val = hashedval.hexdigest()

			res.password = sha1val
			res.put()

		if not res.is_saved():
			return False
		return True
	# end create_user

	# username: string
	# sha1pass: string, sha1 already performed on the plaintext password
	def check_valid_password(self, username, sha1pass):
		if not username or not sha1pass:
			return False

		lowered_username = username.lower()
		hashedval = hashlib.sha1(sha1pass + SOMEVAL)
		sha1val = hashedval.hexdigest()

		user = self.gql('WHERE username = :1 AND password = :2', lowered_username, sha1val).get()
		if not user:
			return False
		else:
			return user.ckey
	# end check_valid_password

	def get_username(self, user_key):
		uname = self.gql('WHERE ckey = :1', user_key).get()
		if not username:
			return False
		else:
			return uname.username
	# end get_username
#end UserTable Class

class ResourceTable(db.Model):
	ckey = db.StringProperty()
	name = db.StringProperty()
	consumer_key = db.StringProperty()
	created= db.IntegerProperty(default=long(time()))

	def create_resource(self, name, consumer):
		if not name or not consumer:
			return False

		if not Consumer().gql('WHERE ckey = :1', consumer).count():
			return False

		ckey = generateString(SECRET_LEN)

		while self.gql('WHERE ckey = :1', ckey).count():
			ckey = generateString(KEY_LEN)

		self.name = name.lower()
		self.consumer_key = consumer
		self.ckey = ckey
		self.put()

		if not self.is_saved():
			return False
		return True
	# end create_user

	# username: string
	# sha1pass: string, sha1 already performed on the plaintext password
	def check_valid_consumer(self, name, consumer):
		if not name or not consumer:
			return False

		user = self.gql('WHERE name = :1 AND consumer_key = :2', name.lower(), consumer).get()
		if not user:
			return False
		else:
			return True
	# end check_valid_consumer
#end UserTable Class

def generateString(length):
	characters ='aeuyAEUYbdghjmnpqrstvzBDGHJLMNPQRSTVWXZ23456789'
	rnd_string = ''

	for i in range(length):
		rnd_string += characters[random.randrange(len(characters))]

	return rnd_string
# end generateString

'''
# original model to hold data collected from phone survey
# replaced by SurveyData and SurveyPhoto
class Survey(db.Model):
	user = db.UserProperty()
	username = db.StringProperty()
	timestamp =	db.DateTimeProperty(auto_now_add=True)
	longitude =	db.StringProperty()
	latitude =	db.StringProperty()
	stressval =	db.FloatProperty()
	comments =	db.TextProperty()
	category =	db.StringProperty()
	subcategory = db.StringProperty()
	version =	db.StringProperty()
	photo =		db.BlobProperty()
	hasphoto =	db.BooleanProperty()
# End Survey Class
'''

# model to hold image blob
class SurveyPhoto(db.Model):
	photo = db.BlobProperty()
	thumb = db.BlobProperty()
	timestamp =	db.DateTimeProperty(auto_now=True)
# End SurveyPhoto Class

# model to hold survey data
class SurveyData(db.Model):
	user = db.ReferenceProperty(UserTable)
	username = db.StringProperty()
	timestamp =	db.DateTimeProperty(auto_now=True)
	longitude =	db.StringProperty()
	latitude =	db.StringProperty()
	stressval =	db.FloatProperty()
	comments =	db.TextProperty()
	category =	db.StringProperty()
	subcategory = db.StringProperty()
	version =	db.StringProperty()
	hasphoto =	db.BooleanProperty()
	photo_ref = db.ReferenceProperty(SurveyPhoto)
# End SurveyData Class

# model to hold data blob
class SurveyCSV(db.Model):
	csv = db.TextProperty()
	last_updated = db.DateTimeProperty(auto_now=True)
	page = db.IntegerProperty()
	last_entry_date = db.DateTimeProperty()
	count = db.IntegerProperty()
# End SurveyCSV Class

# model to hold data blob
class UserSurveyCSV(db.Model):
	csv = db.TextProperty()
	last_updated = db.DateTimeProperty(auto_now=True)
	page = db.IntegerProperty()
	last_entry_date = db.DateTimeProperty()
	count = db.IntegerProperty()
	userid = db.StringProperty()
# End UserSurveyCSV Class

# model to hold data blob
class ClassSurveyCSV(db.Model):
	csv = db.TextProperty()
	last_updated = db.DateTimeProperty(auto_now=True)
	page = db.IntegerProperty()
	last_entry_date = db.DateTimeProperty()
	count = db.IntegerProperty()
	classid = db.StringProperty()
# End ClassSurveyCSV Class

# model to keep running stats of sub-categories
class SubCategoryStat(db.Model):
	category = 	db.StringProperty()
	subcategory = 	db.StringProperty()
	count =		db.IntegerProperty()
	total = 	db.FloatProperty()
	stress_count = db.IntegerProperty()
	stress_total =	db.FloatProperty()
	chill_count = db.IntegerProperty()
	chill_total =	db.FloatProperty()
	last_updated = 	db.DateTimeProperty(auto_now=True)

	# increments the subcategory
	def increment_stats(self, user_subcategory, user_category, value):
		subcat = self.all().filter('subcategory =', user_subcategory).filter('category = ', user_category).get()

		scount = 0
		sval = 0
		ccount = 0
		cval = 0

		if value < 0:
			scount = 1
			sval = value
		else:
			ccount = 1
			cval = value

		if not subcat:
			self.category = user_category
			self.subcategory = user_subcategory
			self.count = 1
			self.total = value
			self.stress_count = scount
			self.stress_total = float(sval)
			self.chill_count = ccount
			self.chill_total = float(cval)
			self.put()

			if self.is_saved():
				return self.key()
			else:
				return None
		else:
			subcat.count += 1
			subcat.total += value
			subcat.stress_count += scount
			subcat.stress_total += sval
			subcat.chill_count += ccount
			subcat.chill_total += cval
			subcat.put()

			if subcat.is_saved():
				return subcat.key()
			else:
				return None
# End SubCategoryStat Class

# model to keep running stats of sub-categories per day
class DailySubCategoryStat(db.Model):
	category = 	db.StringProperty()
	subcategory = 	db.StringProperty()
	count =		db.IntegerProperty()
	total = 	db.FloatProperty()
	stress_count = db.IntegerProperty()
	stress_total =	db.FloatProperty()
	chill_count = db.IntegerProperty()
	chill_total =	db.FloatProperty()
	date =		db.DateProperty()
	last_updated = 	db.DateTimeProperty(auto_now=True)

	# increments the subcategory
	def increment_stats(self, user_subcategory, user_category, user_date, value):
		subcat = self.all().filter('subcategory =', user_subcategory).filter('category = ', user_category).filter('date =', user_date).get()

		scount = 0
		sval = 0
		ccount = 0
		cval = 0

		if value < 0:
			scount = 1
			sval = value
		else:
			ccount = 1
			cval = value

		if not subcat:
			self.category = user_category
			self.subcategory = user_subcategory
			self.count = 1
			self.total = value
			self.date = user_date
			self.stress_count = scount
			self.stress_total = float(sval)
			self.chill_count = ccount
			self.chill_total = float(cval)
			self.put()

			if self.is_saved():
				return self.key()
			else:
				return None
		else:
			subcat.count += 1
			subcat.total += value
			subcat.stress_count += scount
			subcat.stress_total += float(sval)
			subcat.chill_count += ccount
			subcat.chill_total += float(cval)
			subcat.put()

			if subcat.is_saved():
				return subcat.key()
			else:
				return None
# End CategoryStat Class

#model to hold class info
class ClassList(db.Model):
	classid = db.StringProperty()
	created = db.DateTimeProperty(auto_now_add=True)
# End ClassList Class

# model to keep running stats of user's sub-categories
class UserStat(db.Model):
	user_id = db.StringProperty()
	category = 	db.StringProperty()
	subcategory = db.StringProperty()
	count =	db.IntegerProperty()
	total =	db.FloatProperty()
	stress_count = db.IntegerProperty()
	stress_total =	db.FloatProperty()
	chill_count = db.IntegerProperty()
	chill_total =	db.FloatProperty()
	last_updated = 	db.DateTimeProperty(auto_now=True)

	# increments the subcategory
	def increment_stats(self, user_id, user_subcategory, user_category, value):
		userstat = self.all().filter('subcategory =', user_subcategory).filter('category = ', user_category).filter('user_id = ', user_id).get()

		scount = 0
		sval = 0
		ccount = 0
		cval = 0

		if value < 0:
			scount = 1
			sval = value
		else:
			ccount = 1
			cval = value

		if not userstat:
			self.user_id = user_id
			self.category = user_category
			self.subcategory = user_subcategory
			self.count = 1
			self.total = value
			self.stress_count = scount
			self.stress_total = float(sval)
			self.chill_count = ccount
			self.chill_total = float(cval)
			self.put()

			if self.is_saved():
				return self.key()
			else:
				return None
		else:
			userstat.count += 1
			userstat.total += value
			userstat.stress_count += scount
			userstat.stress_total += sval
			userstat.chill_count += ccount
			userstat.chill_total += cval
			userstat.put()

			if userstat.is_saved():
				return userstat.key()
			else:
				return None
# End CategoryStat Class

