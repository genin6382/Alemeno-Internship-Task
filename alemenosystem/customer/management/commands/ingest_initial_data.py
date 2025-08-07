from django.core.management.base import BaseCommand
from customer.models import Customer
from loan.models import Loan
from customer.tasks import ingest_customer_data, update_customer_current_debt
from loan.tasks import ingest_loan_data

class Command(BaseCommand):
    help = 'Ingest initial data from Excel files on first startup'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force ingestion even if data exists',
        )
        parser.add_argument(
            '--loans-only',
            action='store_true',
            help='Only ingest loans and update debt (skip customers)',
        )
        parser.add_argument(
            '--use-celery',
            action='store_true',
            help='Use Celery for processing (requires workers to be running)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Checking if initial data ingestion is needed...'))
        
        customer_count = Customer.objects.count()
        loan_count = Loan.objects.count()
        
        self.stdout.write(f'Current counts - Customers: {customer_count}, Loans: {loan_count}')
        
        # Handle different scenarios
        if options['force']:
            self.stdout.write(self.style.WARNING('Force flag used - proceeding with full ingestion'))
            self.run_full_ingestion(use_celery=options['use_celery'])
        elif options['loans_only']:
            self.stdout.write(self.style.SUCCESS('Running loans-only ingestion...'))
            self.run_loans_only_ingestion(use_celery=options['use_celery'])
        elif customer_count > 0 and loan_count == 0:
            self.stdout.write(self.style.WARNING('Customers exist but no loans found. Running loans ingestion...'))
            self.run_loans_only_ingestion(use_celery=options['use_celery'])
        elif customer_count > 0 and loan_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Data already exists (Customers: {customer_count}, Loans: {loan_count}). '
                    'Use --force to override or --loans-only to just ingest loans.'
                )
            )
            return
        else:
            self.stdout.write(self.style.SUCCESS('No data found. Running full ingestion...'))
            self.run_full_ingestion(use_celery=options['use_celery'])
        
        # Final count check
        final_customers = Customer.objects.count()
        final_loans = Loan.objects.count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Final counts - Customers: {final_customers}, Loans: {final_loans}'
            )
        )

    def run_full_ingestion(self, use_celery=False):
        """Run the complete ingestion step by step"""
        try:
            if use_celery:
                self.stdout.write(self.style.SUCCESS('Starting full data ingestion using Celery...'))
                self._run_with_celery_full()
            else:
                self.stdout.write(self.style.SUCCESS('Starting full data ingestion synchronously...'))
                self._run_synchronously_full()
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during full ingestion: {str(e)}'))

    def run_loans_only_ingestion(self, use_celery=False):
        """Run only loan ingestion and debt update"""
        try:
            if use_celery:
                self.stdout.write(self.style.SUCCESS('Starting loan ingestion using Celery...'))
                self._run_with_celery_loans_only()
            else:
                self.stdout.write(self.style.SUCCESS('Starting loan ingestion synchronously...'))
                self._run_synchronously_loans_only()
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during loans-only ingestion: {str(e)}'))

    def _run_synchronously_full(self):
        """Run tasks synchronously without Celery"""
        # Step 1: Customers
        self.stdout.write('Step 1: Ingesting customers...')
        customer_result = ingest_customer_data()
        
        if customer_result['status'] != 'success':
            self.stdout.write(self.style.ERROR(f"Customer ingestion failed: {customer_result['message']}"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"Customers: {customer_result['message']}"))
        
        # Step 2: Loans
        self.stdout.write('Step 2: Ingesting loans...')
        loan_result = ingest_loan_data()
        
        if loan_result['status'] != 'success':
            self.stdout.write(self.style.ERROR(f"Loan ingestion failed: {loan_result['message']}"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"Loans: {loan_result['message']}"))
        
        # Step 3: Update debt
        self.stdout.write('Step 3: Updating customer current debt...')
        debt_result = update_customer_current_debt()
        
        if debt_result['status'] == 'success':
            self.stdout.write(self.style.SUCCESS(f"Debt Update: {debt_result['message']}"))
        else:
            self.stdout.write(self.style.ERROR(f"Debt update failed: {debt_result['message']}"))

    def _run_synchronously_loans_only(self):
        """Run loans and debt update synchronously"""
        # Step 1: Ingest loans
        loan_result = ingest_loan_data()
        
        if loan_result['status'] == 'success':
            self.stdout.write(self.style.SUCCESS(f"Loans: {loan_result['message']}"))
            
            # Step 2: Update current debt
            self.stdout.write('Updating customer current debt...')
            debt_result = update_customer_current_debt()
            
            if debt_result['status'] == 'success':
                self.stdout.write(self.style.SUCCESS(f"Debt Update: {debt_result['message']}"))
            else:
                self.stdout.write(self.style.ERROR(f"Debt update failed: {debt_result['message']}"))
        else:
            self.stdout.write(self.style.ERROR(f"Loan ingestion failed: {loan_result['message']}"))

    def _run_with_celery_full(self):
        """Run the complete ingestion using Celery (original method)"""
        # Step 1: Customers
        self.stdout.write('Step 1: Ingesting customers...')
        customer_task = ingest_customer_data.delay()
        customer_result = customer_task.get(timeout=300)
        
        if customer_result['status'] != 'success':
            self.stdout.write(self.style.ERROR(f"Customer ingestion failed: {customer_result['message']}"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"Customers: {customer_result['message']}"))
        
        # Step 2: Loans
        self.stdout.write('Step 2: Ingesting loans...')
        loan_task = ingest_loan_data.delay()
        loan_result = loan_task.get(timeout=300)
        
        if loan_result['status'] != 'success':
            self.stdout.write(self.style.ERROR(f"Loan ingestion failed: {loan_result['message']}"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"Loans: {loan_result['message']}"))
        
        # Step 3: Update debt
        self.stdout.write('Step 3: Updating customer current debt...')
        debt_task = update_customer_current_debt.delay()
        debt_result = debt_task.get(timeout=300)
        
        if debt_result['status'] == 'success':
            self.stdout.write(self.style.SUCCESS(f"Debt Update: {debt_result['message']}"))
        else:
            self.stdout.write(self.style.ERROR(f"Debt update failed: {debt_result['message']}"))

    def _run_with_celery_loans_only(self):
        """Run only loan ingestion and debt update using Celery"""
        # Step 1: Ingest loans
        loan_task = ingest_loan_data.delay()
        loan_result = loan_task.get(timeout=300)
        
        if loan_result['status'] == 'success':
            self.stdout.write(self.style.SUCCESS(f"Loans: {loan_result['message']}"))
            
            # Step 2: Update current debt
            self.stdout.write('Updating customer current debt...')
            debt_task = update_customer_current_debt.delay()
            debt_result = debt_task.get(timeout=300)
            
            if debt_result['status'] == 'success':
                self.stdout.write(self.style.SUCCESS(f"Debt Update: {debt_result['message']}"))
            else:
                self.stdout.write(self.style.ERROR(f"Debt update failed: {debt_result['message']}"))
        else:
            self.stdout.write(self.style.ERROR(f"Loan ingestion failed: {loan_result['message']}"))