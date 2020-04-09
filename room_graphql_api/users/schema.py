from .models import User

import graphene
from graphene_django import DjangoObjectType


class UserType(DjangoObjectType):
    class Meta:
        model = User


class CreateUser(graphene.Mutation):
    user = graphene.Field(UserType)

    class Arguments:
        email       = graphene.String(required=True)
        password    = graphene.String(required=True)
        first_name  = graphene.String(required=True)
        last_name   = graphene.String(required=True)

    def mutate(self, info, email, password, first_name, last_name):
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        user.save()

        return CreateUser(user=user)


class Query(graphene.ObjectType):
    users = graphene.List(UserType)

    def resolve_users(self, info):
        return User.objects.all()


class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()