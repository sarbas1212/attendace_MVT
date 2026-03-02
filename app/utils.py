import holidays
from django.conf import settings

def is_working_day(date_obj):
    """Determines if a date is a workday based on weekends and public holidays."""
    # 1. Weekends (5=Saturday, 6=Sunday)
    if date_obj.weekday() in [5, 6]:
        return False, "Weekend"

    # 2. Public Holidays (uses 'IN' for India, change to your country in settings)
    country_code = getattr(settings, 'ERP_REGION', 'IN')
    country_holidays = holidays.CountryHoliday(country_code)
    
    if date_obj in country_holidays:
        return False, f"Holiday ({country_holidays.get(date_obj)})"

    return True, "Working Day"