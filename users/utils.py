from django.core.cache import cache
from django.conf import settings
from django.http import HttpResponseForbidden
from .models import BlacklistedIP
from logs.utils import get_client_ip
from django.contrib import messages



def check_ip(request):
    ip = get_client_ip(request)
    ip_cache_key = "ip_crawler:ip_rate" + ip
    ip_hits_timeout = settings.IP_HITS_TIMEOUT
    max_allowed_hits = settings.MAX_ALLOWED_HITS_PER_IP
    this_ip_hits = cache.get(ip_cache_key)
    if not this_ip_hits:
        this_ip_hits = 1
        cache.set(ip_cache_key, this_ip_hits, ip_hits_timeout)
    else:
        this_ip_hits += 1
        cache.set(ip_cache_key, this_ip_hits,ip_hits_timeout)
    attempts = max_allowed_hits -  this_ip_hits
    messages.error(request, "You have "+str(attempts)+" remaining attempts before you are locked out of the system.")
    if attempts == 0:
        if not BlacklistedIP.objects.filter(ip_address=ip).exists():
            BlacklistedIP.objects.create(ip_address=ip)
        return HttpResponseForbidden()