"""Serializers for the staff directory (list, stats, detail) endpoints."""

from rest_framework import serializers


class StaffDeskRowSerializer(serializers.Serializer):
    """One row in the staff directory table."""

    id = serializers.UUIDField(
        help_text='User id — public identifier used in detail routes.',
    )
    membership_id = serializers.UUIDField(
        help_text='School membership id for this person in the active school.',
    )
    full_name = serializers.CharField(help_text='First and last name combined.')
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField(
        allow_null=True,
        help_text='Email address, shown as the primary contact line.',
    )
    phone_number = serializers.CharField(
        help_text='Primary phone number used for login.',
    )
    role = serializers.CharField(
        help_text='Role in this school: admin, teacher, accountant, or staff.',
    )
    is_active = serializers.BooleanField(
        help_text='Whether membership in this school is active.',
    )
    date_added = serializers.DateTimeField(
        help_text='When this person was added to the school (membership created_at).',
    )
    profile_picture = serializers.URLField(
        allow_null=True,
        help_text='Profile picture URL when one has been uploaded.',
    )
    is_class_teacher = serializers.BooleanField(
        help_text=(
            'True when role is teacher and the person has a class-teacher '
            'assignment in the school active term.'
        ),
    )
    is_subject_teacher = serializers.BooleanField(
        help_text=(
            'True when role is teacher and the person has a subject-teaching '
            'assignment in the school active term.'
        ),
    )


class StaffDeskStatsSerializer(serializers.Serializer):
    """Filter-aware staff counts for the directory stats cards."""

    total_staff = serializers.IntegerField(
        help_text='Total memberships matching the current search/role filters.',
    )
    teachers = serializers.IntegerField(
        help_text='Teachers within the filtered set.',
    )
    accountants = serializers.IntegerField(
        help_text='Accountants within the filtered set.',
    )
    admins = serializers.IntegerField(
        help_text='Admins within the filtered set.',
    )


class StaffDeskClassTeacherAssignmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    class_level_id = serializers.UUIDField()
    class_level_name = serializers.CharField()
    stream_id = serializers.UUIDField(allow_null=True)
    stream_name = serializers.CharField(allow_null=True)
    display_name = serializers.CharField(
        help_text='Class label for cards (stream full name or class level name).',
    )
    students_count = serializers.IntegerField(
        help_text='Enrolled students in this managed class for the active term.',
    )


class StaffDeskTeachingAssignmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    class_subject_id = serializers.UUIDField()
    class_level_id = serializers.UUIDField()
    class_level_name = serializers.CharField()
    subject_id = serializers.UUIDField()
    subject_name = serializers.CharField()
    stream_id = serializers.UUIDField(allow_null=True)
    stream_name = serializers.CharField(allow_null=True)
    subject_group_id = serializers.UUIDField(allow_null=True)
    subject_group_name = serializers.CharField(allow_null=True)
    display_class_name = serializers.CharField(
        help_text='Class label shown under the subject on workspace cards.',
    )
    students_count = serializers.IntegerField(
        help_text='Students covered by this teaching assignment in the active term.',
    )


class StaffDeskProfileSerializer(serializers.Serializer):
    profile_picture = serializers.URLField(allow_null=True)
    bio = serializers.CharField(allow_null=True)
    date_of_birth = serializers.DateField(allow_null=True)
    gender = serializers.CharField(allow_null=True)
    address = serializers.CharField(allow_null=True)
    phone_number_alt = serializers.CharField(allow_null=True)


class StaffDeskDetailSerializer(StaffDeskRowSerializer):
    """Staff member detail for the directory details page."""

    profile = StaffDeskProfileSerializer(allow_null=True)
    school_id = serializers.UUIDField()
    school_setup_completed = serializers.BooleanField()
    class_teacher_assignments = StaffDeskClassTeacherAssignmentSerializer(
        many=True,
        help_text='Class-teacher slots for the active term (teachers only).',
    )
    teaching_assignments = StaffDeskTeachingAssignmentSerializer(
        many=True,
        help_text='Subject-teaching slots for the active term (teachers only).',
    )
