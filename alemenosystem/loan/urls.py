from django.urls import path
from .views import LoanEligibilityView, CreateLoanView

urlpatterns = [
    path('check-eligibility', LoanEligibilityView.as_view(), name='check-eligibility'),
    path('create-loan', CreateLoanView.as_view(), name='create-loan'),
]