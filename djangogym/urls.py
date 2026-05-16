# djangogym/urls.py

from django.contrib import admin
from django.urls import path
from djangogym1 import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Home
    path('', views.HomePage, name='homepage'),
    path('admin/', admin.site.urls),

    # Admin Auth
    path('login/', views.Login, name='login'),
    path('logout/', views.Logout_admin, name='logout'),
    path('register/', views.register_admin, name='register'),
    path('home/', views.Index, name='home'),

    # Static Pages
    path('about/', views.About, name='about'),
    path('contact/', views.Contact, name='contact'),

    # Forgot Password Flow
    path('forgot_password/', views.ForgotPassword_Request, name='forgot_password_request'),
    path('verify_otp/', views.Verify_OTP, name='verify_otp'),
    path('change_password/', views.ChangePassword_Final, name='change_password_final'),

    # Superadmin Approval — ONE consistent set of URLs
    path('approve-admins/', views.pending_admins, name='approve_admins'),
    path('approve-admin/<int:pid>/', views.approve_admin, name='approve_admin'),
    path('reject-admin/<int:pid>/', views.reject_admin, name='reject_admin'),
    path('renew-admin/<int:pid>/', views.renew_admin, name='renew_admin'),
    
    # Enquiry
    path('add_enquiry/', views.Add_Enquiry, name='add_enquiry'),
    path('view_enquiry/', views.View_Enquiry, name='view_enquiry'),
    path('delete_enquiry/<int:pid>/', views.Delete_Enquiry, name='delete_enquiry'),

    # Equipment
    path('add_equipment/', views.Add_Equipment, name='add_equipment'),
    path('view_equipment/', views.View_Equipment, name='view_equipment'),
    path('delete_equipment/<int:pid>/', views.Delete_Equipment, name='delete_equipment'),

    # Plan
    path('add_plan/', views.Add_Plan, name='add_plan'),
    path('view_plan/', views.View_Plan, name='view_plan'),
    path('delete_plan/<int:pid>/', views.Delete_Plan, name='delete_plan'),

    # Member Management (Admin side)
    path('add_member/', views.Add_Member, name='add_member'),
    path('view_member/', views.View_Member, name='view_member'),
    path('delete_member/<int:pid>/', views.Delete_Member, name='delete_member'),
    path('edit_member/<int:pid>/', views.Edit_Member, name='edit_member'),
    path('generate_ai_plan/<int:pid>/', views.generate_ai_plan, name='generate_ai_plan'),

    # PDF Downloads
    path('download-members/', views.download_members_pdf, name='download_members_pdf'),
    path('download-enquiry/', views.download_enquiry_pdf, name='download_enquiry_pdf'),

    # Member Portal (Member side)
    path('member_login/', views.member_login, name='member_login'),
    path('member_dashboard/', views.member_dashboard, name='member_dashboard'),
    path('member_logout/', views.Member_Logout, name='member_logout'),
    path('set_member_password/', views.set_member_password, name='set_member_password'),

    # Trainer
    path('trainer-dashboard/', views.trainer_dashboard, name='trainer_dashboard'),

    # Attendance
    path('attendance/', views.attendance, name='attendance'),
    path('view_attendance/', views.view_attendance, name='view_attendance'),
    path('mark_attendance/<int:id>/', views.mark_attendance, name='mark_attendance'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)