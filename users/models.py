from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager



'''----------------------------HOUSEHOLD----------------------------''' 

class Household(models.Model):
    name = models.CharField(max_length=64)


'''----------------------------TASK----------------------------''' 


class Task(models.Model):
    name        = models.CharField(max_length=64)
    description = models.CharField(max_length=128)
    due_date    = models.DateTimeField()
    in_between  = models.IntegerField()
    complete    = models.BooleanField()
    current     = models.ForeignKey(User, on_delete=models.SET_NULL)
    rotation    = models.ManyToManyField(User)
    household   = models.ForeignKey(
                  Household, 
                  related_name='tasks',
                  on_delete = models.CASCADE
            )






'''----------------------------USERS----------------------------''' 

class UserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None):
        if not email:
            raise ValueError('Users must have an email address')
        if (not first_name) or not(last_name):
            raise ValueError('Users must have a name')

        user = self.model(
            email=self.normalize_email(email),
            first_name=first_name,
            last_name=last_name
        )
        user.set_password(password)
        user.save(user=self._db)
        return user


    def create_superuser(self, email, first_name, last_name, password):
        user = self.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(user=self._db)
        return user



class User(AbstractBaseUser):
    email           = models.EmailField(verbose_name='email',max_length=64, unique=True)
    first_name      = models.CharField(verbose_name='first name', max_length=32)
    last_name       = models.CharField(verbose_name='last name', max_length=32)
    status          = models.CharField(max_length=255, null=True, blank=True)
    household       = models.ForeignKey(
                        Household, 
                        related_name='users',
                        on_delete = models.SET_NULL,
                        null=True,
                        blank=True,
                    )

    date_joined     = models.DateTimeField(verbose_name='date joined', auto_now_add=True)
    last_login      = models.DateTimeField(verbose_name='last login', auto_now=True)
    is_admin        = models.BooleanField(default=False)
    is_active       = models.BooleanField(default=True)
    is_staff        = models.BooleanField(default=False)
    is_superuser    = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name',]

    objects = UserManager()

