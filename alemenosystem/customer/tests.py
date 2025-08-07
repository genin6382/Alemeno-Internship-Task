# tests.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Customer
import json


class CustomerRegistrationTest(APITestCase):
    """Simple test cases for Customer Registration API"""
    
    def setUp(self):
        self.register_url = reverse('customer-register-list')
        self.valid_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'age': 30,
            'monthly_income': 50000,
            'phone_number': '9876543210'
        }
    
    def test_successful_registration(self):
        """Test successful customer registration"""
        response = self.client.post(self.register_url, self.valid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        
        # Check response fields
        self.assertIn('customer_id', data)
        self.assertEqual(data['name'], 'John Doe')
        self.assertEqual(data['age'], 30)
        self.assertEqual(data['monthly_income'], 50000)
        self.assertEqual(data['approved_limit'], 1800000)  # 36 * 50000
        self.assertEqual(data['phone_number'], 9876543210)
    
    def test_approved_limit_calculation(self):
        """Test approved limit calculation"""
        test_data = self.valid_data.copy()
        test_data['monthly_income'] = 55000
        test_data['phone_number'] = '9876543211'
        
        response = self.client.post(self.register_url, test_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        
        # 36 * 55000 = 1,980,000 → rounded to 2,000,000
        self.assertEqual(data['approved_limit'], 2000000)
    
    def test_duplicate_phone_number(self):
        """Test duplicate phone number validation"""
        # Create first customer
        self.client.post(self.register_url, self.valid_data, format='json')
        
        # Try creating duplicate
        response = self.client.post(self.register_url, self.valid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('error', response.json())
    
    def test_invalid_data(self):
        """Test validation errors"""
        invalid_data = {
            'first_name': '',  # Empty name
            'last_name': 'Doe',
            'age': 17,         # Below 18
            'monthly_income': -1000,  # Negative
            'phone_number': 'invalid'  # Non-numeric
        }
        
        response = self.client.post(self.register_url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())


class CustomerListTest(APITestCase):
    """Simple test cases for Customer List API"""
    
    def setUp(self):
        self.list_url = reverse('customer-list-list')
        # Create test customer
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name='Jane',
            last_name='Smith',
            age=25,
            phone_number='9876543210',
            monthly_salary=60000,
            approved_limit=2200000
        )
    
    def test_list_customers(self):
        """Test listing all customers"""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 1)
    
    def test_get_specific_customer(self):
        """Test retrieving specific customer"""
        detail_url = reverse('customer-list-detail', kwargs={'pk': self.customer.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('data', data)


class CustomerModelTest(TestCase):
    """Simple model tests"""
    
    def test_customer_creation(self):
        """Test creating a customer"""
        customer = Customer.objects.create(
            customer_id=1,
            first_name='Test',
            last_name='User',
            age=25,
            phone_number='1234567890',
            monthly_salary=50000,
            approved_limit=1800000
        )
        
        self.assertEqual(str(customer), "Test User")
        self.assertEqual(customer.name, "Test User")
    
    def test_unique_constraints(self):
        """Test unique constraints"""
        Customer.objects.create(
            customer_id=1,
            first_name='Test',
            last_name='User',
            age=25,
            phone_number='1234567890',
            monthly_salary=50000,
            approved_limit=1800000
        )
        
        # Test customer_id uniqueness
        with self.assertRaises(Exception):
            Customer.objects.create(
                customer_id=1,  # Duplicate ID
                first_name='Another',
                last_name='User',
                age=30,
                phone_number='0987654321',
                monthly_salary=60000,
                approved_limit=2000000
            )