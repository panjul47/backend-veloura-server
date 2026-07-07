# Gunicorn configuration — production
bind        = "0.0.0.0:8000"
workers     = 3
timeout     = 60
accesslog   = "-"   # stdout
errorlog    = "-"   # stderr
loglevel    = "warning"
