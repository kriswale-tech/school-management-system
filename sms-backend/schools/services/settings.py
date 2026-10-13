from schools.models import SchoolSettings


def get_school_settings(school) -> SchoolSettings:
    settings_row, _created = SchoolSettings.objects.get_or_create(school=school)
    return settings_row
