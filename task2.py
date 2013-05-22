#-*- coding: utf-8 -*-
import os
import webapp2
import jinja2
import re
import string
import logging
import urllib2

from google.appengine.api import taskqueue
from google.appengine.ext import ndb

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja2_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape = True)


class Handler(webapp2.RequestHandler):

	def write(self,*a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		t = jinja2_env.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))
		
class Task(ndb.Model):

	word = ndb.StringProperty(required=True)
	count = ndb.IntegerProperty()

class Counter():
	
	def projection(self, word):
		ids = Task.query().fetch(projection=['word'])
		return ids
	
	def process_fetch(self,word):
		ids = self.projection(word)
		for i in ids:
			if i.word == word:
				return False

	def decide(self,word):
		if not self.process_fetch(word):
			task = Task(id=word, word=word)
			task.put()
		taskqueue.add(url='/result/{0}'.format(word)) 
		self.redirect('/result/{0}'.format(word))

	def count_word(self,search):
		url = ['http://onet.pl/','http://interia.pl/','http://wp.pl/','http://redtube.com/','http://www.gazeta.pl/0,0.html',
		'http://www.pudelek.pl/','http://www.kozaczek.pl/','http://www.plotek.pl/plotek/0,0.html','http://www.thetimes.co.uk/tto/news/','http://edition.cnn.com/']
		shots = 0
		for u in url:
			result = urllib2.urlopen(u)
			text = self.prepare_text(result)
			shots += self.count(text,search.word)
		return shots
	
	def count(self,text,word):
		shots = 0
		for line in text:
			shots += len(re.findall('(?<![a-zA-Z0-9]){0}'.format(word),line))
		return shots

	def prepare_text(self,result):
		pure_text = []
		for line in result:
			check=True
			while check:
				look = re.search('<.*?>',line)
				if look:
					line = line[:look.span()[0]]+line[look.span()[1]:]
				else:
					check=False
					pure_text.append(line)
		return pure_text

class MainPage(Handler,Counter):

	def get(self):
		self.render('main.html')
	
	def post(self):
		word = self.request.get('word')
		self.decide(word)


class Result(Handler,Counter):

	def get(self,id):
		search = Task.get_by_id(id)
		if search.count == None:
			self.response.out.write('ZADANIE W TOKU, PROSZĘ ODSWIEZYĆ')
		else:
			self.response.out.write('SLOWO WYSTEPUJE {0} RAZY.'.format(search.count))

	def post(self,id):
		search = Task.get_by_id(id)
		SUM = self.count_word(search)
		search.count = SUM
		search.put()


class List(Handler,Counter):
	
	def get(self):
		return


app = webapp2.WSGIApplication([('/search',MainPage),('/result/([a-zA-Z0-9_]+)',Result),('/list',List)], debug=True)
