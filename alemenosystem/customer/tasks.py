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
    Step 3: Update current_debt for all customers based on active loans - DIAGNOSTIC VERSION
    """
    try:
        loan_file_path = settings.DATA_DIR / 'loan_data.xlsx'
        
        if not os.path.exists(loan_file_path):
            logger.warning(f"Loan data file not found at {loan_file_path}, skipping current debt calculation")
            return {"status": "success", "message": "No loan data available for debt calculation"}
        
        loan_df = pd.read_excel(loan_file_path)
       
        # Handle different column names
        customer_col = 'Customer ID' if 'Customer ID' in loan_df.columns else 'Customer'
        
        # Parse dates with error handling
        try:
            loan_df['Date of Approval'] = pd.to_datetime(loan_df['Date of Approval'], format='%m/%d/%Y', errors='coerce')
            loan_df['End Date'] = pd.to_datetime(loan_df['End Date'], format='%m/%d/%Y', errors='coerce')
        except Exception as e:
            logger.error(f"Error parsing dates: {e}")
            loan_df['Date of Approval'] = pd.to_datetime(loan_df['Date of Approval'], errors='coerce')
            loan_df['End Date'] = pd.to_datetime(loan_df['End Date'], errors='coerce')
        
        from datetime import datetime
        current_date = datetime.now()       
        current_debt_map = {}
        processed_loans = 0
        active_loans = 0
                
        # Process all loans
        for index, row in loan_df.iterrows():
            try:
                customer_id = row[customer_col]
                loan_amount = float(row['Loan Amount'])
                monthly_installment = float(row['Monthly payment'])
                emis_paid = int(row['EMIs paid on Time'])
                end_date = row['End Date']
                
                processed_loans += 1
                
                # Check if loan is still active
                if pd.notna(end_date) and end_date > current_date:
                    active_loans += 1
                    total_paid = emis_paid * monthly_installment
                    remaining_debt = max(0, loan_amount - total_paid)
                    
                    if customer_id not in current_debt_map:
                        current_debt_map[customer_id] = 0
                    current_debt_map[customer_id] += remaining_debt
                    
            except Exception as e:
                logger.error(f"Error processing loan row {index}: {e}")
                continue
        
        existing_customers = set(Customer.objects.values_list('customer_id', flat=True))
    
        customers_to_update = set(current_debt_map.keys())
        missing_customers = customers_to_update - existing_customers
        if missing_customers:
            logger.warning(f"Customers in loan data but not in customer table: {list(missing_customers)[:10]}")
        
        updated_count = 0
        update_details = []
        
        # Use individual updates with logging for first 10
        for i, (customer_id, debt) in enumerate(current_debt_map.items()):
            try:
                # Check if customer exists first
                customer_exists = Customer.objects.filter(customer_id=customer_id).exists()
                if not customer_exists:
                    logger.warning(f"Customer {customer_id} not found in database")
                    continue
                
                # Get current debt before update
                current_customer = Customer.objects.get(customer_id=customer_id)
                old_debt = current_customer.current_debt
                
                # Update the debt
                updated_rows = Customer.objects.filter(customer_id=customer_id).update(current_debt=debt)
                
                # Verify the update
                updated_customer = Customer.objects.get(customer_id=customer_id)
                new_debt = updated_customer.current_debt
                
                if updated_rows > 0:
                    updated_count += 1
                    if i < 10:  # Log first 10 updates in detail
                        update_details.append(f"Customer {customer_id}: {old_debt} -> {new_debt} (expected: {debt})")
                        logger.info(f"Updated customer {customer_id}: {old_debt} -> {new_debt} (calculated: {debt})")
                        
                        # Double check the database state
                        verification = Customer.objects.get(customer_id=customer_id)
                        logger.info(f"Verification - Customer {customer_id} current_debt in DB: {verification.current_debt}")
                
            except Exception as e:
                logger.error(f"Error updating debt for customer {customer_id}: {e}")
        
        for detail in update_details:
            logger.info(detail)
        
        # Reset debt to 0 for customers with no active loans
        customers_with_debt_ids = list(current_debt_map.keys())
        customers_without_active_loans = Customer.objects.exclude(customer_id__in=customers_with_debt_ids)
        reset_count = customers_without_active_loans.update(current_debt=0)
    
        sample_customers_final = Customer.objects.filter(
            customer_id__in=list(current_debt_map.keys())[:5]
        ).values('customer_id', 'current_debt')
        
        for customer in sample_customers_final:
            expected_debt = current_debt_map.get(customer['customer_id'], 0)
            actual_debt = float(customer['current_debt'])
            logger.info(f"Customer {customer['customer_id']}: Expected {expected_debt}, Actual {actual_debt}, Match: {abs(expected_debt - actual_debt) < 0.01}")
        
        logger.info(f"Updated current debt for {updated_count} customers with active loans")
        logger.info(f"Reset debt to 0 for {reset_count} customers without active loans")
        
        return {
            "status": "success",
            "updated_count": updated_count,
            "reset_count": reset_count,
            "active_loans": active_loans,
            "processed_loans": processed_loans,
            "customers_with_debt": len(current_debt_map),
            "message": f"Updated current debt for {updated_count} customers with active loans, reset {reset_count} customers to 0 debt"
        }
        
    except Exception as e:
        logger.error(f"Error updating current debt: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}