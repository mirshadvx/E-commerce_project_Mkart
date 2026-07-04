import logging
import os
import requests
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

MAILJET_EMAIL_URL = "https://api.mailjet.com/v3.1/send"
MAILJET_API_KEY = os.environ.get("MAILJET_API_KEY")
MAILJET_SECRET_KEY = os.environ.get("MAILJET_SECRET_KEY")
MAILJET_FROM_EMAIL = os.environ.get(
    "MAILJET_FROM_EMAIL",
    os.environ.get("EMAIL_HOST_USER", "noreply@example.com"),
)
MAILJET_FROM_NAME = os.environ.get("MAILJET_FROM_NAME", "Timexo")


def _send_mailjet_email(to_email, subject, template_name, context):
    if not MAILJET_API_KEY or not MAILJET_SECRET_KEY:
        logger.error("Mailjet credentials are not configured; email was not sent to %s", to_email)
        return False

    try:
        html_content = render_to_string(template_name, context)
        response = requests.post(
            MAILJET_EMAIL_URL,
            auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY),
            headers={"Content-Type": "application/json"},
            json={
                "Messages": [
                    {
                        "From": {
                            "Email": MAILJET_FROM_EMAIL,
                            "Name": MAILJET_FROM_NAME,
                        },
                        "To": [{"Email": to_email}],
                        "Subject": subject,
                        "HTMLPart": html_content,
                    }
                ]
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Mailjet API request failed for %s", to_email)
        return False
    except Exception:
        logger.exception("Unexpected email rendering/sending failure for %s", to_email)
        return False

    logger.info("Email sent to %s with subject: %s", to_email, subject)
    return True


def send_otp_email(email, username, otp):
    return _send_mailjet_email(
        to_email=email,
        subject="Verify Your Email - Timexo",
        template_name="emails/otp_email.html",
        context={"username": username, "otp": otp},
    )


def send_password_reset_email(email, username, reset_link):
    return _send_mailjet_email(
        to_email=email,
        subject="Reset Your Timexo Password",
        template_name="emails/password_reset_email.html",
        context={"username": username, "reset_link": reset_link},
    )


def send_welcome_email(email, username):
    return _send_mailjet_email(
        to_email=email,
        subject="Welcome to Timexo",
        template_name="emails/welcome_email.html",
        context={"username": username},
    )
