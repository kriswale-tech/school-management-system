from rest_framework.views import APIView

from accounts.permissions import HasActiveSchool
from accounts.services.memberships import get_active_school


class SchoolScopedAPIView(APIView):
    """Base for endpoints that operate inside a single school.

    Requiring a school-scoped token here means `self.school` is always the
    school the caller explicitly selected. Without this, a user belonging to
    several schools could read or write against whichever school happened to be
    inferred from their account.
    """

    permission_classes = [HasActiveSchool]

    @property
    def school(self):
        return get_active_school(self.request)

    @property
    def membership(self):
        return self.request.membership
