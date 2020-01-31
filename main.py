#! /usr/bin/python3
#-*- coding: utf-8 -*-

from sanic.views import HTTPMethodView
from sanic import response
from sanic.log import logger
from urllib.parse import quote, urljoin, urlparse, urlencode, parse_qsl
import aiohttp, jinja2, codecs, os, hashlib
from asyncio import TimeoutError
import proxify, util, config



class Base(HTTPMethodView):
	def __init__(self):
		super(Base, self).__init__()

		self.jinja_env = jinja2.Environment(
			loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'res/templates', config.TEMPLATES)),
			extensions=['jinja2.ext.autoescape'],
			autoescape=True)

	def render(self, filename, **template_values):
		template = self.jinja_env.get_template('%s.html' % filename)
		return response.html(template.render(template_values))


class HTML_Index(Base):
	async def get(self, request):
		return self.render('index')


class HTML_Sites(Base):
	def get(self, request):
		return self.render('sites')


class SaveGAEOlderLink(Base):
	def get(self, request, path):
		try:
			url = self._decodeurl_jiou(path)
		except:
			url = ''
		if url:
			return response.redirect('/ee/?%s' % urlencode({'url': url}))
		else:
			return response.redirect('/')
		

	def _decodeurl_jiou(self, url):
		url = codecs.decode(bytes(url,'utf-8'), 'base64').decode()
		r_url = []
		even = url[: len(url) / 2]
		odd = url[len(url) / 2 :]
		for i in xrange(len(odd)):
			r_url.append(odd[i])
			if i < len(even):
				r_url.append(even[i])
		
		r_url = ''.join(r_url)
		if not r_url.startswith('http://') and not r_url.startswith('https://'):
			r_url = 'http://%s' % r_url
		
		return r_url



class Block(Base):
	def get(self, request):
		return self.render('block')

	def post(self, request):
		domain = request.form.get('domain', '')
		if not domain.startswith('http://') and not domain.startswith('https://'):
			domain = 'http://%s' % domain
		try:
			up = urlparse(domain)
			if up.netloc: 
				fp = open(config.BLOCK_FILE, 'a')
				fp.write('%s\n' % up.netloc[:50])
				fp.close()
		except ValueError:
			pass

		return self.render('info', msg='Block %s finish!' % domain)



