from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from schools.services.classes_and_subjects import get_classes_and_subjects_setup
from schools.setup_serializers import ClassesAndSubjectsDataSerializer


@extend_schema(
    summary='Get classes and subjects setup',
    description=(
        'Returns school levels with their classes, streams, and level-scoped subjects. '
        'Subject groups are shared across all classes within a level.'
    ),
    responses={200: ClassesAndSubjectsDataSerializer},
)
class SetupClassesAndSubjectsView(APIView):
    def get(self, request):
        data = get_classes_and_subjects_setup(request.user.school)
        return Response(ClassesAndSubjectsDataSerializer(data).data)
