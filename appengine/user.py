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

			# if data, setup display 
			if saved:
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
		template_values['userdata'] = True

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
				sess['username'] = self.request.get('username')
				sess['userid'] = uid

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

		# redirect to login page if not logged in
		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			sess['redirect'] = '/user/delete?key=' + self.request.get('key')
			sess.save()
			self.redirect('/user/login')
			return
		
		# check if key set
		if not self.request.get('key'):
			sess['error'] = 'No observation was selected.'
			sess.save()
			self.redirect('/user/data')
			return

		# check valid key
		try:
			db_key = db.Key(self.request.get('key'))
			if db_key.kind() != 'SurveyData':
				sess['error'] = 'Bad key.'
				sess.save()
				self.redirect('/user/data')
				return

		except:
			sess['error'] = 'Bad key.'
			sess.save()
			self.redirect('/user/data')
			return

		# check if user owns observation
		observation = db.get(self.request.get('key'))

		# if no observation exists with key, error
		if not observation:
			sess['error'] = 'No observation exists with this key or you do not have permission to delete this observation'
			sess.save()
			self.redirect('/user/data')
			return

		# if user not have permission, error
		if observation.username != sess['userid']:
			sess['error'] = 'No observation exists with this key or you do not have permission to delete this observation'
			sess.save()
			self.redirect('/user/data')
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

		path = os.path.join (os.path.dirname(__file__), 'views/delete.html')
		self.response.out.write (helper.render(self, path, template_values))
	# end get method
# End SetupDelete Class

