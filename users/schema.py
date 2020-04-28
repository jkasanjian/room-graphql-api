from django.core.exceptions import ValidationError
import graphene
from graphene_django import DjangoObjectType
from datetime import datetime, timedelta
from datetime import date as date_o
from dateutil.relativedelta import relativedelta
from .models import User, Household, Task, CompleteTask
from copy import deepcopy


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
            if k == 'password' and v is not None:
                user.set_password(v)

            elif k == 'household' and v is not None:
                household = Household.objects.get(id=v)
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


class DeleteUser(graphene.Mutation):
    ok = graphene.Boolean()
    
    class Arguments:
        email = graphene.String(required=True)

    def mutate(self, info, email):
        user = info.context.user
        user.delete()

        return DeleteUser(ok=True)





'''----------------------------HOUSEHOLD----------------------------''' 

class HouseholdType(DjangoObjectType):
    class Meta:
        model = Household


class CreateHousehold(graphene.Mutation):
    household = graphene.Field(HouseholdType)

    class Arguments:
        name = graphene.String(required=True)

    def mutate(self, info, name):
        user = info.context.user
        household = Household(name=name)
        household.save()
        setattr(user, 'household', household)
        user.save()
        return CreateHousehold(household=household)
        

class UpdateHousehold(graphene.Mutation):
    household = graphene.Field(HouseholdType)

    class Arguments:
        name = graphene.String()
    
    def mutate(self, info, name):
        user = info.context.user
        household = Household.objects.get(id=user.household.id)
        setattr(household, 'name', name)
        household.full_clean()
        household.save()

        return UpdateHousehold(household=household)


class DeleteHousehold(graphene.Mutation):
    ok = graphene.Boolean()

    class Arguments:
        h_id = graphene.Int(required=True)
    
    def mutate(self, info, h_id):
        household = Household.objects.get(id=h_id)
        household.delete()

        return DeleteHousehold(ok=True)



'''----------------------------TASKS----------------------------''' 

class TaskType(DjangoObjectType):
    class Meta:
        model = Task


class CompleteTaskType(DjangoObjectType):
    class Meta:
        model = CompleteTask


class CreateTask(graphene.Mutation):
    task = graphene.Field(TaskType)

    class Arguments:
        name = graphene.String(required=True)
        description = graphene.String(required=True)
        due_date = graphene.String(required=True)
        frequency = graphene.String(required=True)
        current = graphene.Int()
        rotation = graphene.List(graphene.Int)

    def mutate(self, info, name, description, due_date, frequency, current=None, rotation=None):
        user = info.context.user
        task = Task(
            name=name,
            description=description,
            due_date=datetime.strptime(due_date, '%d%m%Y').date(),
            frequency=frequency,
            household=Household.objects.get(id=user.household.id),
        )
        if current:
            setattr(task, 'current', User.objects.get(id=current))
        task.save()

        if rotation:
            for r_id in rotation:
                task.rotation.add(User.objects.get(id=r_id))

        return CreateTask(task=task)
        


class TaskInput(graphene.InputObjectType):
    task_id = graphene.Int(required=True)
    name = graphene.String()
    description = graphene.String()
    due_date = graphene.String()
    frequency = graphene.String()
    current = graphene.Int()
    complete = graphene.Boolean()
    rotation = graphene.List(graphene.Int)


