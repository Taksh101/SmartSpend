from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('signup/', views.signup_view, name='signup'),  
    path('login/', views.login_view, name='login'),
    path('home/', views.home, name='home'),
    path('logout/', views.logout_view, name='logout'),
    path('add-expense/', views.add_expense, name='add_expense'),
    path('manage-expense/', views.manage_expense, name='manage_expense'),
    path('insights/', views.insights, name='insights'),
    path('download-report/', views.download_report, name='download_report'),
    path("generate_pdf/", views.generate_pdf, name="generate_pdf"),
]