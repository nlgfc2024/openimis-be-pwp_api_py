from django.conf import settings
from django.urls import include, path

# Mirror openIMIS.openimisurls' mount convention when generating a module-only schema.
site_root = getattr(settings, "SITE_ROOT", lambda: "")
prefix = site_root() if callable(site_root) else site_root
urlpatterns = [path(f"{prefix}pwp_api/", include("pwp_api.urls"))]
