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
from google.appengine.runtime import DeadlineExceededError

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
		keylist = SurveyData.__dict__.keys()
		self.response.out.write(str(keylist))

		for key in keylist:
			if key.startswith('_'):
				keylist.remove(key)

		self.response.out.write(str(keylist))

		row = SurveyData.all().get()
		self.response.out.write(str(row.__dict__['_'+str(keylist[0])]))
		'''
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
		subcategories = {}

		result = db.GqlQuery("SELECT * FROM SurveyData")

		for row in result:
			pdt = row.timestamp - datetime.timedelta(hours=7)
			time_key = str(pdt).split(' ')[0]

			scount = 0
			sval = 0
			ccount = 0
			cval = 0

			if row.stressval < 0:
				scount = 1
				sval = float(row.stressval)
			else:
				ccount = 1
				cval = float(row.stressval)

			if not subcategories.has_key(time_key):
				subcategories[time_key] = {}

			if subcategories[time_key].has_key(str(row.subcategory)):
				subcategories[time_key][str(row.subcategory)]['count'] += 1
				subcategories[time_key][str(row.subcategory)]['total'] += float(row.stressval)
				subcategories[time_key][str(row.subcategory)]['stress_count'] += scount
				subcategories[time_key][str(row.subcategory)]['stress_total'] += sval
				subcategories[time_key][str(row.subcategory)]['chill_count'] += ccount
				subcategories[time_key][str(row.subcategory)]['chill_total'] += cval
			else:
				tmp = {	'count':1, 
					'total':float(row.stressval),
					'category':str(row.category),
					'stress_count':scount,
					'stress_total':sval,
					'chill_count':ccount,
					'chill_total':cval
					}
				subcategories[time_key][str(row.subcategory)] = tmp
			
		for date_key in subcategories.keys():
			for subcat_keys in subcategories[date_key].keys():
				scstat = DailySubCategoryStat()
				scstat.category = subcategories[date_key][subcat_keys]['category']
				scstat.subcategory = subcat_keys
				datestr = date_key.split('.')[0]
				dt = datetime.datetime.strptime(datestr, "%Y-%m-%d")
				x = datetime.date(dt.year, dt.month, dt.day)
				scstat.date = x
				scstat.count = subcategories[date_key][subcat_keys]['count']
				scstat.total = float(subcategories[date_key][subcat_keys]['total'])
				scstat.stress_count = subcategories[date_key][subcat_keys]['stress_count']
				scstat.stress_total = float(subcategories[date_key][subcat_keys]['stress_total'])
				scstat.chill_count = subcategories[date_key][subcat_keys]['chill_count']
				scstat.chill_total = float(subcategories[date_key][subcat_keys]['chill_total'])
				scstat.put()

# Populates the stats Datastore
# this should only be run once to populate the datastore with existing values
class PopulateStat(webapp.RequestHandler):
	def get(self):
		# populate stats models
		subcategories = {}

		result = db.GqlQuery("SELECT * FROM SurveyData")

		for row in result:
			scount = 0
			sval = 0
			ccount = 0
			cval = 0

			if row.stressval < 0:
				scount = 1
				sval = float(row.stressval)
			else:
				ccount = 1
				cval = float(row.stressval)


			if subcategories.has_key(str(row.subcategory)):
				subcategories[str(row.subcategory)]['count'] += 1
				subcategories[str(row.subcategory)]['total'] += float(row.stressval)
				subcategories[str(row.subcategory)]['stress_count'] += scount
				subcategories[str(row.subcategory)]['stress_total'] += sval
				subcategories[str(row.subcategory)]['chill_count'] += ccount
				subcategories[str(row.subcategory)]['chill_total'] += cval
			else:
				tmp = {	'count':1, 
					'total':float(row.stressval),
					'category':str(row.category),
					'stress_count':scount,
					'stress_total':sval,
					'chill_count':ccount,
					'chill_total':cval
					}
				subcategories[str(row.subcategory)] = tmp


		for subcat_keys in subcategories.keys():
			scstat = SubCategoryStat()
			scstat.category = subcategories[subcat_keys]['category']
			scstat.subcategory = subcat_keys
			scstat.count = subcategories[subcat_keys]['count']
			scstat.total = float(subcategories[subcat_keys]['total'])
			scstat.stress_count = subcategories[subcat_keys]['stress_count']
			scstat.stress_total = float(subcategories[subcat_keys]['stress_total'])
			scstat.chill_count = subcategories[subcat_keys]['chill_count']
			scstat.chill_total = float(subcategories[subcat_keys]['chill_total'])
			scstat.put()

# Populates the user stats Datastore
# this should only be run once to populate the datastore with existing values
class PopulateUserStat(webapp.RequestHandler):
	def get(self):
		# get data from memcache if exist, exit if none
		self.response.out.write('<html><body>')
		data = memcache.get('datastore_all')
		if not data:
			self.response.out.write('no data')
			self.response.out.write('</body></html>')
			return
		if not self.request.get('classid'):
			self.response.out.write('no class set')
			self.response.out.write('</body></html>')
			return

		subcategories = {}

		# update user total stats (this should probably be moved to the task queue)
		classlist = memcache.get('classlist')
		# if not exist, fetch from datastore
		if not classlist:
			cl = ClassList().all()

			classlist = []
			for c in cl:
				classlist.append(c.classid)

			# save to memcache to prevent this lookup from happening everytime
			memcache.set('classlist', classlist)

		for row in data:
			user_key = 'None'
			if row['username'] is not None:
				user_key = row['username']

			scount = 0
			sval = 0
			ccount = 0
			cval = 0

			if row['stressval'] < 0:
				scount = 1
				sval = float(row['stressval'])
			else:
				ccount = 1
				cval = float(row['stressval'])

			if not subcategories.has_key(user_key):
				subcategories[user_key] = {}

			if subcategories[user_key].has_key(str(row['subcategory'])):
				subcategories[user_key][str(row['subcategory'])]['count'] += 1
				subcategories[user_key][str(row['subcategory'])]['total'] += float(row['stressval'])
				subcategories[user_key][str(row['subcategory'])]['stress_count'] += scount
				subcategories[user_key][str(row['subcategory'])]['stress_total'] += sval
				subcategories[user_key][str(row['subcategory'])]['chill_count'] += ccount
				subcategories[user_key][str(row['subcategory'])]['chill_total'] += cval
			else:
				tmp = {	'count':1, 
					'total':float(row['stressval']),
					'category':str(row['category']),
					'stress_count':scount,
					'stress_total':sval,
					'chill_count':ccount,
					'chill_total':cval
					}

				statclass = 'testers'
				if row['classid'] in classlist:
					statclass = row['classid']
				tmp['class_id'] = statclass
				subcategories[user_key][str(row['subcategory'])] = tmp
			
		count = 0

		for user_key in subcategories.keys():
			for subcat_keys in subcategories[user_key].keys():
				if subcategories[user_key][subcat_keys]['class_id'] != self.request.get('classid'):
					self.response.out.write('wrong class. skipping. <br />')
					continue
				else:
					self.response.out.write('writing user stat. <br />')

				count += 1
				if self.request.get('lower'):
					if count < int(self.request.get('lower')):
						continue

				if self.request.get('upper'):
					if count >= int(self.request.get('upper')):
						break


				scstat = UserStat()
				scstat.category = subcategories[user_key][subcat_keys]['category']
				scstat.subcategory = subcat_keys
				scstat.count = subcategories[user_key][subcat_keys]['count']
				scstat.total = float(subcategories[user_key][subcat_keys]['total'])
				scstat.stress_count = subcategories[user_key][subcat_keys]['stress_count']
				scstat.stress_total = float(subcategories[user_key][subcat_keys]['stress_total'])
				scstat.chill_count = subcategories[user_key][subcat_keys]['chill_count']
				scstat.chill_total = float(subcategories[user_key][subcat_keys]['chill_total'])
				scstat.user_id = user_key
				scstat.class_id = subcategories[user_key][subcat_keys]['class_id']
				scstat.put()

class ShowUserCSV(webapp.RequestHandler):
	def get(self):
		ulist = UserStat().all()

		self.response.out.write('<html><body>\n')
		self.response.out.write('<form action="/debug/populate_user_csv" method="post">\n')
		self.response.out.write('<select name="userid">\n')
		for user in ulist:
			self.response.out.write('<option value="'+user.user_id+'">'+user.user_id+'</option>\n')
		self.response.out.write('</select>')
		self.response.out.write('<input type="submit" name="Submit">')
		self.response.out.write('</form></body></html>')

# Populates the User csv
# this should only be run once to populate the datastore with existing values
# this will have to be reimplemented with the task queue and cursors (or something...) if attempting to run on much larger data sets
class PopulateUserCSV(webapp.RequestHandler):
	def post(self):
		if not self.request.get('userid'):
			self.error(401, 'No user selected')
			return

		q = UserSurveyCSV().all().filter('userid =', self.request.get('userid')).fetch(10)
		db.delete(q)

		#write to csv blob and update memcache
		result = SurveyData().all().filter('username =', self.request.get('userid'))

		data = ''
		count = 0
		output = cStringIO.StringIO()
		writer = csv.writer(output, delimiter=',')

		base_url = ''
		if os.environ.get('HTTP_HOST'):
			base_url = os.environ['HTTP_HOST']
		else:
			base_url = os.environ['SERVER_NAME']

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

		try:
			self.response.out.write('<html><body>')
			res_count = 0
			for s in result:
				res_count += 1
				self.response.out.write(str(count+res_count)+',')
				self.response.out.write(str(s.timestamp)+',')
				self.response.out.write(str(s.username)+',')
				self.response.out.write(str(s.stressval)+'<br/>\n')

				# form image url
				if s.hasphoto:
					try:
						photo_url = 'http://' + base_url + "/get_an_image?key="+str(s.photo_ref.key())
					except:
						photo_url = 'no_image'

				else:
					photo_url = 'no_image'

				hashedval = hashlib.sha1(str(s.key()))
				sha1val = hashedval.hexdigest()

				usersha1val = 'Anon'
				if s.username is not None:
					userhashedval = hashlib.sha1(s.username)
					usersha1val = userhashedval.hexdigest()

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

			# append to blob
			data += str(output.getvalue())
			count += res_count

			self.response.out.write('</html></body>')

			insert_csv = UserSurveyCSV()
			insert_csv.csv = db.Text(data)
			insert_csv.count = count
			insert_csv.page = 1
			insert_csv.userid = self.request.get('userid')
			insert_csv.put()
			return
		except DeadlineExceededError:
			self.response.out.write('deadline exceeded.<br>')
			return

		return

# Populates the csv
# this should only be run once to populate the datastore with existing values
# this will only work while the number of rows is not so high that it will not fit in memcache
# once row count gets very high, will probably have to write to a TextProperty instead
# this was not meant to be done very frequently anyway...
class PopulateCSV(webapp.RequestHandler):
	def get(self):
		#write to csv blob and update memcache
		result = SurveyData().all()

		data = ''
		count = 0
		output = cStringIO.StringIO()
		writer = csv.writer(output, delimiter=',')

		base_url = ''
		if os.environ.get('HTTP_HOST'):
			base_url = os.environ['HTTP_HOST']
		else:
			base_url = os.environ['SERVER_NAME']

		if self.request.get('cursor'):
			result.with_cursor(self.request.get('cursor'))
			data = memcache.get('csv_restore')
			count = memcache.get('csv_restore_count')
		else:
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

		try:
			self.response.out.write('<html><body>')
			res_count = 0
			for s in result.fetch(50):
				res_count += 1
				self.response.out.write(str(count+res_count)+',')
				self.response.out.write(str(s.timestamp)+',')
				self.response.out.write(str(s.username)+',')
				self.response.out.write(str(s.stressval)+'<br/>\n')

				# form image url
				if s.hasphoto:
					try:
						photo_url = 'http://' + base_url + "/get_an_image?key="+str(s.photo_ref.key())
					except:
						photo_url = 'no_image'

				else:
					photo_url = 'no_image'

				hashedval = hashlib.sha1(str(s.key()))
				sha1val = hashedval.hexdigest()

				usersha1val = 'Anon'
				if s.username is not None:
					userhashedval = hashlib.sha1(s.username)
					usersha1val = userhashedval.hexdigest()

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

			# append to blob
			data += str(output.getvalue())
			count += res_count

			memcache.set('csv_restore', data)
			memcache.set('csv_restore_count', count)

			cursor = result.cursor()
			if cursor:
				self.response.out.write('<a href="/debug/populate_csv?cursor='+cursor+'">click to continue</a>')
			self.response.out.write('</html></body>')
			return
		except DeadlineExceededError:
			self.response.out.write('deadline exceeded.<br>')
			self.response.out.write('<a href="/debug/populate_csv?cursor='+self.request.get('cursor')+'">click to retry</a>')
			return

		return

class MemCSV(webapp.RequestHandler):
	def get(self):
		data = memcache.get('csv_restore')
		# if all data in cache, output and done
		if data is not None:
			self.response.headers['Content-type'] = 'text/csv'
			self.response.out.write(data)
			return
		return

class WriteMemCSV(webapp.RequestHandler):
	def get(self):
		data = memcache.get('csv_restore')
		count = memcache.get('csv_restore_count')
		# if all data in cache, output and done
		if data is not None:
			insert_csv = SurveyCSV()
			insert_csv.csv = db.Text(data)
			insert_csv.count = count
			insert_csv.page = 1
			insert_csv.put()
		return
		
# this will only work while the number of rows is not so high that it will not fit in memcache
# once row count gets very high, will probably have to write to a TextProperty instead
# this was not meant to be done very frequently anyway...
# saves SurveyData to memcache to preform operations on the entire datastore
class Datastore2Memcache(webapp.RequestHandler):
	def get(self):
		#write to csv blob and update memcache
		result = SurveyData().all()

		data = []
		count = 0

		classlist = memcache.get('classlist')
		# if not exist, fetch from datastore
		if not classlist:
			cl = ClassList().all()

			classlist = []
			for c in cl:
				classlist.append(c.classid)

			# save to memcache to prevent this lookup from happening everytime
			memcache.set('classlist', classlist)

		if self.request.get('cursor'):
			result.with_cursor(self.request.get('cursor'))
			data = memcache.get('datastore_all')
			count = memcache.get('datastore_count')

		try:
			self.response.out.write('<html><body>')
			res_count = 0
			for s in result.fetch(50):
				res_count += 1
				self.response.out.write(str(count+res_count)+',')
				self.response.out.write(str(s.timestamp)+',')
				self.response.out.write(str(s.username)+',')
				self.response.out.write(str(s.stressval)+'<br/>\n')

				if s.classid not in classlist:
					s.classid = 'testers'
					s.put()

				photo_ref = None
				if s.hasphoto:
					try:
						photo_ref = str(s.photo_ref.key())
					except:
						pass

				new_row = {
						'key':str(s.key()),
						'username':s.username,
						'classid':s.classid,
						'timestamp':s.timestamp,
						'latitude':s.latitude,
						'longitude':s.longitude,
						'stressval':s.stressval,
						'category':s.category,
						'subcategory':s.subcategory,
						'comments':s.comments,
						'photo_ref':photo_ref,
						'hasphoto':s.hasphoto,
						'version':s.version
						}
				data.append(new_row)

			count += res_count

			memcache.set('datastore_all', data)
			memcache.set('datastore_count', count)

			cursor = result.cursor()
			if cursor is not None and cursor != self.request.get('cursor'):
				self.response.out.write('<a href="/debug/data2memcache?cursor='+cursor+'">click to continue</a>')
			self.response.out.write('</html></body>')
			return
		except DeadlineExceededError:
			self.response.out.write('deadline exceeded.<br>')
			self.response.out.write('<a href="/debug/data2memcache?cursor='+self.request.get('cursor')+'">click to retry</a>')
			return

		return

class ShowMemStore(webapp.RequestHandler):
	def get(self):
		data = memcache.get('datastore_all')
		if not data:
			self.response.out.write('no data')
			return

		self.response.out.write('<html><body><pre>')
		for s in data:
			self.response.out.write(str(s)+'<br />\n')
			'''
			self.response.out.write(str(s['timestamp'])+',')
			self.response.out.write(str(s['username'])+',')
			self.response.out.write(str(s['category'])+',')
			self.response.out.write(str(s['subcategory'])+',')
			self.response.out.write(str(s['stressval'])+'<br/>\n')
			'''
		self.response.out.write('</pre></body></html>')
		return

# Populates user csv from memcache
# this should only be run once to populate the datastore with existing values
class UserPopulateCSVMemcache(webapp.RequestHandler):
	def get(self):
		# get data from memcache if exist, exit if none
		data = memcache.get('datastore_all')
		if not data:
			self.response.out.write('no data')
			return

		base_url = ''
		if os.environ.get('HTTP_HOST'):
			base_url = os.environ['HTTP_HOST']
		else:
			base_url = os.environ['SERVER_NAME']

		#form user csvs
		user_data = {}

		for s in data:
			if not s['username']:
				s['username'] = 'Anon'

			if not user_data.has_key(str(s['username'])):
				user_data[s['username']] = []
			user_data[s['username']].append(s)

		for key,user in user_data.iteritems():
			output = cStringIO.StringIO()
			writer = csv.writer(output, delimiter=',')

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

			count = 0
			for s in user:
				# form image url
				if s['hasphoto']:
					try:
						photo_url = 'http://' + base_url + "/get_an_image?key="+s['photo_ref']
					except:
						photo_url = 'no_image'

				else:
					photo_url = 'no_image'

				hashedval = hashlib.sha1(s['key'])
				sha1val = hashedval.hexdigest()

				usersha1val = 'Anon'
				if s['username'] is not None and s['username'] != 'Anon':
					userhashedval = hashlib.sha1(s['username'])
					usersha1val = userhashedval.hexdigest()

				# write csv data row
				new_row = [
						sha1val,
						usersha1val,
						s['timestamp'],
						s['latitude'],
						s['longitude'],
						s['stressval'],
						s['category'],
						s['subcategory'],
						s['comments'],
						photo_url
						]
				writer.writerow(new_row)
				count += 1
			q = UserSurveyCSV().all().filter('userid =', key).fetch(10)
			db.delete(q)
			insert_csv = UserSurveyCSV()
			insert_csv.csv = db.Text(output.getvalue())
			insert_csv.count = count
			insert_csv.page = 1
			insert_csv.userid = key
			self.response.out.write(str(insert_csv.userid)+': '+str(insert_csv.count)+'<br>\n')
			insert_csv.put()
			output.close()

		return

# Populates class csv from memcache
# this should only be run once to populate the datastore with existing values
class ClassPopulateCSVMemcache(webapp.RequestHandler):
	def get(self):
		# get data from memcache if exist, exit if none
		data = memcache.get('datastore_all')
		if not data:
			self.response.out.write('no data')
			return

		base_url = ''
		if os.environ.get('HTTP_HOST'):
			base_url = os.environ['HTTP_HOST']
		else:
			base_url = os.environ['SERVER_NAME']

		#form user csvs
		class_data = {}


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

		userlist = memcache.get('user_all')
		# if not exist, fetch from datastore
		if not userlist:
			self.response.out.write('retreive user list first')
			return

		for s in data:
			# get classid of class, or set to 'tester'
			classid = 'testers'

			if not s['username']:
				pass
			elif userlist.has_key(s['username']):
				classid = userlist[s['username']]

				if classid not in classlist:
					classid = 'testers'
				elif s['classid'] != classid:
					self.response.out.write('class: ' + s['classid'] + ' -> ' + classid + '<br />')
					#updaterow = db.get(db.Key(s['key']))
					#updaterow.classid = classid
					#self.response.out.write(updaterow.classid)
					#updaterow.put()
					#if updaterow.is_saved():
					#	self.response.out.write('updated')
					#self.response.out.write('<hr/>')
			else:
				self.response.out.write('user not in list<br />')


			if not class_data.has_key(classid):
				class_data[classid] = []
			class_data[classid].append(s)


		for key,classes in class_data.iteritems():
			output = cStringIO.StringIO()
			writer = csv.writer(output, delimiter=',')

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

			count = 0
			for s in classes:
				# form image url
				if s['hasphoto']:
					try:
						photo_url = 'http://' + base_url + "/get_an_image?key="+s['photo_ref']
					except:
						photo_url = 'no_image'

				else:
					photo_url = 'no_image'

				hashedval = hashlib.sha1(s['key'])
				sha1val = hashedval.hexdigest()

				usersha1val = 'Anon'
				if s['username'] is not None:
					userhashedval = hashlib.sha1(s['username'])
					usersha1val = userhashedval.hexdigest()

				# write csv data row
				new_row = [
						sha1val,
						usersha1val,
						s['timestamp'],
						s['latitude'],
						s['longitude'],
						s['stressval'],
						s['category'],
						s['subcategory'],
						s['comments'],
						photo_url
						]
				writer.writerow(new_row)
				count += 1
			q = ClassSurveyCSV().all().filter('classid =', key).fetch(10)
			db.delete(q)
			insert_csv = ClassSurveyCSV()
			insert_csv.csv = db.Text(output.getvalue())
			insert_csv.count = count
			insert_csv.page = 1
			insert_csv.classid = key
			insert_csv.put()
			output.close()
		return

class ChangePassword(webapp.RequestHandler):
	def get(self):
		self.response.out.write('''
