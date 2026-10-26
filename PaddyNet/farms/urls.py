from django.urls import path
from farms import views

urlpatterns = [
    path('dashboard/', views.farmer_dashboard, name='farmer_dashboard'),
    path('fields/', views.field_list, name='field_list'),
    path('fields/add/', views.field_create, name='field_create'),
    path('fields/<int:field_id>/', views.field_detail, name='field_detail'),
    path('fields/<int:field_id>/edit/', views.field_edit, name='field_edit'),
    path('fields/<int:field_id>/delete/', views.field_delete, name='field_delete'),
    path('fields/<int:field_id>/statistics/', views.field_statistics, name='field_statistics_detail'),
    path('statistics/', views.field_statistics, name='field_statistics'),
    path('activities/<int:activity_id>/delete/', views.activity_delete, name='activity_delete'),
    path('notifications/', views.farmer_notifications, name='farmer_notifications'),
    path('bills/', views.farmer_bills, name='farmer_bills'),
    path('bills/<int:bill_id>/pay/', views.farmer_pay_bill, name='farmer_pay_bill'),
    path('bills/<int:bill_id>/dispute/', views.farmer_raise_dispute, name='farmer_raise_dispute'),
    path('bids/', views.farmer_bids, name='farmer_bids'),
    path('bids/<int:bid_id>/respond/', views.farmer_respond_bid, name='farmer_respond_bid'),
    path('harvest-yield-report/pdf/', views.farmer_harvest_yield_pdf, name='farmer_harvest_yield_pdf'),
]

