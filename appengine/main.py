import cgi
import os
from django.utils import simplejson as json

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.db import stats
from google.appengine.ext.webapp import template

import cStringIO
import csv

def extract_surveys(surveys):
	extracted = []
	for s in surveys:
		item = {}
		item['stressval'] = s.stressval
		item['category'] = s.category
		item['longitude'] = s.longitude
		item['latitude'] = s.latitude
		item['key'] = str(s.key())
		extracted.append(item)
	return extracted

class Survey(db.Model):
	user = db.UserProperty()
	timestamp =	db.DateTimeProperty(auto_now_add=True)
	longitude =	db.StringProperty()
	latitude =	db.StringProperty()
	stressval =	db.FloatProperty()
	comments =	db.StringProperty()
	category =	db.StringProperty()
	version =	db.StringProperty()
	photo =		db.BlobProperty()

class HomePage(webapp.RequestHandler):
	def get(self):
		path = os.path.join (os.path.dirname(__file__), 'views/home.html')
		self.response.out.write (template.render(path, {}))

class MapPage(webapp.RequestHandler):
	def get(self):
		surveys = Survey.all().fetch(10)
		extracted = extract_surveys (surveys)
		template_values = { 'surveys' : extracted }
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
		s.stressval = self.request.get('stressval')
		s.comments = self.requrest.get('comments')
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
		surveys = db.GqlQuery("SELECT * FROM Survey ORDER BY timestamp DESC LIMIT 10")
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
		self.response.headers['Content-type'] = 'text/plain'
		req_key = self.request.get('key')
		if req_key != '':
			try :
				db_key = db.Key(req_key)
				surveys = db.GqlQuery("SELECT * FROM Survey WHERE __key__ = :1", db_key)
				for s in surveys:
					e = {}
					e['photo'] = "http://we-tap.appspot.com/get_image_thumb?key=" + req_key;
					e['latitude'] = s.latitude
					e['longitude'] = s.longitude
					e['stressval'] = s.stressval
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
		self.response.headers['Content-type'] = 'text/html'
		req_key = self.request.get('key')
		self.response.out.write("<html><body><img src=\"http://we-tap.appspot.com/get_an_image?key=")
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
		surveys = Survey.all().fetch(50)
		template_values = { 'surveys' : surveys }
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

		for s in surveys:
			new_row = [
					s.timestamp,
					s.latitude,
					s.longitude,
					s.stressval,
					s.category,
					s.comments,
					"http://stresschill.appspot.com/get_an_image?key="+str(s.key())
					]
			writer.writerow(new_row)

		self.response.headers['Content-type'] = 'text/csv'
		self.response.out.write(output.getvalue())


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
									  ('/data_download_all.csv', DownloadAllData)],
									 debug=True)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
