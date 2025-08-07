# views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from .models import Customer
from .serializers import CustomerRegistrationSerializer, CustomerResponseSerializer


class CustomerRegistrationViewSet(CreateModelMixin, GenericViewSet):
    """
    ViewSet for Customer registration
    """
    queryset = Customer.objects.all()
    serializer_class = CustomerRegistrationSerializer

    def generate_customer_id(self):
        """
        Generate unique customer_id
        """
        last_customer = Customer.objects.order_by('-customer_id').first()
        if last_customer:
            return last_customer.customer_id + 1
        return 1

    def calculate_approved_limit(self, monthly_salary):
        """
        approved_limit = 36 * monthly_salary (rounded to nearest lakh)
        """
        calculated_limit = 36 * monthly_salary
        approved_limit = round(calculated_limit / 100000) * 100000
        return approved_limit

    def create(self, request, *args, **kwargs):
        """
        Register a new customer with calculated approved limit
        """
        try:
            # Validate input data
            serializer = CustomerRegistrationSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response(
                    {
                        'error': 'Validation failed',
                        'details': serializer.errors
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if customer with same phone number already exists
            phone_number = serializer.validated_data.get('phone_number')
            if Customer.objects.filter(phone_number=phone_number).exists():
                return Response(
                    {
                        'error': 'Customer already exists',
                        'message': 'A customer with this phone number already exists.'
                    },
                    status=status.HTTP_409_CONFLICT
                )
            
            #following ATOMIC principle to ensure data integrity
            with transaction.atomic():
                # Generate unique customer_id
                customer_id = self.generate_customer_id()
                
                monthly_income = serializer.validated_data.get('monthly_income')
                approved_limit = self.calculate_approved_limit(monthly_income)
                
                customer = Customer.objects.create(
                    customer_id=customer_id,
                    first_name=serializer.validated_data.get('first_name'),
                    last_name=serializer.validated_data.get('last_name'),
                    age=serializer.validated_data.get('age'),
                    phone_number=serializer.validated_data.get('phone_number'),
                    monthly_salary=monthly_income,
                    approved_limit=approved_limit
                )

            return Response(
                {
                    'customer_id': customer.customer_id,
                    'name': customer.name,
                    'age': customer.age,
                    'monthly_income': customer.monthly_salary,
                    'approved_limit': customer.approved_limit,
                    'phone_number': int(customer.phone_number)
                },
                status=status.HTTP_201_CREATED
            )

        except IntegrityError:
            return Response(
                {
                    'error': 'Database error',
                    'message': 'Could not create customer due to database constraints.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        except DjangoValidationError as e:
            return Response(
                {
                    'error': 'Validation error',
                    'message': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception:
            return Response(
                {
                    'error': 'Internal server error',
                    'message': 'An unexpected error occurred. Please try again later.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomerListViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    ViewSet for Customer listing - Only GET requests allowed
    """
    queryset = Customer.objects.all()
    serializer_class = CustomerResponseSerializer

    def list(self, request, *args, **kwargs):
        """
        List all customers
        GET /customers/
        """
        try:
            customers = Customer.objects.all()
            serializer = CustomerResponseSerializer(customers, many=True)
            return Response(
                {
                    'success': True,
                    'count': customers.count(),
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except Exception:
            return Response(
                {
                    'error': 'Internal server error',
                    'message': 'Could not fetch customer data.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, pk=None):
        """
        Retrieve a specific customer
        GET /customers/{id}/
        """
        try:
            customer = self.get_object()
            serializer = CustomerResponseSerializer(customer)
            return Response(
                {
                    'success': True,
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except Customer.DoesNotExist:
            return Response(
                {
                    'error': 'Customer not found',
                    'message': 'Customer with the specified ID does not exist.'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception:
            return Response(
                {
                    'error': 'Internal server error',
                    'message': 'Could not retrieve customer data.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )