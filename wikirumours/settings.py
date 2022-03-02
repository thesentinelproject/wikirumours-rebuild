from .base_settings import *

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

from distutils.sysconfig import get_python_lib

os.environ["PATH"] += os.pathsep + get_python_lib() + '\\osgeo'