from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class User(AbstractBaseUser):
    email           = models.EmailField(verbose_name='email', max_length=64, unique=True)
    first_name      = models.CharField(verbose_name='first name', max_length=32)
    last_name       = models.CharField(verbose_name='last name', max_length=32)
    status = models.CharField(max_length=255, null=True, blank=True)

    date_joined     = models.DateTimeField(verbose_name='date joined', auto_now_add=True)
    last_login      = models.DateTimeField(verbose_name='last login', auto_now=True)
    is_admin        = models.BooleanField(default=False)
    is_active       = models.BooleanField(default=True)
    is_staff        = models.BooleanField(default=False)
    is_superuser    = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name',]

