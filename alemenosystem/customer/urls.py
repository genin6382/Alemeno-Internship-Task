from .views import CustomerRegistrationViewSet , CustomerListViewSet
from django.urls import path 


urlpatterns = [
    path('', CustomerListViewSet.as_view({'get': 'list'}), name='customer-list'),
    path('<int:pk>/', CustomerListViewSet.as_view({'get': 'retrieve'}), name='customer-detail'),
    path('register/', CustomerRegistrationViewSet.as_view({'post': 'create'}), name='customer-register'),
]