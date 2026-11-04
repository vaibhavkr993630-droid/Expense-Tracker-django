from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models


class UserManager(BaseUserManager):
    """
    Manager that creates users with an email as the primary identifier.

    The default manager assumes `username` is the login field, so a custom user model
    whose USERNAME_FIELD is `email` needs its own create_user / create_superuser.
    """

    use_in_migrations = True

    def _create_user(self, email, username, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        if not username:
            raise ValueError("Users must have a username.")
        # Store emails lower-cased so "A@x.com" and "a@x.com" are the same account.
        email = self.normalize_email(email).lower()
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)  # hashes the password; never store it raw
        user.save(using=self._db)
        return user

    def create_user(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, username, password, **extra_fields)

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields["is_staff"] is not True or extra_fields["is_superuser"] is not True:
            raise ValueError("Superuser must have is_staff=True and is_superuser=True.")
        return self._create_user(email, username, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user: extends Django's AbstractUser (keeps permissions, admin, password hashing)
    but uses the email address as the login identifier.
    """

    # Same rules as the original API: 3-30 chars, letters / digits / underscore only.
    username = models.CharField(
        max_length=30,
        unique=True,
        validators=[
            MinLengthValidator(3),
            RegexValidator(r"^\w+$", "Username can only contain letters, numbers, and underscores."),
        ],
    )
    email = models.EmailField(max_length=75, unique=True)

    USERNAME_FIELD = "email"  # what you type to log in / createsuperuser
    REQUIRED_FIELDS = ["username"]  # extra fields createsuperuser asks for

    objects = UserManager()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.username
