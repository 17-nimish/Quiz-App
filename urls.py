"""
URL configuration for quiz_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from core import views
from core.views import admin_dashboard

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Custom Admin Dashboard
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/download-users-csv/', views.download_users_csv, name='download_users_csv'),

    # Authentication
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Quizzes
    path('category/<int:category_id>/', views.category_quizzes, name='category_quizzes'),
    path('quiz/<int:quiz_id>/start/', views.start_quiz, name='start_quiz'),
    path("quiz/attempt/<int:quiz_id>/", views.attempt_quiz, name="attempt_quiz"),
    path('quiz/result/', views.quiz_result, name='quiz_result'),
    path('my-attempts/', views.my_attempts, name='my_attempts'),

    # Admin - Quiz Management (moved under dashboard/)
    path('dashboard/quizzes/', views.admin_manage_quizzes, name='admin_manage_quizzes'),
    path('dashboard/quizzes/add/', views.admin_add_quiz, name='admin_add_quiz'),
    path('dashboard/quizzes/edit/<int:quiz_id>/', views.admin_edit_quiz, name='admin_edit_quiz'),
    path('dashboard/quizzes/delete/<int:quiz_id>/', views.admin_delete_quiz, name='admin_delete_quiz'),
    path('dashboard/quizzes/upload_csv/', views.upload_quizzes_csv, name='upload_quizzes_csv'),
]
