"""Resolve session capabilities from membership role + teacher assignments."""

from __future__ import annotations

from dataclasses import dataclass

from accounts.capabilities import (
    SCHOOL_WIDE_CAPABILITIES,
    TEACHER_BASE_CAPABILITIES,
    Capability,
)
from accounts.models import SchoolMembership, User
from accounts.services.access_scope import AccessScope, resolve_access_scope


@dataclass(frozen=True)
class SessionAccess:
    capabilities: frozenset[str]
    scope: AccessScope

    def has(self, capability: str) -> bool:
        return capability in self.capabilities

    def as_payload(self) -> dict:
        return {
            'capabilities': sorted(self.capabilities),
            'access': {
                'mode': self.scope.mode,
                'is_class_teacher': self.scope.is_class_teacher,
                'is_subject_teacher': self.scope.is_subject_teacher,
            },
        }


def resolve_session_access(membership: SchoolMembership | None) -> SessionAccess:
    """Capabilities + scope for the active membership (or empty when unscoped)."""
    if membership is None:
        return SessionAccess(capabilities=frozenset(), scope=resolve_access_scope(None))

    scope = resolve_access_scope(membership)
    role = membership.role

    if role == User.RoleChoices.TEACHER:
        caps = set(TEACHER_BASE_CAPABILITIES)
        if scope.is_subject_teacher:
            caps.add(Capability.ASSESSMENTS_RECORD)
        if scope.is_class_teacher:
            caps.add(Capability.NAV_ASSESSMENTS)
            caps.add(Capability.ASSESSMENTS_APPROVE)
            caps.add(Capability.FEES_VIEW)
        return SessionAccess(capabilities=frozenset(caps), scope=scope)

    # Admin, staff, accountant: full school pack until role packs are tightened.
    return SessionAccess(
        capabilities=SCHOOL_WIDE_CAPABILITIES,
        scope=scope,
    )


def membership_has_capability(membership: SchoolMembership | None, capability: str) -> bool:
    return resolve_session_access(membership).has(capability)
