from django.core.exceptions import ValidationError
from django.db import transaction

from assessments.constants.grade_templates import GRADE_TEMPLATES
from assessments.models import AssessmentConfig, GradeBand


def get_grade_template(grade_type):
    try:
        return GRADE_TEMPLATES[grade_type]
    except KeyError as exc:
        raise ValidationError({
            'grade_type': f'Unknown grade type: {grade_type}.',
        }) from exc


def _band_as_dict(band):
    if isinstance(band, dict):
        return {
            'grade': str(band['grade']),
            'min_score': int(band['min_score']),
            'max_score': int(band['max_score']),
            'remark': band.get('remark', ''),
        }
    return {
        'grade': str(band.grade),
        'min_score': int(band.min_score),
        'max_score': int(band.max_score),
        'remark': band.remark,
    }


def validate_grade_bands(bands):
    """Ensure bands are contiguous integer ranges covering 0–100 with unique labels."""
    normalized = [_band_as_dict(band) for band in bands]
    if not normalized:
        raise ValidationError('At least one grade band is required.')

    sorted_bands = sorted(normalized, key=lambda band: band['min_score'])
    errors = []
    seen_grades = set()

    if sorted_bands[0]['min_score'] != 0:
        errors.append('Grade bands must start at 0.')
    if sorted_bands[-1]['max_score'] != 100:
        errors.append('Grade bands must end at 100.')

    for index, band in enumerate(sorted_bands):
        grade = band['grade']
        min_score = band['min_score']
        max_score = band['max_score']

        if grade in seen_grades:
            errors.append(f'Duplicate grade label: {grade}.')
        seen_grades.add(grade)

        if min_score < 0 or max_score > 100:
            errors.append(
                f'Grade {grade} scores must be between 0 and 100.',
            )
        if min_score > max_score:
            errors.append(
                f'Grade {grade} minimum score cannot exceed maximum score.',
            )

        if index > 0:
            previous = sorted_bands[index - 1]
            expected_min = previous['max_score'] + 1
            if min_score < expected_min:
                errors.append(
                    f'Grade bands overlap between {previous["grade"]} '
                    f'and {grade}.',
                )
            elif min_score > expected_min:
                errors.append(
                    f'Gap between grade {previous["grade"]} '
                    f'(ends {previous["max_score"]}) and {grade} '
                    f'(starts {min_score}).',
                )

    if errors:
        raise ValidationError(errors)


@transaction.atomic
def apply_grade_template(config, grade_type):
    """Replace config bands with a copy of the selected template."""
    template = get_grade_template(grade_type)
    validate_grade_bands(template)

    config.grade_type = grade_type
    if not config.uses_grades():
        raise ValidationError({
            'result_type': (
                'Grade templates can only be applied when result type '
                'includes grades.'
            ),
        })
    config.save()

    config.grade_bands.all().delete()
    GradeBand.objects.bulk_create([
        GradeBand(
            assessment_config=config,
            grade=str(item['grade']),
            min_score=item['min_score'],
            max_score=item['max_score'],
            remark=item['remark'],
            order=index,
        )
        for index, item in enumerate(template, start=1)
    ])
    return list(config.grade_bands.all())


@transaction.atomic
def replace_grade_bands(config, bands):
    """Replace config bands with a validated custom set."""
    if not config.uses_grades():
        raise ValidationError({
            'result_type': (
                'Grade bands can only be set when result type includes grades.'
            ),
        })
    if not config.grade_type:
        raise ValidationError({
            'grade_type': 'Grade type is required before saving grade bands.',
        })

    normalized = [_band_as_dict(band) for band in bands]
    validate_grade_bands(normalized)

    config.grade_bands.all().delete()
    GradeBand.objects.bulk_create([
        GradeBand(
            assessment_config=config,
            grade=item['grade'],
            min_score=item['min_score'],
            max_score=item['max_score'],
            remark=item['remark'],
            order=index,
        )
        for index, item in enumerate(
            sorted(normalized, key=lambda band: band['min_score'], reverse=True),
            start=1,
        )
    ])
    return list(config.grade_bands.all())


@transaction.atomic
def clear_grade_configuration(config):
    """Switch to position-only and remove grade type/bands."""
    config.grade_bands.all().delete()
    config.grade_type = None
    config.result_type = AssessmentConfig.ResultType.POSITION
    config.save()
    return config


def validate_assessment_config_ready(config):
    """Validate config is complete enough for assessment setup."""
    config.full_clean()
    if config.uses_grades():
        bands = list(config.grade_bands.all())
        validate_grade_bands(bands)
