from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.urls import reverse 
from django.core.paginator import Paginator
from .models import Expense
from django.db.models import Sum, Count
from datetime import datetime
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle,Spacer
from datetime import datetime
from django.utils.timezone import now
import re
import json 
import os
from django.conf import settings

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        errors = {}

        # Username validation
        if len(username) < 6:
            errors['username'] = 'Username must be at least 6 characters long.'
        elif User.objects.filter(username=username).exists():
            errors['username'] = 'Username already exists.'

        # Email validation
        if User.objects.filter(email=email).exists():
            errors['email'] = 'Email address already exists.'

        # Password validations
        if password1 != password2:
            errors['password_mismatch'] = 'Passwords do not match.'
        
        if (len(password1) < 8 or 
            not re.search(r'[A-Z]', password1) or 
            not re.search(r'[a-z]', password1) or 
            not re.search(r'\d', password1) or 
            not re.search(r'[!@#$%^&*(),.?":{}|<>]', password1)):
            errors['password_strength'] = 'Password must be at least 8 characters long, include one uppercase letter, one lowercase letter, one digit, and one special character.'

        if errors:
            # Preserve form data (excluding passwords)
            form_data = {
                'first_name': first_name,
                'last_name': last_name,
                'username': username,
                'email': email
            }
            return render(request, 'signup.html', {'errors': errors, 'form_data': form_data})

        # Create the user if no errors
        user = User.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            password=password1
        )
        user.save()
        return redirect('home')

    return render(request, 'signup.html')

@never_cache
def logout_view(request):
    logout(request)  # Logs out the user
    return redirect('landing')  # Redirects to the landing page after logout


def landing_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'landing.html')

@never_cache
@login_required(login_url='login')
def home(request):
    # Get all expenses for the logged-in user
    expenses = Expense.objects.filter(user=request.user)

    # Total Expenses
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0

    # Total Transactions
    total_transactions = expenses.count()

    # Most Spent On Category Logic
    most_spent_category = 'N/A'
    category_data = (
        expenses.values('category')
        .annotate(total_amount=Sum('amount'), transaction_count=Count('id'))
        .order_by('-total_amount', '-transaction_count')
    )
    if category_data:
        most_spent_category = category_data[0]['category']

    # Current Month Spending
    current_month = timezone.now().month
    current_year = timezone.now().year
    current_month_spending = (
        expenses.filter(date__month=current_month, date__year=current_year)
        .aggregate(total=Sum('amount'))['total'] or 0
    )

    context = {
        'total_expenses': total_expenses,
        'total_transactions': total_transactions,
        'most_spent_category': most_spent_category,
        'current_month_spending': current_month_spending
    }

    return render(request, 'home.html', context)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        errors = {}

        # Check for empty fields
        if not username:
            errors['username'] = 'Username is required.'
        if not password:
            errors['password'] = 'Password is required.'

        if not errors:
            # Authenticate the user
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)  # Log the user in
                return redirect('home')  # Redirect to home page after successful login
            else:
                errors['invalid'] = 'Invalid username or password.'

        return render(request, 'login.html', {'errors': errors, 'form_data': request.POST})

    return render(request, 'login.html')




@login_required
def add_expense(request):
    if not request.user.is_authenticated:
        return redirect('home')
    errors = {}
    categories = ['Food', 'Transport', 'Shopping', 'Entertainment', 'Health', 'Education', 'Utilities', 'Others']
    current_date = timezone.now().date().isoformat()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        amount = request.POST.get('amount', '').strip()
        category = request.POST.get('category', '')
        date = request.POST.get('date', current_date)

        # Validations
        if not (5 <= len(title) <= 50):
            errors['title'] = 'Title must be between 5 and 50 characters.'

        if not (10 <= len(description) <= 200):
            errors['description'] = 'Description must be between 10 and 200 characters.'

        try:
            amount_value = float(amount)
            if amount_value <= 0:
                errors['amount'] = 'Amount must be a positive number.'
        except ValueError:
            errors['amount'] = 'Amount must be a valid number.'

        if date > current_date:
            errors['date'] = 'Date cannot be in the future.'

        if category not in categories:
            errors['category'] = 'Invalid category selected.'

        # Save Expense if no errors
        if not errors:
            Expense.objects.create(
                user=request.user,
                title=title,
                description=description,
                amount=amount,
                category=category,
                date=date
            )
            return redirect(f"{reverse('home')}?success=1")  # Add success parameter

    return render(request, 'add_expense.html', {
        'errors': errors,
        'current_date': current_date,
        'categories': categories
    })

@login_required
def manage_expense(request):
    user_expenses = Expense.objects.filter(user=request.user).order_by('-date')

    # Apply pagination

    paginator = Paginator(user_expenses, 5)  # Show 5 transactions per page
    page_number = request.GET.get('page')
    expenses_page = paginator.get_page(page_number)
    print("Total Pages:", paginator.num_pages)
    print("Current Page:", expenses_page.number)
    print("Has Next:", expenses_page.has_next())
    print("Has Previous:", expenses_page.has_previous())

    errors = {}
    success_message = request.GET.get('success', None)  # Get success message from URL parameters
    current_date = timezone.now().date().isoformat()
    categories = ['Food', 'Transport', 'Shopping', 'Entertainment', 'Health', 'Education', 'Utilities', 'Others']

    # Edit Expense Logic
    if request.method == 'POST' and 'edit_expense_id' in request.POST:
        expense_id = request.POST.get('edit_expense_id')
        expense = get_object_or_404(Expense, id=expense_id, user=request.user)

        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        amount = request.POST.get('amount', '').strip()
        category = request.POST.get('category', '')
        date = request.POST.get('date', current_date)

        # Validations
        if not (5 <= len(title) <= 50):
            errors['title'] = 'Title must be between 5 and 50 characters.'

        if not (10 <= len(description) <= 200):
            errors['description'] = 'Description must be between 10 and 200 characters.'

        try:
            amount_value = float(amount)
            if amount_value <= 0:
                errors['amount'] = 'Amount must be a positive number.'
        except ValueError:
            errors['amount'] = 'Amount must be a valid number.'

        if date > current_date:
            errors['date'] = 'Date cannot be in the future.'

        if category not in categories:
            errors['category'] = 'Invalid category selected.'

        # Update only if no errors
        if not errors:
            expense.title = title
            expense.description = description
            expense.amount = amount
            expense.category = category
            expense.date = date
            expense.save()
            return redirect(f"{request.path}?success=Expense updated successfully!")

    # Delete Expense Logic
    if request.method == 'POST' and 'delete_expense_id' in request.POST:
        expense_id = request.POST.get('delete_expense_id')
        expense = get_object_or_404(Expense, id=expense_id, user=request.user)
        expense.delete()
        return redirect(f"{request.path}?success=Expense deleted successfully!")

    return render(request, 'manage_expense.html', {
        'expenses_page': expenses_page,
        'errors': errors,
        'success_message': success_message,
        'current_date': current_date,
        'categories': categories
    })

@login_required
def insights(request):
    # Get user expenses
    expenses = Expense.objects.filter(user=request.user)
    category_labels = []
    category_values = []
    monthly_labels = []
    monthly_values = []
    # Category-wise Expense Data
    category_data = expenses.values('category').annotate(total=Sum('amount'))
    category_labels = list(category_data.values_list('category', flat=True))
    category_values = [float(item['total']) for item in category_data]  # Convert Decimal to float

    # Get the current year
    current_year = datetime.now().year

    # Ensure all months (Jan–Dec) appear even if expense is 0
    full_months = {datetime(current_year, i, 1).strftime('%b %Y'): 0 for i in range(1, 13)}

    # Populate with actual expense data
    for item in expenses.values('date__year', 'date__month').annotate(total=Sum('amount')):
        month_label = datetime(item['date__year'], item['date__month'], 1).strftime('%b %Y')
        full_months[month_label] = float(item['total'])  

    # Convert data for template
    monthly_labels = list(full_months.keys())
    monthly_values = list(full_months.values())
    if monthly_values == [0] * 12:  # Check if all values are zero
        monthly_values = []
    context = {
        'category_labels': json.dumps(category_labels),  
        'category_values': json.dumps(category_values),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_values': json.dumps(monthly_values),
    }

    return render(request, 'insights.html', context)

@login_required
def download_report(request):
    expenses = Expense.objects.filter(user=request.user).order_by('-date')
    return render(request, "download_report.html", {"expenses": expenses})








@login_required
def generate_pdf(request):
    expenses = Expense.objects.filter(user=request.user).order_by('-date')

    if not expenses.exists():
        return HttpResponse("No transactions available to generate a report.", status=400)

    total_amount = sum(expense.amount for expense in expenses)
    generated_date = now().strftime("%d %B %Y")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="SmartSpend_Report.pdf"'

    # Fix: Load font using settings.BASE_DIR
    
    font_path = os.path.join(settings.BASE_DIR, 'accounts', 'fonts', 'DejaVuSans.ttf')
    pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    title = [["SmartSpend Expense Report"]]
    summary = [
        [f"\nGenerated for: {request.user.first_name} {request.user.last_name}"],
        [f"Generated on: {generated_date}"],
        [f"Total Expenses: ₹{total_amount}"],
    ]

    data = [["Sr No.", "Date", "Category", "Amount (₹)"]]
    for index, expense in enumerate(expenses, start=1):
        data.append([
            index, 
            expense.date.strftime("%d-%m-%Y"), 
            expense.category, 
            f"₹{expense.amount}"
        ])

    title_table = Table(title, colWidths=[5 * inch])
    title_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
        ("FONTSIZE", (0, 0), (-1, -1), 18),
    ]))

    summary_table = Table(summary, colWidths=[5 * inch])
    summary_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
    ]))

    data_table = Table(data, colWidths=[1 * inch, 1.5 * inch, 2.5 * inch, 1.5 * inch])
    data_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(title_table)
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    elements.append(data_table)

    doc.build(elements)
    return response