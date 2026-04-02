from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings

def send_admin_activation_email(user, request):
    """Generates a secure token link and sends activation email to Admin."""
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Build the relative path
    activation_path = reverse('activate_admin_account', kwargs={
        'uidb64': uid,
        'token': token
    })
    
    # Build the full absolute URL (http://domain.com/accounts/activate/...)
    activation_link = request.build_absolute_uri(activation_path)

    subject = "Activate Your Admin Account"
    message = (
        f"Hello {user.first_name},\n\n"
        f"Thank you for registering as the system administrator.\n\n"
        f"Please activate your account by clicking the link below:\n\n"
        f"{activation_link}\n\n"
        f"If you did not register, please ignore this email.\n\n"
        f"Thank you."
    )
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )