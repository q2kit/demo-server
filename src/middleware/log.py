import logging

from django.conf import settings
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin
from ipware import get_client_ip


class RequestLoggerMiddleware(MiddlewareMixin):
    def process_request(self, request) -> None:
        if hasattr(settings, "LOGGING_EXCEPT_URL_NAME_LIST"):
            LOGGING_EXCEPT_URL_NAME_LIST = (  # noqa: N806
                settings.LOGGING_EXCEPT_URL_NAME_LIST
            )
        else:
            LOGGING_EXCEPT_URL_NAME_LIST = ()  # noqa: N806

        if resolve(request.path_info).url_name in LOGGING_EXCEPT_URL_NAME_LIST:
            return

        ip, _ = get_client_ip(request)

        logging.info(
            " - ".join(
                (
                    f"IP: {ip}",
                    f"User: {request.user}",
                    f"Method: {request.method}",
                    f"Path: {request.get_full_path()}",
                ),
            ),
        )

    def process_exception(self, request, exception) -> None:
        if hasattr(settings, "LOGGING_EXCEPT_URL_NAME_LIST"):
            LOGGING_EXCEPT_URL_NAME_LIST = (  # noqa: N806
                settings.LOGGING_EXCEPT_URL_NAME_LIST
            )
        else:
            LOGGING_EXCEPT_URL_NAME_LIST = ()  # noqa: N806

        if resolve(request.path_info).url_name in LOGGING_EXCEPT_URL_NAME_LIST:
            return

        ip, _ = get_client_ip(request)

        logging.error(
            " - ".join(
                (
                    f"IP: {ip}",
                    f"User: {request.user}",
                    f"Method: {request.method}",
                    f"Path: {request.get_full_path()}",
                    f"Error: {exception}",
                ),
            ),
        )
