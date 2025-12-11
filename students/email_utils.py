from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
import random
import string


def generate_otp(length=6):
    """
    Generate a random numeric OTP
    """
    return ''.join(random.choices(string.digits, k=length))


def send_otp_email(student, otp, validity_minutes=10):
    """
    Send OTP email to student for password reset

    Args:
        student: Student object
        otp: Generated OTP code
        validity_minutes: OTP validity period in minutes (default: 10)

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    subject = f'Password Reset OTP - {otp}'

    # Plain text version
    text_content = f"""
Password Reset Request

Hello {student.get_full_name()},

We received a request to reset the password for your account associated with USN: {student.usn}

Your One-Time Password (OTP) for password reset is: {otp}

This OTP is valid for {validity_minutes} minutes only. Do not share this code with anyone.

If you didn't request this password reset, please ignore this email or contact support if you have concerns.

Security Tips:
- Never share your OTP with anyone
- Our team will never ask for your password or OTP
- Always verify the sender's email address

This is an automated email. Please do not reply to this message.

Best regards,
Event Assistant Team
"""

    # HTML version
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif;">
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f4f4f4;">
        <div style="background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Password Reset Request</h1>
            </div>

            <!-- Content -->
            <div style="padding: 40px 30px;">
                <p style="color: #333333; font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                    Hello <strong>{student.get_full_name()}</strong>,
                </p>

                <p style="color: #666666; font-size: 14px; line-height: 1.6; margin-bottom: 20px;">
                    We received a request to reset the password for your account associated with USN: <strong>{student.usn}</strong>
                </p>

                <p style="color: #666666; font-size: 14px; line-height: 1.6; margin-bottom: 30px;">
                    Your One-Time Password (OTP) for password reset is:
                </p>

                <!-- OTP Box -->
                <div style="background-color: #f8f9fa; border: 2px dashed #667eea; border-radius: 8px; padding: 20px; text-align: center; margin-bottom: 30px;">
                    <div style="font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 8px;">
                        {otp}
                    </div>
                </div>

                <!-- Important Info -->
                <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
                    <p style="color: #856404; font-size: 13px; margin: 0; line-height: 1.5;">
                        <strong>⚠️ Important:</strong> This OTP is valid for <strong>{validity_minutes} minutes</strong> only. Do not share this code with anyone.
                    </p>
                </div>

                <p style="color: #666666; font-size: 14px; line-height: 1.6; margin-bottom: 20px;">
                    If you didn't request this password reset, please ignore this email or contact support if you have concerns.
                </p>

                <!-- Security Tips -->
                <div style="background-color: #e7f3ff; padding: 15px; border-radius: 4px; margin-top: 20px;">
                    <p style="color: #004085; font-size: 13px; margin: 0 0 10px 0; font-weight: bold;">
                        🔒 Security Tips:
                    </p>
                    <ul style="color: #004085; font-size: 12px; margin: 0; padding-left: 20px;">
                        <li>Never share your OTP with anyone</li>
                        <li>Our team will never ask for your password or OTP</li>
                        <li>Always verify the sender's email address</li>
                    </ul>
                </div>
            </div>

            <!-- Footer -->
            <div style="background-color: #f8f9fa; padding: 20px 30px; text-align: center; border-top: 1px solid #e0e0e0;">
                <p style="color: #999999; font-size: 12px; margin: 0 0 10px 0;">
                    This is an automated email. Please do not reply to this message.
                </p>
                <p style="color: #999999; font-size: 12px; margin: 0;">
                    © 2024 Event Assistant. All rights reserved.
                </p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        print(f"OTP email sent successfully to {student.email}")
        return True

    except Exception as e:
        print(f"Failed to send OTP email: {str(e)}")
        return False


def send_password_reset_success_email(student, login_url=None):
    """
    Send confirmation email after successful password reset

    Args:
        student: Student object
        login_url: URL to login page (optional)

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if login_url is None:
        base_url = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'http://localhost:8000'
        login_url = f"{base_url}/login/"

    subject = 'Password Reset Successful'

    # Plain text version
    text_content = f"""
Password Reset Successful

Hello {student.get_full_name()},

Your password has been successfully reset for USN: {student.usn}

You can now login to your account using your new password.

Login URL: {login_url}

SECURITY ALERT: If you did not perform this password reset, please contact our support team immediately.

Best regards,
Event Assistant Team

This is an automated email. Please do not reply to this message.
"""

    # HTML version
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif;">
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f4f4f4;">
        <div style="background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); padding: 30px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">✓ Password Reset Successful</h1>
            </div>

            <!-- Content -->
            <div style="padding: 40px 30px;">
                <p style="color: #333333; font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                    Hello <strong>{student.get_full_name()}</strong>,
                </p>

                <p style="color: #666666; font-size: 14px; line-height: 1.6; margin-bottom: 20px;">
                    Your password has been successfully reset for USN: <strong>{student.usn}</strong>
                </p>

                <!-- Success Icon -->
                <div style="text-align: center; margin: 30px 0;">
                    <div style="display: inline-block; width: 80px; height: 80px; background-color: #d4edda; border-radius: 50%;">
                        <span style="color: #28a745; font-size: 48px; line-height: 80px;">✓</span>
                    </div>
                </div>

                <p style="color: #666666; font-size: 14px; line-height: 1.6; margin-bottom: 20px;">
                    You can now login to your account using your new password.
                </p>

                <!-- Warning Box -->
                <div style="background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
                    <p style="color: #721c24; font-size: 13px; margin: 0; line-height: 1.5;">
                        <strong>⚠️ Security Alert:</strong> If you did not perform this password reset, please contact our support team immediately.
                    </p>
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <a href="{login_url}" style="display: inline-block; padding: 12px 30px; background-color: #667eea; color: #ffffff; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Login to Your Account
                    </a>
                </div>
            </div>

            <!-- Footer -->
            <div style="background-color: #f8f9fa; padding: 20px 30px; text-align: center; border-top: 1px solid #e0e0e0;">
                <p style="color: #999999; font-size: 12px; margin: 0 0 10px 0;">
                    This is an automated email. Please do not reply to this message.
                </p>
                <p style="color: #999999; font-size: 12px; margin: 0;">
                    © 2024 Event Assistant. All rights reserved.
                </p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        print(f"Password reset success email sent to {student.email}")
        return True

    except Exception as e:
        print(f"Failed to send success email: {str(e)}")
        return False


