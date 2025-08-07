from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta
from django.urls import reverse
from customer.models import Customer
from .models import Loan
"""UNIT TESTS FOR LOAN APPLICATION VIEWS"""

class LoanViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.customer1 = Customer.objects.create(
            customer_id=1,
            first_name="John",
            last_name="Doe",
            age=30,
            phone_number="9999999999",
            monthly_salary=50000,
            approved_limit=1000000,
            current_debt=0
        )

        self.customer2 = Customer.objects.create(
            customer_id=2,
            first_name="Jane",
            last_name="Smith",
            age=25,
            phone_number="8888888888",
            monthly_salary=30000,
            approved_limit=500000,
            current_debt=100000
        )

        self.loan1 = Loan.objects.create(
            loan_id=1,
            customer=self.customer1,
            loan_amount=100000,
            tenure=12,
            interest_rate=10.0,
            monthly_installment=8791.59,
            emis_paid_on_time=5,
            start_date=date.today() - timedelta(days=150),
            end_date=date.today() + timedelta(days=215)
        )

""" Test cases for Loan Eligibility, Create Loan, View Loan, and View Loans views """

class LoanEligibilityViewTest(LoanViewTestCase):
    def test_loan_eligibility_success(self):
        data = {
            "customer_id": 1,
            "loan_amount": 50000,
            "interest_rate": 8.0,
            "tenure": 12
        }
        response = self.client.post(reverse('check-eligibility'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('approval', response.data)
        self.assertIn('monthly_installment', response.data)

    def test_loan_eligibility_customer_not_found(self):
        data = {
            "customer_id": 999,
            "loan_amount": 50000,
            "interest_rate": 8.0,
            "tenure": 12
        }
        response = self.client.post(reverse('check-eligibility'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_loan_eligibility_invalid_data(self):
        data = {
            "customer_id": "invalid",
            "loan_amount": -1000
        }
        response = self.client.post(reverse('check-eligibility'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_high_credit_score_approval(self):
        data = {
            "customer_id": 1,
            "loan_amount": 25000,
            "interest_rate": 8.0,
            "tenure": 6
        }
        response = self.client.post(reverse('check-eligibility'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['approval'])


class CreateLoanViewTest(LoanViewTestCase):
    def test_create_loan_success(self):
        data = {
            "customer_id": 1,
            "loan_amount": 25000,
            "interest_rate": 8.0,
            "tenure": 6
        }
        response = self.client.post(reverse('create-loan'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['loan_id'])
        self.assertTrue(response.data['loan_approved'])
        self.assertTrue(Loan.objects.filter(loan_id=response.data['loan_id']).exists())

    def test_create_loan_customer_not_found(self):
        data = {
            "customer_id": 999,
            "loan_amount": 50000,
            "interest_rate": 8.0,
            "tenure": 12
        }
        response = self.client.post(reverse('create-loan'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['loan_approved'])

    def test_create_loan_high_emi_rejection(self):
        data = {
            "customer_id": 1,
            "loan_amount": 500000,
            "interest_rate": 15.0,
            "tenure": 12
        }
        response = self.client.post(reverse('create-loan'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['loan_approved'])
        self.assertIn("EMI to salary ratio", response.data['message'])


class ViewLoanViewTest(LoanViewTestCase):
    def test_view_loan_success(self):
        response = self.client.get(reverse('view-loan', kwargs={'loan_id': self.loan1.loan_id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['loan_id'], self.loan1.loan_id)
        self.assertEqual(response.data['customer']['id'], self.customer1.customer_id)
        self.assertEqual(float(response.data['loan_amount']), float(self.loan1.loan_amount))

    def test_view_loan_not_found(self):
        response = self.client.get(reverse('view-loan', kwargs={'loan_id': 999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ViewLoansViewTest(LoanViewTestCase):
    def test_view_loans_success(self):
        response = self.client.get(reverse('view-loans', kwargs={'customer_id': self.customer1.customer_id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['loan_id'], self.loan1.loan_id)

    def test_view_loans_customer_not_found(self):
        response = self.client.get(reverse('view-loans', kwargs={'customer_id': 999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_view_loans_no_active_loans(self):
        customer3 = Customer.objects.create(
            customer_id=3,
            first_name="Bob",
            last_name="Wilson",
            age=40,
            phone_number="7777777777",
            monthly_salary=60000,
            approved_limit=800000,
            current_debt=0
        )

        Loan.objects.create(
            loan_id=2,
            customer=customer3,
            loan_amount=50000,
            tenure=6,
            interest_rate=12.0,
            monthly_installment=8606.64,
            emis_paid_on_time=6,
            start_date=date.today() - timedelta(days=200),
            end_date=date.today() - timedelta(days=20)
        )

        response = self.client.get(reverse('view-loans', kwargs={'customer_id': customer3.customer_id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class CreditScoreCalculationTest(LoanViewTestCase):
    def test_credit_score_no_history(self):
        from .views import LoanEligibilityView
        view = LoanEligibilityView()
        score = view.calculate_credit_score(self.customer2)
        self.assertEqual(score, 0)

    def test_credit_score_with_history(self):
        from .views import LoanEligibilityView
        view = LoanEligibilityView()
        score = view.calculate_credit_score(self.customer1)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_monthly_installment_calculation(self):
        from .views import LoanEligibilityView
        view = LoanEligibilityView()
        emi = view.calculate_monthly_installment(100000, 10.0, 12)
        self.assertAlmostEqual(emi, 8791.59, places=2)

    def test_interest_rate_correction(self):
        from .views import LoanEligibilityView
        view = LoanEligibilityView()
        approval, rate = view.determine_approval(60, 8.0)
        self.assertTrue(approval)
        self.assertEqual(rate, 8.0)

        approval, rate = view.determine_approval(40, 8.0)
        self.assertTrue(approval)
        self.assertEqual(rate, 12.0)

        approval, rate = view.determine_approval(20, 8.0)
        self.assertTrue(approval)
        self.assertEqual(rate, 16.0)

        approval, rate = view.determine_approval(5, 8.0)
        self.assertFalse(approval)
