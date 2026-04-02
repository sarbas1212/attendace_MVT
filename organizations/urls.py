from django.urls import path
from . import views

urlpatterns = [
    path('create-order/', views.create_order, name='create_order'),
    path('payment-success/', views.payment_success, name='payment_success'),

]