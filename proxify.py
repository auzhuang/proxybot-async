#! /usr/bin/python
#-*- coding: utf-8 -*-

import re
from config import INSERT_AD_CODE
from urllib.parse import quote, unquote

attrfind = re.compile(												 
	r"""\s*([a-zA-Z_][-:.a-zA-Z_0-9]*)(\s*=\s*(\'[^\']*\'|"[^"]*"|[][\-a-zA-Z0-9./,:;+*%?!&$\(\)_#=~\'"@]*))?""")

_re_tag = re.compile(r'<\s*([a-zA-Z\?-]+)([^>]*)>')
_re_inlinecss_url = re.compile('url\s*\(([^\(\)]+)\)', re.IGNORECASE)
_re_cssfile_url = re.compile(r"""@import\s*(?:\"([^\">]*)\"?|'([^'>]*)'?)([^;]*)""", re.IGNORECASE)
_re_mine_div = re.compile(r'<\s*body(.*?)>', re.IGNORECASE)
_re_end_body = re.compile(r'</\s*body>', re.IGNORECASE)
_re_end_head = re.compile(r'</\s*head>', re.IGNORECASE)
_re_begin_head  = re.compile(r'<\s*head(.*?)>', re.IGNORECASE)

_url_tag_attr = {
	'a'		 :('href',),
	'img'	   :('src', 'longdesc', 'thumb'),
	'image'	 :('src', 'longdesc'),
	'body'	  :('background',),
	'base'	  :('href',),
	'frame'	 :('src', 'longdesc'),
	'iframe'	:('src', 'longdesc'),
	'head'	  :('profile',),
	'layer'	 :('src',),
	'input'	 :('src', 'usemap', 'formaction'),
	'form'	  :('action',),
	'area'	  :('href',),
	'link'	  :('href', 'src', 'urn'),
	#'meta'	  :(),
	'param'	 :('value',),
	'applet'	:('codebase', 'code', 'object', 'archive'),
	'object'	:('usermap', 'codebase', 'classid', 'archive','data'),
	'script'	:('src',),
	'select'	:('src',),
	'hr'		:('src',),
	'table'	 :('background',),
	'tr'		:('background',),
	'th'		:('background',),
	'td'		:('background',),
	'bgsound'   :('src',),
	'blockquote':('cite',),
	'del'	   :('cite',),
	'embed'	 :('src',),
	'fig'	   :('src', 'imagemap'),
	'ilayer'	:('src',),
	'ins'	   :('cite',),
	'note'	  :('src',),
	'overlay'   :('src', 'imagemap',),
	'q'		 :('cite',),
	'ul'		:('src',),

	# html 5
	'button'		:('formaction',),
	'command'		:('icon',),
	'source'		:('src',),
	'track'		:('src',),
	'video'		:('poster', 'src'),
	'audio'		:('src',)
}


def parse_attrstring(attrstring):

	attrs = {}
	attr_splits = {}
	alls = attrfind.findall(attrstring)
	for i in alls:
		split_str = ''
		attrname, rest, attrvalue = i[0], i[1], i[2]
		if not rest:
			attrvalue = None
		else:
			if (attrvalue[:1] == "'" == attrvalue[-1:] or
				attrvalue[:1] == '"' == attrvalue[-1:]):
				# strip quotes
				split_str = attrvalue[:1]
				attrvalue = attrvalue[1:-1]
		attrs[attrname.lower()] = attrvalue
		attr_splits[attrname.lower()] = split_str

	return attrs, attr_splits

def unparse_attrstring(attr, attr_splits):
	attrstring = []
	for k, v in attr.items():
		if v == None:
			attrstring.append(k)
		else:
			split_str = attr_splits[k]
			attrstring.append('%s=%s%s%s' % (k, split_str, v, split_str))
	return ' '.join(attrstring)


