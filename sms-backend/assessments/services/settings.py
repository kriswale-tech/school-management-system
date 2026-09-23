"""Admin desk: term-scoped assessment structure settings."""

from schools.models import Term
from assessments.services.admin_overview import get_admin_assessment_filter_options
from assessments.services.term_config import (
    copy_forward_assessment_configs,
    is_term_ended,
    term_has_recorded_marks,
)
from schools.services.assessment import get_assessment_setup
from students.services import resolve_term


def get_assessment_settings(*, school, term_id=None) -> dict:
    term = resolve_term(school, term_id)
    copy_forward_assessment_configs(school=school, target_term=term)
    payload = get_assessment_setup(school, term=term)
    filters = get_admin_assessment_filter_options(school=school)
    ended_by_id = {
        str(item.id): is_term_ended(item)
        for item in Term.objects.filter(school=school)
    }
    terms = [
        {
            **item,
            'is_ended': ended_by_id.get(str(item['id']), False),
        }
        for item in filters['terms']
    ]
    ended = is_term_ended(term)
    return {
        **payload,
        'term_id': term.id,
        'term_ended': ended,
        'is_editable': not ended,
        'has_recorded_marks': term_has_recorded_marks(school=school, term=term),
        'terms': terms,
        'active_term_id': filters['active_term_id'],
    }
