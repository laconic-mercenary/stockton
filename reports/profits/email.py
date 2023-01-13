
import smtplib

from . import config

from email.message import EmailMessage
from email.utils import make_msgid

__GMAIL_PROVIDER='smtp.gmail.com'
__GMAIL_PORT=465

def __send_smtp_email(msg, pwd, provider, port):
    with smtplib.SMTP_SSL(provider, port) as email_connection:
        email_connection.login(msg['From'], pwd)
        email_connection.send_message(msg)

def __send_gmail_email(msg, pwd):
    __send_smtp_email(msg, pwd, __GMAIL_PROVIDER, __GMAIL_PORT)

def send_email(html_report):
    msg = EmailMessage()
    asparagus_cid = make_msgid()
    msg.add_alternative(html_report.format(asparagus_cid=asparagus_cid[1:-1]), subtype='html')

    msg['Subject'] = config.get_email_subject()
    msg['From'] = config.get_from_email()
    msg['To'] = config.get_to_email()
    pwd = config.get_email_password()

    __send_gmail_email(msg, pwd)