def send_failed_attempt_notification(student, attempt_count, cooldown_minutes=15, ip_address=None):
    """
    Send security alert email for multiple failed password reset attempts

    Args:
        student: Student object
        attempt_count: Number of failed attempts
        cooldown_minutes: Cooldown period in minutes (default: 15)
        ip_address: IP address of the request (optional)

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    timestamp = timezone.now().strftime('%B %d, %Y at %I:%M %p')
    ip_display = ip_address if ip_address else 'Not available'

    base_url = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'http://localhost:8000'
    support_url = f"{base_url}/support/"

    subject = '⚠️ Security Alert - Multiple Failed Password Reset Attempts'

    # Plain text version
    text_content = f"""
SECURITY ALERT - Multiple Failed Password Reset Attempts

Hello {student.get_full_name()},

We detected multiple failed password reset attempts for your account (USN: {student.usn}).

Details:
- Time: {timestamp}
- IP Address: {ip_display}
- Failed Attempts: {attempt_count}

If this was you, please wait for {cooldown_minutes} minutes before trying again. 

If this wasn't you, we recommend changing your password immediately and contacting support.

Contact Support: {support_url}

This is an automated security notification.

Best regards,
Event Assistant Team
"""

    # HTML version
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif;">
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f4f4f4;">
        <div style="background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 30px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">⚠️ Security Alert</h1>
            </div>

            <!-- Content -->
            <div style="padding: 40px 30px;">
                <p style="color: #333333; font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                    Hello <strong>{student.get_full_name()}</strong>,
                </p>

                <p style="color: #666666; font-size: 14px; line-height: 1.6; margin-bottom: 20px;">
                    We detected multiple failed password reset attempts for your account (USN: <strong>{student.usn}</strong>).
                </p>

                <div style="background-color: #fff3cd; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <p style="color: #856404; font-size: 14px; margin: 0 0 10px 0;"><strong>Details:</strong></p>
                    <ul style="color: #856404; font-size: 13px; margin: 0; padding-left: 20px;">
                        <li>Time: {timestamp}</li>
                        <li>IP Address: {ip_display}</li>
                        <li>Attempts: {attempt_count}</li>
                    </ul>
                </div>

                <p style="color: #666666; font-size: 14px; line-height: 1.6; margin-bottom: 20px;">
                    If this was you, please wait for <strong>{cooldown_minutes} minutes</strong> before trying again. If this wasn't you, we recommend changing your password immediately.
                </p>

                <div style="text-align: center; margin-top: 30px;">
                    <a href="{support_url}" style="display: inline-block; padding: 12px 30px; background-color: #dc3545; color: #ffffff; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Contact Support
                    </a>
                </div>
            </div>

            <!-- Footer -->
            <div style="background-color: #f8f9fa; padding: 20px 30px; text-align: center; border-top: 1px solid #e0e0e0;">
                <p style="color: #999999; font-size: 12px; margin: 0 0 10px 0;">
                    This is an automated security notification.
                </p>
                <p style="color: #999999; font-size: 12px; margin: 0;">
                    © 2024 Event Assistant. All rights reserved.
                </p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        print(f"Security alert email sent to {student.email}")
        return True

    except Exception as e:
        print(f"Failed to send security alert email: {str(e)}")
        return False