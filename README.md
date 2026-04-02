.

🚀 AttendancePro – Multi-Organization SaaS Attendance System

AttendancePro is a SaaS-based multi-organization attendance management system built using Django.
Each organization gets a 7-day free trial and must subscribe to a monthly or yearly plan to continue using the platform.

🌟 Core Features

🏢 Multi-Organization (SaaS Architecture)
Multiple organizations can register
Each organization has isolated data
Tenant-style architecture using ForeignKey relationships
Subscription-based access control
Trial and paid plan enforcement
💼 Subscription Model (SaaS Logic)
🆓 7-Day Free Trial
Automatically activated when an organization registers
Trial expiry tracked using date fields
Access restricted after trial ends
💳 Paid Subscription (Organization Level Only)
Monthly Plan
Yearly Plan
Only Organization Admin can purchase subscription
Integrated with Razorpay payment gateway
🔒 Subscription Enforcement
Middleware or access checks block features if:
Trial expired
No active subscription
Teachers and Students depend on organization’s subscription status

👉 This shows strong SaaS business logic implementation.

🔐 Role-Based Access Control (RBAC)
👑 Organization Admin
Manage organization profile
Manage teachers and students
Import students via Excel
View attendance reports
Purchase & manage subscription
👨‍🏫 Teacher
Mark attendance
View assigned student records
Track attendance history
🎓 Student
View personal attendance records
Access dashboard
📊 Excel Bulk Import
Supports .xlsx, .xls, .csv
Built with Pandas & OpenPyXL
Duplicate roll numbers update existing records
Validation before saving to database
Optimized bulk operations
☁️ AWS S3 Integration
Media files stored in AWS S3
Configured using boto3 and django-storages
Region: ap-south-1
Production-ready cloud storage
📧 Email System
Gmail SMTP integration
TLS-enabled secure email sending
Used for:
Organization registration
Trial notifications
Subscription confirmation
🛠️ Tech Stack
Category	Technology
Backend	Django 6
Database	SQLite (Dev) / PostgreSQL (Production Ready)
Cloud Storage	AWS S3
Excel Processing	Pandas, OpenPyXL
Payment Integration	Razorpay
Authentication	Django Auth (RBAC)
Deployment	Gunicorn + Whitenoise
🧠 Architecture Highlights
Multi-tenant data isolation
Subscription-based middleware enforcement
Role-based authentication & authorization
Cloud storage integration
Production-ready configuration
🔐 Environment Configuration

⚠️ Never commit .env file.

Required variables:

SECRET_KEY=your_secret_key
DEBUG=True

# Email
EMAIL_HOST_USER=your_email
EMAIL_HOST_PASSWORD=your_app_password

# Razorpay
RAZORPAY_KEY_ID=your_key
RAZORPAY_KEY_SECRET=your_secret

# AWS
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_STORAGE_BUCKET_NAME=your_bucket
AWS_S3_REGION_NAME=ap-south-1
🔥 Why This Project Is Strong

This project demonstrates:

SaaS subscription model implementation
Trial management logic
Payment gateway integration
Multi-tenant architecture
Role-based access control
Cloud storage handling
Bulk data processing

This is closer to a real-world ERP SaaS product than a simple attendance app.
