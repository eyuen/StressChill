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
import logging
from time import time

import cStringIO
import csv
import os

import re
import datetime

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
	date_created = db.DateTimeProperty(auto_now_add=True)
	date_modified = db.DateTimeProperty(auto_now=True)
	admin = db.BooleanProperty(default=False)
	teacher = db.BooleanProperty(default=False)
	approved = db.BooleanProperty(default=False)

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
		if not uname:
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

# function to write csv blob
def write_csv(data, csv_blob = None):
	# init csv writer
	output = cStringIO.StringIO()
	writer = csv.writer(output, delimiter=',')

	base_url = ''
	if os.environ.get('HTTP_HOST'):
		base_url = os.environ['HTTP_HOST']
	else:
		base_url = os.environ['SERVER_NAME']

	# write header row if csv blob doesnt exist yet
	if not csv_blob:
		logging.debug('csv not exist, writing header row')
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
	else:
		logging.debug('csv exist, do not output header')

	# form image url
	if data['hasphoto']:
		photo_url = 'http://' + base_url + "/get_an_image?key="+str(data['photo_key'])

	else:
		photo_url = 'no_image'

	hashedval = hashlib.sha1(str(data['key']))
	sha1val = hashedval.hexdigest()

	userhashedval = hashlib.sha1(data['username'])
	usersha1val = userhashedval.hexdigest()

	# write csv data row
	new_row = [
			sha1val,
			usersha1val,
			data['timestamp'],
			data['latitude'],
			data['longitude'],
			data['stressval'],
			data['category'],
			data['subcategory'],
			data['comments'],
			photo_url
			]
	writer.writerow(new_row)
	#logging.debug('output: ' + str(output.getvalue()))

	if not csv_blob:
		return str(output.getvalue())
	else:
		return csv_blob + str(output.getvalue())
# end write_csv function

# function to delete from csv blob
def delete_from_csv_blob(csv_blob, del_key):
	if csv_blob == None:
		return None

	# init csv reader
	csv_file = csv.DictReader(cStringIO.StringIO(str(csv_blob)))


	row_count = 0
	last_entry_date = None
	del_flag = False

	hashedval = hashlib.sha1(str(del_key))
	sha1val = hashedval.hexdigest()

	output = None
	writer = None

	header_flag = False

	# iterate through csv file
	for row in csv_file:
		# seems you have to try accessing the csv_file before fieldnames is populated?
		if not header_flag:
			# init csv writer
			output = cStringIO.StringIO()
			writer = csv.DictWriter(output, csv_file.fieldnames)

			# output csv header
			header = {}
			for h in csv_file.fieldnames:
				header[h] = h
			writer.writerow(header)

			# set header_flag True, so only write header once
			header_flag = True

		# if csv row id matches key to delete, do not copy to output
		if row['id'] == sha1val:
			del_flag = True
			logging.debug('csv row to del: '+str(row))
		else: # if not row to delete, copy to output
			writer.writerow(row)
			row_count+= 1
			last_entry_date = row['timestamp']

	# if deleted flag set, write new csv
	if del_flag:
		logging.debug('del row cnt: '+str(row_count))
		dt = None
		if row_count > 0:
			# convert string to time
			m = re.match(r'(.*?)(?:\.(\d+))?(([-+]\d{1,2}):(\d{2}))?$',
				str(last_entry_date))
			datestr, fractional, tzname, tzhour, tzmin = m.groups()

			logging.debug('datestr: '+str(datestr))

			if datestr is not None and datestr != 'None':
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

		# write csv values/blob
		return_val = {}
		return_val['csv'] = db.Blob(output.getvalue())
		return_val['count'] = row_count
		return_val['dt'] = dt
		return return_val
	else:
		logging.debug('row not found')
		return None
# end delete_from_csv_blob function
	

# model to hold image blob
class SurveyPhoto(db.Model):
	photo = db.BlobProperty()
	thumb = db.BlobProperty()
	timestamp =	db.DateTimeProperty(auto_now=True)
	flagged = db.BooleanProperty(default=False)
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
	classid = db.StringProperty()
	flagged = db.BooleanProperty(default=False)
# End SurveyData Class

