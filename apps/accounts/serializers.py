from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    """Validates the signup payload and creates the user through the custom manager."""

    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "confirm_password")
        # The model's unique=True would produce generic messages; we check duplicates ourselves
        # so the messages match the old API ("Email already registered.").
        extra_kwargs = {
            "username": {"validators": []},
            "email": {"validators": []},
        }

    def validate_username(self, value):
        # Re-run the model's validators (3-30 chars, \w+ only) because we removed the defaults.
        for validator in User._meta.get_field("username").validators:
            validator(value)
        return value

    def validate(self, attrs):
        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError({"detail": "Email already registered."})
        if User.objects.filter(username=attrs["username"]).exists():
            raise serializers.ValidationError({"detail": "Username already taken."})
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"detail": "Passwords do not match."})
        # Django's password validators (common passwords, all-numeric, similarity to user data).
        validate_password(attrs["password"], user=User(username=attrs["username"], email=attrs["email"]))
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        return User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
        )


class LoginSerializer(serializers.Serializer):
    """Login payload. No length rules here: wrong credentials must be a 401, not a 400."""

    username = serializers.CharField()  # may hold the username OR the email
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")
        read_only_fields = fields


class UpdateUsernameSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("username",)
        extra_kwargs = {"username": {"validators": []}}

    def validate_username(self, value):
        for validator in User._meta.get_field("username").validators:
            validator(value)
        return value

    def validate(self, attrs):
        # exclude(pk=...) so a user can "change" to their own current name without an error
        if User.objects.filter(username=attrs["username"]).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError({"detail": "Username already in use."})
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"detail": "Current password is incorrect."})
        validate_password(attrs["new_password"], user=user)  # Django's password rules
        return attrs
