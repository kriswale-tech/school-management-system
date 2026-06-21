from accounts.models import PhoneOtp, User
from schools.models import School

PHONE = '+233244567890'
LOCAL_PHONE = '0244567890'
OTP = '123456'


def signup_payload(**overrides):
    data = {
        'school_name': 'Test Academy',
        'first_name': 'Kofi',
        'last_name': 'Mensah',
        'phone_number': LOCAL_PHONE,
        'email': 'kofi@test.com',
    }
    data.update(overrides)
    return data


def create_school(name='Test School', phone_number=PHONE):
    return School.objects.create(name=name, phone_number=phone_number)


def create_user(
    *,
    phone_number=PHONE,
    email='admin@test.com',
    school=None,
    role=User.RoleChoices.ADMIN,
    is_active=False,
    first_name='Kofi',
    last_name='Mensah',
):
    school = school or create_school(phone_number=phone_number)
    user = User.objects.create(
        phone_number=phone_number,
        email=email,
        first_name=first_name,
        last_name=last_name,
        school=school,
        role=role,
        is_active=is_active,
    )
    user.set_unusable_password()
    user.save(update_fields=['password'])
    return user


def create_phone_otp(
    phone_number=PHONE,
    otp=OTP,
    purpose=PhoneOtp.Purpose.SIGNUP,
    attempts=0,
    is_verified=False,
    expires_at=None,
    sent_at=None,
):
    from django.utils import timezone

    return PhoneOtp.objects.create(
        phone_number=phone_number,
        purpose=purpose,
        otp=otp,
        attempts=attempts,
        is_verified=is_verified,
        expires_at=expires_at or PhoneOtp.default_expires_at(),
        sent_at=sent_at or timezone.now(),
    )


def set_client_auth_cookies(client, user):
    from django.conf import settings
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    client.cookies[settings.SIMPLE_JWT['AUTH_COOKIE']] = str(refresh.access_token)
    client.cookies[settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH']] = str(refresh)
    return refresh

