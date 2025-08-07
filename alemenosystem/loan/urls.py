from django.urls import path
from .views import LoanEligibilityView, CreateLoanView,ViewLoansView,ViewLoanView

urlpatterns = [
    path('check-eligibility', LoanEligibilityView.as_view(), name='check-eligibility'),
    path('create-loan', CreateLoanView.as_view(), name='create-loan'),
    path('view-loan/<int:loan_id>', ViewLoanView.as_view(), name='view-loan'),
    path('view-loans/<int:customer_id>', ViewLoansView.as_view(), name='view-loans'),
]