class WebProxy(Base):
	def __init__(self):
		super(WebProxy, self).__init__()
		self.url_prefix = ''     #子类需定义
		self.url_query_key = ''  #子类需定义
		self.url_encoder = None  #子类需定义
		self.url_decoder = None  #子类需定义
		self.request = None


	####通过当前访问路径和将要访问的路径构造输出的路径
	def build_url(self, visit_url, next_url):
		return ''

	#### 通过fullpath解释请求的url
	def parse_url(self, fullpath):
		return ''


	def get_visit_url(self):
		url = self.parse_url('%s?%s' % (self.request.path,self.request.query_string))
		if not url:
			referer_url = self.parse_url(self.request.headers.get('referer', ''))
			if referer_url:
				return urljoin(referer_url, self.request.path.replace(self.url_prefix, ''))
		return url


	def error_msg(self, url, msg):
		return self.render('error', url=url, msg=msg)


	def create_encode_url(self):
		url = self.request.form.get('url', '')
		return self.build_url('', url)


	async def get(self, request, path):
		self.request = request
		try:
			#拦截输出点：'/ee/' 这是用于encode url，然后重定向，去掉页面的encode js
			if self.request.path.startswith('/ee/'):
				return response.redirect(self.create_encode_url())
			return await self.real_process()
		except:
			util.exception_handle('%s?%s' % (self.request.path,self.request.query_string))
			return self.error_msg('', 'unknow error')


	def if_should_cached(self, url):
		if config.CACHED_CONTENT:
			method = self.request.method
			if method == 'GET' or (method == 'POST' and config.CACHED_LEVEL == 2):
				ftype = util.get_ftype_from_url(url)
				if len(config.CACHED_TYPE) == 0:
					return True
				elif not ftype:
					return False
				elif ftype in config.CACHED_TYPE:
					return True
		return False


	def get_cached_file_path(self, url):
		md5_url = hashlib.new("md5", url).hexdigest()
		ftype = util.get_ftype_from_url(url)
		cached_file_dir = os.path.join(config.CACHED_DIR, ftype, md5_url[0:2])
		if not os.path.isdir(cached_file_dir):
			os.makedirs(cached_file_dir)
		return os.path.join(cached_file_dir, md5_url)
		

	async def save_cache(self, url, content):
		self.mc = memcache.Client([config.CACHED_MEMCACHE_PATH],debug=0)
		md5_url = hashlib.new("md5", url).hexdigest()
		if not self.mc.get(md5_url):
			self.mc.set(md5_url, '1', time=config.CACHED_TIME)
		
		else:
			# 访问第二次才创建文件
			# 若首次即创建，命中率会低于20%（在memcached版本测试过），过低的命中率意味着在空耗io，创建很多无谓的文件
			# 这里我们假定若文件会被第二次访问，那么它被第三次访问的几率将更大
			file_path = self.get_cached_file_path(url)
			if not os.path.isfile(file_path):
				fileobj =  open(file_path, 'wb')
				cPickle.dump(content, fileobj)
				fileobj.close()
		return True



	def check_block_sites(self, url):
		if not config.BLOCK_CHECK:
			return True

		block_sites = set()
		with open(config.BLOCK_FILE) as file:
			for line in file:
				block_sites.add(line.strip())

		up = urlparse(url)
		if up.netloc != '' and up.netloc in block_sites:
			return False

		return True

	def get_resp_from_cache(self, url):
		self.mc = memcache.Client([config.CACHED_MEMCACHE_PATH],debug=0)
		md5_url = hashlib.new("md5", url).hexdigest()
		result = self.mc.get(md5_url)
		if result:
			file_path = self.get_cached_file_path(url)
			if os.path.isfile(file_path):
				f = open(file_path, 'rb')
				resp = cPickle.load(f)
				f.close()

				#fp = open(config.DIR_LOG + '/cachehit.log', 'a')
				#fp.write('%s %s\n' % (time.ctime(), url))
				#fp.close()
				return resp
		return None


	async def real_process(self):

		#拦截输出点：'/dd/' decode url
		if self.request.path.startswith('/dd/'):
			self.url_prefix = '/dd/'
			return self.error_msg(self.get_visit_url(), 'decode!')

		url = self.get_visit_url()

		if not url:
			return response.redirect('/')

		if not self.check_block_sites(url):
			return self.error_msg(url, 'The url:%s you visited has been blocked！' % url)

		return await self.visit(url)


	async def visit(self, url):
		resp = None
		msg = ''

		if self.if_should_cached(url):
			resp, msg = self.get_resp_from_cache(url)

		if not resp: 
			resp, msg = await self.get_resp_from_network(url)

		if not resp:
			return self.error_msg(url, msg)


		### 剔除不能回传客户端的header ###

		headers = []
		for key, value in resp['headers'].items():
			if key.lower() not in ['connection', 'keep-alive', 'proxy-authenticate', 'te', \
						'proxy-authorization', 'trailers', 'transfer-encoding', 'upgrade', \
						'last-modified', 'pragma', 'content-length', 'location', 'content-encoding', 'status']:
				headers.append((key, value))

		#######
		if resp['status'] == 200:
			content_type = resp['headers'].get('content-type', '')

			if 'text/html' in content_type or content_type == '':
				resp['content'] = proxify.proxify_html(util.byte2str(resp['content'], resp['encoding']), lambda u:self.build_url(url, u))
				resp['content'] = util.str2byte(resp['content'], resp['encoding'])
			elif 'text/css' in content_type:
				resp['content'] = proxify.proxify_css(util.byte2str(resp['content'], resp['encoding']), lambda u:self.build_url(url, u))
				resp['content'] = util.str2byte(resp['content'], resp['encoding'])
			
			return response.raw(resp['content'], headers=headers)

		elif resp['status'] in [300, 301, 302, 303, 304, 305, 306, 307]:
			location = resp['headers'].get('location', '')
			if location != '':
				if url.lower() == location.lower():
					return self.error_msg(url, '404 Not Found!')
				else:
					return response.redirect(self.build_url(url, location), status=resp['status'])
			return response.redirect(self.build_url(url, location), status=resp['status'])

		elif resp['status'] in [500, 510, 509, 423, 508, 451, 543, 422, 420]:
			return self.error_msg(url, 'The server is busy. Please try again later.')
		elif resp['status'] in [404, 400]:
			return self.error_msg(url, 'The requested URL was not found on this server.')
		elif resp['status'] in [403,]:
			return self.error_msg(url, 'HTTP Error 403 - Forbidden.')
		else:
			return self.error_msg(url, 'Unknown http response status!')
		
		return self.error_msg(url, 'unknown error!!!')


	async def get_resp_from_network(self, url):
		### 组装请求的header ###
		headers = {}
		for key, value in self.request.headers.items():
			if key.lower() not in ['host', 'referer', 'content-length', 'if-none-match']:
				headers[key] = value

		headers['Referer'] = self.parse_url(self.request.headers.get('referer', ''))
		headers['User-Agent'] = config.USER_AGENT

		try:
			timeout = aiohttp.ClientTimeout(total=10)
			async with aiohttp.ClientSession(timeout=timeout) as session:
				if self.request.method == 'GET':
					async with session.get(url, headers=headers, allow_redirects=False, timeout=timeout) as r:
						resp = {"status":r.status, "headers":r.headers, "content":await r.read(), 'encoding':r.get_encoding()}
				else:
					async with session.post(url, data=self.request.body, headers=headers, allow_redirects=False, timeout=timeout) as r:
						resp = {"status":r.status, "headers":r.headers, "content":await r.read(), 'encoding':r.get_encoding()}					
				await session.close()
				if self.if_should_cached(url):
					await self.save_cache(url, resp)
				return resp, ''
		except aiohttp.ClientConnectorError as e:
			return None, str(e)
		except TimeoutError as e:
			return None, str(e)
		except aiohttp.InvalidURL as e:
			return None, str(e)
		except:
			return None, 'unknown response error!'

	post = get


