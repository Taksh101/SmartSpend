from django.db import models
from django.contrib.auth.models import User

class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Links each expense to a specific user
    title = models.CharField(max_length=60)                  # Title with max 60 characters
    description = models.TextField(max_length=300)           # Description up to 300 characters
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Handles large amounts with 2 decimal places
    date = models.DateField()                                # Date of the expense
    category = models.CharField(max_length=30)               # Category (Food, Travel, etc.)

    def __str__(self):
        return f"{self.title} - {self.user.username}"
