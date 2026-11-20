"""Private migration uploads.

Files are not given a public URL. When R2 credentials and
MIGRATION_FILE_STORAGE=r2 are both set, objects go to a migration prefix on
that bucket. Otherwise they stay on a local directory that Django does not serve.
"""

from django.conf import settings
from django.core.files.storage import FileSystemStorage, storages
from django.utils.module_loading import import_string


class PrivateMigrationStorage(FileSystemStorage):
    def __init__(self, **kwargs):
        kwargs.setdefault('location', str(settings.MIGRATION_PRIVATE_ROOT))
        kwargs['base_url'] = None
        super().__init__(**kwargs)

    def url(self, name):
        raise NotImplementedError('Migration files are not publicly addressable.')


def migration_storage():
    backend = getattr(settings, 'MIGRATION_FILE_STORAGE', 'local')
    if backend == 'r2' and settings.R2_BUCKET_NAME and settings.R2_ACCESS_KEY_ID:
        return storages['migration']
    return PrivateMigrationStorage()


def get_migration_storage():
    """Allow tests to swap the storage class via MIGRATION_STORAGE_CLASS."""
    dotted = getattr(settings, 'MIGRATION_STORAGE_CLASS', '')
    if dotted:
        return import_string(dotted)()
    return migration_storage()
