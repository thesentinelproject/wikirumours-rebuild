from .base_settings import *

DEBUG = False

ALLOWED_HOSTS = [
    "wikirumours.org",
    "www.wikirumours.org",
    "peacefultruth.org",
    "www.test.peacefultruth.org",
    "unahakika.org",
    "lka.wikirumours.org",
    "kijijichaamani.org",
    "hagigawahid.org",
    "runtuwaanabad.org",
    "137.184.164.69",
]

# MEDIA_URL = "/media/"
# MEDIA_ROOT = "/home/wikirumours/wikirumours.org/media"

#GEOS_LIBRARY_PATH = '/home/wikirumours/libraries/geos-3.5.2/capi/.libs/libgeos_c.so'
#GDAL_LIBRARY_PATH = '/home/wikirumours/libraries/gdal-2.4.4/.libs/libgdal.so'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
