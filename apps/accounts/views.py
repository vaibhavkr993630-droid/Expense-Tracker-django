from django.contrib.auth import authenticate
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    SignupSerializer,
    UpdateUsernameSerializer,
    UserSerializer,
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


class ChangePasswordView(APIView):
    """PATCH /users/change-password"""

    def patch(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"msg": "Password updated successfully."})
