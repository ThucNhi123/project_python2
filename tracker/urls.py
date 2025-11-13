from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('bat-dau/', views.main_views, name ='main_views'), 
    path("save-survey/", views.save_survey, name="save_survey"),

    path('weekly-plan-generator/', views.weekly_plan_generator, name='weekly_plan_generator'),
    path('goal-translator/', views.goal_translator, name='goal_translator'),
    path('class-picker/', views.class_picker, name='class_picker'),
    path('what-if-coach/', views.what_if_coach, name='what_if_coach'),
    path('calorie-swap/', views.calorie_swap, name='calorie_swap'),
]
