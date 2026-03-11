from django.shortcuts import render
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from accounts.decorators import role_required


# Create your views here.
@role_required(['ADMIN'])
def create_order(request):
    plan = request.POST.get('plan')

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    if plan == "MONTHLY":
        amount = 99900  # ₹999
    elif plan == "YEARLY":
        amount = 999900  # ₹9999
    else:
        return JsonResponse({"error": "Invalid plan"}, status=400)

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    # Save order ID temporarily
    org = request.user.organization
    org.razorpay_order_id = order["id"]
    org.save()

    return JsonResponse({
        "order_id": order["id"],
        "amount": amount,
        "key": settings.RAZORPAY_KEY_ID
    })


@csrf_exempt
@role_required(['ADMIN'])
def payment_success(request):
    if request.method == "POST":
        plan = request.POST.get("plan")
        payment_id = request.POST.get("payment_id")

        org = request.user.organization
        org.razorpay_payment_id = payment_id

        if plan == "MONTHLY":
            org.activate_monthly()
        elif plan == "YEARLY":
            org.activate_yearly()

        return JsonResponse({"status": "success"})

    return JsonResponse({"error": "Invalid request"}, status=400)