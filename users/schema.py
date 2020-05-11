from django.core.exceptions import ValidationError
import graphene
from graphene_django import DjangoObjectType
from datetime import datetime, timedelta
from datetime import date as date_o
from dateutil.relativedelta import relativedelta
from .models import User, Household, Task, CompleteTask, Bill, BillCycle
from copy import deepcopy
from decimal import Decimal, ROUND_UP


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

        return DeleteUser(ok=True)  # TODO: error handling





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
        name        = graphene.String(required=True)
        description = graphene.String(required=True)
        due_date    = graphene.String(required=True)
        frequency   = graphene.String(required=True)
        current     = graphene.Int()
        rotation    = graphene.List(graphene.Int)

    def mutate(self, info, name, description, due_date, frequency, current=None, rotation=None):
        user = info.context.user
        task = Task(
            name=name,
            description=description,
            due_date=datetime.strptime(due_date, '%d%m%Y').date(),
            frequency=frequency,
            household=Household.objects.get(id=user.household.id)
        )
        if current:
            setattr(task, 'current', User.objects.get(id=current))
        task.full_clean()
        task.save()

        if rotation:
            for r_id in rotation:
                task.rotation.add(User.objects.get(id=r_id))

        return CreateTask(task=task)
        


class TaskInput(graphene.InputObjectType):
    task_id         = graphene.Int(required=True)
    name            = graphene.String()
    description     = graphene.String()
    due_date        = graphene.String()
    frequency       = graphene.String()
    current         = graphene.Int()
    complete        = graphene.Boolean()
    add_rotation    = graphene.List(graphene.Int)
    remove_rotation = graphene.List(graphene.Int)


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

                    if task.rotation.all().exists():
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
                                up_next = True
                
                        # if here, current was last, so first is next
                        setattr(task, 'current', first)

                else:   # if changing to false
                    setattr(task, k, v)
            
            elif k == 'add_rotation' and v is not None:
                for r_id in v:
                    if not task.rotation.filter(id=r_id).exists():
                        task.rotation.add(User.objects.get(id=r_id))
            
            elif k == 'remove_rotation' and v is not None:
                for r_id in v:
                    if task.rotation.filter(id=r_id).exists():
                        task.rotation.remove(User.objects.get(id=r_id))

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




'''----------------------------BILLS----------------------------''' 
class BillType(DjangoObjectType):
    class Meta:
        model = Bill


class BillCycleType(DjangoObjectType):
    class Meta:
        model = BillCycle


class CreateBill(graphene.Mutation):
    bill = graphene.Field(BillType)

    class Arguments:
        name            = graphene.String(required=True)
        due_date        = graphene.String(required=True)
        frequency       = graphene.String(required=True)
        participants    = graphene.List(graphene.Int)  
        total_balance   = graphene.Decimal()
    
    def mutate(self, info, name, due_date, frequency, total_balance=0.00, participants=[]):
        user = info.context.user
        bill = Bill(
            name=name,
            due_date=datetime.strptime(due_date, '%d%m%Y').date(),
            frequency=frequency,
            total_balance=total_balance,
            manager=user,
            num_split=len(participants)+1,
            household=Household.objects.get(id=user.household.id),
        )
        bill.full_clean()
        bill.save()
        if participants:
            for r_id in participants:
                bill.participants.add(User.objects.get(id=r_id))

        return CreateBill(bill=bill)


class BillInput(graphene.InputObjectType):
    bill_id             = graphene.Int(required=True)
    name                = graphene.String()
    due_date            = graphene.String()
    add_participants    = graphene.List(graphene.Int)
    remove_participants = graphene.List(graphene.Int)
    total_balance       = graphene.Decimal()
    is_active           = graphene.Boolean()


