from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from schools.services.fees import (
    complete_fees_setup,
    create_fee_item,
    delete_fee_item,
    get_fees_setup,
    update_fee_item,
)
from schools.setup_serializers.common import SetupStepResponseSerializer
from schools.setup_serializers.fees import (
    CreateFeeItemSerializer,
    SetupFeeItemSerializer,
    SetupFeesDataSerializer,
    UpdateFeeItemSerializer,
)
from shared.views import SchoolScopedAPIView


@extend_schema(
    summary='Get fees setup',
    description=(
        'Returns the active term fee structure and its fee items with display labels '
        'for scope and student audience.'
    ),
    responses={200: SetupFeesDataSerializer},
)
class SetupFeesView(SchoolScopedAPIView):
    def get(self, request):
        data = get_fees_setup(
            self.school,
            created_by=request.user,
        )
        return Response(SetupFeesDataSerializer(data).data)


@extend_schema(
    summary='Create a fee item',
    description='Adds a fee item to the active term structure while it is still editable.',
    request=CreateFeeItemSerializer,
    responses={201: SetupFeeItemSerializer},
)
class SetupFeeItemCreateView(SchoolScopedAPIView):
    def post(self, request):
        serializer = CreateFeeItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = create_fee_item(
            self.school,
            created_by=request.user,
            **serializer.validated_data,
        )
        return Response(SetupFeeItemSerializer(data).data, status=status.HTTP_201_CREATED)


@extend_schema(
    methods=['PATCH'],
    summary='Update a fee item',
    description='Updates a fee item on the active term structure while it is still editable.',
    request=UpdateFeeItemSerializer,
    responses={200: SetupFeeItemSerializer},
)
@extend_schema(
    methods=['DELETE'],
    summary='Delete a fee item',
    description='Removes a fee item from the active term structure while it is still editable.',
    responses={204: None},
)
class SetupFeeItemDetailView(SchoolScopedAPIView):
    def patch(self, request, fee_item_id):
        serializer = UpdateFeeItemSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = update_fee_item(
            self.school,
            fee_item_id=fee_item_id,
            **serializer.validated_data,
        )
        return Response(SetupFeeItemSerializer(data).data)

    def delete(self, request, fee_item_id):
        delete_fee_item(self.school, fee_item_id=fee_item_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary='Complete fees setup',
    description=(
        'Validates that the active term has at least one fee item, '
        'then advances setup to the next step.'
    ),
    request=None,
    responses={200: SetupStepResponseSerializer},
)
class CompleteFeesSetupView(SchoolScopedAPIView):
    def post(self, request):
        result = complete_fees_setup(self.school)
        return Response(SetupStepResponseSerializer(result).data)
