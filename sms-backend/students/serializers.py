from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from students.models import Student, StudentParent


class StudentClassLevelSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class StudentStreamSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(allow_null=True)
    full_name = serializers.CharField()
    is_default = serializers.BooleanField()

    def to_representation(self, instance):
        return {
            'id': instance.id,
            'name': instance.name or None,
            'full_name': instance.full_name,
            'is_default': instance.is_default,
        }


class PrimaryParentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    phone_number = serializers.CharField()
    phone_number_alt = serializers.CharField(allow_blank=True)
    email = serializers.EmailField(allow_blank=True)
    relationship = serializers.CharField()


class StudentListSerializer(serializers.Serializer):
    id = serializers.UUIDField(source='student.id')
    student_id = serializers.CharField(source='student.student_id')
    first_name = serializers.CharField(source='student.first_name')
    last_name = serializers.CharField(source='student.last_name')
    other_names = serializers.CharField(source='student.other_names')
    gender = serializers.CharField(source='student.gender')
    date_of_birth = serializers.DateField(source='student.date_of_birth')
    admission_date = serializers.DateField(source='student.admission_date')
    class_level = StudentClassLevelSerializer()
    stream = StudentStreamSerializer()
    is_new_student = serializers.BooleanField()
    payment_status = serializers.CharField()
    primary_parent = serializers.SerializerMethodField()

    @extend_schema_field(PrimaryParentSerializer(allow_null=True))
    def get_primary_parent(self, obj):
        links = getattr(obj.student, 'primary_parent_links', None)
        if links is None:
            link = (
                obj.student.parent_links
                .filter(is_primary=True)
                .select_related('parent')
                .first()
            )
        else:
            link = links[0] if links else None

        if link is None:
            return None

        return PrimaryParentSerializer({
            'id': link.parent.id,
            'name': link.parent.name,
            'phone_number': link.parent.phone_number,
            'phone_number_alt': link.parent.phone_number_alt,
            'email': link.parent.email,
            'relationship': link.relationship,
        }).data


class StudentStatsSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    total_students = serializers.IntegerField()
    new_students = serializers.IntegerField()
    continuing_students = serializers.IntegerField()
    boys = serializers.IntegerField()
    girls = serializers.IntegerField()
    fully_paid = serializers.IntegerField()
    partially_paid = serializers.IntegerField()
    owing = serializers.IntegerField()
    no_fees = serializers.IntegerField()


class ParentListSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    phone_number = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)


class GuardianInputSerializer(serializers.Serializer):
    parent_id = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    phone_number = serializers.CharField(
        max_length=15,
        required=False,
        allow_blank=True,
        default='',
    )
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    relationship = serializers.ChoiceField(choices=StudentParent.RelationshipChoices.choices)

    def validate(self, attrs):
        parent_id = attrs.get('parent_id')
        if parent_id:
            return {
                'parent_id': parent_id,
                'relationship': attrs['relationship'],
            }

        name = (attrs.get('name') or '').strip()
        phone_number = (attrs.get('phone_number') or '').strip()
        if not name:
            raise serializers.ValidationError({'name': 'This field is required.'})
        if not phone_number:
            raise serializers.ValidationError({'phone_number': 'This field is required.'})

        return {
            'name': name,
            'phone_number': phone_number,
            'email': (attrs.get('email') or '').strip(),
            'relationship': attrs['relationship'],
        }


class StudentOnboardSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    other_names = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default='',
    )
    gender = serializers.ChoiceField(choices=Student.GenderChoices.choices)
    date_of_birth = serializers.DateField()
    admission_date = serializers.DateField()
    guardians = GuardianInputSerializer(many=True, min_length=1)
    stream_id = serializers.UUIDField()
    is_new_student = serializers.BooleanField()


class StudentClassAssignmentSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text='Stream UUID used for enrollment.')
    class_level_id = serializers.UUIDField()
    display_name = serializers.CharField()
    is_default = serializers.BooleanField()


class StudentGuardianSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text='StudentParent link id.')
    parent_id = serializers.UUIDField()
    name = serializers.CharField()
    phone_number = serializers.CharField()
    phone_number_alt = serializers.CharField(allow_blank=True)
    email = serializers.EmailField(allow_blank=True)
    address = serializers.CharField(allow_blank=True)
    relationship = serializers.CharField()
    is_primary = serializers.BooleanField()
    is_emergency_contact = serializers.BooleanField()


class StudentDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    student_id = serializers.CharField()
    full_name = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    other_names = serializers.CharField(allow_blank=True)
    gender = serializers.CharField()
    date_of_birth = serializers.DateField()
    age = serializers.IntegerField()
    admission_date = serializers.DateField()
    address = serializers.CharField(allow_blank=True)
    is_active = serializers.BooleanField()
    is_new_student = serializers.BooleanField(allow_null=True)
    class_assignment = StudentClassAssignmentSerializer(allow_null=True)
    guardians = StudentGuardianSerializer(many=True)
    term_id = serializers.UUIDField()


class StudentUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=255, required=False)
    last_name = serializers.CharField(max_length=255, required=False)
    other_names = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    gender = serializers.ChoiceField(
        choices=Student.GenderChoices.choices,
        required=False,
    )
    date_of_birth = serializers.DateField(required=False)
    admission_date = serializers.DateField(required=False)
    address = serializers.CharField(required=False, allow_blank=True)


class GuardianUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    phone_number = serializers.CharField(max_length=15, required=False)
    phone_number_alt = serializers.CharField(
        max_length=15,
        required=False,
        allow_blank=True,
    )
    email = serializers.EmailField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    relationship = serializers.ChoiceField(
        choices=StudentParent.RelationshipChoices.choices,
        required=False,
    )
    is_primary = serializers.BooleanField(required=False)
    is_emergency_contact = serializers.BooleanField(required=False)


class GuardianCreateSerializer(GuardianInputSerializer):
    is_primary = serializers.BooleanField(required=False, default=False)
    is_emergency_contact = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        base = super().validate(attrs)
        base['is_primary'] = attrs.get('is_primary', False)
        base['is_emergency_contact'] = attrs.get('is_emergency_contact', False)
        return base


class StudentFeeItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class StudentTermFeesSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term = serializers.CharField()
    term_name = serializers.CharField()
    total_billed = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_status = serializers.CharField()
    fee_items = StudentFeeItemSerializer(many=True)


class StudentYearFeesSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    academic_year_id = serializers.UUIDField()
    academic_year = serializers.CharField()
    total_billed = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_status = serializers.CharField()
    terms = StudentTermFeesSerializer(many=True)


class StudentFeeHistorySerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    years = StudentYearFeesSerializer(many=True)


class StudentPaymentReceiptSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    receipt_number = serializers.CharField()


class StudentPaymentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    term_id = serializers.UUIDField()
    term = serializers.CharField()
    term_name = serializers.CharField()
    academic_year_id = serializers.UUIDField()
    academic_year = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.CharField()
    payment_method_display = serializers.CharField()
    paid_at = serializers.DateTimeField()
    payment_reference = serializers.CharField(allow_blank=True)
    receipt = StudentPaymentReceiptSerializer(allow_null=True)