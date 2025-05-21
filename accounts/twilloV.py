import os
from twilio.rest import Client
from django.conf import settings


def send_sms(phone_number, code):
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    client = Client(account_sid, auth_token)
    client.messages.create(
        from_=settings.TWILIO_PHONE_NUMBER,
        content_sid='HXb5b62575e6e4ff6129ad7c8efe1f983e',
        content_variables=f'{"1":{code}}',
        to=f'whatsapp:+{phone_number}'
    )

