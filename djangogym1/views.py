# djangogym1/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Sum
from django.http import HttpResponse
from collections import Counter
from datetime import date, timedelta, datetime
import random

from .models import AdminUser, AdminProfile, Enquiry, Equipment, Plan, Member, Attendance

# ─────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp_code):
    subject = 'Gym Admin Password Reset Code'
    message = f"Your one-time code is: {otp_code}. Do not share it."
    email_from = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)
    try:
        send_mail(subject, message, email_from, [email], fail_silently=False)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


# ─────────────────────────────────────────────────────────
# STATIC PAGES
# ─────────────────────────────────────────────────────────

def HomePage(request):
    return render(request, 'homepage.html')

def About(request):
    return render(request, 'about.html')

def Contact(request):
    return render(request, 'contact.html')


# ─────────────────────────────────────────────────────────
# ADMIN DASHBOARD (INDEX)
# ─────────────────────────────────────────────────────────

def Index(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('login')

    today = date.today()
    current_year = today.year

    members = Member.objects.filter(user=request.user)
    equipments = Equipment.objects.filter(user=request.user)

    active_count = members.filter(status="Active").count()
    expired_count = members.filter(status="Expired").count()
    total_count = members.count()

    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    member_counter = Counter(m.joining_date for m in members if m.joining_date)
    equip_counter = Counter(e.date for e in equipments if e.date)

    chart_labels = [d.strftime("%d %b") for d in last_7_days]
    chart_members = [member_counter.get(d, 0) for d in last_7_days]
    chart_equips = [equip_counter.get(d, 0) for d in last_7_days]

    monthly_revenue = (
        members.filter(joining_date__year=current_year)
        .values_list('joining_date__month')
        .annotate(total=Sum('initial_amount'))
    )
    revenue_dict = {month: total or 0 for month, total in monthly_revenue}
    chart_revenue = [revenue_dict.get(i, 0) for i in range(1, 13)]
    total_revenue = sum(chart_revenue)

    context = {
        "active_count": active_count,
        "expired_count": expired_count,
        "total_count": total_count,
        "members": members,
        "member_count": total_count,
        "enquiry_count": Enquiry.objects.filter(user=request.user).count(),
        "plan_count": Plan.objects.filter(user=request.user).count(),
        "equipment_count": equipments.count(),
        "expired_members": members.filter(expiry_date__lt=today),
        "expiring_members": members.filter(
            expiry_date__gte=today,
            expiry_date__lte=today + timedelta(days=7)
        ),
        "chart_labels": chart_labels,
        "chart_members": chart_members,
        "chart_equips": chart_equips,
        "chart_revenue": chart_revenue,
        "total_revenue": total_revenue,
    }
    return render(request, "index.html", context)


# ─────────────────────────────────────────────────────────
# AUTHENTICATION
# ─────────────────────────────────────────────────────────

def Login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # superuser bypasses everything
            if user.is_superuser:
                login(request, user)
                return redirect('home')

            if user.is_staff:
                try:
                    profile = AdminProfile.objects.get(user=user)
                    if not profile.is_approved:
                        messages.error(request, "Your account is pending approval.")
                        return redirect('login')
                    if profile.is_access_expired():
                        messages.error(request, "Your access has expired.")
                        return redirect('login')
                    login(request, user)
                    return redirect('home')
                except AdminProfile.DoesNotExist:
                    messages.error(request, "No admin profile found.")
            else:
                messages.error(request, "Not authorized as admin.")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'login.html')


def Logout_admin(request):
    request.session.flush()
    logout(request)
    return redirect('homepage')


# ─────────────────────────────────────────────────────────
# FORGOT PASSWORD FLOW
# ─────────────────────────────────────────────────────────

def ForgotPassword_Request(request):
    error = ""
    if request.method == 'POST':
        uname = request.POST.get('uname')
        try:
            user = User.objects.get(username=uname, is_staff=True)
            if not user.email:
                error = "Admin exists but no email is registered."
                return render(request, 'forgot_password_request.html', {'error': error})
            otp_code = generate_otp()
            if send_otp_email(user.email, otp_code):
                request.session['otp_user_id'] = user.id
                request.session['otp_secret'] = otp_code
                return redirect('verify_otp')
            else:
                error = "Email sending failed."
        except User.DoesNotExist:
            error = "Invalid username."
    return render(request, 'forgot_password_request.html', {'error': error})


def Verify_OTP(request):
    error = ""
    user_id = request.session.get('otp_user_id')
    stored_otp = request.session.get('otp_secret')
    if not user_id or not stored_otp:
        messages.error(request, "OTP session expired.")
        return redirect('forgot_password_request')
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        if str(entered_otp) == str(stored_otp):
            request.session.pop('otp_secret', None)
            return redirect('change_password_final')
        else:
            error = "Invalid OTP."
    return render(request, 'verify_otp.html', {'error': error})


def ChangePassword_Final(request):
    error = ""
    user_id = request.session.get('otp_user_id')
    if not user_id:
        messages.error(request, "Session expired.")
        return redirect('forgot_password_request')
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        p1 = request.POST.get('pwd1')
        p2 = request.POST.get('pwd2')
        if p1 != p2:
            error = "Passwords do not match."
        elif not p1 or len(p1) < 6:
            error = "Password must be at least 6 characters."
        else:
            user.set_password(p1)
            user.save()
            request.session.pop('otp_user_id', None)
            return render(request, 'password_reset_success.html')
    return render(request, 'change_password_final.html', {'error': error})


# ─────────────────────────────────────────────────────────
# ADMIN REGISTRATION & APPROVAL
# ─────────────────────────────────────────────────────────

from django.contrib.auth.models import User
from .models import AdminProfile

def register_admin(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        email = request.POST.get("email")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email
        )
        user.is_staff = False
        user.is_active = False
        user.save()
        

        AdminProfile.objects.create(
            user=user,
            is_approved=False
        )

        messages.success(request, "Registered! Wait for approval.")
        return redirect('login')

    return render(request, 'register.html')


# ─────────────────────────────────────────────────────────
# ADMIN REGISTRATION & APPROVAL
# ─────────────────────────────────────────────────────────
def pending_admins(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('home')
    today = date.today()
    pending  = AdminProfile.objects.filter(is_approved=False).select_related('user')
    approved = AdminProfile.objects.filter(is_approved=True).select_related('user')
    # Annotate days left on each approved profile
    for a in approved:
        a.days_remaining = a.days_left()
        a.expired = a.is_access_expired()
    return render(request, 'pending_admins.html', {
        'pending':  pending,
        'approved': approved,
    })



def approve_admin(request, pid):
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "Superadmin access required.")
        return redirect('login')

    try:
        profile = AdminProfile.objects.get(user__id=pid)
        profile.is_approved = True
        profile.access_expires_on = date.today() + timedelta(days=30)
        profile.save()

        user = profile.user
        user.is_staff  = True
        user.is_active = True
        user.save()

        messages.success(request, f"✅ {user.username} approved and can now log in.")
    except AdminProfile.DoesNotExist:
        messages.error(request, "Admin profile not found.")

    return redirect('approve_admins')

def reject_admin(request, pid):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('home')
    try:
        profile = AdminProfile.objects.get(user__id=pid)
        user = profile.user
        profile.delete()
        user.delete()
        messages.success(request, f"Admin removed.")
    except AdminProfile.DoesNotExist:
        messages.error(request, "Not found.")
    return redirect('approve_admins')

