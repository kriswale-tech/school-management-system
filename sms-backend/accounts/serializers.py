from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from shared.helpers import format_phone_number
from accounts.models import User, Profile
from shared.services.curriculum import provision_school_curriculum
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

