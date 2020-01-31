import multiprocessing

home = '/home/project/proxybot-async'
bind = '127.0.0.1:9000'
#bind = 'unix:' + home + '/tools/gunicorn-sanic.sock'
workers = multiprocessing.cpu_count() * 2 + 1
backlog = 2048
timeout = 30
daemon = True
debug = True
worker_class = 'sanic.worker.GunicornWorker'
errorlog = home + '/logs/gunicorn-sanic.error.log'
access_logfile = home + '/logs/gunicorn-sanic.access.log'
pidfile = home + '/tools/gunicorn-sanic.pid'
log_level = 'debug'