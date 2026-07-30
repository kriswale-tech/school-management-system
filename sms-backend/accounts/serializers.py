from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from shared.helpers import format_phone_number
from accounts.models import Profile, SchoolMembership, User
from accounts.services.registration import (
    create_additional_school,
    ensure_school_name_available,
    register_school_admin,
)
from accounts.services.users import (
    add_school_member,
    email_taken,
    manageable_roles,
    update_school_member,
)

GENDER_CHOICES = [('male', 'Male'), ('female', 'Female'), ('other', 'Other')]


def _formatted_phone(value: str) -> str:
    try:
        return format_phone_number(value)
    except ValueError as exc:
        raise serializers.ValidationError(str(exc))


class AdminSignUpSerializer(serializers.Serializer):
    school_name = serializers.CharField(max_length=255)
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=15)
    email = serializers.EmailField()

    def validate_phone_number(self, value):
        return _formatted_phone(value)

    def validate_email(self, value):
        phone = self.initial_data.get('phone_number')
        formatted_phone = None

        if phone:
            try:
                formatted_phone = format_phone_number(phone)
            except ValueError:
                pass

        queryset = User.objects.filter(email=value, is_active=True)
        if formatted_phone:
            queryset = queryset.exclude(phone_number=formatted_phone)

        if queryset.exists():
            raise serializers.ValidationError('Email already exists')

        return value

    def validate(self, attrs):
        # Catch same-name collisions before OTP so the form can fix the name.
        existing = User.objects.filter(
            phone_number=attrs['phone_number'],
            is_active=True,
        ).first()
        if existing is not None:
            ensure_school_name_available(existing, attrs['school_name'])
        return attrs

    def create(self, validated_data):
        return register_school_admin(validated_data)


class CreateSchoolSerializer(serializers.Serializer):
    school_name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)

    def validate_phone_number(self, value):
        if not value:
            return value
        return _formatted_phone(value)

    def validate_school_name(self, value):
        ensure_school_name_available(self.context['request'].user, value)
        return value

    def create(self, validated_data):
        return create_additional_school(self.context['request'].user, validated_data)


class AdminVerifyOtpSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)

    def validate_phone_number(self, value):
        return _formatted_phone(value)


class ResendOtpSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)

    def validate_phone_number(self, value):
        return _formatted_phone(value)


class SelectSchoolSerializer(serializers.Serializer):
    school_id = serializers.UUIDField()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            'profile_picture', 'bio', 'date_of_birth',
            'gender', 'address', 'phone_number_alt',
        ]


def _profile_data(user: User):
    try:
        return ProfileSerializer(user.profile).data
    except Profile.DoesNotExist:
        return None


class SchoolMembershipSerializer(serializers.ModelSerializer):
    """One school a user can act in; used to populate the school picker."""

    school_id = serializers.UUIDField(read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    school_logo = serializers.ImageField(source='school.logo', read_only=True)
    school_setup_completed = serializers.BooleanField(
        source='school.setup_completed',
        read_only=True,
    )

    class Meta:
        model = SchoolMembership
        fields = [
            'id', 'school_id', 'school_name', 'school_logo',
            'role', 'school_setup_completed', 'last_active_at',
        ]


class UserSerializer(serializers.ModelSerializer):
    """The authenticated identity plus the school the request is scoped to."""

    profile = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    school_id = serializers.SerializerMethodField()
    school_setup_completed = serializers.SerializerMethodField()
    schools = serializers.SerializerMethodField()
    requires_school_selection = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'first_name', 'last_name',
            'phone_number', 'email', 'role', 'is_active', 'profile',
            'school_setup_completed', 'school_id',
            'schools', 'requires_school_selection',
        ]

    @property
    def _membership(self) -> SchoolMembership | None:
        return self.context.get('membership')

    def get_full_name(self, obj):
        return obj.get_full_name()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_role(self, obj):
        membership = self._membership
        return membership.role if membership else None

    @extend_schema_field(serializers.UUIDField(allow_null=True))
    def get_school_id(self, obj):
        membership = self._membership
        return str(membership.school_id) if membership else None

    @extend_schema_field(serializers.BooleanField(allow_null=True))
    def get_school_setup_completed(self, obj):
        membership = self._membership
        return membership.school.setup_completed if membership else None

    @extend_schema_field(SchoolMembershipSerializer(many=True))
    def get_schools(self, obj):
        return SchoolMembershipSerializer(
            self.context.get('memberships', []),
            many=True,
        ).data

    @extend_schema_field(serializers.BooleanField())
    def get_requires_school_selection(self, obj):
        return self._membership is None

    @extend_schema_field(ProfileSerializer(allow_null=True))
    def get_profile(self, obj):
        return _profile_data(obj)


