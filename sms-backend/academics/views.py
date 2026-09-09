from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response

from academics.models import ClassLevel, Level
from academics.serializers import (
    AllClassesSerializer,
    AssignClassTeacherSerializer,
    AssignSubjectTeacherSerializer,
    ClassDetailSerializer,
    ClassListSerializer,
    ClassStatsSerializer,
    ClassStudentListSerializer,
    ClassSubjectListSerializer,
    ClassTeacherOptionListSerializer,
    SubjectGroupCandidateListSerializer,
    SubjectGroupStudentIdsSerializer,
    TeachingAssignmentDetailSerializer,
)
from academics.services.all_classes import get_all_classes
from academics.services.class_detail import (
    assign_class_teacher,
    assign_subject_teacher,
    get_class_detail,
    get_class_students,
    get_class_subjects,
    get_class_teacher_options,
)
from academics.services.classes import get_class_list, get_class_stats
from academics.services.teaching_assignments import (
    assign_students_to_subject_group,
    get_teaching_assignment_detail,
    get_teaching_assignment_students,
    list_subject_group_candidates,
    unassign_students_from_subject_group,
)
from accounts.capabilities import Capability
from accounts.permissions import HasActiveSchool, HasCapability
from accounts.services.access_scope import resolve_access_scope
from shared.views import SchoolScopedAPIView
from students.services import resolve_term


class ActiveLevelListSerializerMixin:
    @staticmethod
    def serialize_levels(levels):
        return [
            {
                'id': level.id,
                'name': level.name,
                'order': level.order,
            }
            for level in levels
        ]


@extend_schema(
    tags=['Academics'],
    summary='List active levels',
    description="Returns active levels for the authenticated user's school.",
    responses={
        200: {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string', 'format': 'uuid'},
                    'name': {'type': 'string'},
                    'order': {'type': 'integer'},
                },
            },
        },
    },
)
class ActiveLevelListView(SchoolScopedAPIView, ActiveLevelListSerializerMixin):
    def get(self, request):
        levels = Level.objects.filter(
            school=self.school,
            is_active=True,
        ).order_by('order', 'name')
        return Response(self.serialize_levels(levels))


@extend_schema(
    tags=['Academics'],
    summary='List active class levels',
    description="Returns active classes for the authenticated user's school.",
    responses={
        200: {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string', 'format': 'uuid'},
                    'name': {'type': 'string'},
                    'level_id': {'type': 'string', 'format': 'uuid'},
                    'level_name': {'type': 'string'},
                    'order': {'type': 'integer'},
                },
            },
        },
    },
)
class ActiveClassLevelListView(SchoolScopedAPIView):
    def get(self, request):
        class_levels = ClassLevel.objects.filter(
            school=self.school,
            is_active=True,
            level__is_active=True,
        ).select_related('level').order_by('level__order', 'order', 'name')

        return Response([
            {
                'id': class_level.id,
                'name': class_level.name,
                'level_id': class_level.level_id,
                'level_name': class_level.level.name,
                'order': class_level.order,
            }
            for class_level in class_levels
        ])


@extend_schema(
    tags=['Academics'],
    summary='All classes for assignment',
    description=(
        'Returns active levels with flat selectable class entries. '
        'Each entry id is a stream UUID for enrollment. Named streams are listed '
        'as separate entries; classes with only a default stream expose that '
        'default using the class display name. student_count is for the active '
        'term (or optional term query param).'
    ),
    parameters=[
        OpenApiParameter(
            name='term',
            type=str,
            description='Optional term UUID. Defaults to the school active term.',
        ),
    ],
    responses={200: AllClassesSerializer},
)
class AllClassesView(SchoolScopedAPIView):
    def get(self, request):
        term = resolve_term(
            self.school,
            request.query_params.get('term'),
        )
        payload = get_all_classes(school=self.school, term=term)
        return Response(AllClassesSerializer(payload).data)


@extend_schema(
    tags=['Academics'],
    summary='List classes',
    description=(
        'Returns a flat list of class streams for the Classes page. '
        'Each item id is a stream UUID. Named streams are listed as separate '
        'rows (e.g. Nursery 1 A); classes with only a default stream appear '
        'as a single row using the class display name (e.g. Nursery 1). '
        'level_name is the department (Level). Student and class-teacher data '
        'are for the active term (or optional term query param).'
    ),
    parameters=[
        OpenApiParameter(
            name='term',
            type=str,
            description='Optional term UUID. Defaults to the school active term.',
        ),
        OpenApiParameter(
            name='search',
            type=str,
            description='Optional search against class display name or department name.',
        ),
    ],
    responses={200: ClassListSerializer},
)
class ClassListView(SchoolScopedAPIView):
    def get(self, request):
        term = resolve_term(
            self.school,
            request.query_params.get('term'),
        )
        payload = get_class_list(
            school=self.school,
            term=term,
            search=request.query_params.get('search'),
            scope=resolve_access_scope(self.membership),
        )
        return Response(ClassListSerializer(payload).data)


