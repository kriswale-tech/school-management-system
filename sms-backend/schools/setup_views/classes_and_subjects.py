from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from schools.services import classes_and_subjects as setup_service
from schools.setup_serializers.classes_and_subjects import (
    ActivationResponseSerializer,
    ActivationSerializer,
    CreateCustomClassSerializer,
    CreateStreamSerializer,
    CreateSubjectGroupSerializer,
    CreateSubjectSerializer,
    SetupClassLevelSerializer,
    SetupClassStreamSerializer,
    SetupClassSubjectSerializer,
    SetupLevelSerializer,
    SetupSubjectGroupSerializer,
    SubjectDetailSerializer,
    UpdateCustomClassSerializer,
    UpdateStreamSerializer,
    UpdateSubjectGroupSerializer,
    UpdateSubjectSerializer,
)
from schools.setup_serializers.common import SetupStepResponseSerializer
from shared.views import SchoolScopedAPIView


@extend_schema(
    summary='Get classes and subjects setup',
    description=(
        'Returns school levels with their classes, streams, and subjects. '
        'Level subjects come from the level catalog (LevelSubject). '
        'Class lists show current class assignments. '
        'Subject groups are shared across classes in the level that have the subject. '
        'Default class streams are hidden; streams[] only lists user-created named streams.'
    ),
    responses={200: SetupLevelSerializer(many=True)},
)
class SetupClassesAndSubjectsView(SchoolScopedAPIView):
    def get(self, request):
        data = setup_service.get_classes_and_subjects_setup(self.school)
        return Response(SetupLevelSerializer(data, many=True).data)


@extend_schema(
    summary='Complete classes and subjects setup',
    description=(
        'Validates stream/group constraints and advances setup to the next step. '
        'If a class has any named streams, it must have at least two '
        '(the hidden default stream does not count). '
        'Any subject with groups must have at least two.'
    ),
    request=None,
    responses={200: SetupStepResponseSerializer},
)
class CompleteClassesAndSubjectsSetupView(SchoolScopedAPIView):
    def post(self, request):
        result = setup_service.complete_classes_and_subjects_setup(self.school)
        return Response(SetupStepResponseSerializer(result).data)


@extend_schema(
    summary='Add stream to a class',
    description=(
        'Adds a named stream to the class. The system default stream stays hidden; '
        'once named streams exist, at least two are required to complete setup.'
    ),
    request=CreateStreamSerializer,
    responses={201: SetupClassStreamSerializer},
)
class SetupClassStreamCreateView(SchoolScopedAPIView):
    def post(self, request, class_id):
        serializer = CreateStreamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = setup_service.add_stream(
            self.school,
            class_id=class_id,
            **serializer.validated_data,
        )
        return Response(SetupClassStreamSerializer(data).data, status=status.HTTP_201_CREATED)


@extend_schema(
    methods=['PATCH'],
    summary='Edit a class stream',
    request=UpdateStreamSerializer,
    responses={200: SetupClassStreamSerializer},
)
@extend_schema(
    methods=['DELETE'],
    summary='Delete a class stream',
    description='Deletes a non-default stream when it has no student associations.',
    responses={204: None},
)
class SetupClassStreamDetailView(SchoolScopedAPIView):
    def patch(self, request, stream_id):
        serializer = UpdateStreamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = setup_service.edit_stream(
            self.school,
            stream_id=stream_id,
            **serializer.validated_data,
        )
        return Response(SetupClassStreamSerializer(data).data)

    def delete(self, request, stream_id):
        setup_service.remove_stream(self.school, stream_id=stream_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary='Add subject group',
    description=(
        'Creates a subject group on every class in the level that already has '
        'this subject. For level-scoped subjects that is usually all classes; '
        'for class-scoped subjects it is only the assigned classes.'
    ),
    request=CreateSubjectGroupSerializer,
    responses={201: SetupSubjectGroupSerializer},
)
class SetupSubjectGroupCreateView(SchoolScopedAPIView):
    def post(self, request, level_id, subject_id):
        serializer = CreateSubjectGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = setup_service.add_subject_group(
            self.school,
            level_id=level_id,
            subject_id=subject_id,
            **serializer.validated_data,
        )
        return Response(SetupSubjectGroupSerializer(data).data, status=status.HTTP_201_CREATED)


@extend_schema(
    methods=['PATCH'],
    summary='Edit a subject group',
    request=UpdateSubjectGroupSerializer,
    responses={200: SetupSubjectGroupSerializer},
)
@extend_schema(
    methods=['DELETE'],
    summary='Delete a subject group',
    description='Deletes the group when no students are assigned to it.',
    responses={204: None},
)
class SetupSubjectGroupDetailView(SchoolScopedAPIView):
    def patch(self, request, group_id):
        serializer = UpdateSubjectGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = setup_service.edit_subject_group(
            self.school,
            group_id=group_id,
            **serializer.validated_data,
        )
        return Response(SetupSubjectGroupSerializer(data).data)

    def delete(self, request, group_id):
        setup_service.remove_subject_group(self.school, group_id=group_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary='Add a custom class to a level',
    request=CreateCustomClassSerializer,
    responses={201: SetupClassLevelSerializer},
)
class SetupCustomClassCreateView(SchoolScopedAPIView):
    def post(self, request, level_id):
        serializer = CreateCustomClassSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = setup_service.add_custom_class(
            self.school,
            level_id=level_id,
            **serializer.validated_data,
        )
        return Response(SetupClassLevelSerializer(data).data, status=status.HTTP_201_CREATED)


