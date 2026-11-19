"""Project URL file: C:\\the_sawanih\\sawanih\\urls.py  (the one next to settings.py)"""
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", include("login.urls")),
    # Photos are only served to logged-in users.
    re_path(r"^media/(?P<path>.*)$", login_required(serve), {"document_root": settings.MEDIA_ROOT}),
    # /dashboard and /dashboard/ both go to the real dashboard at "/".
    re_path(r"^dashboard/?$", RedirectView.as_view(pattern_name="sawanih:dashboard")),
    # Sawanih app (dashboard at "/") -- keep this LAST.
    path("", include("sawanih.app_urls")),
]