@extend_schema(
    tags=['Academics'],
    summary='Class statistics',
    description=(
        'Returns summary counts for class streams in the active term: '
        'total classes, enrolled students, distinct class teachers assigned, '
        'unassigned classes, empty classes, and classes with students.'
    ),
    parameters=[
        OpenApiParameter(
            name='term',
            type=str,
            description='Optional term UUID. Defaults to the school active term.',
        ),
    ],
    responses={200: ClassStatsSerializer},
)
class ClassStatsView(SchoolScopedAPIView):
    def get(self, request):
        term = resolve_term(
            self.school,
            request.query_params.get('term'),
        )
        stats = get_class_stats(
            school=self.school,
            term=term,
            scope=resolve_access_scope(self.membership),
        )
        return Response(ClassStatsSerializer(stats).data)


@extend_schema(
    tags=['Academics'],
    summary='Teacher options for class assignment',
    description=(
        'Returns active teachers with class-teacher and teaching assignment '
        'summaries for the active term. Used by class/subject teacher pickers.'
    ),
    parameters=[
        OpenApiParameter(
            name='term',
            type=str,
            description='Optional term UUID. Defaults to the school active term.',
        ),
        OpenApiParameter(
            name='search',
            type=str,
            description='Optional search against teacher name or assignment summary.',
        ),
    ],
    responses={200: ClassTeacherOptionListSerializer},
)
class ClassTeacherOptionsView(SchoolScopedAPIView):
    def get(self, request):
        term = resolve_term(
            self.school,
            request.query_params.get('term'),
        )
        payload = get_class_teacher_options(
            school=self.school,
            term=term,
            search=request.query_params.get('search'),
        )
        return Response(ClassTeacherOptionListSerializer(payload).data)


@extend_schema(
    tags=['Academics'],
    summary='Class detail',
    description=(
        'Returns header details for a class stream, including department, '
        'student count, flattened subject count, and class teacher for the term.'
    ),
    parameters=[
        OpenApiParameter(
            name='term',
            type=str,
            description='Optional term UUID. Defaults to the school active term.',
        ),
    ],
    responses={200: ClassDetailSerializer},
)
class ClassDetailView(SchoolScopedAPIView):
    def get(self, request, stream_id):
        term = resolve_term(
            self.school,
            request.query_params.get('term'),
        )
        payload = get_class_detail(
            school=self.school,
            stream_id=stream_id,
            term=term,
        )
        return Response(ClassDetailSerializer(payload).data)


@extend_schema(
    tags=['Academics'],
    summary='Students in a class',
    description='Returns students enrolled in the class stream for the active term.',
    parameters=[
        OpenApiParameter(
            name='term',
            type=str,
            description='Optional term UUID. Defaults to the school active term.',
        ),
        OpenApiParameter(
            name='search',
            type=str,
            description='Optional search against student name or student ID.',
        ),
    ],
    responses={200: ClassStudentListSerializer},
)
class ClassStudentsView(SchoolScopedAPIView):
    def get(self, request, stream_id):
        term = resolve_term(
            self.school,
            request.query_params.get('term'),
        )
        payload = get_class_students(
            school=self.school,
            stream_id=stream_id,
            term=term,
            search=request.query_params.get('search'),
        )
        return Response(ClassStudentListSerializer(payload).data)


@extend_schema(
    tags=['Academics'],
    summary='Subjects in a class',
    description=(
        'Returns flattened subject rows for the class. Subject groups appear as '
        'separate entries (e.g. Ghanaian Language (Twi)); subjects without groups '
        'appear once.'
    ),
    parameters=[
        OpenApiParameter(
            name='term',
            type=str,
            description='Optional term UUID. Defaults to the school active term.',
        ),
    ],
    responses={200: ClassSubjectListSerializer},
)
class ClassSubjectsView(SchoolScopedAPIView):
    def get(self, request, stream_id):
        term = resolve_term(
            self.school,
            request.query_params.get('term'),
        )
        payload = get_class_subjects(
            school=self.school,
            stream_id=stream_id,
            term=term,
        )
        return Response(ClassSubjectListSerializer(payload).data)