# model to hold quarantined survey data
class QuarantineSurveyData(db.Model):
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
	classid = db.StringProperty()
	flagged = db.BooleanProperty(default=False)
# End SurveyData Class

# model to hold data blob
class SurveyCSV(db.Model):
	csv = db.TextProperty()
	last_updated = db.DateTimeProperty(auto_now=True)
	page = db.IntegerProperty()
	last_entry_date = db.DateTimeProperty()
	count = db.IntegerProperty()

	def update_csv(self, data, key=None):
		# create new blob if one does not exist
		if not key:
			csv_blob = write_csv(data) #write the csv (defined above)
			logging.debug('csv not exist, setup')
			insert_csv = SurveyCSV()
			insert_csv.csv = str(csv_blob)
			insert_csv.last_entry_date = data['timestamp']
			insert_csv.count = 1
			insert_csv.page = 1
		else:	#if blob exists, append and update
			insert_csv = db.get(key)
			csv_blob = write_csv(data, insert_csv.csv) #write the csv (defined above)
			logging.debug('csv exist, append')
			insert_csv.csv = str(csv_blob)
			insert_csv.last_entry_date = data['timestamp']
			insert_csv.count += 1

		insert_csv.put()
		return insert_csv

	def delete_from_csv(self, key, del_key):
		# create new blob if one does not exist
		if not key:
			return None

		csv_store = db.get(key)

		if csv_store is not None:
			rtn_value = delete_from_csv_blob(csv_store.csv, del_key)
			if not rtn_value:
				logging.debug('the csv row not found')
				return None

			csv_store.csv = rtn_value['csv']
			csv_store.count = rtn_value['count']
			csv_store.last_entry_date = rtn_value['dt']
			csv_store.put()
		else:
			logging.debug('the csv blob could not be retreived')

		return True
	# end delete_from_csv method
# End SurveyCSV Class

# model to hold data blob
class UserSurveyCSV(db.Model):
	csv = db.TextProperty()
	last_updated = db.DateTimeProperty(auto_now=True)
	page = db.IntegerProperty()
	last_entry_date = db.DateTimeProperty()
	count = db.IntegerProperty()
	userid = db.StringProperty()

	def update_csv(self, data, key=None):
		# create new blob if one does not exist
		if not key:
			csv_blob = write_csv(data)
			logging.debug('csv not exist, setup')
			insert_csv = UserSurveyCSV()
			insert_csv.csv = str(csv_blob)
			insert_csv.last_entry_date = data['timestamp']
			insert_csv.count = 1
			insert_csv.page = 1
			insert_csv.userid = data['username']
		else:	#if blob exists, append and update
			insert_csv = db.get(key)
			csv_blob = write_csv(data, insert_csv.csv)
			logging.debug('csv exist, append')
			insert_csv.csv = str(csv_blob)
			insert_csv.last_entry_date = data['timestamp']
			insert_csv.count += 1

		insert_csv.put()
		return insert_csv
	# end update_csv method

	def delete_from_csv(self, key, del_key):
		# create new blob if one does not exist
		if not key:
			return None

		csv_store = db.get(key)

		if csv_store is not None:
			rtn_value = delete_from_csv_blob(csv_store.csv, del_key)
			if not rtn_value:
				logging.debug('the csv row not found')
				return None

			csv_store.csv = rtn_value['csv']
			csv_store.count = rtn_value['count']
			csv_store.last_entry_date = rtn_value['dt']
			csv_store.put()
		else:
			logging.debug('the csv blob could not be retreived')

		return True
	# end delete_from_csv method
# End UserSurveyCSV Class