#return False for no modify
def _proxify_attr(tag, attrdict, proxify_url):
	tag = tag.lower()
	modified = False

	#inline css
	v = attrdict.get('style', None)
	if v != None:
		newv =  _proxify_inline_css(v, proxify_url)
		if newv != v:
			modified = True
			attrdict['style'] = newv

	attrs_tp = _url_tag_attr.get(tag.lower(), ())
	#url
	if len(attrs_tp) > 0:
		for attr in attrs_tp:
			v = attrdict.get(attr, None)
			if v != None :
				modified = True
				attrdict[attr] = proxify_url(v)
		return modified

	#meta refresh
	if tag == 'meta' and 'content' in attrdict and 'http-equiv' in attrdict and attrdict['content'] != None:
		rf_url_find = re.compile(r'(\s*[0-9]*\s*;\s*url=*)(.*)', re.IGNORECASE)
		rf_info = rf_url_find.findall(attrdict['content'])
		if len(rf_info) > 0:
			modified = True
			
			rf_info = rf_info[0]
			if (rf_info[1][:1] == "'" == rf_info[1][-1:] or rf_info[1][:1] == '"' == rf_info[1][-1:]):
				meta_url = rf_info[1][1:-1]
			else:
				meta_url = rf_info[1]
			attrdict['content'] = '%s%s' % (rf_info[0], proxify_url(meta_url))

	#tag object todo
	#tag applet todo
	#tag param todo
	#<script>setTimeout("window.location.href ='http://tt.sglost.com/forum/index.php';", 3000);</script>
	return modified


def _proxify_inline_css(css,proxify_url):
	lastpos = 0
	newcss = []

	for m in re.finditer(_re_inlinecss_url, css):
		newcss.append(css[lastpos:m.start()])
		url = m.groups()[0]
		if url.find('"')>=0:
			delma = '"'
		elif url.find("'")>=0:
			delma = "'"
		else:
			delma = ''
		url = url.strip('\'"')
		url = proxify_url(url)
		newcss.append('url(%s%s%s)'%(delma,url,delma))
		lastpos = m.end()
	newcss.append(css[lastpos:len(css)])
	return ''.join(newcss)
	

def proxify_css(css, proxify_url):
	css = _proxify_inline_css(css, proxify_url)
	#return css
	lastpos = 0
	newcss = []
	
	for m in re.finditer(_re_cssfile_url, css):
		newcss.append(css[lastpos:m.start()])
		if m.group(2) != None:
			delma = "'"
			url = m.group(2)
		else:
			delma = '"'
			url = m.group(1)

		url = proxify_url(url)
		newcss.append('@import %s%s%s'%(delma, url, delma))
		lastpos = m.end()
	newcss.append(css[lastpos:len(css)])
	return ''.join(newcss)


#return string for new tag
def proxify_tag(tagstring, tag, attrstring, proxify_url):
	attrdict, attr_splits = parse_attrstring(attrstring)
	#if not mofidy,then return the old tagstring
	if _proxify_attr(tag, attrdict, proxify_url):
		return '<%s %s>'%(tag, unparse_attrstring(attrdict, attr_splits))
	return tagstring




def proxify_html(html,proxify_url):
	newhtml = []
	#matchs = _re_tag.findall(html)
	lastpos = 0
	for m in re.finditer(_re_tag, html):
		newhtml.append(html[lastpos : m.start()])
		newhtml.append(proxify_tag(m.group(), m.groups()[0], m.groups()[1], proxify_url))
		lastpos = m.end()
	newhtml.append(html[lastpos:])
	#return ''.join(newhtml)
	newhtml = _re_end_body.sub(r'%s</body>' % INSERT_AD_CODE['body_end'], ''.join(newhtml), count=1)
	#newhtml = _re_end_head.sub(r'%s</head>' % proxyad.head_begin_ad, newhtml, count=1)
	newhtml = _re_begin_head.sub(r'<head\1>%s' % INSERT_AD_CODE['head_begin'], newhtml, count=1)
	return _re_mine_div.sub(r'<body\1>%s' % INSERT_AD_CODE['body_begin'], newhtml, count=1)

