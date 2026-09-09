"""Stable capability codes shared by API checks and the /me payload.

Keep these strings stable — frontend mirrors them in TypeScript constants.
"""


class Capability:
    NAV_DASHBOARD = 'nav.dashboard'
    NAV_STUDENTS = 'nav.students'
    NAV_CLASSES = 'nav.classes'
    NAV_ASSESSMENTS = 'nav.assessments'
    NAV_FEES = 'nav.fees'
    NAV_STAFF = 'nav.staff'

    CLASSES_VIEW = 'classes.view'
    CLASSES_MANAGE = 'classes.manage'

    STUDENTS_VIEW = 'students.view'
    STUDENTS_CREATE = 'students.create'

    ASSESSMENTS_RECORD = 'assessments.record'
    ASSESSMENTS_APPROVE = 'assessments.approve'

    FEES_VIEW = 'fees.view'
    FEES_RECORD_PAYMENT = 'fees.record_payment'
    FEES_MANAGE_SETTINGS = 'fees.manage_settings'

    STAFF_VIEW = 'staff.view'
    STAFF_MANAGE = 'staff.manage'


# Full school operators (admin today; staff/accountant keep full access until
# their packs are tightened in a later phase).
SCHOOL_WIDE_CAPABILITIES = frozenset({
    Capability.NAV_DASHBOARD,
    Capability.NAV_STUDENTS,
    Capability.NAV_CLASSES,
    Capability.NAV_ASSESSMENTS,
    Capability.NAV_FEES,
    Capability.NAV_STAFF,
    Capability.CLASSES_VIEW,
    Capability.CLASSES_MANAGE,
    Capability.STUDENTS_VIEW,
    Capability.STUDENTS_CREATE,
    Capability.ASSESSMENTS_RECORD,
    Capability.ASSESSMENTS_APPROVE,
    Capability.FEES_VIEW,
    Capability.FEES_RECORD_PAYMENT,
    Capability.FEES_MANAGE_SETTINGS,
    Capability.STAFF_VIEW,
    Capability.STAFF_MANAGE,
})

TEACHER_BASE_CAPABILITIES = frozenset({
    Capability.NAV_DASHBOARD,
    Capability.NAV_CLASSES,
    Capability.CLASSES_VIEW,
    Capability.STUDENTS_VIEW,
})