# model to hold data blob
class ClassSurveyCSV(db.Model):
	csv = db.TextProperty()
	last_updated = db.DateTimeProperty(auto_now=True)
	page = db.IntegerProperty()
	last_entry_date = db.DateTimeProperty()
	count = db.IntegerProperty()
	classid = db.StringProperty()

	def update_csv(self, data, key=None):
		# create new blob if one does not exist
		if not key:
			csv_blob = write_csv(data)
			logging.debug('csv not exist, setup')
			insert_csv = ClassSurveyCSV()
			insert_csv.csv = str(csv_blob)
			insert_csv.last_entry_date = data['timestamp']
			insert_csv.count = 1
			insert_csv.page = 1
			insert_csv.classid = data['classid']
		else:	#if blob exists, append and update
			insert_csv = db.get(key)
			csv_blob = write_csv(data, insert_csv.csv)
			logging.debug('csv exist, append')
			insert_csv.csv = str(csv_blob)
			insert_csv.last_entry_date = data['timestamp']
			insert_csv.count += 1

		insert_csv.put()
		return insert_csv
	# end update_csv method

	def delete_from_csv(self, key, del_key):
		# create new blob if one does not exist
		if not key:
			return None

		csv_store = db.get(key)

		if csv_store is not None:
			rtn_value = delete_from_csv_blob(csv_store.csv, del_key)
			if not rtn_value:
				logging.debug('the csv row not found')
				return None

			csv_store.csv = rtn_value['csv']
			csv_store.count = rtn_value['count']
			csv_store.last_entry_date = rtn_value['dt']
			csv_store.put()
		else:
			logging.debug('the csv blob could not be retreived')

		return True
	# end delete_from_csv method
# End ClassSurveyCSV Class

