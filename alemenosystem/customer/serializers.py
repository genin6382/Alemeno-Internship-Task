# serializers.py
from rest_framework import serializers
from .models import Customer
import re


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for customer registration with input validation
    """
    first_name = serializers.CharField(
        max_length=15,
        required=True,
        error_messages={
            'required': 'First name is required.',
            'max_length': 'First name cannot exceed 15 characters.'
        }
    )
    last_name = serializers.CharField(
        max_length=15,
        required=True,
        error_messages={
            'required': 'Last name is required.',
            'max_length': 'Last name cannot exceed 15 characters.'
        }
    )
    age = serializers.IntegerField(
        min_value=18,
        max_value=100,
        required=True,
        error_messages={
            'required': 'Age is required.',
            'min_value': 'Age must be at least 18 years.',
            'max_value': 'Age cannot exceed 100 years.'
        }
    )
    monthly_income = serializers.IntegerField(
        min_value=1,
        required=True,
        error_messages={
            'required': 'Monthly income is required.',
            'min_value': 'Monthly income must be greater than 0.'
        }
    )
    phone_number = serializers.CharField(
        max_length=15,
        min_length=10,
        required=True,
        error_messages={
            'required': 'Phone number is required.',
            'max_length': 'Phone number cannot exceed 15 characters.',
            'min_length': 'Phone number must be at least 10 digits.'
        }
    )

    class Meta:
        model = Customer
        fields = ['first_name', 'last_name', 'age', 'monthly_income', 'phone_number']

    def validate_phone_number(self, value):
        # Remove any spaces or special characters
        phone_clean = re.sub(r'[^\d]', '', value)
        
        if len(phone_clean) < 10 or len(phone_clean) > 15:
            raise serializers.ValidationError("Phone number must be between 10 and 15 digits.")
        
        if not phone_clean.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        
        return phone_clean

    def validate_first_name(self, value):
        # Validate first name contains only alphabetic characters and spaces
        if not re.match(r'^[a-zA-Z\s]+', value):
            raise serializers.ValidationError("First name must contain only alphabetic characters and spaces.")
        return value.strip().title()

    def validate_last_name(self, value):
        # Validate last name contains only alphabetic characters and spaces
        if not re.match(r'^[a-zA-Z\s]+', value):
            raise serializers.ValidationError("Last name must contain only alphabetic characters and spaces.")
        return value.strip().title()


class CustomerResponseSerializer(serializers.ModelSerializer):
    """
    Serializer for customer response data
    """
    name = serializers.CharField(read_only=True)
    monthly_income = serializers.IntegerField(source='monthly_salary', read_only=True)

    class Meta:
        model = Customer
        fields = [
            'customer_id', 
            'name', 
            'age', 
            'monthly_income', 
            'approved_limit', 
            'phone_number'
        ]
        read_only_fields = ['customer_id', 'name', 'approved_limit']