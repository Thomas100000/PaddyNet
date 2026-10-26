from django.urls import path
from accounts import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_select_view, name='register'),
    path('register/farmer/', views.register_farmer_view, name='register_farmer'),
    path('register/millowner/', views.register_millowner_view, name='register_millowner'),
]
