from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .authentication import issue_token
from .permissions import ResourcePermission
from .serializers import LoginRequestSerializer, LoginResponseSerializer, SubscriptionSerializer
from .services import SubscriptionService


class BoundedPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class ResourceViewSet(viewsets.ReadOnlyModelViewSet):
    adapter = None
    permission_classes = (ResourcePermission,)
    pagination_class = BoundedPagination

    def get_queryset(self):
        return self.adapter.service_class(self.request.user).get_queryset()


class SubscriptionViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SubscriptionSerializer
    pagination_class = BoundedPagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            from .models import Subscription
            return Subscription.objects.none()
        return SubscriptionService(self.request.user).get_queryset()

    def perform_destroy(self, instance):
        SubscriptionService(self.request.user).delete(instance)


class LoginView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    serializer_class = LoginRequestSerializer

    @extend_schema(responses=LoginResponseSerializer)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(issue_token(request, **serializer.validated_data))