def renew_admin(request, pid):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('home')
    try:
        profile = AdminProfile.objects.get(user__id=pid)
        today = date.today()
        # Extend from current expiry if still active, else from today
        base = profile.access_expires_on if (profile.access_expires_on and profile.access_expires_on > today) else today
        profile.access_expires_on = base + timedelta(days=30)
        # Reactivate if was expired
        profile.is_approved = True
        profile.user.is_staff  = True
        profile.user.is_active = True
        profile.user.save()
        profile.save()
        messages.success(request, f"🔄 {profile.user.username} renewed — access until {profile.access_expires_on}.")
    except AdminProfile.DoesNotExist:
        messages.error(request, "Admin not found.")
    return redirect('approve_admins')


# ─────────────────────────────────────────────────────────
# ENQUIRY
# ─────────────────────────────────────────────────────────

def Add_Enquiry(request):
    if not request.user.is_staff:
        return redirect('login')
    error = ""
    if request.method == 'POST':
        try:
            Enquiry.objects.create(
                user=request.user,
                name=request.POST['name'],
                contact=request.POST['contact'],
                email=request.POST['emailid'],
                age=request.POST['age'],
                gender=request.POST['gender']
            )
            error = "no"
        except Exception as e:
            print("Add_Enquiry error:", e)
            error = "yes"
    return render(request, 'add_enquiry.html', {'error': error})


def View_Enquiry(request):
    if not request.user.is_staff:
        return redirect('login')
    enq = Enquiry.objects.filter(user=request.user)
    return render(request, 'view_enquiry.html', {'enq': enq})


def Delete_Enquiry(request, pid):
    if not request.user.is_staff:
        return redirect('login')
    enq = get_object_or_404(Enquiry, id=pid, user=request.user)
    enq.delete()
    return redirect('view_enquiry')


# ─────────────────────────────────────────────────────────
# EQUIPMENT
# ─────────────────────────────────────────────────────────

def Add_Equipment(request):
    if not request.user.is_staff:
        return redirect('login')
    error = ""
    if request.method == 'POST':
        try:
            Equipment.objects.create(
                user=request.user,
                name=request.POST['name'],
                price=request.POST['price'],
                unit=request.POST['unit'],
                date=request.POST['date'],
                description=request.POST['description']
            )
            error = "no"
        except Exception as e:
            print("Add_Equipment error:", e)
            error = "yes"
    return render(request, 'add_equipment.html', {'error': error})


def View_Equipment(request):
    if not request.user.is_staff:
        return redirect('login')
    equipment = Equipment.objects.filter(user=request.user)
    return render(request, 'view_equipment.html', {'equipment': equipment})


def Delete_Equipment(request, pid):
    if not request.user.is_staff:
        return redirect('login')
    equipment = get_object_or_404(Equipment, id=pid, user=request.user)
    equipment.delete()
    return redirect('view_equipment')


# ─────────────────────────────────────────────────────────
# PLAN
# ─────────────────────────────────────────────────────────

def Add_Plan(request):
    if not request.user.is_staff:
        return redirect('login')
    error = ""
    if request.method == 'POST':
        try:
            Plan.objects.create(
                user=request.user,
                name=request.POST.get('name'),
                amount=int(request.POST.get('amount')),
                duration=request.POST.get('duration'),
                description=request.POST.get('description')
            )
            error = "no"
        except Exception as e:
            print("Add_Plan error:", e)
            error = "yes"
    return render(request, 'add_plan.html', {'error': error})


def View_Plan(request):
    if not request.user.is_staff:
        return redirect('login')
    plans = Plan.objects.filter(user=request.user)
    return render(request, 'view_plan.html', {'plans': plans})


def Delete_Plan(request, pid):
    if not request.user.is_staff:
        return redirect('login')
    plan = get_object_or_404(Plan, id=pid, user=request.user)
    plan.delete()
    return redirect('view_plan')


# ─────────────────────────────────────────────────────────
# MEMBER
# ─────────────────────────────────────────────────────────

