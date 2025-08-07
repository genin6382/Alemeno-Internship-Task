from celery import shared_task
import pandas as pd
import logging
import os
from django.db import transaction
from django.conf import settings
from .models import Loan
from customer.models import Customer

logger = logging.getLogger(__name__)

@shared_task
def ingest_loan_data():
    """
    Step 2: Ingest loan data from Excel file
    """
    try:
        file_path = settings.DATA_DIR / 'loan_data.xlsx'

        
        if not os.path.exists(file_path):
            logger.error(f"Loan data file not found: {file_path}")
            return {"status": "error", "message": "Loan data file not found"}
        
        df = pd.read_excel(file_path)
        logger.info(f"Loan Excel columns: {list(df.columns)}")
        
        # Handle different column names
        customer_col = 'Customer ID' if 'Customer ID' in df.columns else 'Customer'
        
        if customer_col not in df.columns:
            return {"status": "error", "message": f"Customer column not found. Available: {list(df.columns)}"}
        
        # Parse dates
        df['Date of Approval'] = pd.to_datetime(df['Date of Approval'], format='%m/%d/%Y')
        df['End Date'] = pd.to_datetime(df['End Date'], format='%m/%d/%Y')
        
        loans_to_create = []
        skipped = 0
        skip_reasons = {}  # Track skip reasons
        
        for index, row in df.iterrows():
            try:
                customer_id = row[customer_col]
                loan_id = row['Loan ID']
                
                # Check if customer exists
                try:
                    customer = Customer.objects.get(customer_id=customer_id)
                except Customer.DoesNotExist:
                    logger.warning(f"Row {index}: Customer {customer_id} not found for loan {loan_id}")
                    skipped += 1
                    skip_reasons['customer_not_found'] = skip_reasons.get('customer_not_found', 0) + 1
                    continue
                
                # Check for duplicate loan IDs
                if Loan.objects.filter(loan_id=loan_id).exists():
                    logger.warning(f"Row {index}: Loan {loan_id} already exists, skipping")
                    skipped += 1
                    skip_reasons['duplicate_loan'] = skip_reasons.get('duplicate_loan', 0) + 1
                    continue
                
                loan = Loan(
                    customer=customer,
                    loan_id=loan_id,
                    loan_amount=row['Loan Amount'],
                    tenure=row['Tenure'],
                    interest_rate=row['Interest Rate'],
                    monthly_installment=row['Monthly payment'],
                    emis_paid_on_time=row['EMIs paid on Time'],
                    start_date=row['Date of Approval'],
                    end_date=row['End Date'],
                )
                loans_to_create.append(loan)
                
            except KeyError as e:
                logger.error(f"Row {index}: Missing column in loan data: {e}")
                skipped += 1
                skip_reasons['missing_column'] = skip_reasons.get('missing_column', 0) + 1
                continue
            except Exception as e:
                logger.error(f"Row {index}: Error processing loan row: {e}")
                skipped += 1
                skip_reasons['other_error'] = skip_reasons.get('other_error', 0) + 1
                continue
        
        # Log skip reasons
        if skip_reasons:
            logger.info(f"Skip reasons: {skip_reasons}")
        
        # Bulk create with transaction
        with transaction.atomic():
            created_loans = Loan.objects.bulk_create(loans_to_create, batch_size=1000, ignore_conflicts=True)
        
        logger.info(f"Successfully ingested {len(loans_to_create)} loans, skipped {skipped}")
        logger.info(f"Total rows in Excel: {len(df)}, Created: {len(loans_to_create)}, Skipped: {skipped}")
        
        return {
            "status": "success",
            "count": len(loans_to_create),
            "skipped": skipped,
            "total_rows": len(df),
            "skip_reasons": skip_reasons,
            "message": f"Successfully ingested {len(loans_to_create)} loans, skipped {skipped}"
        }
        
    except Exception as e:
        logger.error(f"Error ingesting loans: {str(e)}")
        return {"status": "error", "message": str(e)}