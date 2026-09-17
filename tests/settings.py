SECRET_KEY = "isolated-test-settings-only"
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes",
    "rest_framework", "drf_spectacular", "pwp_api.apps.PwpApiConfig",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
ROOT_URLCONF = "pwp_api.schema_urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
ALLOWED_HOSTS = ["testserver", "localhost"]
MIDDLEWARE = []
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.BasicAuthentication"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
PWP_API_ADAPTERS = ["tests.adapters.example"]
PWP_API = {"notification_endpoints": ["https://partner.example/events"]}
SPECTACULAR_SETTINGS = {"TITLE": "openIMIS PWP API", "VERSION": "1.0.0"}
