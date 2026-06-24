from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import School, SchoolSetup
from .serializers import SchoolSerializer, SchoolSetupSerializer
from drf_spectacular.utils import extend_schema
# Create your views here.


@extend_schema(
    summary="Get school",
    description="Get the school",
    responses={
        200: SchoolSerializer,
    }
)
class SchoolView(APIView):
    def get(self, request):
        school = School.objects.get(id=request.user.school_id)
        return Response(SchoolSerializer(school).data)

    # update school.
