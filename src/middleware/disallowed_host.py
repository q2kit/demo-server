from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import DisallowedHost
from django.http import HttpResponse


class DisallowedHostMiddleware(MiddlewareMixin):
    def process_request(self, request):
        try:
            request.get_host()
        except DisallowedHost:
            return HttpResponse(status=406)
