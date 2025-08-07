from django.db import models
from customer.models import Customer

class Loan(models.Model):
    loan_id = models.IntegerField(unique=True, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tenure = models.IntegerField(help_text="Tenure in months")
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    monthly_installment = models.DecimalField(max_digits=12, decimal_places=2)
    emis_paid_on_time = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"Loan {self.loan_id} - Customer {self.customer.customer_id}"

    class Meta:
        db_table = 'loan'
        # using indexes to speed up queries on loan_id and customer
        indexes = [
            models.Index(fields=["loan_id"]),
            models.Index(fields=["customer"]),
        ]