def Add_Member(request):
    if not request.user.is_staff:
        return redirect('login')

    error = ""
    plans = Plan.objects.filter(user=request.user)

    if request.method == 'POST':
        try:
            name = request.POST['name']
            email = request.POST['email']
            plan_id = request.POST['plan']
            joindate = datetime.strptime(request.POST.get('joindate'), "%Y-%m-%d").date()
            expiredate = datetime.strptime(request.POST.get('expiredate'), "%Y-%m-%d").date()
            plan_obj = Plan.objects.get(id=plan_id)

            base_username = name.lower().replace(" ", "_")
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            temp_password = "member@123"
            new_user = User.objects.create_user(username=username, email=email, password=temp_password)
            new_user.is_staff = False
            new_user.save()

            Member.objects.create(
                user=request.user,
                member_user=new_user,
                role="MEMBER",
                name=name,
                email=email,
                contact=request.POST.get('contact'),
                age=request.POST.get('age'),
                gender=request.POST.get('gender'),
                plan=plan_obj,
                joining_date=joindate,
                expiry_date=expiredate,
                initial_amount=int(request.POST.get('initialamount')),
                height=request.POST.get('height') or None,
                weight=request.POST.get('weight') or None,
                goal_weight=request.POST.get('goal_weight') or None,
                health_issue=request.POST.get('health_issue') or "",
                first_login=True
            )

            messages.success(request, f"Member '{name}' added! Temp password: {temp_password}")
            error = "no"
        except Exception as e:
            print("Add_Member error:", e)
            messages.error(request, f"Something went wrong: {str(e)}")
            error = "yes"

    return render(request, 'add_member.html', {'error': error, 'plan': plans})


def View_Member(request):
    if not request.user.is_staff:
        return redirect('login')

    today = date.today()
    members = Member.objects.filter(user=request.user)

    for member in members:
        member.days_left = max((member.expiry_date - today).days, 0)
        member.status = "Expired" if member.expiry_date < today else "Active"

    context = {
        'members': members,
        'active_count': sum(1 for m in members if m.status == "Active"),
        'expired_count': sum(1 for m in members if m.status == "Expired"),
        'total_count': members.count(),
    }
    return render(request, 'view_member.html', context)


def Delete_Member(request, pid):
    if not request.user.is_staff:
        return redirect('login')
    try:
        member = get_object_or_404(Member, id=pid, user=request.user)
        if member.member_user:
            member.member_user.delete()
        member.delete()
        messages.success(request, f"Member '{member.name}' deleted.")
    except Exception as e:
        print("Delete_Member error:", e)
        messages.error(request, f"Error deleting member: {e}")
    return redirect('view_member')


def Edit_Member(request, pid):
    if not request.user.is_staff:
        return redirect('login')

    member = get_object_or_404(Member, id=pid, user=request.user)
    plans = Plan.objects.filter(user=request.user)

    if request.method == 'POST':
        try:
            member.plan = Plan.objects.get(id=request.POST['plan'])
            member.joining_date = request.POST['joindate']
            member.expiry_date = request.POST['expiredate']
            member.initial_amount = int(request.POST['initialamount'])
            member.status = "Active"
            member.save()
            messages.success(request, f"{member.name}'s membership renewed successfully!")
            return redirect('view_member')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'edit_member.html', {'member': member, 'plan': plans})


# ─────────────────────────────────────────────────────────
# AI PLAN
# ─────────────────────────────────────────────────────────

