import webapp2
import re
import jinja2
import os
import facebook
import urllib2
import re
import datetime
import urllib
import cgi
import base64
import Cookie
import email.utils
import hashlib
import hmac
import logging
import os.path
import time
import urllib
import wsgiref.handlers

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
from google.appengine.api import mail
def dt(u): return datetime.datetime.fromtimestamp(u)

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
    	if not hasattr(self, "_current_user"):
    		self._current_user = None
    		user_id = parse_cookie(self.request.cookies.get("fb_user"))
    		if user_id:
    			self._current_user = User.get_by_key_name(user_id)
    	return self._current_user


class LoginHandler(BaseHandler):
	def get(self):
		verification_code = self.request.get("code")
		args = dict(client_id=FACEBOOK_APP_ID,
							redirect_uri=self.request.path_url,
							scope="user_status,email"
							)
		if self.request.get("code"):
			args["client_secret"] = FACEBOOK_APP_SECRET
			args["code"] = self.request.get("code")
			args["scope"]="user_status,email"
			response = cgi.parse_qs(urllib.urlopen(
				"https://graph.facebook.com/oauth/access_token?" +
				urllib.urlencode(args)).read())
			access_token = response["access_token"][-1]
			#Download the user profile and cache a local instance of the
			#basic profile info
			profile = json.load(urllib.urlopen(
				"https://graph.facebook.com/me?" +\
				urllib.urlencode(dict(access_token=access_token))))
			user = User(key_name=str(profile["id"]), id=str(profile["id"]),
						name=profile["name"], access_token=access_token,
						profile_url=profile["link"], email=profile["email"])
			user.put()
			set_cookie(self.response, "fb_user", str(profile["id"]),
					expires=time.time() + 30 * 86400)
			self.redirect("/")
		else:
			self.redirect(
				"https://graph.facebook.com/oauth/authorize?" +
				urllib.urlencode(args))

    
class Contact(BaseHandler):
		
	def get(self):
		template = JINJA_ENVIRONMENT.get_template('contact.html')
		self.response.write(template.render());
		
class About(BaseHandler):
	def get(self):
		template = JINJA_ENVIRONMENT.get_template('about.html')
		self.response.write(template.render());

class Home(BaseHandler):
		
	def get(self):
		if parse_cookie(self.request.cookies.get("fb_user")) is None:
			template = JINJA_ENVIRONMENT.get_template('home2.html')
			self.response.write(template.render(dict(facebook_app_id=FACEBOOK_APP_ID,current_user=self.current_user)))
		else:
			template = JINJA_ENVIRONMENT.get_template('home.html')
			graph = facebook.GraphAPI(self.current_user.access_token)
			status=graph.fql('SELECT message,time,status_id From status WHERE uid=me() ');
			mlist=status['data']
	
			for m in mlist:
				m['time']=dt(m['time'])
			self.response.write(template.render(dict(
					facebook_app_id=FACEBOOK_APP_ID,
					current_user=self.current_user,
					messages=mlist
				)))
	def post(self):
		template = JINJA_ENVIRONMENT.get_template('home.html')
		keyword= self.request.get("keyword")
		badwords= self.request.get("badwords");
		badcontent=self.request.get("badcontent");
		graph = facebook.GraphAPI(self.current_user.access_token)
		status=graph.fql('SELECT message,time,status_id From status WHERE uid=me() ');
		mlist=status['data']
		if keyword:
			for m in mlist:
				m['time']=dt(m['time'])
				if keywordSearch(m['message'], keyword) is None:
					del m['message']
		if badwords and badcontent:
			for m in mlist:
				if 'message' in m:
					if badWordSearch(m['message']) is None:
						if badContentSearch(m['message']) is None:
							del m['message']
						else:
							m['flag']=2
					else:
						m['flag']=1

		elif badwords:
			for m in mlist:
				if 'message' in m:
					if badWordSearch(m['message']) is None:
						del m['message']
					else:
						m['flag']=1
		
		elif badcontent:
			for m in mlist:
				if 'message' in m:
					if badContentSearch(m['message']) is None:
						del m['message']
					else:
						m['flag']=2;

		self.response.write(template.render(dict(
			facebook_app_id=FACEBOOK_APP_ID,
			current_user=self.current_user,
			messages=mlist
			)))
class LogoutHandler(BaseHandler):
	def get(self):
		set_cookie(self.response, "fb_user", "", expires=time.time() - 86400)
		self.redirect("/")
	
class User(db.Model):
    id = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    name = db.StringProperty(required=True)
    profile_url = db.StringProperty(required=True)
    email = db.StringProperty()
    access_token = db.StringProperty(required=True)
    
def keywordSearch(message, keyword):
	search=re.compile("%s" % keyword, re.I);
	return search.search(message)

def badWordSearch(message):
	for w in badWordList:
		search=re.compile("%s" % w, re.I);
		if (search.search(message) is not None):
			return 1
	for w in badWordListAlone:
		search= re.compile("(^|\s)%s[\s|\b]", re.I);
		if (search.search(message) is not None):
			return 1
	return None
	
