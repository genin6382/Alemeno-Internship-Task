from .views import CustomerViewSet
from django.urls import path 


url_patterns = [
    path('register/', CustomerViewSet.as_view({'post': 'create'}), name='customer-register'),
]