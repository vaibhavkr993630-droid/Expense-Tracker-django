from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.schema import ErrorSerializer

from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    SignupSerializer,
    UpdateUsernameSerializer,
    UserSerializer,
)


@extend_schema_view(
    post=extend_schema(
        tags=["Authentication"],
        summary="Register a new user",
        auth=[],  # no token needed
        responses={
            201: inline_serializer(
                "SignupResponse", {"detail": serializers.CharField(), "id": serializers.IntegerField()}
            ),
            400: ErrorSerializer,
            429: ErrorSerializer,
        },
    )
)
class SignupView(generics.CreateAPIView):
    """POST /signup: register a new user."""

    serializer_class = SignupSerializer
    permission_classes = [AllowAny]  # anyone may sign up
    authentication_classes = []  # a stale/invalid token must not block signing up
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "signup"  # rate comes from REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"detail": f"User '{user.username}' successfully registered", "id": user.id},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /login: exchange credentials for a JWT.

    The React app posts form-urlencoded data (OAuth2-style) and reads `access_token`,
    so we accept form + JSON and return that shape instead of simplejwt's default
    {"access", "refresh"}. The token itself is still created by simplejwt.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [FormParser, JSONParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(
        tags=["Authentication"],
        summary="Log in and get an access token",
        description=(
            "Send `username` (username or email) and `password` as form fields. "
            "Limited to 10 requests/minute."
        ),
        auth=[],
        request={"application/x-www-form-urlencoded": LoginSerializer, "application/json": LoginSerializer},
        responses={
            200: inline_serializer(
                "LoginResponse",
                {"access_token": serializers.CharField(), "token_type": serializers.CharField()},
            ),
            400: ErrorSerializer,
            401: ErrorSerializer,
            429: ErrorSerializer,
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # authenticate() runs our EmailOrUsernameBackend (see AUTHENTICATION_BACKENDS).
        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        token = AccessToken.for_user(user)
        return Response({"access_token": str(token), "token_type": "bearer"})


@extend_schema_view(
    get=extend_schema(
        tags=["Users"], summary="Get my profile", responses={200: UserSerializer, 401: ErrorSerializer}
    ),
    put=extend_schema(
        tags=["Users"],
        summary="Change my username",
        request=UpdateUsernameSerializer,
        responses={
            200: inline_serializer(
                "UpdateUsernameResponse",
                {"msg": serializers.CharField(), "username": serializers.CharField()},
            ),
            400: ErrorSerializer,
            401: ErrorSerializer,
        },
    ),
    delete=extend_schema(
        tags=["Users"],
        summary="Delete my account and all my data",
        responses={204: None, 401: ErrorSerializer},
    ),
)
class ProfileView(generics.RetrieveUpdateDestroyAPIView):
    """
    The logged-in user's own account.

    GET /users/me (profile), DELETE /users/me (delete account),
    PUT /user (change username), DELETE /user (delete account, legacy URL).
    There is no id in the URL: the object is always `request.user`, so one user can never
    reach another user's account.
    """

    http_method_names = ["get", "put", "delete", "head", "options"]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        return UpdateUsernameSerializer if self.request.method == "PUT" else UserSerializer

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"msg": "Username updated successfully.", "username": user.username})


@extend_schema(exclude=True)  # same behaviour as /users/me; hidden so the docs list each operation once
class LegacyProfileView(ProfileView):
    """PUT/DELETE /user: URL kept from the FastAPI API."""


class ChangePasswordView(APIView):
    """PATCH /users/change-password"""

    @extend_schema(
        tags=["Users"],
        summary="Change my password",
        request=ChangePasswordSerializer,
        responses={
            200: inline_serializer("ChangePasswordResponse", {"msg": serializers.CharField()}),
            400: ErrorSerializer,
            401: ErrorSerializer,
        },
    )
    def patch(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"msg": "Password updated successfully."})