# model to hold data blob
class CleanSurveyCSV(db.Model):
	csv = db.TextProperty()
	last_updated = db.DateTimeProperty(auto_now=True)
	page = db.IntegerProperty()
	last_entry_date = db.DateTimeProperty()
	count = db.IntegerProperty()

	# function to write csv blob, this differs from the default write_csv used by other classes
	def write_csv(self, data, csv_blob = None):
		# init csv writer
		output = cStringIO.StringIO()
		writer = csv.writer(output, delimiter=',')

		base_url = ''
		if os.environ.get('HTTP_HOST'):
			base_url = os.environ['HTTP_HOST']
		else:
			base_url = os.environ['SERVER_NAME']

		# write header row if csv blob doesnt exist yet
		if not csv_blob:
			logging.debug('csv not exist, writing header row')
			header_row = [	'id',
				'userid',
				'classid',
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
		else:
			logging.debug('csv exist, do not output header')

		# form image url
		if data['hasphoto']:
			photo_url = 'http://' + base_url + "/get_an_image?key="+str(data['photo_key'])

		else:
			photo_url = 'no_image'

		hashedval = hashlib.sha1(str(data['key']))
		sha1val = hashedval.hexdigest()

		userhashedval = hashlib.sha1(data['username'])
		usersha1val = userhashedval.hexdigest()

		classhashedval = hashlib.sha1(data['classid'])
		classsha1val = classhashedval.hexdigest()

		# write csv data row
		new_row = [
				sha1val,
				usersha1val,
				classsha1val,
				data['timestamp'],
				data['latitude'],
				data['longitude'],
				data['stressval'],
				data['category'],
				data['subcategory'],
				data['comments'],
				photo_url
				]
		writer.writerow(new_row)
		#logging.debug('output: ' + str(output.getvalue()))

		if not csv_blob:
			return str(output.getvalue())
		else:
			return csv_blob + str(output.getvalue())
	# end write_csv function

	def update_csv(self, data, key=None):
		# create new blob if one does not exist
		if not key:
			csv_blob = self.write_csv(data) #write the csv (defined above)
			logging.debug('csv not exist, setup')
			insert_csv = CleanSurveyCSV()
			insert_csv.csv = str(csv_blob)
			insert_csv.last_entry_date = data['timestamp']
			insert_csv.count = 1
			insert_csv.page = 1
		else:	#if blob exists, append and update
			insert_csv = db.get(key)
			csv_blob = self.write_csv(data, insert_csv.csv) #write the csv (defined above)
			logging.debug('csv exist, append')
			insert_csv.csv = str(csv_blob)
			insert_csv.last_entry_date = data['timestamp']
			insert_csv.count += 1

		insert_csv.put()
		return insert_csv

	def delete_from_csv(self, key, del_key):
		# create new blob if one does not exist
		if not key:
			return None

		csv_store = db.get(key)

		if csv_store is not None:
			rtn_value = delete_from_csv_blob(csv_store.csv, del_key)
			if not rtn_value:
				logging.debug('the csv row not found')
				return None

			csv_store.csv = rtn_value['csv']
			csv_store.count = rtn_value['count']
			csv_store.last_entry_date = rtn_value['dt']
			csv_store.put()
		else:
			logging.debug('the csv blob could not be retreived')

		return True
	# end delete_from_csv method
# End SurveyCSV Class

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
	def increment_stats(self, key, user_category, user_subcategory, value):
		subcat = None
		if key is not None:
			subcat = db.get(key)

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
	# end increment_stats method

	# decrement the subcategory
	def decrement_stats(self, key, value):
		subcatstat = db.get(key)

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

		if subcatstat is not None:
			subcatstat.count -= 1
			subcatstat.total -= value
			subcatstat.stress_count -= scount
			subcatstat.stress_total -= sval
			subcatstat.chill_count -= ccount
			subcatstat.chill_total -= cval
			subcatstat.put()
			logging.debug('subcategory count: '+str(subcatstat.count))
			logging.debug('subcategory total: '+str(subcatstat.total))
			return True
		else:
			logging.debug('subcategory stat not found')
			return False
	# end decrement_stats method
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
	def increment_stats(self, key, user_subcategory, user_category, user_date, value):
		subcat = None
		if key is not None:
			subcat = db.get(key)

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

	# decrement the subcategory
	def decrement_stats(self, key, value):
		dailysubcatstat = db.get(key)

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

		if dailysubcatstat is not None:
			dailysubcatstat.count -= 1
			dailysubcatstat.total -= value
			dailysubcatstat.stress_count -= scount
			dailysubcatstat.stress_total -= sval
			dailysubcatstat.chill_count -= ccount
			dailysubcatstat.chill_total -= cval
			dailysubcatstat.put()
			logging.debug('daily subcategory count: '+str(dailysubcatstat.count))
			logging.debug('daily subcategory total: '+str(dailysubcatstat.total))
			return True
		else:
			logging.debug('daily subcategory stat not found')
			return False
	# end decrement_stats method
# End DailySubCategoryStat Class

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
	class_id = db.StringProperty()

	# increments the subcategory
	def increment_stats(self, key, user_id, user_subcategory, user_category, value, statclass):
		userstat = None
		if key is not None:
			userstat = db.get(key)


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
			self.class_id = statclass
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

	# decrement the subcategory
	def decrement_stats(self, key, value):
		userstat = db.get(key)

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

		if userstat is not None:
			userstat.count -= 1
			userstat.total -= value
			userstat.stress_count -= scount
			userstat.stress_total -= sval
			userstat.chill_count -= ccount
			userstat.chill_total -= cval
			userstat.put()
			logging.debug('user count: '+str(userstat.count))
			logging.debug('user total: '+str(userstat.total))
		else:
			logging.debug('user stat not found')
	# end decrement_stats method
# End UserStat Class

# model to keep total stats per user
class UserTotalStat(db.Model):
	user_id = db.StringProperty()
	username = db.StringProperty()
	count =	db.IntegerProperty()
	class_id = db.StringProperty()
	last_updated = 	db.DateTimeProperty(auto_now=True)

	# increments the subcategory
	def increment_stats(self, key, user_id, username = None, class_id = None):
		userstat = None
		if key is not None:
			userstat = db.get(key)

		setclass = 'testers'
		if class_id is not None:
			setclass = class_id

		if not userstat:
			self.user_id = user_id
			if not username:
				self.username = 'Anon'
			else:
				self.username = username
			self.count = 1
			self.class_id = setclass
			self.put()

			if self.is_saved():
				return self.key()
			else:
				return None
		else:
			userstat.count += 1
			userstat.put()

			if userstat.is_saved():
				return userstat.key()
			else:
				return None

	# decrement the subcategory
	def decrement_stats(self, key):
		userstat = db.get(key)

		if userstat is not None:
			userstat.count -= 1
			userstat.put()
			logging.debug('user count: '+str(userstat.count))
		else:
			logging.debug('user stat not found')
	# end decrement_stats method
# End UserTotalStat Class

#model to hold class info
class ClassList(db.Model):
	teacher = db.StringProperty()
	head_teacher = db.BooleanProperty()
	classid = db.StringProperty()
	classname = db.StringProperty()
	created = db.DateTimeProperty(auto_now_add=True)
# End ClassList Class

