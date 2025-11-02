from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('bat-dau/', views.main_views, name ='main_views'),
    path('save-survey/', views.save_survey, name='save_survey'),
    path('tod   ay_calories/', views.today_calories, name='today_calories'),
    path('goal_plan/', views.goal_plan, name='goal_plan'),
    path('daily/<str:day_name>/', views.daily_detail, name='daily_detail'),
]
