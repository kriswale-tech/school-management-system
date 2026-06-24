import requests
from django.conf import settings


ARKESEL_SMS_URL = 'https://sms.arkesel.com/api/v2/sms/send'


def send_sms(phone_number: str, message: str) -> dict:
    
    headers = {
        "api-key": settings.ARKESEL_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "sender": settings.ARKESEL_SMS_SENDER,
        "message": message,
        "recipients": [phone_number],
        "sandbox": settings.DEBUG,
    }

    print(headers)
    print(payload)

    response = requests.post(
        ARKESEL_SMS_URL,
        json=payload,
        headers=headers,
        timeout=15,
    )

    print(response.json())

    response.raise_for_status()

    return response.json()