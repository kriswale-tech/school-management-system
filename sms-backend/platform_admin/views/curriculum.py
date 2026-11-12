from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from academics.services import curriculum_versions
from platform_admin.authentication import PlatformJWTCookieAuthentication
from platform_admin.models import PlatformUser
from platform_admin.permissions import HasPlatformRole, IsPlatformAuthenticated
from platform_admin.services.audit import record_audit
from platform_admin.utils import client_ip

WRITERS = [PlatformUser.Role.SUPER_ADMIN, PlatformUser.Role.CURRICULUM]


def _raise(exc: DjangoValidationError):
    messages = getattr(exc, 'messages', None) or [str(exc)]
    raise ValidationError(messages[0] if len(messages) == 1 else messages)


class CurriculumOverviewView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated, HasPlatformRole]
    allowed_roles = WRITERS

    @extend_schema(responses={200: dict})
    def get(self, request):
        return Response(curriculum_versions.curriculum_overview())


class CurriculumDraftCreateView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated, HasPlatformRole]
    allowed_roles = WRITERS

    @extend_schema(responses={201: dict})
    def post(self, request):
        try:
            draft = curriculum_versions.start_draft()
        except DjangoValidationError as exc:
            _raise(exc)
        record_audit(
            actor=request.platform_user,
            action='platform.curriculum.draft_started',
            target_type='curriculum',
            target_id=draft['id'],
            detail={'version': draft['version']},
            ip_address=client_ip(request),
        )
        return Response(draft, status=201)


class CurriculumDraftView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated, HasPlatformRole]
    allowed_roles = WRITERS

    @extend_schema(responses={200: dict})
    def put(self, request, pk):
        try:
            saved = curriculum_versions.save_draft(
                pk,
                version=request.data.get('version') or '',
                levels=request.data.get('levels') or [],
            )
        except DjangoValidationError as exc:
            _raise(exc)
        return Response(saved)

    @extend_schema(responses={200: dict})
    def post(self, request, pk):
        try:
            result = curriculum_versions.publish_draft(pk)
        except DjangoValidationError as exc:
            _raise(exc)
        record_audit(
            actor=request.platform_user,
            action='platform.curriculum.published',
            target_type='curriculum',
            target_id=result['curriculum']['id'],
            detail={
                'version': result['curriculum']['version'],
                'schools_alerted': result['schools_alerted'],
            },
            ip_address=client_ip(request),
        )
        return Response(result)


class SchoolCurriculumAdoptionView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated, HasPlatformRole]
    allowed_roles = WRITERS

    def _school(self, pk):
        from rest_framework.exceptions import NotFound
        from schools.models import School

        school = School.objects.filter(pk=pk).first()
        if school is None:
            raise NotFound('School not found.')
        return school

    @extend_schema(responses={200: dict})
    def get(self, request, pk):
        return Response(curriculum_versions.plan_adoption(self._school(pk)))

    @extend_schema(responses={200: dict})
    def post(self, request, pk):
        school = self._school(pk)
        try:
            result = curriculum_versions.adopt(school)
        except DjangoValidationError as exc:
            _raise(exc)
        record_audit(
            actor=request.platform_user,
            action='platform.curriculum.adopted',
            target_type='school',
            target_id=str(school.pk),
            detail={'to_version': result['to_version'], 'source': 'platform'},
            ip_address=client_ip(request),
        )
        return Response(result)
