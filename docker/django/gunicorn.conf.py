# =============================================================================
# SafraLog — docker/django/gunicorn.conf.py
# =============================================================================
import multiprocessing
import os

# Binding
bind = "0.0.0.0:8000"
backlog = 2048

# Workers
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
worker_connections = 1000
threads = int(os.environ.get("GUNICORN_THREADS", 2))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
keepalive = 5
graceful_timeout = 30

# Logging
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
accesslog = "-"
errorlog = "-"
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sms'
)

# Reload (apenas dev)
reload = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"
reload_extra_files = []

# Process naming
proc_name = "safralog"
default_proc_name = "safralog"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# Hooks
def on_starting(server):
    pass

def on_reload(server):
    pass

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    server.log.info("SafraLog Gunicorn ready. Listening on: %s", bind)

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def worker_abort(worker):
    worker.log.info("worker received SIGABRT signal")
