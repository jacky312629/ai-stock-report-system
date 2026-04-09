import base64
import logging

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import TOKEN_PATH, SCOPES


def get_gmail_service():
    """
    建立 Gmail API service
    """
    if not TOKEN_PATH.exists():
        raise FileNotFoundError(f"找不到 token.json：{TOKEN_PATH}")

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    service = build("gmail", "v1", credentials=creds)
    return service


def send_email_gmail_api(to_email, subject, html_body, plain_body=None):
    try:
        service = get_gmail_service()

        message = MIMEMultipart("alternative")
        message["To"] = to_email
        message["Subject"] = subject

        if plain_body:
            message.attach(MIMEText(plain_body, "plain", "utf-8"))

        message.attach(MIMEText(html_body, "html", "utf-8"))

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        body = {"raw": raw_message}

        result = service.users().messages().send(userId="me", body=body).execute()

        logging.info("Email寄送成功（Gmail API）")
        print("📧 Email 已成功寄出（Gmail API）")
        return result

    except Exception as e:
        logging.exception(f"Email寄送失敗（Gmail API）: {e}")
        print(f"❌ Email寄送失敗: {e}")
        raise