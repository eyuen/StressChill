import logging
import cgi
import datetime

from google.appengine.api import memcache
from google.appengine.ext.webapp import template
import gmemsess

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
			item['hasphoto'] = True
			try:
				item['photo_key'] = str(s.photo_ref.key())
			except:
				item['photo_key'] = None
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


	return template.render(path, values)	

# end render function