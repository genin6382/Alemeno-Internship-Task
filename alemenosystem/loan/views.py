from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Max
from django.utils import timezone
from decimal import Decimal
import datetime

from .models import Loan
from customer.models import Customer
from .serializers import (
    LoanRequestSerializer, 
    LoanEligibilityResponseSerializer,
    CreateLoanResponseSerializer
)

class LoanEligibilityView(APIView):
    """API View for checking loan eligibility"""
    
    def calculate_credit_score(self, customer):
        """
        Calculate credit score based on historical loan data
        """
        loans = Loan.objects.filter(customer=customer)
        
        if not loans.exists():
            return 0  # No loan history
        
        # Check if sum of current loans > approved limit
        current_loans_sum = loans.filter(
            end_date__gte=timezone.now().date()
        ).aggregate(
            total=Sum('loan_amount')
        )['total'] or 0
        
        if current_loans_sum > customer.approved_limit:
            return 0
        
        credit_score = 0
        
        # 1. Past Loans paid on time (30 points max)
        total_loans = loans.count()
        if total_loans > 0:
            total_emis_expected = loans.aggregate(Sum('tenure'))['tenure__sum'] or 0
            total_emis_paid_on_time = loans.aggregate(Sum('emis_paid_on_time'))['emis_paid_on_time__sum'] or 0
            
            if total_emis_expected > 0:
                payment_ratio = total_emis_paid_on_time / total_emis_expected
                credit_score += min(30, payment_ratio * 30)
        
        # 2. Number of loans taken in past (20 points max, diminishing returns after 5 loans)
        if total_loans <= 5:
            credit_score += min(20, total_loans * 4)
        else:
            credit_score += 20 - ((total_loans - 5) * 2)  # Penalty for too many loans
        
        # 3. Loan activity in current year (25 points max)
        current_year = timezone.now().year
        current_year_loans = loans.filter(start_date__year=current_year).count()
        if current_year_loans > 0:
            credit_score += min(25, current_year_loans * 8)
        
        # 4. Loan approved volume vs salary ratio (25 points max)
        total_approved_amount = loans.aggregate(Sum('loan_amount'))['loan_amount__sum'] or 0
        if customer.monthly_salary > 0:
            approval_ratio = total_approved_amount / (customer.monthly_salary * 12)  # Annual salary
            if approval_ratio <= 5:  # Good ratio
                credit_score += 25
            elif approval_ratio <= 10:  # Moderate ratio
                credit_score += 15
            elif approval_ratio <= 15:  # High ratio
                credit_score += 5
        
        return min(100, max(0, credit_score))
    
    def calculate_monthly_installment(self, loan_amount, interest_rate, tenure):
        """Calculate monthly installment using EMI formula"""
        P = float(loan_amount)
        r = float(interest_rate) / (12 * 100)  # Monthly interest rate
        n = int(tenure)
        
        if r == 0:
            return P / n
        
        emi = P * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
        return round(emi, 2)
    
    def get_corrected_interest_rate(self, credit_score, requested_rate):
        """Get corrected interest rate based on credit score"""
        if credit_score > 50:
            return requested_rate  # No minimum restriction for high scores
        elif credit_score > 30:
            return max(requested_rate, 12.0)
        elif credit_score > 10:
            return max(requested_rate, 16.0)
        else:
            return requested_rate  # Will be rejected anyway

    def determine_approval(self, credit_score, requested_rate):
        """Determine approval and corrected interest rate based on credit score"""
        if credit_score > 50:
            return True, requested_rate
        elif credit_score > 30:
            corrected_rate = max(requested_rate, 12.0)
            return True, corrected_rate
        elif credit_score > 10:
            corrected_rate = max(requested_rate, 16.0)
            return True, corrected_rate
        else:
            return False, requested_rate
    
    def post(self, request):
        """Check loan eligibility for a customer"""
        serializer = LoanRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        customer_id = data['customer_id']
        loan_amount = data['loan_amount']
        interest_rate = data['interest_rate']
        tenure = data['tenure']
        
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate credit score
        credit_score = self.calculate_credit_score(customer)
        
        # Determine approval and corrected interest rate
        approval, corrected_interest_rate = self.determine_approval(credit_score, interest_rate)
        
        # Check EMI to salary ratio (50% rule)
        monthly_installment = 0
        if approval:
            # Get current EMIs
            current_emis = Loan.objects.filter(
                customer=customer,
                end_date__gte=timezone.now().date()
            ).aggregate(
                total_emi=Sum('monthly_installment')
            )['total_emi'] or 0
            
            # Calculate new EMI
            new_emi = self.calculate_monthly_installment(
                loan_amount, corrected_interest_rate, tenure
            )
            
            total_emi = float(current_emis) + new_emi
            
            # Check if total EMI exceeds 50% of monthly salary
            if total_emi > (customer.monthly_salary * 0.5):
                approval = False
            else:
                monthly_installment = new_emi
        
        response_data = {
            'customer_id': customer_id,
            'approval': approval,
            'interest_rate': interest_rate,
            'corrected_interest_rate': corrected_interest_rate,
            'tenure': tenure,
            'monthly_installment': monthly_installment
        }
        
        response_serializer = LoanEligibilityResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        return Response(response_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateLoanView(APIView):
    """API View for creating/processing new loans"""
    
    def calculate_credit_score(self, customer):
        """
        Calculate credit score based on historical loan data
        """
        loans = Loan.objects.filter(customer=customer)
        
        if not loans.exists():
            return 0  # No loan history
        
        # Check if sum of current loans > approved limit
        current_loans_sum = loans.filter(
            end_date__gte=timezone.now().date()
        ).aggregate(
            total=Sum('loan_amount')
        )['total'] or 0
        
        if current_loans_sum > customer.approved_limit:
            return 0
        
        credit_score = 0
        
        # 1. Past Loans paid on time (30 points max)
        total_loans = loans.count()
        if total_loans > 0:
            total_emis_expected = loans.aggregate(Sum('tenure'))['tenure__sum'] or 0
            total_emis_paid_on_time = loans.aggregate(Sum('emis_paid_on_time'))['emis_paid_on_time__sum'] or 0
            
            if total_emis_expected > 0:
                payment_ratio = total_emis_paid_on_time / total_emis_expected
                credit_score += min(30, payment_ratio * 30)
        
        # 2. Number of loans taken in past (20 points max, diminishing returns after 5 loans)
        if total_loans <= 5:
            credit_score += min(20, total_loans * 4)
        else:
            credit_score += 20 - ((total_loans - 5) * 2)  # Penalty for too many loans
        
        # 3. Loan activity in current year (25 points max)
        current_year = timezone.now().year
        current_year_loans = loans.filter(start_date__year=current_year).count()
        if current_year_loans > 0:
            credit_score += min(25, current_year_loans * 8)
        
        # 4. Loan approved volume vs salary ratio (25 points max)
        total_approved_amount = loans.aggregate(Sum('loan_amount'))['loan_amount__sum'] or 0
        if customer.monthly_salary > 0:
            approval_ratio = total_approved_amount / (customer.monthly_salary * 12)  # Annual salary
            if approval_ratio <= 5:  # Good ratio
                credit_score += 25
            elif approval_ratio <= 10:  # Moderate ratio
                credit_score += 15
            elif approval_ratio <= 15:  # High ratio
                credit_score += 5
            # No points for very high ratio
        
        return min(100, max(0, credit_score))
    
    def calculate_monthly_installment(self, loan_amount, interest_rate, tenure):
        """Calculate monthly installment using EMI formula"""
        P = float(loan_amount)
        r = float(interest_rate) / (12 * 100)  # Monthly interest rate
        n = int(tenure)
        
        if r == 0:
            return P / n
        
        emi = P * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
        return round(emi, 2)
    
    def determine_approval(self, credit_score, requested_rate):
        """Determine approval and corrected interest rate based on credit score"""
        if credit_score > 50:
            return True, requested_rate
        elif credit_score > 30:
            corrected_rate = max(requested_rate, 12.0)
            return True, corrected_rate
        elif credit_score > 10:
            corrected_rate = max(requested_rate, 16.0)
            return True, corrected_rate
        else:
            return False, requested_rate
    
    def get_next_loan_id(self):
        """Generate next loan ID"""
        max_loan_id = Loan.objects.aggregate(Max('loan_id'))['loan_id__max']
        return (max_loan_id or 0) + 1
    
    def post(self, request):
        """Process a new loan based on eligibility"""
        serializer = LoanRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        customer_id = data['customer_id']
        loan_amount = data['loan_amount']
        interest_rate = data['interest_rate']
        tenure = data['tenure']
        
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            response_data = {
                'loan_id': None,
                'customer_id': customer_id,
                'loan_approved': False,
                'message': "Customer not found",
                'monthly_installment': 0.0
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        
        # Calculate credit score
        credit_score = self.calculate_credit_score(customer)
        
        # Determine approval and corrected interest rate
        approval, corrected_interest_rate = self.determine_approval(credit_score, interest_rate)
        
        message = ""
        monthly_installment = 0.0
        loan_id = None
        
        if not approval:
            if credit_score <= 10:
                message = "Loan not approved due to low credit score"
            else:
                message = "Loan not approved"
        else:
            # Check EMI to salary ratio (50% rule)
            current_emis = Loan.objects.filter(
                customer=customer,
                end_date__gte=timezone.now().date()
            ).aggregate(
                total_emi=Sum('monthly_installment')
            )['total_emi'] or 0
            
            # Calculate new EMI
            new_emi = self.calculate_monthly_installment(
                loan_amount, corrected_interest_rate, tenure
            )
            
            total_emi = float(current_emis) + new_emi
            
            # Check if total EMI exceeds 50% of monthly salary
            if total_emi > (customer.monthly_salary * 0.5):
                approval = False
                message = "Loan not approved due to high EMI to salary ratio (exceeds 50%)"
            else:
                # Create the loan
                loan_id = self.get_next_loan_id()
                start_date = timezone.now().date()
                end_date = start_date + datetime.timedelta(days=tenure*30)  # Approximate
                
                loan = Loan.objects.create(
                    loan_id=loan_id,
                    customer=customer,
                    loan_amount=Decimal(str(loan_amount)),
                    tenure=tenure,
                    interest_rate=Decimal(str(corrected_interest_rate)),
                    monthly_installment=Decimal(str(new_emi)),
                    emis_paid_on_time=0,
                    start_date=start_date,
                    end_date=end_date
                )
                
                monthly_installment = new_emi
                message = "Loan approved successfully"
                if corrected_interest_rate != interest_rate:
                    message += f" with corrected interest rate of {corrected_interest_rate}%"
        
        response_data = {
            'loan_id': loan_id,
            'customer_id': customer_id,
            'loan_approved': approval,
            'message': message,
            'monthly_installment': monthly_installment
        }
        
        response_serializer = CreateLoanResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        return Response(response_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)