import webapp2
import re
import jinja2
import os

from time import sleep
from google.appengine.ext import db

FACEBOOK_APP_ID = "629500937079404"

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])
    
class HomeNotLogin(webapp2.RequestHandler):
		
	def get(self):
		current_user=None
		template = JINJA_ENVIRONMENT.get_template('home2.html')
		self.response.write(template.render({"current_user": current_user}))
		
		
	def post(self):
		username = self.request.get("username")
		password= self.request.get("password")
		self.redirect('/home?user=%s' % username)
		
		
class HomeLogin(webapp2.RequestHandler):
		
	def get(self):
		user=self.request.get("user")
		template = JINJA_ENVIRONMENT.get_template('home.html')
		self.response.write(template.render({"user":user}))

	
application = webapp2.WSGIApplication([
    ('/', HomeNotLogin),
    ('/home', HomeLogin),
    ], debug=True)