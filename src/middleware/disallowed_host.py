from django.core.exceptions import DisallowedHost
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


class DisallowedHostMiddleware(MiddlewareMixin):
    def process_request(self, request) -> HttpResponse | None:
        try:
            request.get_host()
        except DisallowedHost:
            return HttpResponse(status=406)
