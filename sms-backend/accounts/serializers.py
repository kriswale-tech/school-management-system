from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from shared.helpers import format_phone_number
from accounts.models import User, Profile
from accounts.services.users import (
    MANAGEABLE_ROLES_BY_REQUESTER,
    PROFILE_FIELDS,
    update_user,
)
from academics.services.curriculum import provision_school_curriculum
from schools.models import School, SchoolSetup


class AdminSignUpSerializer(serializers.Serializer):
    school_name = serializers.CharField(max_length=255)
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=15)
    email = serializers.EmailField()

    def validate_phone_number(self, value):
        try:
            phone = format_phone_number(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

        if User.objects.filter(phone_number=phone, is_active=True).exists():
            raise serializers.ValidationError('Account with this phone number already exists')

        return phone

    def validate_email(self, value):
        phone = self.initial_data.get('phone_number')
        formatted_phone = None

        if phone:
            try:
                formatted_phone = format_phone_number(phone)
            except ValueError:
                pass

        qs = User.objects.filter(email=value, is_active=True)
        if formatted_phone:
            qs = qs.exclude(phone_number=formatted_phone)

        if qs.exists():
            raise serializers.ValidationError('Email already exists')

        return value

    def create(self, validated_data):
        with transaction.atomic():
            existing_user = User.objects.filter(
                phone_number=validated_data['phone_number'],
                is_active=False,
            ).select_related('school').first()

            if existing_user:
                school = existing_user.school
                school.name = validated_data['school_name']
                school.phone_number = validated_data['phone_number']
                school.save()

                existing_user.email = validated_data['email']
                existing_user.first_name = validated_data['first_name']
                existing_user.last_name = validated_data['last_name']
                existing_user.role = User.RoleChoices.ADMIN
                existing_user.save()
                SchoolSetup.objects.get_or_create(school=school)
                return existing_user

            school = School.objects.create(
                name=validated_data['school_name'],
                phone_number=validated_data['phone_number'],
            )
            SchoolSetup.objects.create(school=school)
            provision_school_curriculum(school)

            return User.objects.create(
                phone_number=validated_data['phone_number'],
                email=validated_data['email'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                school=school,
                role=User.RoleChoices.ADMIN,
                is_active=False,
            )


class AdminVerifyOtpSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)

    def validate_phone_number(self, value):
        try:
            return format_phone_number(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class ResendOtpSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)

    def validate_phone_number(self, value):
        try:
            return format_phone_number(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            'profile_picture', 'bio', 'date_of_birth',
            'gender', 'address', 'phone_number_alt',
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    school_setup_completed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'first_name', 'last_name',
            'phone_number', 'email', 'role', 'is_active', 'profile',
            'school_setup_completed',
            'school_id',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()
    
    @extend_schema_field(serializers.BooleanField())
    def get_school_setup_completed(self, obj):
        return obj.school.setup_completed

    @extend_schema_field(ProfileSerializer(allow_null=True))
    def get_profile(self, obj):
        try:
            return ProfileSerializer(obj.profile).data
        except Profile.DoesNotExist:
            return None


class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField(read_only=True)
    retry_after_seconds = serializers.IntegerField(read_only=True, required=False)


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
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
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
        try:
            phone = format_phone_number(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

        if User.objects.filter(phone_number=phone).exists():
            raise serializers.ValidationError('Account with this phone number already exists')

        return phone

    def validate_role(self, value):
        request = self.context.get('request')
        if not request:
            return value

        allowed_roles = MANAGEABLE_ROLES_BY_REQUESTER.get(request.user.role, set())
        if value not in allowed_roles:
            raise serializers.ValidationError(
                'You do not have permission to add a user with this role.',
            )

        return value

    def validate_email(self, value):
        if not value:
            return value

        if User.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError('Email already exists')

        return value

    def validate_phone_number_alt(self, value):
        if not value:
            return value

        try:
            return format_phone_number(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def create(self, validated_data):
        profile_data = {
            field: validated_data.pop(field)
            for field in PROFILE_FIELDS
            if field in validated_data
        }
        school = self.context['school']

        user = User.objects.create(
            school=school,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data['phone_number'],
            role=validated_data['role'],
            email=validated_data.get('email') or '',
            is_active=True,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])

        Profile.objects.create(user=user, **profile_data)
        return user


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
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
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

        allowed_roles = MANAGEABLE_ROLES_BY_REQUESTER.get(request.user.role, set())
        if value not in allowed_roles:
            raise serializers.ValidationError(
                'You do not have permission to assign this role.',
            )

        return value

    def validate_phone_number(self, value):
        try:
            phone = format_phone_number(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

        queryset = User.objects.filter(phone_number=phone)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError('Account with this phone number already exists')

        return phone

    def validate_email(self, value):
        if not value:
            return value

        target = self.instance
        queryset = User.objects.filter(email=value, is_active=True)
        if target:
            queryset = queryset.exclude(pk=target.pk)

        if queryset.exists():
            raise serializers.ValidationError('Email already exists')

        return value

    def validate_phone_number_alt(self, value):
        if not value:
            return value

        try:
            return format_phone_number(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def update(self, instance, validated_data):
        return update_user(
            self.context['request'].user,
            instance,
            validated_data,
        )


class DeleteUserResponseSerializer(serializers.Serializer):
    hard_deleted = serializers.BooleanField()
    user = UserSerializer(required=False, allow_null=True)

