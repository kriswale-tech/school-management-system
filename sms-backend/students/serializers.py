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
