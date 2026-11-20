from migration.models import MigrationAuditEvent


def record_migration_audit(*, school, job, actor, action, summary, payload=None):
    return MigrationAuditEvent.objects.create(
        school=school,
        job=job,
        actor=actor,
        action=action,
        summary=summary[:500],
        payload=payload or {},
    )
