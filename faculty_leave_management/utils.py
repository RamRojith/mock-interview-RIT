from datetime import datetime, timedelta
from calendar import monthrange

def leave_allotment_update(start_date, end_date, default_allotment):
    # Calculate total months in the academic year
    total_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
    
    # Handle division by zero
    if total_months <= 0:
        return 0
    
    # Get today's date as date object for consistent comparison
    today = datetime.now().date()
    
    # Corrected: Days remaining in the current month
    days_in_month = monthrange(today.year, today.month)[1]
    days_remaining = days_in_month - today.day
    
    # Check if today is within the academic year
    if start_date <= today <= end_date:
        # Calculate remaining months from today until the end_date
        remaining_months = (end_date.year - today.year) * 12 + (end_date.month - today.month) + 1
        
        # If 10 or fewer days are remaining, exclude this month
        if days_remaining <= 10:
            remaining_months -= 1
        
        # Handle negative remaining_months
        if remaining_months < 0:
            remaining_months = 0
    else:
        remaining_months = 0  # Today is outside the academic year range

    # Calculate remaining days
    if total_months==remaining_months:
        remaining=default_allotment
    else:
        remaining = (default_allotment // total_months) * remaining_months
  
    return remaining
