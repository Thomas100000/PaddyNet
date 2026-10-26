from django.urls import path
from millowner import views

urlpatterns = [
    path('dashboard/', views.millowner_dashboard, name='millowner_dashboard'),
    path('fields/', views.millowner_field_browse, name='millowner_field_browse'),
    path('fields/<int:field_id>/', views.millowner_field_detail, name='millowner_field_detail'),
    path('bids/', views.millowner_bid_history, name='millowner_bid_history'),
    path('fields/<int:field_id>/harvest-pdf/', views.millowner_field_harvest_pdf, name='millowner_field_harvest_pdf'),
]

