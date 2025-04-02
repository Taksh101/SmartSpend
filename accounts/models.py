from django.db import models
from django.contrib.auth.models import User

class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    title = models.CharField(max_length=60)                 
    description = models.TextField(max_length=300)           
    amount = models.DecimalField(max_digits=10, decimal_places=2)  
    date = models.DateField()                                
    category = models.CharField(max_length=30)               
    def __str__(self):
        return f"{self.title} - {self.user.username}"
