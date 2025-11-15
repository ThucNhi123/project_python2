from django.urls import path
from . import views

app_name = 'planner'

urlpatterns = [
    path('', views.planner_view, name='planner_home'),
    path('plan/', views.plan_result_view, name='plan_result'),
    path('modify/', views.modify_plan_view, name='modify_plan'),
]