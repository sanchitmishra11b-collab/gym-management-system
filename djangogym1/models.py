# djangogym1/models.py
from email.policy import default

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save
from django.core.exceptions import ValidationError
from django.dispatch import receiver

@receiver(pre_save, sender=User)
def check_email_for_admin(sender, instance, **kwargs):
    """
    Ensures every admin or superuser has an email before saving.
    Prevents creation or update of admin without an email.
    """
    if (instance.is_staff or instance.is_superuser) and not instance.email:
        raise ValidationError("Admin or Superuser must have a valid email address!")

# Create your models here.

class Enquiry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='enquiries')
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=10)
    email = models.EmailField(max_length=60)
    age = models.IntegerField()
    gender = models.CharField(max_length=11)

    def __str__(self):
        owner = self.user.username if self.user else "NoOwner"
        return f"{self.name} ({owner})"


class Equipment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='equipment_items')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=60)
    date = models.DateField()
    description = models.TextField()

    def __str__(self):
        owner = self.user.username if self.user else "NoOwner"
        return f"{self.name} ({owner})"


class Plan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='plans')
    name = models.CharField(max_length=100)
    amount = models.IntegerField()
    duration = models.CharField(max_length=60)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        owner = self.user.username if self.user else "NoOwner"
        return f"{self.name} ({owner})"

# models.py

# models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Member(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    member_user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name='member_profile'
    )

    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=15)
    email = models.EmailField()
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)

    status = models.CharField(max_length=10, default="Active")
    joining_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField(default=timezone.now)

    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    initial_amount = models.IntegerField(default=0)
    height = models.FloatField(blank=True, null=True)
    weight = models.FloatField(blank=True, null=True)
    goal_weight = models.FloatField(blank=True, null=True)
    activity_level = models.CharField(max_length=20, default="moderate")
    health_issue = models.TextField(blank=True, null=True)

    ai_diet_plan = models.TextField(blank=True, null=True)
    ai_workout_plan = models.TextField(blank=True, null=True)

    def days_left(self):
        from datetime import date
        if self.expiry_date:
            return max((self.expiry_date - date.today()).days, 0)
        return 0

    profile_image = models.ImageField(upload_to='member_profiles/', null=True, blank=True)

    first_login = models.BooleanField(default=True)
    ROLE_CHOICES = (
    ("ADMIN", "Admin"),
    ("TRAINER", "Trainer"),
    ("MEMBER", "Member"),
)

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="MEMBER")

    fitness_goal = models.CharField(max_length=100, blank=True, null=True)
    diet_type = models.CharField(max_length=100, blank=True, null=True)

def days_left(self):
    from datetime import date
    if self.expiry_date:
        return max((self.expiry_date - date.today()).days, 0)
    return 0


    def __str__(self):
        return f"{self.name} ({self.user.username if self.user else 'NoOwner'})"

from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Member


from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

@receiver(post_delete, sender=Member)
def delete_linked_user(sender, instance, **kwargs):
    """
    Safely delete the linked User when a Member is deleted.
    Skips deletion if the User already doesn't exist.
    """
    try:
        user = instance.member_user
        if user and User.objects.filter(pk=user.pk).exists():
            user.delete()
    except ObjectDoesNotExist:
        # The linked user was already deleted — just ignore it
        pass
    except Exception as e:
        print("delete_linked_user error:", e)


from django.utils import timezone

class Attendance(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)
    check_in_time = models.TimeField(default=timezone.now)
    status = models.CharField(max_length=20, default='Present')

    class Meta:
        unique_together = ('member', 'date')

    def __str__(self):
        return f"{self.member.name} - {self.date}"
    

    from django.contrib.auth.models import User
from django.db import models

class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username
    

from django.db import models

class AdminUser(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.username   
    
from django.contrib.auth.models import User
from django.db import models

from datetime import date, timedelta

class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=False)
    access_expires_on = models.DateField(null=True, blank=True)
    plan_type = models.CharField(max_length=20, default='monthly',
                choices=[('monthly','Monthly'),('quarterly','Quarterly'),('yearly','Yearly')])
    grace_period_days = models.IntegerField(default=3)  # 3 day grace after expiry

    def is_access_expired(self):
        if not self.access_expires_on:
            return False
        # grace period — 3 extra days after expiry
        grace_until = self.access_expires_on + timedelta(days=self.grace_period_days)
        return date.today() > grace_until

    def is_in_grace_period(self):
        if not self.access_expires_on:
            return False
        return self.access_expires_on < date.today() <= (
            self.access_expires_on + timedelta(days=self.grace_period_days)
        )

    def days_left(self):
        if not self.access_expires_on:
            return None
        return (self.access_expires_on - date.today()).days

    def plan_duration_days(self):
        return {'monthly': 30, 'quarterly': 90, 'yearly': 365}.get(self.plan_type, 30)