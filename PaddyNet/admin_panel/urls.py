from django.urls import path
from admin_panel import views

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('farmers/', views.farmer_list_view, name='admin_farmer_list'),
    path('farmers/<int:farmer_id>/', views.farmer_detail_view, name='admin_farmer_detail'),
    path('farmer/<int:farmer_id>/verify/', views.verify_farmer_view, name='verify_farmer'),
    path('farmer/<int:farmer_id>/reject/', views.reject_farmer_view, name='reject_farmer'),
    path('millowner/<int:millowner_id>/verify/', views.verify_millowner_view, name='verify_millowner'),
    path('millowner/<int:millowner_id>/reject/', views.reject_millowner_view, name='reject_millowner'),
    path('bills/', views.bill_management_view, name='admin_bills'),
    path('bills/<int:bill_id>/toggle-status/', views.toggle_bill_status_view, name='toggle_bill_status'),
    path('notifications/post/', views.post_notification_view, name='post_notification'),
]
