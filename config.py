#!/usr/lib/python2.6/bin/python
#-*- coding: utf-8 -*-

import os

#ProxyflyWebProxy/ProxypyWebProxy
EnabledWebProxy = 'ProxypyWebProxy'
TEMPLATES = 'proxypy'

WORKER_PORT = 9000
WORKER_NUM = 4


DIR_PROJECT_HOME =  os.path.dirname(os.path.realpath(__file__))
DIR_LOG = os.path.join(DIR_PROJECT_HOME, 'logs')
FILE_PAHT_ERRORLOG = os.path.join(DIR_LOG, 'error.log')

BLOCK_CHECK = False
BLOCK_FILE = os.path.join(DIR_LOG, 'block.log')



SOCKET_TIME_OUT = 10
MAX_CONTENT_LENGTH = 15 * 1024 * 1024

########################cache####################
CACHED_CONTENT = False
CACHED_MEMCACHE_PATH = '127.0.0.1:11211'
CACHED_TIME = 5 * 60
CACHED_LEVEL = 2 # 1:GET 2:GET&POST
CACHED_TYPE = ['jpg','gif','bmp','png','css','js','htm','html','jpeg','txt','ico','swf','rss','xml','ttf','json','gz','zip','rar'] # []表示所有  ['jpg','gif', 'html'] 表示cache这3种类型
CACHED_DIR = os.path.join(DIR_PROJECT_HOME, 'cache')

USER_AGENT = "Mozilla/5.0 (compatible; ProxyBot/2.0; +http://proxybot.cc)"

############## AD CODE ####
INSERT_AD_CODE = {
	'head_begin' : """<script async src="https://www.googletagmanager.com/gtag/js?id=UA-156489712-4"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'UA-156489712-4');
</script>
""",
	'body_begin' : """ """,
	'body_end'   : """ """,
}