@extend_schema(
    methods=['PATCH'],
    summary='Edit a custom class',
    request=UpdateCustomClassSerializer,
    responses={200: SetupClassLevelSerializer},
)
@extend_schema(
    methods=['DELETE'],
    summary='Delete a custom class',
    description='Deletes a custom class when it has no student associations.',
    responses={204: None},
)
class SetupCustomClassDetailView(SchoolScopedAPIView):
    def patch(self, request, class_id):
        serializer = UpdateCustomClassSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = setup_service.edit_custom_class(
            self.school,
            class_id=class_id,
            **serializer.validated_data,
        )
        return Response(SetupClassLevelSerializer(data).data)

    def delete(self, request, class_id):
        setup_service.remove_custom_class(self.school, class_id=class_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary='Add a subject',
    description=(
        'Creates a subject on the level catalog. For class-scoped levels, optional '
        'class_ids assigns it to classes (can be empty). For level-scoped levels, '
        'the subject is assigned to all classes.'
    ),
    request=CreateSubjectSerializer,
    responses={201: SubjectDetailSerializer},
)
class SetupSubjectCreateView(SchoolScopedAPIView):
    def post(self, request):
        serializer = CreateSubjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = setup_service.add_subject(
            self.school,
            **serializer.validated_data,
        )
        return Response(SubjectDetailSerializer(data).data, status=status.HTTP_201_CREATED)


@extend_schema(
    methods=['PATCH'],
    summary='Edit a custom subject',
    description=(
        'Rename custom subjects and/or sync class assignments for class-scoped levels. '
        'System subjects can change class_ids but cannot be renamed.'
    ),
    request=UpdateSubjectSerializer,
    responses={200: SubjectDetailSerializer},
)
@extend_schema(
    methods=['DELETE'],
    summary='Delete a custom subject',
    responses={204: None},
)
class SetupSubjectDetailView(SchoolScopedAPIView):
    def patch(self, request, subject_id):
        serializer = UpdateSubjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = setup_service.edit_subject(
            self.school,
            subject_id=subject_id,
            **serializer.validated_data,
        )
        return Response(SubjectDetailSerializer(data).data)

    def delete(self, request, subject_id):
        setup_service.remove_subject(self.school, subject_id=subject_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    methods=['POST'],
    summary='Assign subject to a class',
    description=(
        'Only for class-scoped levels. Assigns a level subject to the class. '
        'Returns an error if the subject is already assigned.'
    ),
    request=None,
    responses={201: SetupClassSubjectSerializer},
)
@extend_schema(
    methods=['DELETE'],
    summary='Remove subject from a class',
    description=(
        'Only for class-scoped levels. Removes the subject assignment from the class '
        '(including provisioned subjects). The subject itself is kept on the level.'
    ),
    responses={204: None},
)
class SetupClassSubjectAssignmentView(SchoolScopedAPIView):
    def post(self, request, class_id, subject_id):
        data = setup_service.assign_subject_to_class(
            self.school,
            class_id=class_id,
            subject_id=subject_id,
        )
        return Response(SetupClassSubjectSerializer(data).data, status=status.HTTP_201_CREATED)

    def delete(self, request, class_id, subject_id):
        setup_service.remove_subject_from_class(
            self.school,
            class_id=class_id,
            subject_id=subject_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary='Activate or deactivate a level',
    request=ActivationSerializer,
    responses={200: ActivationResponseSerializer},
)
class SetupLevelStatusView(SchoolScopedAPIView):
    def patch(self, request, level_id):
        serializer = ActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = setup_service.set_level_status(
            self.school,
            level_id=level_id,
            **serializer.validated_data,
        )
        return Response(ActivationResponseSerializer(data).data)


@extend_schema(
    summary='Activate or deactivate a class',
    request=ActivationSerializer,
    responses={200: ActivationResponseSerializer},
)
class SetupClassStatusView(SchoolScopedAPIView):
    def patch(self, request, class_id):
        serializer = ActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = setup_service.set_class_status(
            self.school,
            class_id=class_id,
            **serializer.validated_data,
        )
        return Response(ActivationResponseSerializer(data).data)


@extend_schema(
    summary='Activate or deactivate a subject',
    request=ActivationSerializer,
    responses={200: ActivationResponseSerializer},
)
class SetupSubjectStatusView(SchoolScopedAPIView):
    def patch(self, request, subject_id):
        serializer = ActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = setup_service.set_subject_status(
            self.school,
            subject_id=subject_id,
            **serializer.validated_data,
        )
        return Response(ActivationResponseSerializer(data).data)
