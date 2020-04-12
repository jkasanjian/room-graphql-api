from django.core.exceptions import ValidationError
import graphene
from graphene_django import DjangoObjectType

from .models import User, Household

'''----------------------------USERS----------------------------''' 

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


class UserInput(graphene.InputObjectType):
        email           = graphene.String()
        password        = graphene.String()
        first_name      = graphene.String()
        last_name       = graphene.String()
        status          = graphene.String()
        household       = graphene.Int()


class UpdateUser(graphene.Mutation):
    user = graphene.Field(UserType)

    class Arguments:
        user_data = UserInput(required=True)

    def mutate(self, info, user_data):
        user = info.context.user

        for k, v in user_data.items():
            if(k == 'password') and (v is not None):
                user.set_password(user_data.password)
            elif(k == 'household') and (v is not None):
                household = Household.objects.filter(id=v).first()
                if not household:
                    raise Exception('Household not in database')
                setattr(user, 'household', household)
            else:
                setattr(user, k, v)
        
        try:
            user.full_clean()
            user.save()
            return UpdateUser(user=user)
        
        except ValidationError as e:
            return UpdateUser(user=user, errors=e)

'''----------------------------HOUSEHOLD----------------------------''' 

class HouseholdType(DjangoObjectType):
    class Meta:
        model = Household


class CreateHousehold(graphene.Mutation):
    household = graphene.Field(HouseholdType)

    class Arguments:
        name = graphene.String(required=True)

    def mutate(self, info, name):
        household = Household(name=name)
        household.save()
        return CreateHousehold(household=household)
        




'''--------------------------------------------------------''' 

class Query(graphene.ObjectType):
    users = graphene.List(UserType)
    me = graphene.Field(UserType)
    households = graphene.List(HouseholdType)
    homepage = graphene.Field(HouseholdType)

    def resolve_users(self, info):
        return User.objects.all()

    def resolve_me(self, info):
        user = info.context.user
        if user.is_anonymous:
            raise Exception('Not logged in')
        return user
    
    def resolve_households(self, info):
        return Household.objects.all()

    def resolve_homepage(self, info):
        user = info.context.user
        h_id = user.household.id
        
        return Household.objects.filter(id=h_id).first()



class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()
    update_user = UpdateUser.Field()
    create_household = CreateHousehold.Field()