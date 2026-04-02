# organizations/models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta

class Organization(models.Model):
    PLAN_CHOICES = [
        ('FREE_TRIAL', 'Free Trial'),
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
        ('EXPIRED', 'Expired'),
    ]

    name = models.CharField(max_length=150)
    email = models.EmailField()

    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='FREE_TRIAL')

    trial_start = models.DateField(null=True, blank=True)
    trial_end = models.DateField(null=True, blank=True)

    subscription_start = models.DateField(null=True, blank=True)
    subscription_end = models.DateField(null=True, blank=True)

    razorpay_order_id = models.CharField(max_length=150, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=150, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def start_trial(self, days=7):
        today = timezone.now().date()
        self.plan = 'FREE_TRIAL'
        self.trial_start = today
        self.trial_end = today + timedelta(days=days)
        self.save(update_fields=['plan', 'trial_start', 'trial_end'])

    def activate_monthly(self):
        today = timezone.now().date()
        self.plan = 'MONTHLY'
        self.subscription_start = today
        self.subscription_end = today + timedelta(days=30)
        self.save(update_fields=['plan', 'subscription_start', 'subscription_end'])

    def activate_yearly(self):
        today = timezone.now().date()
        self.plan = 'YEARLY'
        self.subscription_start = today
        self.subscription_end = today + timedelta(days=365)
        self.save(update_fields=['plan', 'subscription_start', 'subscription_end'])

    def is_trial_valid(self):
        if self.plan != 'FREE_TRIAL':
            return False
        if not self.trial_end:
            return False
        return timezone.now().date() <= self.trial_end

    def is_subscription_valid(self):
        if self.plan in ['MONTHLY', 'YEARLY']:
            return bool(self.subscription_end) and timezone.now().date() <= self.subscription_end
        return False