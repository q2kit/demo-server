from django.utils.deprecation import MiddlewareMixin
from django.contrib import messages
from django.urls import reverse


class MessageMiddleware(MiddlewareMixin):
    def process_request(self, request):
        self.should_add_message(request) and messages.warning(
            request,
            " ".join((
                "Each user can't have more than one project simultaneously.",
                "If you want to create a new project or change the domain,",
                "please delete the current project and create a new one.",
                "For any questions, please contact the admin.",
            )),
            extra_tags="alert alert-warning",
        )

    def should_add_message(self, request):
        user = request.user
        except_paths = (
            reverse("admin:jsi18n"),
        )
        except_keywords = (
            "static",
            "media",
            "favicon.ico",
        )
        return request.method == "GET" \
            and user.is_authenticated \
            and not user.is_superuser \
            and user.project_set.count() != 0 \
            and request.path not in except_paths \
            and not any(keyword in request.path for keyword in except_keywords)