# handler for: /user/confirm_delete
# delete observation
class ConfirmDelete(webapp.RequestHandler):
	def post(self):
		sess = gmemsess.Session(self)

		# redirect to login page if not logged in
		if sess.is_new() or not sess.has_key('username'):
			sess['error'] = 'Please log in to use this feature.'
			sess['redirect'] = '/user/delete?key=' + self.request.get('key')
			sess.save()
			self.redirect('/user/login')
			return

		# check if key set
		if not self.request.get('key'):
			sess['error'] = 'No observation was selected.'
			sess.save()
			self.redirect('/user/data')
			return

		# check valid key
		try:
			db_key = db.Key(self.request.get('key'))
			if db_key.kind() != 'SurveyData':
				sess['error'] = 'Bad key.'
				sess.save()
				self.redirect('/user/data')
				return

		except:
			sess['error'] = 'Bad key.'
			sess.save()
			self.redirect('/user/data')
			return

		# check if user owns observation
		observation = db.get(self.request.get('key'))

		# if no observation exists with key, error
		if not observation:
			sess['error'] = 'No observation exists with this key or you do not have permission to delete this observation'
			sess.save()
			self.redirect('/user/data')
			return

		# if user not have permission, error
		if observation.username != sess['userid']:
			sess['error'] = 'No observation exists with this key or you do not have permission to delete this observation'
			sess.save()
			self.redirect('/user/data')
			return

		#
		# TODO: the following operations need to occur in transactions...
		#

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

		# decrement category count and subtract from total 
		catstat = CategoryStat().all().filter('category =', observation.category).get()
		if catstat is not None:
			catstat.count -= 1
			catstat.total -= observation.stressval
			catstat.put()
			logging.debug('category count: '+str(catstat.count))
			logging.debug('category total: '+str(catstat.total))
		else:
			logging.debug('category stat not found')

		# decrement subcategory count and subtract from total
		subcatstat = SubCategoryStat().all().filter('category =', observation.category).filter('subcategory =', observation.subcategory).get()
		if subcatstat is not None:
			subcatstat.count -= 1
			subcatstat.total -= observation.stressval
			subcatstat.put()
			logging.debug('subcategory count: '+str(subcatstat.count))
			logging.debug('subcategory total: '+str(subcatstat.total))
		else:
			logging.debug('subcategory stat not found')

		pdt = observation.timestamp - datetime.timedelta(hours=7)
		time_key = str(pdt).split(' ')[0]
		dt = datetime.datetime.strptime(time_key, "%Y-%m-%d")
		date = datetime.date(dt.year, dt.month, dt.day)

		# decrement daily category count and subtract from total 
		dailycatstat = DailyCategoryStat().all().filter('category =', observation.category).filter('date =', date).get()
		if dailycatstat is not None:
			dailycatstat.count -= 1
			dailycatstat.total -= observation.stressval
			dailycatstat.put()
			logging.debug('daily category count: '+str(dailycatstat.count))
			logging.debug('daily category total: '+str(dailycatstat.total))
		else:
			logging.debug('daily category stat not found')
	
		# decrement daily subcategory count and subtract from total
		dailysubcatstat = DailySubCategoryStat().all().filter('category =', observation.category).filter('date =', date).filter('subcategory =', observation.subcategory).get()
		if dailysubcatstat is not None:
			dailysubcatstat.count -= 1
			dailysubcatstat.total -= observation.stressval
			dailysubcatstat.put()
			logging.debug('daily subcategory count: '+str(dailysubcatstat.count))
			logging.debug('daily subcategory total: '+str(dailysubcatstat.total))
		else:
			logging.debug('daily subcategory stat not found')

		# delete observation from csv blob
		# get csv blob
		csv_store = SurveyCSV.all().filter('page = ', 1).get()
		if csv_store is not None:
			# init csv reader
			csv_file = csv.DictReader(cStringIO.StringIO(str(csv_store.csv)))

			# hack... for some reason cant access csv_file.fieldnames until after tryng to iterate through csv_file...
			header_keys = []
			for row in csv_file:
				self.response.out.write('rowkeys: '+str(row.keys()))
				header_keys = row.keys()
				break

			# init csv writer
			output = cStringIO.StringIO()
			writer = csv.DictWriter(output, csv_file.fieldnames)

			# output csv header
			header = {}
			for h in csv_file.fieldnames:
				header[h] = h
			writer.writerow(header)

			row_count = 0
			last_entry_date = csv_store.last_entry_date
			del_flag = False

			hashedval = hashlib.sha1(str(observation.key()))
			sha1val = hashedval.hexdigest()


			# iterate through csv file
			for row in csv_file:

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
				# convert string to time
				m = re.match(r'(.*?)(?:\.(\d+))?(([-+]\d{1,2}):(\d{2}))?$',
					str(last_entry_date))
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

				# write csv values/blob
				csv_store.last_entry_date = dt
				csv_store.count = row_count
				csv_store.csv = db.Blob(output.getvalue())
				csv_store.put()
			else:
				logging.debug('row not found')
		else:
			logging.debug('the csv blob could not be retreived')

		# invalidate related cached items
		saved = memcache.get('saved')
		if saved is not None:
			oldest_date = saved[-1]['realtime']

			if oldest_date <= observation.timestamp:
				memcache.delete('saved')

		# form user data cache name
		cache_name = 'data_' + sess['userid']

		usersaved = memcache.get(cache_name)

		db.delete(observation)
		if usersaved is not None:
			oldest_date = usersaved[-1]['realtime']

			if oldest_date <= observation.timestamp:
				memcache.delete(cache_name)

		memcache.delete('csv')


		sess['success'] = 'Observation deleted.'
		sess.save()
		self.redirect('/user/data')
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


		# you should never get here except for the first time this url is called
		# if you need to populate the blob, make sure to call this url
		#	before any requests to write new data or the blob will start from that entry instead
		# NOTE: this will probably only work as long as the number of entries in your survey is low
		#	If there are too many entries already, this will likely time out
		#	I have added page as a property of the model incase we need it in future
		surveys = SurveyData.all().filter('username =', sess['userid']).order('timestamp').fetch(1000)

		if os.environ.get('HTTP_HOST'):
			base_url = os.environ['HTTP_HOST']
		else:
			base_url = os.environ['SERVER_NAME']

		counter = 0
		last_entry_date = ''
		page = 1

		# setup csv
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
		for s in surveys:
			photo_url = ''
			if s.hasphoto:
				try:
					photo_url = 'http://' + base_url + "/get_an_image?key="+str(s.photo_ref.key())
				except:
					photo_url = 'no_image'

			else:
				photo_url = 'no_image'

			hashedval = hashlib.sha1(str(s.key()))
			sha1val = hashedval.hexdigest()

			usersha1val = ''
			if s.username is not None:
				userhashedval = hashlib.sha1(s.username)
				usersha1val = userhashedval.hexdigest()
			else:
				usersha1val = 'none'

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
			counter += 1
			last_entry_date = s.timestamp

		# write blob csv so we dont have to do this again
		insert_csv = UserSurveyCSV()
		insert_csv.csv = db.Blob(output.getvalue())
		insert_csv.last_entry_date = last_entry_date
		insert_csv.count = counter
		insert_csv.page = page
		insert_csv.userid = sess['userid']
		insert_csv.put()

		self.response.headers['Content-type'] = 'text/csv'
		self.response.out.write(output.getvalue())
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
		result = CategoryStat().all()

		data = []
		for row in result:
			if row.count <= 0:
				cat_avg = 0
			else:
				cat_avg = row.total/row.count

			datarow = { 'category':str(row.category), 'count':str(row.count), 'avg':str(cat_avg) }

			subcat = SubCategoryStat().all().filter('category = ', row.category)
			allsub = []
			for subrow in subcat:
				if subrow.count <= 0:
					avg = 0
				else:
					avg = subrow.total/subrow.count
				subdatarow = { 'subcategory':str(subrow.subcategory), 'count':str(subrow.count), 'avg':str(avg) }
				allsub.append(subdatarow)
			datarow['subcategories'] = allsub

			data.append(datarow)

		num = len(data)

		template_values = { 'summary1' : data[:int(num/2)], 'summary2' : data[int(num/2):] }
		template_values['datasummary'] = True
		template_values['divstyle'] = ['span-11 colborder','span-12 last']
		path = os.path.join (os.path.dirname(__file__), 'views/summary.html')
		self.response.out.write (helper.render(self, path, template_values))
	# end handle method
# End SummaryHandler Class


application = webapp.WSGIApplication(
									 [
									  ('/user/data', UserDataByDatePage),
									  ('/user/map', UserMapPage),
									  ('/user/login', DisplayLogin),
									  ('/user/confirmlogin', ConfirmLogin),
									  ('/user/logout', LogoutHandler),
									  ('/user/delete', SetupDelete),
									  ('/user/confirm_delete', ConfirmDelete),
									  ('/user/user_data_download.csv', DownloadUserData)
									 ],
									 debug=True)

def main():
	logging.getLogger().setLevel(logging.DEBUG)
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
