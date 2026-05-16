# djangogym1/admin.py

from django.contrib import admin
from django.contrib.auth.models import User
from .models import Enquiry, Equipment, Plan, Member, Attendance, AdminUser


@admin.register(AdminUser)
class AdminUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'is_approved')
    list_filter = ('is_approved',)
    search_fields = ('username',)

    def save_model(self, request, obj, form, change):
        """
        When superadmin ticks 'is_approved' and saves in Django Admin,
        this automatically creates a Django User with is_staff=True
        so the new admin can login immediately.
        """
        super().save_model(request, obj, form, change)

        if obj.is_approved:
            # Create or update the linked Django User
            user, created = User.objects.get_or_create(username=obj.username)
            user.set_password(obj.password)
            user.is_staff = True
            user.is_active = True
            if not user.email:
                user.email = f"{obj.username}@gym.local"  # required by your email signal
            user.save()

            if created:
                self.message_user(
                    request,
                    f"✅ Admin '{obj.username}' approved! Django User created. They can now login at /login/",
                )
            else:
                self.message_user(
                    request,
                    f"✅ Admin '{obj.username}' approved! Existing user updated with staff access.",
                )


admin.site.register(Enquiry)
admin.site.register(Equipment)
admin.site.register(Plan)
admin.site.register(Member)
admin.site.register(Attendance)