def generate_ai_plan(request, pid):
    member = get_object_or_404(Member, id=pid)

    age = member.age or 25
    weight = float(member.weight or 60)
    height_m = float(member.height or 170) / 100
    goal_weight = float(member.goal_weight or weight)
    activity = (member.activity_level or "moderate").lower()

    try:
        bmi = round(weight / (height_m ** 2), 2)
    except:
        bmi = 0

    if bmi >= 25:
        bmi_status, bmi_class = "Overweight", "danger"
    elif bmi >= 18.5:
        bmi_status, bmi_class = "Normal", "success"
    else:
        bmi_status, bmi_class = "Underweight", "warning"

    if goal_weight > weight:
        goal = "weight_gain"
    elif goal_weight < weight:
        goal = "weight_loss"
    else:
        goal = "muscle_build"

    base_calories = 22 * weight
    if activity == "high":
        calories = base_calories * 1.5
    elif activity == "low":
        calories = base_calories * 1.2
    else:
        calories = base_calories * 1.35

    if goal == "weight_loss":
        calories -= 400
    elif goal == "weight_gain":
        calories += 400
    calories = int(calories)

    if goal == "weight_loss":
        workout = f"\n🏃 FAT LOSS PROGRAM (Age {age})\n• Cardio: 25 min treadmill daily\n• HIIT: 3 days/week\n• Strength: Full body (3×12 reps)\n• Steps target: 8,000/day\n"
        diet = f"\n🥗 FAT LOSS DIET (~{calories} kcal)\n• High protein (eggs, paneer, dal)\n• Oats + vegetables\n• Avoid sugar & fried food\n• 3L water daily\n"
    elif goal == "weight_gain":
        workout = f"\n🍽️ WEIGHT GAIN PROGRAM (Age {age})\n• Heavy compound lifts (5×5)\n• Chest/Back/Leg split\n• Rest between sets: 90 sec\n• Minimal cardio (5–10 min warm-up)\n"
        diet = f"\n🍛 WEIGHT GAIN DIET (~{calories} kcal)\n• Milk, banana, peanut butter\n• Rice + potato + ghee\n• 5 meals/day\n• Protein shake after workout\n"
    else:
        workout = f"\n💪 MUSCLE BUILD PROGRAM (Age {age})\n• Push/Pull/Leg split\n• Progressive overload weekly\n• Protein timing post-workout\n• Core training 3×/week\n"
        diet = f"\n🥗 MUSCLE BUILD DIET (~{calories} kcal)\n• Protein: 1.6g × body weight\n• Chicken/paneer/soybean\n• Complex carbs + healthy fats\n• Post-workout carbs mandatory\n"

    member.ai_workout_plan = workout
    member.ai_diet_plan = diet
    member.save()

    return render(request, 'show_ai_plan.html', {
        'member': member,
        'bmi': bmi,
        'bmi_status': bmi_status,
        'bmi_class': bmi_class
    })


# ─────────────────────────────────────────────────────────
# MEMBER PORTAL
# ─────────────────────────────────────────────────────────

def member_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None and not user.is_staff:
            login(request, user)
            member = Member.objects.filter(member_user=user).first()

            if member and member.first_login:
                return redirect("set_member_password")
            if member and member.role and member.role.upper() == "TRAINER":
                return redirect("trainer_dashboard")
            return redirect("member_dashboard")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "member_login.html")


@login_required(login_url='member_login')
def set_member_password(request):
    member = Member.objects.filter(member_user=request.user).first()

    if request.method == 'POST':
        pwd1 = request.POST.get('password1', '').strip()
        pwd2 = request.POST.get('password2', '').strip()

        if not pwd1 or not pwd2:
            messages.error(request, "Please enter both password fields.")
        elif pwd1 != pwd2:
            messages.error(request, "Passwords do not match.")
        elif len(pwd1) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
        else:
            user = request.user
            user.set_password(pwd1)
            user.save()
            if member:
                member.first_login = False
                member.save()
            login(request, user)
            messages.success(request, "Password set successfully!")
            return redirect('member_dashboard')

    return render(request, 'set_member_password.html')


