from djangogym1.models import AdminProfile

def pending_count(request):
    pending_count = 0
    if request.user and request.user.is_superuser:
        pending_count = AdminProfile.objects.filter(is_approved=False).count()
    return {
        'pending_admins_count': pending_count,
    }