def badContentSearch(message):
	for w in badContentList:
		search=re.compile("%s" % w, re.I);
		if search.search(message) is not None:
			return 1
	for w in badContentListAlone:
		search= re.compile("(^|\s)%s[\s|\b]", re.I);
		if (search.search(message) is not None):
			return 1
	return None
    
def set_cookie(response, name, value, domain=None, path="/", expires=None):
	"""Generates and signs a cookie for the give name/value"""
	timestamp = str(int(time.time()))
	value = base64.b64encode(value)
	signature = cookie_signature(value, timestamp)
	cookie = Cookie.BaseCookie()
	cookie[name] = "|".join([value, timestamp, signature])
	cookie[name]["path"] = path
	if domain:
		cookie[name]["domain"] = domain
	if expires:
		cookie[name]["expires"] = email.utils.formatdate(
			expires, localtime=False, usegmt=True)
	response.headers.add_header("Set-Cookie", cookie.output()[12:])
	
def parse_cookie(value):
	"""Parses and verifies a cookie value from set_cookie"""
	if not value:
		return None
	parts = value.split("|")
	if len(parts) != 3:
		return None
	if cookie_signature(parts[0], parts[1]) != parts[2]:
		logging.warning("Invalid cookie signature %r", value)
		return None
	timestamp = int(parts[1])
	if timestamp < time.time() - 30 * 86400:
		logging.warning("Expired cookie %r", value)
		return None
	try:
		return base64.b64decode(parts[0]).strip()
	except:
		return None
		
def cookie_signature(*parts):
	"""Generates a cookie signature.
	
	We use the Facebook app secret since it is different for every app (so
	people using this example don't accidentally all use the same secret).
	"""
	hash = hmac.new(FACEBOOK_APP_SECRET, digestmod=hashlib.sha1)
	for part in parts:
		hash.update(part)
	return hash.hexdigest()
    
application = webapp2.WSGIApplication([
	('/', Home),
	('/contact', Contact),
	('/about', About),
    ('/login', LoginHandler),
    ('/logout', LogoutHandler)
    ], debug=True, config=config)
    
badWordList=set(['ass', 'axwound', 'bampot', 'bastard','bitch',
'blow job', 'blowjob', 'bollocks', 'bollox', 'boner', 'fuck', 'shit', 'butt', 'camel toe',
'chesticle','choad', 'chode', 'clit', 'cock', 'cooch', 'cooter', 'cunnie', 'cunnilingus', 
'damn', 'dick', 'dildo', 'douche', 'dookie', 'fellatio', 'gooch', 'handjob', 'hand job', 'hard on', 'hell',
 'hoe', 'humping', 'jagoff', 'jerk off', 'jizz', 'kooch', 'kootch',  'minge', 'munging',
'nut sack', 'nutsack', 'panooch', 'pecker', 'penis', 'pussy', 'pussies',
 'queef',  'rimjob', 'schlong', 'scrote', 'shiz', 'skank', 'skeet', 'slut', 
'snatch', 'splooge', 'tard', 'testicle', 'vajay', 'va-j-j', 'vjay', 'wank',
'whore', 'bang']);

badWordListAlone=set(['anus', 'arse', 'cum' , 'cunt', 'gooch', 'ho', 'muff', 'poon', 'punta', 'kunt', 'piss', 'puto',
'renob', 'smeg', 'tit', 'twat', 'vag', ]);

badContentList=set(['beaner', 'chinc', 'chink',  'cracker',  'deggo',  'carpetmuncher',
'dyke', 'fag', 'flamer', 'gay',  'gook', 'gringo', 'guido', 'heeb', 'homo', 'honkey',  'jigaboo',
'junglebunny', 'jungle bunny',  'kyke', 'lesbo', 'lezzie',  'negro', 'nigaboo', 'nigga',
'nigger', 'niglet',  'polesmoker', 'pollock', 'porchmonkey', 'porch monkey', 'queer', 
'ruski',  'wetback','alchohol', 'amfetamine', 'blackout', 'coke', 'crack',
'ecstasy', 'hallucinogens', 'joint', 'marijuana',  'mary jane', 'lsd', 'dos equis', 'bud lite', 
'Natty Lite', "Natural Lite", "natty", "coors", 'whiskey', 'vodka', 'shiner', 'keystone', 'miller lite'
'booze', 'beer', 'wine', 'meth', 'speed', 'crank', 'uppers', 'pcp', 'heroin', 'cocaine', 'mescaline', 
'drug', 'blow', 'blunt', 'cigarette',  'liquor',  'reefer', 'weed', 'smoke', 'tobacco']);

badContentListAlone=set(['coon', 'dago', 'dike', 'jap', 'kike', 'mick', 'paki', 'spic', "spick"
'wop', 'keg', 'pot', 'acid', 'bong', 'hash', 'rum', 'gin']);