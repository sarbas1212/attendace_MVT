from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.contrib import messages
from django.shortcuts import redirect

from accounts.models import User


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = (sociallogin.user.email or "").strip().lower()

        if not email:
            messages.error(request, "Unable to fetch email from your Google account.")
            raise ImmediateHttpResponse(redirect('login'))

        existing_user = User.objects.filter(email__iexact=email).first()

        if not existing_user:
            messages.error(
                request,
                "No account is linked to this Google email. Please register first or sign in using your email and password."
            )
            raise ImmediateHttpResponse(redirect('login'))

        if not sociallogin.is_existing:
            sociallogin.connect(request, existing_user)

    def is_open_for_signup(self, request, sociallogin):
        return False