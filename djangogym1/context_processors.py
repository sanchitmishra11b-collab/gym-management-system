from .models import AdminProfile

def pending_count(request):
    if request.user.is_authenticated and request.user.is_superuser:
        count = AdminProfile.objects.filter(is_approved=False).count()
        return {'pending_count': count}
    return {'pending_count': 0}