<html><body>
	<form action="/debug/change_pass" method="POST">
		<input type="text" name="username">
		<input type="password" name="password">
		<input type="password" name="repeat">
		<input type="submit">
	</form>
</body></html>
		''')

	def post(self):
		if not self.request.get('username') or \
				not self.request.get('password') or \
				not self.request.get('repeat'):
			self.response.out.write('missing field.')
			return

		if self.request.get('password') != self.request.get('repeat'):
			self.response.out.write('mismatch')
			return
		
		if UserTable().update_user(self.request.get('username'), self.request.get('password')):
			self.response.out.write('changed')
		else:
			self.response.out.write('failed')
# End ChanePassword Class

class UploadUsers(webapp.RequestHandler):
	def get(self):
		self.response.out.write('''
<html><body>
	<form action="/debug/upload_users" method="POST" enctype="multipart/form-data">
		<input type="file" name="classfile">
		<input type="submit">
	</form>
</body></html>
		''')
	def post(self):
		if not self.request.get('classfile'):
			self.response.out.write('missing file')
			return

		data = self.request.get('classfile').split('\r\n')

		self.response.out.write('<html><body>')
		for row in data:
			field = row.split(',')
			if len(field) > 6:
				if field[2] != 'username':
					self.response.out.write('--' + field[2] + ': ' + field[3] + ' - ' + field[4] + ' - ' + field[5] + '<br />')
					if not UserTable().create_user(field[2], field[3], field[5], field[4]):
						self.response.out.write ('<strong><font color="red">could not create user</font></strong><br /><br />')

		self.response.out.write('</body></html>')

# Populates user csv from memcache
# this should only be run once to populate the datastore with existing values
class UserTotalMemcache(webapp.RequestHandler):
	def get(self):
		# get data from memcache if exist, exit if none
		self.response.out.write('<html><body>')
		data = memcache.get('datastore_all')
		if not data:
			self.response.out.write('no data')
			self.response.out.write('</body></html>')
			return
		if not self.request.get('classid'):
			self.response.out.write('no class set')
			self.response.out.write('</body></html>')
			return

		user_data = {}

		# update user total stats (this should probably be moved to the task queue)
		classlist = memcache.get('classlist')
		# if not exist, fetch from datastore
		if not classlist:
			cl = ClassList().all()

			classlist = []
			for c in cl:
				classlist.append(c.classid)

			# save to memcache to prevent this lookup from happening everytime
			memcache.set('classlist', classlist)

		userlist = memcache.get('full_user')
		# if not exist, fetch from datastore
		if not userlist:
			self.response.out.write('retreive user list first')
			return

		for s in data:
			if not s['username']:
				s['username'] = 'Anon'

			if not user_data.has_key(str(s['username'])):
				user_data[s['username']] = {}

				user_data[s['username']]['count'] = 0

				statclass = 'testers'
				if s['classid'] in classlist:
					statclass = s['classid']
				user_data[s['username']]['classid'] = statclass

			user_data[s['username']]['count'] += 1

		usertotalstat = UserTotalStat().all().filter('class_id =', self.request.get('classid')).fetch(500)
		db.delete(usertotalstat)

		for user,stat in user_data.iteritems():
			if user == 'Anon':
				continue

			if not userlist.has_key(user):
				self.response.out.write(user+' not found.<br />\n')
				continue

			newstat = UserTotalStat()
			newstat.user_id = user
			uname = userlist[user]['username']
			if uname:
				newstat.username = uname
			else:
				newstat.username = 'Anon'
			newstat.count = stat['count']
			newstat.class_id = stat['classid']

			if stat['classid'] != self.request.get('classid'):
				self.response.out.write('wrong class. skipping. <br />')
				continue

			newstat.put()
			self.response.out.write(str(newstat.username)+' - '+str(user)+': '+str(stat['count'])+' - '+str(stat['classid'])+'<br />')

		self.response.out.write('</body></html>')
		return

# unapprove all user
# /debug/unapprove_user
class UnapproveUser(webapp.RequestHandler):
	def get(self):
		result = UserTable().all()

		data = []
		count = 0

		if self.request.get('cursor'):
			result.with_cursor(self.request.get('cursor'))

		self.response.out.write('<html><body>')
		for s in result.fetch(100):
			self.response.out.write(str(s.username) + '<br />\n')
			s.approved = False
			s.put()

		cursor = result.cursor()

		if cursor is not None and cursor != self.request.get('cursor'):
			self.response.out.write('<a href="/debug/unapprove_user?cursor='+cursor+'">click to continue</a>')
		self.response.out.write('</body></html>')

class ApproveUser(webapp.RequestHandler):
	def get(self):
		result = UserTable().all().filter('approved =', False)


		s = result.get()

		if s:
			self.response.out.write('<html><body>')
			self.response.out.write('<form action="/debug/approve_user" method="POST">')
			self.response.out.write(str(s.username))
			self.response.out.write('<input name = "classid" type="text" value="' + str(s.classid) + '">')
			cursor = result.cursor()
			self.response.out.write('<input type="hidden" name="cursor" value="' + str(cursor) + '">')
			self.response.out.write('<input type="hidden" name="key" value="' + str(s.key()) + '">')
			self.response.out.write('<input type="submit"')


			self.response.out.write('</form>')
			self.response.out.write('</body></html>')
		else:
			self.response.out.write('no user found')

	def post(self):
		if self.request.get('key'):
			db_key = db.Key(self.request.get('key'))

			res = db.get(db_key)

			if not res:
				self.response.out.write('error, bad key')
				return

			res.classid = self.request.get('classid')
			res.approved = True
			res.put()
		else:
			logging.debug('key: not set')

		if not self.request.get('cursor'):
			self.response.out.write('no more user')
			return


		result = UserTable().all().filter('approved =', False).with_cursor(self.request.get('cursor'))


		s = result.get()
		if s:
			self.response.out.write('<html><body>')
			self.response.out.write('<form action="/debug/approve_user" method="POST">')
			self.response.out.write(str(s.username))
			self.response.out.write('<input name = "classid" type="text" value="' + str(s.classid) + '">')
			cursor = result.cursor()
			self.response.out.write('<input type="hidden" name="cursor" value="' + str(cursor) + '">')
			self.response.out.write('<input type="hidden" name="key" value="' + str(s.key()) + '">')
			self.response.out.write('<input type="submit"')


			self.response.out.write('</form>')
			self.response.out.write('</body></html>')
		else:
			self.response.out.write('no user found')

class User2Mem(webapp.RequestHandler):
	def get(self):
		#write to csv blob and update memcache
		result = UserTable().all()

		data = {}
		fulldata = {}
		count = 0

		classlist = memcache.get('classlist')
		# if not exist, fetch from datastore
		if not classlist:
			cl = ClassList().all()

			classlist = []
			for c in cl:
				classlist.append(c.classid)

			# save to memcache to prevent this lookup from happening everytime
			memcache.set('classlist', classlist)

		if self.request.get('cursor'):
			result.with_cursor(self.request.get('cursor'))
			data = memcache.get('user_all')
			count = memcache.get('user_count')

		try:
			self.response.out.write('<html><body>')
			res_count = 0
			classid = 'testers'
			for s in result.fetch(500):
				res_count += 1

				classid = 'testers'
				if s.classid not in classlist:
					classid = 'testers'
				else:
					classid = s.classid
				self.response.out.write(str(count+res_count)+',')
				self.response.out.write(str(s.ckey)+',')
				self.response.out.write(str(classid)+'<br />')

				data[s.ckey] = classid

				fulldata[s.ckey] = {}
				fulldata[s.ckey]['username'] = s.username
				fulldata[s.ckey]['classid'] = classid
				

			memcache.set('user_all', data)
			memcache.set('user_count', count)
			memcache.set('full_user', fulldata)

			cursor = result.cursor()
			if cursor is not None and cursor != self.request.get('cursor'):
				self.response.out.write('<a href="/debug/user2mem?cursor='+cursor+'">click to continue</a>')
			self.response.out.write('</html></body>')
			return
		except DeadlineExceededError:
			self.response.out.write('deadline exceeded.<br>')
			return

		return

# create csv from memcache including no testers
class CleanPopulateCSVMemcache(webapp.RequestHandler):
	def get(self):
		# get data from memcache if exist, exit if none
		data = memcache.get('datastore_all')
		if not data:
			self.response.out.write('no data')
			return

		base_url = ''
		if os.environ.get('HTTP_HOST'):
			base_url = os.environ['HTTP_HOST']
		else:
			base_url = os.environ['SERVER_NAME']

		#form user csvs
		out_data = []

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

		for s in data:
			# get classid of class, or set to 'tester'
			classid = 'testers'
			if s['classid'] in classlist:
				classid = s['classid']

			if classid != 'testers':
				out_data.append(s)

		output = cStringIO.StringIO()
		writer = csv.writer(output, delimiter=',')


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

		count = 0
		for s in out_data:
			# form image url
			if s['hasphoto']:
				try:
					photo_url = 'http://' + base_url + "/get_an_image?key="+s['photo_ref']
				except:
					photo_url = 'no_image'

			else:
				photo_url = 'no_image'

			hashedval = hashlib.sha1(s['key'])
			sha1val = hashedval.hexdigest()

			usersha1val = 'Anon'
			if s['username'] is not None:
				userhashedval = hashlib.sha1(s['username'])
				usersha1val = userhashedval.hexdigest()

			# write csv data row
			new_row = [
					sha1val,
					usersha1val,
					s['timestamp'],
					s['latitude'],
					s['longitude'],
					s['stressval'],
					s['category'],
					s['subcategory'],
					s['comments'],
					photo_url
					]
			writer.writerow(new_row)
			count += 1

		q = CleanSurveyCSV().all().filter('page =', 1).fetch(10)
		db.delete(q)
		insert_csv = CleanSurveyCSV()
		insert_csv.csv = db.Text(output.getvalue())
		insert_csv.count = count
		insert_csv.page = 1
		insert_csv.put()
		output.close()
		return


class DeleteDatastore(webapp.RequestHandler):
	def get(self):
		self.handler()
	def post(self):
		self.handler()
	def handler(self):
		'''
		q = UserStat().all().filter('class_id =', 'testers').fetch(500)
		db.delete(q)

		q = UserTotalStat().all().fetch(500)
		db.delete(q)

		q = DailySubCategoryStat().all().fetch(500)
		db.delete(q)

		q = SubCategoryStat().all().fetch(500)
		db.delete(q)

		q = UserSurveyCSV().all().fetch(500)
		db.delete(q)

		q = SurveyCSV().all().fetch(500)
		db.delete(q)

		q = SurveyData().all().fetch(500)
		db.delete(q)

		q = SurveyPhoto().all().fetch(500)
		db.delete(q)

		q = UserSurveyCSV().all().fetch(500)
		db.delete(q)

		q = ClassSurveyCSV().all().fetch(500)
		db.delete(q)

		'''
		memcache.flush_all()


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
									  ('/debug/show_user_csv', ShowUserCSV),
									  ('/debug/populate_user_csv', PopulateUserCSV),
									  ('/debug/populate_csv', PopulateCSV),
									  ('/debug/show_mem_csv.csv', MemCSV),
									  ('/debug/write_mem_csv', WriteMemCSV),
									  ('/debug/data2memcache', Datastore2Memcache),
									  ('/debug/show_mem_store', ShowMemStore),
									  ('/debug/populate_all_user_csv', UserPopulateCSVMemcache),
									  ('/debug/populate_all_class_csv', ClassPopulateCSVMemcache),
									  ('/debug/change_pass', ChangePassword),
									  ('/debug/upload_users', UploadUsers),
									  ('/debug/populate_total_stat', UserTotalMemcache),
									  ('/debug/unapprove_user', UnapproveUser),
									  ('/debug/approve_user', ApproveUser),
									  ('/debug/user2mem', User2Mem),
									  ('/debug/clean_csv', CleanPopulateCSVMemcache),
									  ('/debug/delete_all', DeleteDatastore)
									  ],
									 debug=True)

def main():
	logging.getLogger().setLevel(logging.DEBUG)
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
