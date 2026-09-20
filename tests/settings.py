import os

os.environ["ASYNC"] = "False"  # Exercise synchronous native mutation execution.

os.environ["NO_DATABASE"] = "1"  # Do not query application configuration during startup.

SECRET_KEY = "isolated-test-settings-only"
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes",
    "graphene_django", "axes", "django_apscheduler", "core",
    "location", "tests.medical_pricelist_stub.apps.MedicalPricelistStubConfig", "pwp_api",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
ROOT_URLCONF = "pwp_api.urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = False
TIME_ZONE = "UTC"  # Match core history timestamps, which use datetime.now().
ALLOWED_HOSTS = ["testserver", "localhost"]
MIDDLEWARE = []
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
PWP_API_ADAPTERS = ["tests.adapters.example"]
PWP_API = {"notification_endpoints": ["https://partner.example/events"]}

# Load real openIMIS models/services; sync only their test schema instead of
# running their PostgreSQL/legacy data migrations against SQLite.
AUTH_USER_MODEL = "core.User"
MIGRATION_MODULES = {"core": None, "location": None, "medical_pricelist": None}
IS_TESTING = True
CACHE_OBJECT_DEFAULT = False
CACHE_OBJECT_TTL = 0
CACHES = {name: {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}
          for name in ("default", "location")}
ROW_SECURITY = True
SCHEDULER_AUTOSTART = False
SCHEDULER_CONFIG = {}
MSSQL = False
PASSWORD_MIN_LENGTH = 8
PASSWORD_UPPERCASE = 0
PASSWORD_LOWERCASE = 0
PASSWORD_DIGITS = 0
PASSWORD_SYMBOLS = 0

MODE = "dev"

AUTHENTICATION_BACKENDS = ["axes.backends.AxesStandaloneBackend", "django.contrib.auth.backends.ModelBackend"]
