# organizations/models.py

from django.db import models
from django.utils import timezone
from datetime import timedelta


class Organization(models.Model):

    PLAN_CHOICES = [
        ('FREE', 'Free'),
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]

    name = models.CharField(max_length=150)
    email = models.EmailField()

    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='FREE')

    subscription_start = models.DateField(null=True, blank=True)
    subscription_end = models.DateField(null=True, blank=True)

    razorpay_order_id = models.CharField(max_length=150, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=150, null=True, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def activate_monthly(self):
        self.plan = "MONTHLY"
        self.subscription_start = timezone.now().date()
        self.subscription_end = self.subscription_start + timedelta(days=30)
        self.save()

    def activate_yearly(self):
        self.plan = "YEARLY"
        self.subscription_start = timezone.now().date()
        self.subscription_end = self.subscription_start + timedelta(days=365)
        self.save()

    def is_subscription_valid(self):
        if self.plan == "FREE":
            return True

        if self.subscription_end:
            return timezone.now().date() <= self.subscription_end

        return False

    def __str__(self):
        return self.name