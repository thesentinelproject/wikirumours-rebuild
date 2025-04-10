from .base_settings import *

DEBUG = False

ALLOWED_HOSTS = [
    "wikirumours.org",
    "www.wikirumours.org",
    "peacefultruth.org",
    "www.peacefultruth.org",
    "www.test.peacefultruth.org",
    "unahakika.org",
    "www.unahakika.org",
    "lka.wikirumours.org",
    "kijijichaamani.org",
    "www.kijijichaamani.org",
    "hagigawahid.org",
    "www.hagigawahid.org",
    "runtuwaanabad.org",
    "www.runtuwaanabad.org",
    "137.184.164.69",
    "159.203.42.49",
]

# MEDIA_URL = "/media/"
# MEDIA_ROOT = "/home/wikirumours/wikirumours.org/media"

#GEOS_LIBRARY_PATH = '/home/wikirumours/libraries/geos-3.5.2/capi/.libs/libgeos_c.so'
#GDAL_LIBRARY_PATH = '/home/wikirumours/libraries/gdal-2.4.4/.libs/libgdal.so'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
