from django.urls import path
from . import views
from .views import api_swap_calorie, save_survey, api_generate_plan

urlpatterns = [
    path('', views.landing_page, name='landing_page'),

    path('bat-dau/', views.main_views, name ='main_views'), 
    path("api/save-survey/", save_survey, name="save_survey"),

    path('weekly-plan-generator/', views.weekly_plan_generator_view, name='weekly_plan_generator'),
    path("api/weekly-plan/", api_generate_plan, name="api_generate_plan"),

    path('goal-translator/', views.goal_translator, name='goal_translator'),
    path("api/goal-translator/", views.api_goal_translator, name="api_goal_translator"),

    path('class-picker/', views.class_picker, name='class_picker'),
    path('what-if-coach/', views.what_if_coach, name='what_if_coach'),

    path('calorie-swap/', views.calorie_swap, name='calorie_swap'),
    path('api/swap-calorie/', api_swap_calorie, name="api_swap_calorie")
]
