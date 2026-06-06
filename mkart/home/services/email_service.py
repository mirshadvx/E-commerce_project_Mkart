import logging
import os
import requests
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

RESEND_EMAIL_URL = "https://api.resend.com/emails"
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "Timexo <onboarding@resend.dev>")


def _send_resend_email(to_email, subject, template_name, context):
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY is not configured; email was not sent to %s", to_email)
        return False

    try:
        html_content = render_to_string(template_name, context)
        response = requests.post(
            RESEND_EMAIL_URL,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": RESEND_FROM_EMAIL,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Resend API request failed for %s", to_email)
        return False
    except Exception:
        logger.exception("Unexpected email rendering/sending failure for %s", to_email)
        return False

    logger.info("Email sent to %s with subject: %s", to_email, subject)
    return True


def send_otp_email(email, username, otp):
    return _send_resend_email(
        to_email=email,
        subject="Verify Your Email - Timexo",
        template_name="emails/otp_email.html",
        context={"username": username, "otp": otp},
    )


def send_password_reset_email(email, username, reset_link):
    return _send_resend_email(
        to_email=email,
        subject="Reset Your Timexo Password",
        template_name="emails/password_reset_email.html",
        context={"username": username, "reset_link": reset_link},
    )


def send_welcome_email(email, username):
    return _send_resend_email(
        to_email=email,
        subject="Welcome to Timexo",
        template_name="emails/welcome_email.html",
        context={"username": username},
    )