class ProxyflyWebProxy(WebProxy):
	def __init__(self):
		super(ProxyflyWebProxy, self).__init__()
		self.url_prefix = '/o/'
		self.url_querykey = ''
		self.url_encoder = self._encodeurl_ord
		self.url_decoder = self._decodeurl_ord

	def _encodeurl_ord(self, url):
		url = url[::-1]
		result = ''
		for c in url:
			try:
				result += hex(ord(c))[2:]
			except:
				break
		return result


	def _decodeurl_ord(self, url):
		result = ''
		for i in range(0, len(url), 2):
			try:
				result += chr(int(url[i:i+2],16))
			except:
				break
		return result[::-1]

	##重载
	def build_url(self, visit_url, next_url):
		if visit_url.startswith('//'):
			visit_url = 'http:%s' % visit_url
		new_url = urljoin(visit_url, next_url)
		try:
			return '%s%s' % (self.url_prefix, self.url_encoder(new_url))
		except:
			return '/'

	##重载
	def parse_url(self, fullpath):
		try:
			parseinfo = urlparse(fullpath)
		except:
			return ''
		# /o/342094830948348/a/b?a=1
		if parseinfo[2].startswith(self.url_prefix):

			tmp = parseinfo[2].split('/')
			if len(tmp) < 3:
				return ''
			decode_url = self.url_decoder(tmp[2])
			url = urljoin(decode_url, '/'.join(tmp[3:]))
			if parseinfo[4] != '':
				url = '%s?%s' % (url, parseinfo[4])

			if not url.startswith('http://') and not url.startswith('https://'):
				url = 'http://%s' % url
			return url
		return ''



class ProxypyWebProxy(WebProxy):
	def __init__(self):
		super(ProxypyWebProxy, self).__init__()
		self.url_prefix = '/p'
		self.url_querykey = 'q'
		self.url_encoder = self._encodeurl_base64
		self.url_decoder = self._decodeurl_base64

	def _encodeurl_base64(self, url):
		return codecs.encode(bytes(url[::-1], 'utf-8'), 'base64')

	def _decodeurl_base64(self, url):
		try:
			url = codecs.decode(bytes(url,'utf-8'), 'base64')[::-1].decode()
		except:
			return ''

		if not url.startswith('http://') and not url.startswith('https://'):
			url = 'http://%s' %  url

		#来一个小fix，针对 http://a.com?abc
		#在浏览器会自动转换为：http://a.com/?abc
		try:
			urlp = urlparse(url)
			if urlp.netloc != '':
				url = url.replace('://%s?' % urlp.netloc, '://%s/?' % urlp.netloc)
				url = url.replace('://%s#' % urlp.netloc, '://%s/#' % urlp.netloc)
		except ValueError:
			return ''

		return url


	def build_url(self, visit_url, next_url):
		if visit_url.startswith('//'):
			visit_url = 'http:%s' % visit_url
		new_url = urljoin(visit_url, next_url)
		return '%s?%s' % (self.url_prefix, urlencode({self.url_querykey : self.url_encoder(new_url)}))


	def parse_url(self, fullpath):
		try:
			parseinfo = urlparse(fullpath)
		except:
			return ''
		#如果访问路径不对，例如不是 /p 直接返回空
		if parseinfo[2] != self.url_prefix:   
			return ''
		query_dic = parse_qsl(parseinfo[4])
		for key, value in query_dic:
			if key == self.url_querykey:
				return self.url_decoder(value)
		return ''

