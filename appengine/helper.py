import logging
import cgi
import datetime as datetime_module

from google.appengine.api import memcache
from google.appengine.ext.webapp import template
import gmemsess

from datastore import *
import re

import cStringIO
import csv
import os

### date time stuff

# from python tzinfo docs
ZERO = datetime_module.timedelta(0)
PAGE_SIZE = 20


class UTC_tzinfo(datetime_module.tzinfo):
	"""UTC"""

	def utcoffset(self, dt):
		return ZERO

	def tzname(self, dt):
		return "UTC"

	def dst(self, dt):
		return ZERO

# from the appengine docs
class Pacific_tzinfo(datetime_module.tzinfo):
	"""Implementation of the Pacific timezone."""
	def utcoffset(self, dt):
		return datetime_module.timedelta(hours=-8) + self.dst(dt)

	def _FirstSunday(self, dt):
		"""First Sunday on or after dt."""
		return dt + datetime_module.timedelta(days=(6-dt.weekday()))

	def dst(self, dt):
		# 2 am on the second Sunday in March
		dst_start = self._FirstSunday(datetime_module.datetime(dt.year, 3, 8, 2))
		# 1 am on the first Sunday in November
		dst_end = self._FirstSunday(datetime_module.datetime(dt.year, 11, 1, 1))

		if dst_start <= dt.replace(tzinfo=None) < dst_end:
			return datetime_module.timedelta(hours=1)
		else:
			return datetime_module.timedelta(hours=0)
	def tzname(self, dt):
		if self.dst(dt) == datetime_module.timedelta(hours=0):
			return "PST"
		else:
			return "PDT"


# returns up to page_size + 1 values
def get_page_from_cache(cache_entry, page, page_size=20):
	if page <= 0:
		logging.debug('page must be greater than 1')
		return None

	if page_size <= 0:
		logging.debug('page size must be possitive')
		return None

	logging.debug('trying cache')

	# if cache entry not exist, return error
	if not cache_entry:
		logging.debug('cache entry not exist')
		return None

	# if in cache, get values
	entry_len = len(cache_entry)
	logging.debug('saved_len: '+str(entry_len))

	# if page not in cache, return error
	if (page-1)*page_size > entry_len:
		logging.debug('page not in cache')
		return None

	# get page
	extracted = []

	lower_limit = (page - 1) * page_size
	upper_limit = page * page_size + 1
	# check if full page in cache
	# if less, get 
	if upper_limit > entry_len:
		upper_limit = entry_len

	logging.debug(lower_limit)
	logging.debug(upper_limit)

	extracted = cache_entry[lower_limit:upper_limit]

	return extracted
# end get_page_from_cache


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
			try:
				item['hasphoto'] = True
				item['photo_key'] = str(s.photo_ref.key())
			except:
				item['hasphoto'] = False
				item['photo_key'] = None
		else:
			item['hasphoto'] = False
			item['photo_key'] = None

		if not s.timestamp:
			item['timestamp'] = s.timestamp
		else:
			#pdt = s.timestamp - datetime.timedelta(hours=7)
			#item['timestamp'] = str(pdt).split('.')[0] + " PDT"
			item['timestamp'] = s.timestamp.replace(tzinfo=UTC_tzinfo()).astimezone(Pacific_tzinfo()).strftime('%Y-%m-%d %H:%M:%S %Z')

		item['realtime'] = s.timestamp

		item['longitude'] = s.longitude
		item['latitude'] = s.latitude
		item['key'] = str(s.key())
		item['version'] = s.version
		extracted.append(item)
	return extracted
# End extract_surveys function

# adds login status to template values
# returns template.render
def render(parent_request_handler, path, values):
	sess = gmemsess.Session(parent_request_handler)

	# if this is a new session, the user is not logged in
	# if session is not new, check if logged in
	if not sess.is_new():
		# if username set, user is logged in
		if sess.has_key('username'):
			values['username'] = sess['username']

		# check if error message set
		if sess.has_key('error'):
			values['error'] = sess['error']
			# clear error
			del sess['error']
			sess.save()

		# check if success message set
		if sess.has_key('success'):
			values['success'] = sess['success']
			# clear error
			del sess['success']
			sess.save()

		if sess.has_key('admin'):
			values['admin'] = sess['admin']

		if sess.has_key('teacher'):
			values['teacher'] = sess['teacher']

		if sess.has_key('classname'):
			values['classname'] = sess['classname']

		values['show_all'] = False

	return template.render(path, values)	

# end render function

# get data page
# display data in table format
def get_data_page(template_values, cache_name, filter_field = None, filter_value = None, bookmark = None, page = 1):
	forward = True

	# fetch cached values if any
	saved = None
	extracted = None

	query = SurveyData().all()

	if filter_field is not None and filter_value is not None:
		query.filter(filter_field, filter_value)

	# if page set, and page in range, get page for cache
	if page > 0 and page <=5: 
		saved = memcache.get(cache_name)
		logging.debug('get from cache: '+str(cache_name))

		# if not in cache, try fetching from datastore
		if not saved:
			logging.debug('cache miss, populate')
			# get 5 pages of most recent records and cache
			#surveys = SurveyData.all().filter(filter_field, filter_value).order('-timestamp').fetch(PAGE_SIZE*5 + 1)
			surveys = query.order('-timestamp').fetch(PAGE_SIZE*5 + 1)
			saved = extract_surveys (surveys)
			# if values returned, save in cache
			if surveys is not None:
				memcache.set(cache_name, saved)

		# if data, setup display 
		if saved:
			# get page
			extracted = get_page_from_cache(saved, page, PAGE_SIZE)

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
			x = datetime_module.datetime.strptime(datestr, "%Y-%m-%d %H:%M:%S")
			if fractional is None:
				fractional = '0'
				fracpower = 6 - len(fractional)
				fractional = float(fractional) * (10 ** fracpower)
			dt = x.replace(microsecond=int(fractional), tzinfo=tz)


			if forward:
				#surveys = SurveyData.all().filter(filter_field, filter_value).filter('timestamp <', dt).order('-timestamp').fetch(PAGE_SIZE+1)
				surveys = query.filter('timestamp <', dt).order('-timestamp').fetch(PAGE_SIZE+1)
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
				#surveys = SurveyData.all().filter(filter_field, filter_value).filter('timestamp >', dt).order('timestamp').fetch(PAGE_SIZE+1)
				surveys = query.filter('timestamp >', dt).order('timestamp').fetch(PAGE_SIZE+1)
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
			#surveys = SurveyData.all().filter(filter_field, filter_value).order('-timestamp').fetch(PAGE_SIZE+1)
			surveys = query.order('-timestamp').fetch(PAGE_SIZE+1)
			if len(surveys) == PAGE_SIZE + 1:
				template_values['next'] = str(surveys[-2].timestamp)
				template_values['nextpage'] = 2
				surveys = surveys[:PAGE_SIZE]

		extracted = extract_surveys (surveys)

	template_values['surveys'] = extracted 

	return
# end get_data_page