class UpdateTask(graphene.Mutation):
    task = graphene.Field(TaskType)
    
    class Arguments:
        task_data = TaskInput(required=True)
    
    def mutate(self, info, task_data):
        task = Task.objects.get(id=task_data['task_id'])

        for k, v in task_data.items():
            if k == 'task_id':
                continue

            elif k == 'due_date' and v is not None:
                new_date = datetime.strptime(v, '%d%m%Y').date()
                setattr(task, k, new_date)
            
            elif k == 'current' and v is not None:
                new_current = User.objects.get(id=v)
                setattr(task, k, new_current)
                
            elif k == 'complete' and v is not None:
                if v:   # if changing completed to true
                    # Saving CompleteTask to database
                    done_task = CompleteTask(
                        name=task.name,
                        roommate=task.current,
                        date=date_o.today(),
                        household=task.household
                        )
                    done_task.full_clean()
                    done_task.save()

                    unit, num = task.frequency[0], int(task.frequency[1:])
                    if unit == 'X':
                        setattr(task, 'name', 'deleted')
                        ret = deepcopy(task)
                        task.delete()
                        return UpdateTask(task=ret)
                    elif unit == 'D':
                        delta = timedelta(days=num)
                    elif unit == 'W':
                        delta = timedelta(weeks=num)
                    elif unit == 'M':
                        delta = relativedelta(months=num)
                    elif unit == 'Y':
                        delta = relativedelta(years=num)
                    # updating to next due date based on frequency
                    next_date = task.due_date + delta
                    setattr(task, 'due_date', next_date)
                    setattr(task, k, False) # setting complete to false

                    if task.rotation:
                        # update current to next in rotation
                        start = True
                        up_next = False
                        for r in task.rotation.all():
                            if start:
                                first = r
                                start = False

                            if up_next:
                                setattr(task, 'current', r)
                                task.full_clean()
                                task.save()
                                return UpdateTask(task=task)

                            if r == task.current:
                                print('up next called', r.first_name)
                                up_next = True
                
                        # if here, current was last, so first is next
                        print('at the end')
                        setattr(task, 'current', first)

                else:   # if changing to false
                    setattr(task, k, v)
            
            elif k == 'rotation' and v is not None:
                for r_id in v:
                    task.rotation.add(User.objects.get(id=r_id))

            else:
                setattr(task, k, v)
            
            task.full_clean()
            task.save()

        return UpdateTask(task=task)


class DeleteTask(graphene.Mutation):
    ok = graphene.Boolean()

    class Arguments:
        task_id = graphene.Int(required=True)
    
    def mutate(self, info, task_id):
        task = Task.objects.get(id=task_id)
        task.delete()

        return DeleteTask(ok=True)




'''-----------------------QUERIES-----------------------''' 

class HomepageUnion(graphene.Union):
    class Meta:
        types = (HouseholdType, UserType)


class Query(graphene.ObjectType):
    users           = graphene.List(UserType)
    me              = graphene.Field(UserType)

    households      = graphene.List(HouseholdType)
    homepage        = graphene.List(HomepageUnion)

    tasks           = graphene.List(graphene.List(TaskType))
    complete_tasks  = graphene.List(CompleteTaskType)

    # USERS
    def resolve_users(self, info):
        return User.objects.all()

    def resolve_me(self, info):
        user = info.context.user
        if user.is_anonymous:
            raise Exception('Not logged in')
        return user
    
    # HOUSEHOLD
    def resolve_households(self, info):
        return Household.objects.all()

    def resolve_homepage(self, info):
        logged_in = info.context.user
        household = logged_in.household
        roommates = []
        roommates.extend([logged_in])
        roommates.extend(household.users.exclude(id=logged_in.id))
        return [household, *roommates]

    # TASKS
    def resolve_tasks(self, info):
        user = info.context.user
        my_tasks = []
        task_list = user.household.tasks.order_by('complete', 'due_date')
        for t in task_list:
            if t.current == user:
                my_tasks.append(t)

        other_tasks = [x for x in task_list if x not in my_tasks]
        
        return [my_tasks, other_tasks]


    def resolve_complete_tasks(self, info):
        return info.context.user.household.complete_tasks.order_by('date')



'''-----------------------MUTATIONS-----------------------''' 
class Mutation(graphene.ObjectType):
    # USERS
    create_user = CreateUser.Field()
    update_user = UpdateUser.Field()
    delete_user = DeleteUser.Field()
    # HOUSEHOLDS
    create_household = CreateHousehold.Field()
    update_household = UpdateHousehold.Field()
    delete_household = DeleteHousehold.Field()
    # TASKS
    create_task = CreateTask.Field()
    update_task = UpdateTask.Field()
    delete_task = DeleteTask.Field()