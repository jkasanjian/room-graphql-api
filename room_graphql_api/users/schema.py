from django.core.exceptions import ValidationError
import graphene
from graphene_django import DjangoObjectType

from .models import User


class UserType(DjangoObjectType):
    class Meta:
        model = User


class CreateUser(graphene.Mutation):
    user = graphene.Field(UserType)

    class Arguments:
        username    = graphene.String(required=True)
        password    = graphene.String(required=True)
        first_name  = graphene.String(required=True)
        last_name   = graphene.String(required=True)

    def mutate(self, info, username, password, first_name, last_name):
        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        user.save()

        return CreateUser(user=user)


class UserInput(graphene.InputObjectType):
        username    = graphene.String()
        password    = graphene.String()
        first_name  = graphene.String()
        last_name   = graphene.String()
        status      = graphene.String()


class UpdateUser(graphene.Mutation):
    user = graphene.Field(UserType)

    class Arguments:
        user_data = UserInput(required=True)

    def mutate(self, info, user_data=None):
        user = info.context.user

        for k, v in user_data.items():
            if(k == 'password') and (v is not None):
                user.set_password(user_data.password)
            else:
                setattr(user, k, v)
        
        try:
            user.full_clean()
            user.save()
            return UpdateUser(user=user)
        
        except ValidationError as e:
            return UpdateUser(user=user, errors=e)


class Query(graphene.ObjectType):
    users = graphene.List(UserType)
    me = graphene.Field(UserType)

    def resolve_users(self, info):
        return User.objects.all()

    def resolve_me(self, info):
        user = info.context.user
        if user.is_anonymous:
            raise Exception('Not logged in')

        return user


class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()
    update_user = UpdateUser.Field()