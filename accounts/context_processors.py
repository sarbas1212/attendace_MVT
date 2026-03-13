from django.utils import timezone

def subscription_context(request):
    """
    Provides org subscription/trial status globally to templates.
    """
    if not request.user.is_authenticated:
        return {}

    org = getattr(request.user, "organization", None)
    if not org:
        return {}

    today = timezone.now().date()

    trial_days_left = None
    if getattr(org, "plan", None) == "FREE_TRIAL" and org.trial_end:
        trial_days_left = (org.trial_end - today).days

    return {
        "org_plan": getattr(org, "plan", None),
        "trial_end": getattr(org, "trial_end", None),
        "trial_days_left": trial_days_left,
        "subscription_end": getattr(org, "subscription_end", None),
        "subscription_valid": org.is_subscription_valid() if hasattr(org, "is_subscription_valid") else False,
        "trial_valid": org.is_trial_valid() if hasattr(org, "is_trial_valid") else False,
    }