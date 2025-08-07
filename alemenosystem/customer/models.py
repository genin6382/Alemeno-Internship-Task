from django.db import models
from django.core.validators import MinLengthValidator

class Customer(models.Model):
    customer_id = models.IntegerField(unique=True, db_index=True)
    first_name = models.CharField(max_length=15)
    last_name = models.CharField(max_length=15)
    age = models.IntegerField()
    phone_number = models.CharField(max_length=15, unique=True, db_index=True,validators=[MinLengthValidator(10)])
    monthly_salary = models.IntegerField(help_text="Monthly salary in local currency")
    approved_limit = models.IntegerField(help_text="Approved loan limit")
    current_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        db_table = 'customer'
        #using indexes to speed up queries on customer_id and phone_number
        indexes = [
            models.Index(fields=["customer_id"]),
            models.Index(fields=["phone_number"])
        ]


