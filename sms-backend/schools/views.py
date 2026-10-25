from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from accounts.permissions import HasActiveSchool, IsAdmin
from schools.models import AcademicYear
from schools.serializers import (
    AcademicYearCalendarSerializer,
    AcademicYearScheduleSerializer,
    SchoolAlertSerializer,
    SchoolProfileUpdateSerializer,
    SchoolSerializer,
    SchoolSettingsSerializer,
    TermSwitchPreviewSerializer,
    TermSwitchSerializer,
    TransitionConfirmSerializer,
)
from schools.services.academic_calendar import (
    create_next_academic_year,
    list_academic_calendar,
    preview_term_switch,
    update_academic_year_dates,
)
from schools.services.alerts import list_school_alerts
from schools.services.settings import get_school_settings
from schools.services.term_transition import (
    build_transition_preview,
    confirm_transition,
    transition_status,
)
from shared.exceptions import cloudinary_error_detail
from shared.views import SchoolScopedAPIView


@extend_schema(
    methods=['GET'],
    summary='Get school',
    description='Get the school the session is currently scoped to.',
    responses={200: SchoolSerializer},
)
@extend_schema(
    methods=['PATCH'],
    summary='Update school profile',
    description=(
        'Admin update of the school profile and student ID prefix. '
        'Does not change setup progress.'
    ),
    request=SchoolProfileUpdateSerializer,
    responses={200: SchoolSerializer},
)
class SchoolView(SchoolScopedAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [HasActiveSchool(), IsAdmin()]
        return [HasActiveSchool()]

    def get(self, request):
        return Response(SchoolSerializer(self.school).data)

    def patch(self, request):
        serializer = SchoolProfileUpdateSerializer(
            self.school,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except Exception as exc:
            from cloudinary.exceptions import Error as CloudinaryError

            if isinstance(exc, CloudinaryError):
                raise ValidationError({'logo': cloudinary_error_detail(exc)}) from exc
            raise
        self.school.refresh_from_db()
        return Response(SchoolSerializer(self.school).data)


@extend_schema(
    methods=['GET'],
    summary='List academic years',
    description='Every academic year and its terms. The active term is marked.',
    responses={200: AcademicYearCalendarSerializer},
)
@extend_schema(
    methods=['POST'],
    summary='Add the next academic year',
    description=(
        'Creates the following academic year and its three terms without '
        'making them active. Assessment settings are copied onto the new terms.'
    ),
    request=AcademicYearScheduleSerializer,
    responses={200: AcademicYearCalendarSerializer},
)
class AcademicYearListCreateView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, IsAdmin]

    def get(self, request):
        return Response(AcademicYearCalendarSerializer(list_academic_calendar(self.school)).data)

    def post(self, request):
        serializer = AcademicYearScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        calendar = create_next_academic_year(self.school, serializer.validated_data)
        return Response(AcademicYearCalendarSerializer(calendar).data)


@extend_schema(
    methods=['PATCH'],
    summary='Update academic year dates',
    description='Updates term dates for a current or upcoming year. Past years stay fixed.',
    request=AcademicYearScheduleSerializer,
    responses={200: AcademicYearCalendarSerializer},
)
class AcademicYearDetailView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, IsAdmin]

    def patch(self, request, year_id):
        year = AcademicYear.objects.filter(school=self.school, id=year_id).first()
        if year is None:
            raise NotFound('Academic year not found.')
        serializer = AcademicYearScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        calendar = update_academic_year_dates(self.school, year, serializer.validated_data)
        return Response(AcademicYearCalendarSerializer(calendar).data)


@extend_schema(
    summary='Preview a term switch',
    description='Blockers stop the switch. Warnings are shown and can be acknowledged.',
    responses={200: TermSwitchPreviewSerializer},
)
class TermSwitchPreviewView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, IsAdmin]

    def get(self, request, term_id):
        preview = preview_term_switch(self.school, term_id)
        return Response(TermSwitchPreviewSerializer(preview).data)


@extend_schema(
    summary='Make a term current (disabled)',
    description=(
        'Standalone term activation is disabled. Use Open the next term '
        '(transition confirm) so pupils are placed and fees applied before '
        'the term becomes current.'
    ),
    request=TermSwitchSerializer,
    responses={403: None},
    deprecated=True,
)
class TermActivateView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, IsAdmin]

    def post(self, request, term_id):
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied(
            'Activating a term directly is disabled. '
            'Open the next term from the transition wizard so continuing pupils '
            'are enrolled (or graduated) and fees are applied first.'
        )


@extend_schema(
    methods=['GET'],
    summary='Get school settings',
    description='Alert rules and report-card field visibility.',
    responses={200: SchoolSettingsSerializer},
)
@extend_schema(
    methods=['PATCH'],
    summary='Update school settings',
    description='Admin update of alert rules and report-card field visibility.',
    request=SchoolSettingsSerializer,
    responses={200: SchoolSettingsSerializer},
)
class SchoolSettingsView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, IsAdmin]

    def get(self, request):
        preferences = get_school_settings(self.school)
        return Response(SchoolSettingsSerializer(preferences).data)

    def patch(self, request):
        preferences = get_school_settings(self.school)
        serializer = SchoolSettingsSerializer(
            preferences,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema(
    summary='List in-app alerts',
    description='Alerts for the signed-in role on the active term.',
    responses={200: SchoolAlertSerializer(many=True)},
)
@extend_schema(
    summary='Term transition status',
    description='Checklist shown before the current term ends. Admins only.',
)
class TermTransitionStatusView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, IsAdmin]

    def get(self, request):
        return Response(transition_status(self.school))


@extend_schema(
    summary='Preview the next term transition',
    description=(
        'Where each class goes, which streams need a choice, and the fees '
        'that will be applied on the next term. Does not change data.'
    ),
)
class TermTransitionPreviewView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, IsAdmin]

    def get(self, request):
        return Response(build_transition_preview(self.school))


@extend_schema(
    summary='Open the next term',
    description=(
        'Places continuing pupils, marks leavers graduated, copies teachers, '
        'applies the next term’s fees, and makes that term current.'
    ),
    request=TransitionConfirmSerializer,
    responses={200: AcademicYearCalendarSerializer},
)
class TermTransitionConfirmView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, IsAdmin]

    def post(self, request):
        serializer = TransitionConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        calendar = confirm_transition(
            self.school,
            request.user,
            stream_choices=[
                {
                    'source_stream_id': str(item['source_stream_id']),
                    'destination_stream_id': str(item['destination_stream_id']),
                }
                for item in data['stream_choices']
            ],
            acknowledge_warnings=data['acknowledge_warnings'],
        )
        return Response(AcademicYearCalendarSerializer(calendar).data)


class SchoolAlertListView(SchoolScopedAPIView):
    def get(self, request):
        alerts = list_school_alerts(school=self.school, membership=self.membership)
        return Response(SchoolAlertSerializer(alerts, many=True).data)
