import webapp2
import re
import jinja2
import os
import facebook
import urllib2
import re

# Find a JSON parser
try:
    import simplejson as json
except ImportError:
    try:
        from django.utils import simplejson as json
    except ImportError:
        import json
_parse_json = json.dumps

from time import sleep
from google.appengine.ext import db
from webapp2_extras import sessions

FACEBOOK_APP_ID = "629500937079404"
FACEBOOK_APP_SECRET= "8ca2eedf6a2594ea1fb42694509aacd8"

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])
    
config = {}
config['webapp2_extras.sessions'] = dict(secret_key='')    
    
class BaseHandler(webapp2.RequestHandler):
    """Provides access to the active Facebook user in self.current_user

    The property is lazy-loaded on first access, using the cookie saved
    by the Facebook JavaScript SDK to determine the user ID of the active
    user. See http://developers.facebook.com/docs/authentication/ for
    more information.
    """
    @property
    def current_user(self):
        if self.session.get("user"):
            # User is logged in
            return self.session.get("user")
        else:
            # Either used just logged in or just saw the first page
            # We'll see here
            cookie = facebook.get_user_from_cookie(self.request.cookies,
                                                   FACEBOOK_APP_ID,
                                                   FACEBOOK_APP_SECRET)
            if cookie:
                # Okay so user logged in.
                # Now, check to see if existing user
                user = User.get_by_key_name(cookie["uid"])
                if not user:
                    # Not an existing user so get user info
                    graph = facebook.GraphAPI(cookie["access_token"])
                    profile = graph.get_object("me")
                    user = User(
                        key_name=str(profile["id"]),
                        id=str(profile["id"]),
                        name=profile["name"],
                        profile_url=profile["link"],
                        access_token=cookie["access_token"]
                    )
                    user.put()
                elif user.access_token != cookie["access_token"]:
                    user.access_token = cookie["access_token"]
                    user.put()
                # User is now logged in
                self.session["user"] = dict(
                    name=user.name,
                    profile_url=user.profile_url,
                    id=user.id,
                    access_token=user.access_token
                )
                return self.session.get("user")
        return None

    def dispatch(self):
        """
        This snippet of code is taken from the webapp2 framework documentation.
        See more at
        http://webapp-improved.appspot.com/api/webapp2_extras/sessions.html

        """
        self.session_store = sessions.get_store(request=self.request)
        try:
            webapp2.RequestHandler.dispatch(self)
        finally:
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        """
        This snippet of code is taken from the webapp2 framework documentation.
        See more at
        http://webapp-improved.appspot.com/api/webapp2_extras/sessions.html

        """
        return self.session_store.get_session()    		
    
    
class HomeNotLoggedIn(BaseHandler):
		
	def get(self):
		template = JINJA_ENVIRONMENT.get_template('home2.html')
		if self.current_user is None:
			self.response.write(template.render(dict(facebook_app_id=FACEBOOK_APP_ID,current_user=self.current_user)))
		elif self.current_user is not None:
			self.redirect('/home')
		

class HomeLoggedIn(BaseHandler):
		
	def get(self):
		template = JINJA_ENVIRONMENT.get_template('home.html')
		graph = facebook.GraphAPI(self.current_user["access_token"])
		status=graph.fql('SELECT message From status WHERE uid=me() ');
		mlist=status['data']

		self.response.write(template.render(dict(
        	    facebook_app_id=FACEBOOK_APP_ID,
        	    current_user=self.current_user,
        	    messages=mlist
        	)))

	
class User(db.Model):
    id = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    name = db.StringProperty(required=True)
    profile_url = db.StringProperty(required=True)
    access_token = db.StringProperty(required=True)
    
    

    
application = webapp2.WSGIApplication([
    ('/', HomeNotLoggedIn),
    ('/home', HomeLoggedIn),
    ], debug=True, config=config)