class UpdateBill(graphene.Mutation):
    bill = graphene.Field(BillType)

    class Arguments:
        bill_data = BillInput(required=True)
    
    def mutate(self, info, bill_data):
        bill = Bill.objects.get(id=bill_data['bill_id'])

        for k, v in bill_data.items():
            if k == 'bill_id':
                continue
            
            elif k == 'due date' and v is not None:
                new_date = datetime.strptime(v, '%d%m%Y').date()
                setattr(bill, k, new_date)

            elif k == 'total_balance' and v is not None:
                setattr(bill, k, v)
                
            elif k == 'add_participants' and v is not None:
                count = 0
                for r_id in v:
                    if not bill.participants.filter(id=r_id).exists():
                        bill.participants.add(User.objects.get(id=r_id))
                        count += 1
                if count > 0:
                    new_num = bill.num_split + count
                    setattr(bill, 'num_split', new_num)
            
            elif k == 'remove_participants' and v is not None:
                count = 0
                for r_id in v:
                    if bill.participants.filter(id=r_id).exists():
                        bill.participants.remove(User.objects.get(id=r_id))
                        count += 1
                if count > 0:
                    new_num = bill.num_split - count
                    setattr(bill, 'num_split', new_num)

            elif k == 'is_active' and v is not None:
                # if switching bill from inavtive to active
                if v and not bill.is_active:
                    if bill.participants: # if bill has participants
                        setattr(bill, k, v)
                        cents = Decimal('.01')
                        amount = Decimal((bill.total_balance / bill.num_split).quantize(cents, rounding=ROUND_UP))
                        for r in bill.participants.all():
                            cycle = BillCycle (
                                bill=bill,
                                recipient=r,
                                amount=amount
                            )
                            cycle.full_clean()
                            cycle.save()
                    
                    else:
                        raise Exception('No roommates splitting bill')
                
                # if swtiching bill from active to inactive (e.g. all users paid)
                elif not v and bill.is_active:
                    # calculate next due date
                    unit, num = bill.frequency[0], int(bill.frequency[1:])
                    if unit == 'X':
                        setattr(bill, 'name', 'deleted')
                        ret = deepcopy(bill)
                        bill.delete()
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
                    next_date = bill.due_date + delta
                    setattr(bill, 'due_date', next_date)
                    setattr(bill, 'total_balance', Decimal('0.00'))
                    setattr(bill, k, v) # setting active to false
            
            else:
                setattr(bill, k, v)
            
        bill.full_clean()
        bill.save()
        return UpdateBill(bill=bill)
                                        

class PayBillCycle(graphene.Mutation):
    cycle = graphene.Field(BillCycleType)

    class Arguments:
        bill_id = graphene.Int(required=True)
    
    def mutate(self, info, bill_id):
        user = info.context.user
        bill = Bill.objects.get(id=bill_id)
        cycle = bill.cycles.get(recipient=user)
        setattr(cycle, 'is_paid', True)
        setattr(cycle, 'date_paid', date_o.today())
        cycle.full_clean()
        cycle.save()
        return PayBillCycle(cycle=cycle)
        


class DeleteBill(graphene.Mutation):
    ok = graphene.Boolean()

    class Arguments:
        bill_id = graphene.Int(required=True)

    def mutate(self, info, bill_id):
        bill = Bill.objects.get(id=bill_id)
        bill.delete()

        return DeleteBill(ok=True)





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
    # BILLS
    create_bill = CreateBill.Field()
    update_bill = UpdateBill.Field()
    delete_bill = DeleteBill.Field()
    pay_bill_cycle = PayBillCycle.Field()





'''-----------------------QUERIES-----------------------''' 

class HomepageUnion(graphene.Union):
    class Meta:
        types = (HouseholdType, UserType)

class BillListType(graphene.ObjectType):
    data = graphene.List(BillType)

class CycleListType(graphene.ObjectType):
    data = graphene.List(BillCycleType)

class BillsPageUnion(graphene.Union):
    class Meta:
        types = (BillListType, CycleListType)


class Query(graphene.ObjectType):
    users           = graphene.List(UserType)
    me              = graphene.Field(UserType)

    households      = graphene.List(HouseholdType)
    homepage        = graphene.List(HomepageUnion)

    tasks           = graphene.List(graphene.List(TaskType))
    complete_tasks  = graphene.List(CompleteTaskType)

    bills           = graphene.List(BillsPageUnion)
    complete_bills  = graphene.List(BillCycleType)

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
        # TODO: use filtering instead of a for loop
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


    # BILLS
    def resolve_bills(self, info):
        user = info.context.user
        all_bills = user.household.bills.all()
        my_bills = all_bills.filter(manager=user)
        other_bills = all_bills.exclude(manager=user)

        my_cycles = []
        for b in other_bills:
            my_cycles.extend(b.cycles.filter(recipient=user, is_paid=False))
        
        return [BillListType(data=my_bills), CycleListType(data=my_cycles)]


    def resolve_complete_bills(self, info):
        bills = info.context.user.household.bills
        complete_cycles = []
        for b in bills.all():
            complete_cycles.extend(b.cycles.filter(is_paid=True)) 

        complete_cycles.sort(key=lambda x: x.date_paid, reverse=True)

        return complete_cycles