class SchoolMemberSerializer(serializers.Serializer):
    """A person as seen from inside one school; role and status are per-school."""

    id = serializers.UUIDField(source='user.id', read_only=True)
    membership_id = serializers.UUIDField(source='id', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    role = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    school_id = serializers.UUIDField(read_only=True)
    full_name = serializers.SerializerMethodField()
    school_setup_completed = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name()

    @extend_schema_field(serializers.BooleanField())
    def get_school_setup_completed(self, obj):
        return obj.school.setup_completed

    @extend_schema_field(ProfileSerializer(allow_null=True))
    def get_profile(self, obj):
        return _profile_data(obj.user)


class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField(read_only=True)
    retry_after_seconds = serializers.IntegerField(read_only=True, required=False)
    linked_existing_account = serializers.BooleanField(read_only=True, required=False)


class AuthResponseSerializer(serializers.Serializer):
    """Login/OTP result, telling the client whether a school must be chosen."""

    message = serializers.CharField(read_only=True)
    requires_school_selection = serializers.BooleanField(read_only=True)
    linked_existing_account = serializers.BooleanField(read_only=True, default=False)
    active_school = SchoolMembershipSerializer(read_only=True, allow_null=True)
    schools = SchoolMembershipSerializer(many=True, read_only=True)


class AddUserSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=15)
    role = serializers.ChoiceField(choices=User.RoleChoices.choices)
    email = serializers.EmailField(required=False, allow_blank=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=GENDER_CHOICES,
        required=False,
        allow_null=True,
    )
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    phone_number_alt = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=15,
    )

    def validate_phone_number(self, value):
        phone = _formatted_phone(value)
        school = self.context['school']

        already_member = SchoolMembership.objects.filter(
            user__phone_number=phone,
            school=school,
            is_active=True,
        ).exists()
        if already_member:
            raise serializers.ValidationError(
                'This person is already a member of this school.',
            )

        return phone

    def validate_role(self, value):
        request = self.context.get('request')
        if not request:
            return value

        if value not in manageable_roles(request.membership.role):
            raise serializers.ValidationError(
                'You do not have permission to add a user with this role.',
            )

        return value

    def validate_email(self, value):
        if not value:
            return value

        # Reusing an existing identity keeps that person's own email, so only a
        # different person holding the address is a conflict.
        phone = self.initial_data.get('phone_number')
        owner = None
        if phone:
            try:
                owner = User.objects.filter(
                    phone_number=format_phone_number(phone),
                ).first()
            except ValueError:
                owner = None

        if email_taken(value, exclude_user=owner):
            raise serializers.ValidationError('Email already exists')

        return value

    def validate_phone_number_alt(self, value):
        if not value:
            return value
        return _formatted_phone(value)

    def create(self, validated_data):
        return add_school_member(self.context['school'], validated_data)


class UpdateUserSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=255, required=False)
    last_name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=User.RoleChoices.choices, required=False)
    phone_number = serializers.CharField(max_length=15, required=False)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=GENDER_CHOICES,
        required=False,
        allow_null=True,
    )
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    phone_number_alt = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=15,
    )

    def validate_role(self, value):
        request = self.context.get('request')
        if not request:
            return value

        if value not in manageable_roles(request.membership.role):
            raise serializers.ValidationError(
                'You do not have permission to assign this role.',
            )

        return value

    def validate_phone_number(self, value):
        return _formatted_phone(value)

    def validate_email(self, value):
        if not value:
            return value

        target_user = self.instance.user if self.instance else None
        if email_taken(value, exclude_user=target_user):
            raise serializers.ValidationError('Email already exists')

        return value

    def validate_phone_number_alt(self, value):
        if not value:
            return value
        return _formatted_phone(value)

    def update(self, instance, validated_data):
        return update_school_member(
            self.context['request'].membership,
            instance,
            validated_data,
        )


class UpdateUserResponseSerializer(serializers.Serializer):
    user = SchoolMemberSerializer(read_only=True)
    linked_existing_user = serializers.BooleanField(read_only=True)


class DeleteUserResponseSerializer(serializers.Serializer):
    hard_deleted = serializers.BooleanField()
    user = SchoolMemberSerializer(required=False, allow_null=True)
