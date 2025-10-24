from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('today_calories/', views.today_calories, name='today_calories'),
    path('goal_plan/', views.goal_plan, name='goal_plan'),
    path('daily/<str:day_name>/', views.daily_detail, name='daily_detail'),
]
