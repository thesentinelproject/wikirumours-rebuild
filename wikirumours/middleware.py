from django.http import HttpResponseForbidden

from report.models import Domain, CMSPage
from users.models import User, BlacklistedIP


class DomainCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_template_response(self, request, response):
        host = request.get_host()
        domain = Domain.objects.filter(domain=host).first()

        if domain is not None:
            if response.context_data is not None:
                response.context_data["domain"] = domain

        # else:
        #     response.context_data["default"] = settings.STATIC_URL + "sample_logo.png"

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        host = request.get_host()
        domain = Domain.objects.filter(domain=host).first()

        request.cms_pages = CMSPage.objects.filter(visible_to_domains=domain)
        if domain:
            request.domain = domain

        # check if user has special role (non end user) for current domain
        if not request.user.is_anonymous:
            user_domain = request.user.role_domains.filter(domain=request.get_host())
            if not user_domain:
                request.user.role = User.END_USER

            # set tasks count to show in header
            if request.user.role != User.END_USER:
                request.user.tasks_count = request.user.get_tasks_count(domain)

        else:
            request.user.role = User.END_USER


class BlacklistIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        if BlacklistedIP.objects.filter(ip_address=request.META['REMOTE_ADDR']).exists():
            return HttpResponseForbidden()

        response = self.get_response(request)
        return response
