#! /usr/bin/python
#-*- coding: utf-8 -*-

import traceback, time
from io import StringIO
from config import FILE_PAHT_ERRORLOG


def exception_handle(msg):
	cstr = StringIO()
	traceback.print_exc(None, cstr)	
	log_msg = "DateTime=%s \n %s \n %s \n" % (time.ctime(), msg, cstr.getvalue())
	cstr.close()
	fp = open(FILE_PAHT_ERRORLOG, 'a')
	fp.write(log_msg)
	fp.close()


def byte2str(b, encoding):
	try:
		return b.decode(encoding)
	except UnicodeDecodeError:
		return b.decode('utf-8', errors='replace')

def str2byte(s, encoding):
	try:
		return s.encode(encoding)
	except UnicodeEncodeError:
		return s.encode('utf-8', errors='replace')


def str2utf8(string):
	try:
		if type(string) == str:
			return string.encode('utf-8')
		else:
			return string
	except UnicodeDecodeError:
		return ''


def urlparse_fix(url):
	# fix bug in urljoin:fails to remove an odd number of '../' from the path
	tmp = url.split('/')
	tmp_len = len(tmp)
	if tmp_len > 3:
		for i in xrange(3, tmp_len):
			if tmp[i] != '..':
				break
		url = '/'.join(tmp[0:3] + tmp[i:])
	return url


def get_ftype_from_url(url):
	path = urlparse(url).path
	path_split = path.split('.')
	if len(path_split) < 2:
		return None
	else:
		return path_split[-1].lower()