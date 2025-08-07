from celery import shared_task
import pandas as pd
import logging
import os
from django.db import transaction
from django.conf import settings
from .models import Customer

logger = logging.getLogger(__name__)

@shared_task
def ingest_customer_data():
    """
    Step 1: Ingest customer data from Excel file (without current_debt initially)
    """
    try:
        file_path = settings.DATA_DIR / 'customer_data.xlsx'
        
        if not os.path.exists(file_path):
            logger.error(f"Customer data file not found: {file_path}")
            return {"status": "error", "message": "Customer data file not found"}
        
        df = pd.read_excel(file_path)
        logger.info(f"Customer Excel columns: {list(df.columns)}")
        
        customers_to_create = []
        
        for _, row in df.iterrows():
            customer = Customer(
                customer_id=row['Customer ID'],
                first_name=row['First Name'],
                last_name=row['Last Name'],
                age=row.get('Age', 0),
                phone_number=row['Phone Number'],
                monthly_salary=row['Monthly Salary'],
                approved_limit=row['Approved Limit'],
                current_debt=0,  # Set to 0 initially, will be updated later
            )
            customers_to_create.append(customer)
        
        # Bulk create with transaction
        with transaction.atomic():
            Customer.objects.bulk_create(customers_to_create, batch_size=1000, ignore_conflicts=True)
        
        logger.info(f"Successfully ingested {len(customers_to_create)} customers")
        return {
            "status": "success",
            "count": len(customers_to_create),
            "message": f"Successfully ingested {len(customers_to_create)} customers"
        }
        
    except Exception as e:
        logger.error(f"Error ingesting customers: {str(e)}")
        return {"status": "error", "message": str(e)}

@shared_task
def update_customer_current_debt():
    """
    Step 3: Update current_debt for all customers based on active loans
    """
    try:
        loan_file_path = os.path.join(settings.BASE_DIR.parent, 'data', 'loan_data.xlsx')
        
        if not os.path.exists(loan_file_path):
            logger.warning("Loan data file not found, skipping current debt calculation")
            return {"status": "success", "message": "No loan data available for debt calculation"}
        
        loan_df = pd.read_excel(loan_file_path)
        logger.info(f"Loan Excel columns for debt calculation: {list(loan_df.columns)}")
        
        # Handle different column names
        customer_col = 'Customer ID' if 'Customer ID' in loan_df.columns else 'Customer'
        
        # Parse dates
        loan_df['Date of Approval'] = pd.to_datetime(loan_df['Date of Approval'], format='%m/%d/%Y')
        loan_df['End Date'] = pd.to_datetime(loan_df['End Date'], format='%m/%d/%Y')
        
        from datetime import datetime
        current_date = datetime.now()
        
        current_debt_map = {}
        
        for _, row in loan_df.iterrows():
            try:
                customer_id = row[customer_col]
                loan_amount = row['Loan Amount']
                monthly_installment = row['Monthly payment']  # Excel column name
                emis_paid = row['EMIs paid on Time']
                end_date = row['End Date']
                
                # Check if loan is still active
                if end_date > current_date:
                    total_paid = emis_paid * monthly_installment  # Fixed variable name
                    remaining_debt = max(0, loan_amount - total_paid)
                    current_debt_map[customer_id] = current_debt_map.get(customer_id, 0) + remaining_debt
                    
            except Exception as e:
                logger.error(f"Error processing loan row for debt calculation: {e}")
                continue
        
        # Update customers with calculated debt
        updated_count = 0
        for customer_id, debt in current_debt_map.items():
            try:
                Customer.objects.filter(customer_id=customer_id).update(current_debt=debt)
                updated_count += 1
            except Exception as e:
                logger.error(f"Error updating debt for customer {customer_id}: {e}")
        
        logger.info(f"Updated current debt for {updated_count} customers")
        return {
            "status": "success",
            "updated_count": updated_count,
            "message": f"Updated current debt for {updated_count} customers"
        }
        
    except Exception as e:
        logger.error(f"Error updating current debt: {str(e)}")
        return {"status": "error", "message": str(e)}