@extend_schema(
    tags=['Academics'],
    summary='Assign class teacher',
    description=(
        'Assigns or replaces the class teacher for this stream in the active term.'
    ),
    request=AssignClassTeacherSerializer,
    responses={200: ClassDetailSerializer},
)
class ClassTeacherAssignView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.CLASSES_MANAGE

    def put(self, request, stream_id):
        serializer = AssignClassTeacherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = assign_class_teacher(
            school=self.school,
            stream_id=stream_id,
            teacher_id=serializer.validated_data['teacher_id'],
        )
        return Response(ClassDetailSerializer(payload).data)


@extend_schema(
    tags=['Academics'],
    summary='Assign subject teacher',
    description=(
        'Assigns or replaces the subject teacher for a class subject or subject '
        'group in this class stream for the active term. Pass subject_group_id '
        'for grouped subjects (e.g. Ghanaian Language (Twi)).'
    ),
    request=AssignSubjectTeacherSerializer,
    responses={200: ClassSubjectListSerializer},
)
class ClassSubjectTeacherAssignView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.CLASSES_MANAGE

    def put(self, request, stream_id):
        serializer = AssignSubjectTeacherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = assign_subject_teacher(
            school=self.school,
            stream_id=stream_id,
            **serializer.validated_data,
        )
        return Response(ClassSubjectListSerializer(payload).data)


@extend_schema(
    tags=['Academics'],
    summary='Teaching assignment detail',
    description=(
        'Returns subject teaching assignment details for the subject workspace. '
        'Teachers may only view their own assignments.'
    ),
    responses={200: TeachingAssignmentDetailSerializer},
)
class TeachingAssignmentDetailView(SchoolScopedAPIView):
    def get(self, request, assignment_id):
        payload = get_teaching_assignment_detail(
            school=self.school,
            membership=self.membership,
            assignment_id=assignment_id,
        )
        return Response(TeachingAssignmentDetailSerializer(payload).data)


@extend_schema(
    tags=['Academics'],
    summary='Students for a teaching assignment',
    description=(
        'Lists students covered by a subject teaching assignment in the active term.'
    ),
    parameters=[
        OpenApiParameter(
            name='search',
            type=str,
            description='Optional search against student name or student ID.',
        ),
    ],
    responses={200: ClassStudentListSerializer},
)
class TeachingAssignmentStudentsView(SchoolScopedAPIView):
    def get(self, request, assignment_id):
        payload = get_teaching_assignment_students(
            school=self.school,
            membership=self.membership,
            assignment_id=assignment_id,
            search=request.query_params.get('search'),
        )
        return Response(ClassStudentListSerializer(payload).data)


@extend_schema(
    tags=['Academics'],
    summary='Subject group placement candidates',
    description=(
        'Lists class roster students with placement status for a grouped '
        'teaching assignment. Only unassigned students are selectable.'
    ),
    parameters=[
        OpenApiParameter(
            name='search',
            type=str,
            description='Optional search against student name or student ID.',
        ),
    ],
    responses={200: SubjectGroupCandidateListSerializer},
)
class SubjectGroupCandidatesView(SchoolScopedAPIView):
    def get(self, request, assignment_id):
        payload = list_subject_group_candidates(
            school=self.school,
            membership=self.membership,
            assignment_id=assignment_id,
            search=request.query_params.get('search'),
        )
        return Response(SubjectGroupCandidateListSerializer(payload).data)


@extend_schema(
    tags=['Academics'],
    summary='Assign students to subject group',
    description=(
        'Adds unassigned roster students to this teaching assignment\'s group. '
        'Students already in another group are rejected.'
    ),
    request=SubjectGroupStudentIdsSerializer,
    responses={200: TeachingAssignmentDetailSerializer},
)
class SubjectGroupAssignStudentsView(SchoolScopedAPIView):
    def post(self, request, assignment_id):
        serializer = SubjectGroupStudentIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = assign_students_to_subject_group(
            school=self.school,
            membership=self.membership,
            assignment_id=assignment_id,
            student_ids=serializer.validated_data['student_ids'],
        )
        return Response(TeachingAssignmentDetailSerializer(payload).data)


@extend_schema(
    tags=['Academics'],
    summary='Unassign students from subject group',
    description=(
        'Removes students from this teaching assignment\'s group only. '
        'They become unassigned for the class-subject.'
    ),
    request=SubjectGroupStudentIdsSerializer,
    responses={200: TeachingAssignmentDetailSerializer},
)
class SubjectGroupUnassignStudentsView(SchoolScopedAPIView):
    def post(self, request, assignment_id):
        serializer = SubjectGroupStudentIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = unassign_students_from_subject_group(
            school=self.school,
            membership=self.membership,
            assignment_id=assignment_id,
            student_ids=serializer.validated_data['student_ids'],
        )
        return Response(TeachingAssignmentDetailSerializer(payload).data)
