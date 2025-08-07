from rest_framework import serializers
from .models import Loan
from customer.models import Customer


class LoanRequestSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.FloatField()
    interest_rate = serializers.FloatField()
    tenure = serializers.IntegerField()

    def validate_customer_id(self, value):
        """Validate that customer exists"""
        try:
            Customer.objects.get(customer_id=value)
        except Customer.DoesNotExist:
            raise serializers.ValidationError("Customer with this ID does not exist.")
        return value

    def validate_loan_amount(self, value):
        """Validate loan amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Loan amount must be greater than 0.")
        return value

    def validate_interest_rate(self, value):
        """Validate interest rate is positive"""
        if value < 0:
            raise serializers.ValidationError("Interest rate must be non-negative.")
        return value

    def validate_tenure(self, value):
        """Validate tenure is positive"""
        if value <= 0:
            raise serializers.ValidationError("Tenure must be greater than 0 months.")
        return value


class LoanEligibilityResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.FloatField()
    corrected_interest_rate = serializers.FloatField()
    tenure = serializers.IntegerField()
    monthly_installment = serializers.FloatField()


class CreateLoanResponseSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField(allow_null=True)
    customer_id = serializers.IntegerField()
    loan_approved = serializers.BooleanField()
    message = serializers.CharField()
    monthly_installment = serializers.FloatField()