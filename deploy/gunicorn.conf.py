"""gunicorn configuration of the container image; GUNICORN_CMD_ARGS overrides any of it"""

wsgi_app = "chords.wsgi:application"
proc_name = "song-book"

# nginx connects through the socket; umask 0 leaves it 0777, as reachable as a 127.0.0.1 port
bind = "unix:/run/gunicorn/gunicorn.sock"
umask = 0
# The control socket would live in the read-only /app
control_socket_disable = True

# Requests are mostly cache reads, so threads add concurrency cheaply. nginx buffers responses,
# so slow clients do not hold a thread.
worker_class = "gthread"
workers = 2
threads = 4
# Recycle workers now and then to cap slow memory growth
max_requests = 1000
max_requests_jitter = 100

# To stdout, i.e. the journal. Over a unix socket %(h)s is empty, so log the client nginx saw;
# %(M)s is the request duration in milliseconds.
accesslog = "-"
access_log_format = '%({x-forwarded-for}i)s %(M)sms "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %({host}i)s'
