from platform_admin.models import PlatformAuditLog, PlatformUser


def record_audit(
    *,
    action: str,
    actor: PlatformUser | None = None,
    target_type: str = '',
    target_id: str = '',
    detail: dict | None = None,
    ip_address: str | None = None,
) -> PlatformAuditLog:
    return PlatformAuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type or '',
        target_id=str(target_id) if target_id else '',
        detail=detail or {},
        ip_address=ip_address,
    )
