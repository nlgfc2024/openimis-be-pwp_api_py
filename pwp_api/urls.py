from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import DefaultRouter

from .registry import registry
from .views import LoginView, ResourceViewSet, SubscriptionViewSet

app_name = "pwp_api"
router = DefaultRouter()
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
for adapter in registry.all():
    viewset = type(f"{adapter.name}ViewSet", (ResourceViewSet,), {
        "adapter": adapter, "serializer_class": adapter.serializer_class,
        "__module__": __name__,
    })
    router.register(adapter.name, viewset, basename=adapter.name)

schema_settings = {
    "TITLE": "openIMIS PWP API", "DESCRIPTION": "PWP API infrastructure and registered adapters",
    "VERSION": "1.0.0", "AUTHENTICATION_WHITELIST": None,
}
urlpatterns = [
    path("v1/login/", LoginView.as_view(), name="login"),
    path("v1/", include(router.urls)),
    path("v1/docs/", SpectacularAPIView.as_view(
        urlconf="pwp_api.schema_urls", custom_settings=schema_settings,
        permission_classes=(IsAuthenticated,),
    ), name="schema"),
    path("v1/docs/swagger/", SpectacularSwaggerView.as_view(
        url_name="pwp_api:schema", permission_classes=(IsAuthenticated,),
    ), name="swagger"),
    path("v1/docs/redoc/", SpectacularRedocView.as_view(
        url_name="pwp_api:schema", permission_classes=(IsAuthenticated,),
    ), name="redoc"),
]