@login_required(login_url='/member_login/')
def member_dashboard(request):
    if request.user.is_staff:
        return redirect('home')

    member, created = Member.objects.get_or_create(
        member_user=request.user,
        defaults={
            'user': request.user,
            'name': request.user.username,
            'email': request.user.email or f"{request.user.username}@example.com",
            'contact': '', 'age': 0, 'gender': '',
        }
    )

    if request.method == "POST" and 'profile_image' in request.FILES:
        member.profile_image = request.FILES['profile_image']
        member.save()

    expiry = member.expiry_date
    if isinstance(expiry, datetime):
        expiry = expiry.date()
    days_left = max((expiry - date.today()).days, 0) if expiry else 0

    attendance_records = Attendance.objects.filter(member=member).order_by('-date')
    attendance_dates = [a.date for a in attendance_records]
    attendance_count = attendance_records.count()

    streak = 0
    check = date.today()
    date_set = set(attendance_dates)
    while check in date_set:
        streak += 1
        check = check - timedelta(days=1)

    return render(request, 'member_dashboard.html', {
        'member': member,
        'days_left': days_left,
        'attendance_dates': attendance_dates,
        'attendance_count': attendance_count,
        'streak': streak,
    })


def Member_Logout(request):
    logout(request)
    return redirect('homepage')


@login_required(login_url='member_login')
def trainer_dashboard(request):
    member = Member.objects.filter(member_user=request.user).first()
    if not member or member.role != "TRAINER":
        return redirect('member_dashboard')
    assigned_members = Member.objects.filter(role="MEMBER")
    return render(request, 'trainer_dashboard.html', {
        'trainer': member,
        'members': assigned_members
    })


# ─────────────────────────────────────────────────────────
# ATTENDANCE
# ─────────────────────────────────────────────────────────

def attendance(request):
    if not request.user.is_staff:
        return redirect('login')
    members = Member.objects.filter(user=request.user)
    return render(request, 'attendance.html', {'members': members})


def mark_attendance(request, id):
    if not request.user.is_staff:
        return redirect('login')
    member = get_object_or_404(Member, id=id, user=request.user)
    today = date.today()
    if not Attendance.objects.filter(member=member, date=today).exists():
        Attendance.objects.create(member=member, date=today, status='Present')
        messages.success(request, f"Attendance marked for {member.name}!")
    else:
        messages.warning(request, f"Attendance already marked for {member.name} today.")
    return redirect('attendance')


def view_attendance(request):
    if not request.user.is_staff:
        return redirect('login')

    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    selected_member_id = request.GET.get('member_id')
    page_number = request.GET.get('page')
    today = timezone.localdate()

    members = Member.objects.filter(user=request.user).order_by('name')

    if search:
        members = members.filter(
            Q(name__icontains=search) |
            Q(contact__icontains=search) |
            Q(email__icontains=search)
        )
    if status == 'active':
        members = members.filter(expiry_date__gte=today)
    elif status == 'expired':
        members = members.filter(expiry_date__lt=today)

    paginator = Paginator(members, 25)
    members = paginator.get_page(page_number)

    attendance = Attendance.objects.none()
    if selected_member_id:
        attendance = Attendance.objects.filter(
            member_id=selected_member_id,
            member__user=request.user
        ).select_related('member').order_by('-date', '-id')

    return render(request, 'view_attendance.html', {
        'members': members,
        'attendance': attendance,
        'selected_member_id': selected_member_id,
        'today': today,
        'search': search,
        'status': status,
    })


# ─────────────────────────────────────────────────────────
# PDF DOWNLOADS
# ─────────────────────────────────────────────────────────

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

@login_required
def download_members_pdf(request):
    if not request.user.is_staff:
        return redirect('login')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="members_list.pdf"'
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    members = Member.objects.filter(user=request.user)
    data = [['Name', 'Contact', 'Email', 'Age', 'Plan']]
    for member in members:
        data.append([member.name, member.contact, member.email, str(member.age), str(member.plan)])
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    doc.build(elements)
    return response


@login_required
def download_enquiry_pdf(request):
    if not request.user.is_staff:
        return redirect('login')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="enquiry_list.pdf"'
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    enquiries = Enquiry.objects.filter(user=request.user)
    data = [['Name', 'Contact', 'Email', 'Age', 'Gender']]
    for enquiry in enquiries:
        data.append([enquiry.name, enquiry.contact, enquiry.email, str(enquiry.age), enquiry.gender])
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    doc.build(elements)
    return response