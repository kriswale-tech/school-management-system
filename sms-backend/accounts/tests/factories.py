from accounts.models import PhoneOtp, Role, User
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


def create_admin_role():
    return Role.objects.get_or_create(
        name=Role.RoleChoices.ADMIN,
        defaults={'description': 'School administrator'},
    )[0]


def create_school(name='Test School', phone_number=PHONE):
    return School.objects.create(name=name, phone_number=phone_number)


def create_user(
    *,
    phone_number=PHONE,
    email='admin@test.com',
    school=None,
    role=None,
    is_active=False,
    first_name='Kofi',
    last_name='Mensah',
):
    school = school or create_school(phone_number=phone_number)
    role = role or create_admin_role()
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


def create_phone_otp(phone_number=PHONE, otp=OTP, attempts=0, is_verified=False):
    return PhoneOtp.objects.create(
        phone_number=phone_number,
        otp=otp,
        attempts=attempts,
        is_verified=is_verified,
    )
