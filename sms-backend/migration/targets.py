"""Target fields the mapper can point at. Phase 1 does not write these models."""

STUDENT_FIELDS = (
    ('student_id', 'Student ID', False),
    ('first_name', 'First name', True),
    ('last_name', 'Last name', True),
    ('other_names', 'Other names', False),
    ('full_name', 'Full name', False),
    ('gender', 'Gender', True),
    ('date_of_birth', 'Date of birth', True),
    ('admission_date', 'Admission date', True),
    ('address', 'Address', False),
    ('guardian_name', 'Guardian name', False),
    ('guardian_phone', 'Guardian phone', False),
    ('guardian_email', 'Guardian email', False),
    ('guardian_relationship', 'Guardian relationship', False),
    ('class_name', 'Class', False),
    ('academic_year', 'Academic year', False),
    ('term', 'Term', False),
    ('is_active', 'Active', False),
    ('is_graduated', 'Graduated', False),
    ('external_id', 'External student ID', False),
    ('leave_reason', 'Leave reason', False),
)

FEE_FIELDS = (
    ('student_id', 'Student ID', False),
    ('full_name', 'Student name', False),
    ('term', 'Term', False),
    ('academic_year', 'Academic year', False),
    ('fee_name', 'Fee name', False),
    ('amount', 'Amount', False),
    ('payment_date', 'Payment date', False),
    ('payment_amount', 'Payment amount', False),
    ('payment_method', 'Payment method', False),
    ('receipt_number', 'Receipt number', False),
    ('payment_reference', 'Payment reference', False),
)

FIELDS_BY_JOB = {
    'student_enrollment': STUDENT_FIELDS,
    'fee_financial_history': FEE_FIELDS,
}

STUDENT_TEMPLATE_FIELDS = (
    ('student_id', 'Student ID', False),
    ('first_name', 'First name', True),
    ('last_name', 'Last name', True),
    ('other_names', 'Other names', False),
    ('full_name', 'Full name', False),
    ('gender', 'Gender', True),
    ('date_of_birth', 'Date of birth', True),
    ('admission_date', 'Admission date', True),
    ('is_new_student', 'New student', False),
    ('class_name', 'Class', False),
    ('stream_name', 'Stream', False),
    ('guardian_name', 'Guardian name', False),
    ('guardian_phone', 'Guardian phone', False),
    ('guardian_email', 'Guardian email', False),
    ('guardian_relationship', 'Relationship', False),
    ('student_status', 'Status', False),
    ('external_id', 'External student ID', False),
    ('address', 'Address', False),
)

ENROLLMENT_TEMPLATE_FIELDS = (
    ('student_id', 'Student ID', True),
    ('academic_year', 'Academic year', True),
    ('term', 'Term', True),
    ('class_name', 'Class', True),
    ('stream_name', 'Stream', False),
    ('enrollment_date', 'Enrollment date', False),
    ('enrollment_status', 'Status', False),
)

OPENING_BALANCE_FIELDS = (
    ('student_id', 'Student ID', True),
    ('academic_year', 'Academic year', True),
    ('term', 'Term', True),
    ('outstanding_balance', 'Outstanding balance', True),
    ('source_reference', 'Source reference', False),
    ('notes', 'Notes', False),
    ('first_name', 'First name', False),
    ('last_name', 'Last name', False),
    ('full_name', 'Full name', False),
    ('date_of_birth', 'Date of birth', False),
    ('external_id', 'External student ID', False),
    ('guardian_phone', 'Guardian phone', False),
    ('currency', 'Currency', False),
)

OPENING_BALANCE_DOWNLOAD_FIELDS = tuple(
    item for item in OPENING_BALANCE_FIELDS
    if item[0] in {
        'student_id',
        'academic_year',
        'term',
        'outstanding_balance',
        'source_reference',
        'notes',
    }
)

HISTORICAL_CHARGE_FIELDS = (
    ('student_id', 'Student ID', True),
    ('academic_year', 'Academic year', True),
    ('term', 'Term', True),
    ('fee_item', 'Fee item', True),
    ('amount', 'Amount', True),
    ('source_reference', 'Source reference', False),
    ('notes', 'Notes', False),
    ('first_name', 'First name', False),
    ('last_name', 'Last name', False),
    ('full_name', 'Full name', False),
    ('date_of_birth', 'Date of birth', False),
    ('external_id', 'External student ID', False),
    ('guardian_phone', 'Guardian phone', False),
)

HISTORICAL_PAYMENT_FIELDS = (
    ('student_id', 'Student ID', True),
    ('payment_reference', 'Payment reference', True),
    ('payment_date', 'Payment date', True),
    ('amount', 'Amount', True),
    ('payment_method', 'Payment method', True),
    ('academic_year', 'Academic year', True),
    ('term', 'Term', True),
    ('legacy_receipt_number', 'Receipt number', False),
    ('payment_type', 'Payment type', True),
    ('notes', 'Notes', False),
    ('first_name', 'First name', False),
    ('last_name', 'Last name', False),
    ('full_name', 'Full name', False),
    ('date_of_birth', 'Date of birth', False),
    ('external_id', 'External student ID', False),
    ('guardian_phone', 'Guardian phone', False),
)

TEMPLATE_FIELDS = {
    'student_information': STUDENT_TEMPLATE_FIELDS,
    'enrollment_history': ENROLLMENT_TEMPLATE_FIELDS,
    'opening_balances': OPENING_BALANCE_FIELDS,
    'historical_finance': HISTORICAL_CHARGE_FIELDS,
}

TEMPLATE_DOWNLOAD_FIELDS = {
    'student_information': tuple(
        item for item in STUDENT_TEMPLATE_FIELDS if item[0] not in {'full_name', 'external_id', 'address'}
    ),
    'enrollment_history': ENROLLMENT_TEMPLATE_FIELDS,
    'opening_balances': OPENING_BALANCE_DOWNLOAD_FIELDS,
    'historical_charges': HISTORICAL_CHARGE_FIELDS[:7],
    'historical_payments': HISTORICAL_PAYMENT_FIELDS[:10],
}

DATE_FIELDS = frozenset({
    'date_of_birth',
    'admission_date',
    'enrollment_date',
    'payment_date',
})

PHONE_FIELDS = frozenset({'guardian_phone'})

HEADER_ALIASES = {
    'external id': 'external_id',
    'legacy id': 'external_id',
    'student id': 'student_id',
    'student_id': 'student_id',
    'admission number': 'student_id',
    'admission no': 'student_id',
    'pupil id': 'student_id',
    'first name': 'first_name',
    'firstname': 'first_name',
    'last name': 'last_name',
    'lastname': 'last_name',
    'surname': 'last_name',
    'other names': 'other_names',
    'other name': 'other_names',
    'middle name': 'other_names',
    'full name': 'full_name',
    'pupil name': 'full_name',
    'student name': 'full_name',
    'name': 'full_name',
    'sex': 'gender',
    'gender': 'gender',
    'dob': 'date_of_birth',
    'date of birth': 'date_of_birth',
    'birth date': 'date_of_birth',
    'born': 'date_of_birth',
    'admission date': 'admission_date',
    'date admitted': 'admission_date',
    'address': 'address',
    'residence': 'address',
    'guardian': 'guardian_name',
    'guardian name': 'guardian_name',
    'parent name': 'guardian_name',
    'father': 'guardian_name',
    'phone': 'guardian_phone',
    'guardian phone': 'guardian_phone',
    'parent phone': 'guardian_phone',
    'tel': 'guardian_phone',
    'mobile': 'guardian_phone',
    'email': 'guardian_email',
    'guardian email': 'guardian_email',
    'relationship': 'guardian_relationship',
    'parent type': 'guardian_relationship',
    'guardian relationship': 'guardian_relationship',
    'class': 'class_name',
    'class name': 'class_name',
    'form': 'class_name',
    'academic year': 'academic_year',
    'year': 'academic_year',
    'term': 'term',
    'fee': 'fee_name',
    'fee name': 'fee_name',
    'amount': 'amount',
    'balance': 'amount',
    'amount owed': 'amount',
    'payment date': 'payment_date',
    'date paid': 'payment_date',
    'paid': 'payment_amount',
    'payment amount': 'payment_amount',
    'receipt': 'receipt_number',
    'receipt number': 'receipt_number',
    'receipt no': 'receipt_number',
    'reference': 'payment_reference',
    'payment method': 'payment_method',
    'method': 'payment_method',
    'graduated': 'is_graduated',
    'is graduated': 'is_graduated',
    'leave reason': 'leave_reason',
    'reason for leaving': 'leave_reason',
    'stream': 'stream_name',
    'stream name': 'stream_name',
    'current class': 'class_name',
    'birthday': 'date_of_birth',
    'date joined': 'admission_date',
    'parent contact': 'guardian_phone',
    'new student': 'is_new_student',
    'is new student': 'is_new_student',
    'status': 'student_status',
    'student status': 'student_status',
}

ENROLLMENT_ALIASES = {
    'student id': 'student_id',
    'student_id': 'student_id',
    'admission number': 'student_id',
    'admission no': 'student_id',
    'pupil id': 'student_id',
    'academic year': 'academic_year',
    'year': 'academic_year',
    'term': 'term',
    'class': 'class_name',
    'class name': 'class_name',
    'current class': 'class_name',
    'form': 'class_name',
    'stream': 'stream_name',
    'stream name': 'stream_name',
    'enrollment date': 'enrollment_date',
    'date enrolled': 'enrollment_date',
    'status': 'enrollment_status',
    'enrollment status': 'enrollment_status',
}


def fields_for(job_type, template='', role=''):
    if template == 'historical_finance':
        if role == 'payments':
            return HISTORICAL_PAYMENT_FIELDS
        return HISTORICAL_CHARGE_FIELDS
    if template in TEMPLATE_FIELDS:
        return TEMPLATE_FIELDS[template]
    return FIELDS_BY_JOB[job_type]


OPENING_ALIASES = {
    'student id': 'student_id',
    'student_id': 'student_id',
    'admission number': 'student_id',
    'admission no': 'student_id',
    'pupil id': 'student_id',
    'academic year': 'academic_year',
    'year': 'academic_year',
    'term': 'term',
    'outstanding balance': 'outstanding_balance',
    'outstanding_balance': 'outstanding_balance',
    'balance': 'outstanding_balance',
    'amount': 'outstanding_balance',
    'arrears': 'outstanding_balance',
    'amount owing': 'outstanding_balance',
    'amount owed': 'outstanding_balance',
    'source reference': 'source_reference',
    'reference': 'source_reference',
    'notes': 'notes',
    'note': 'notes',
    'first name': 'first_name',
    'last name': 'last_name',
    'full name': 'full_name',
    'name': 'full_name',
    'date of birth': 'date_of_birth',
    'dob': 'date_of_birth',
    'external id': 'external_id',
    'external student id': 'external_id',
    'guardian phone': 'guardian_phone',
    'parent phone': 'guardian_phone',
    'currency': 'currency',
}


CHARGE_ALIASES = {
    'student id': 'student_id',
    'student_id': 'student_id',
    'admission number': 'student_id',
    'admission no': 'student_id',
    'pupil id': 'student_id',
    'academic year': 'academic_year',
    'year': 'academic_year',
    'term': 'term',
    'fee item': 'fee_item',
    'fee': 'fee_item',
    'fee name': 'fee_item',
    'item': 'fee_item',
    'amount': 'amount',
    'source reference': 'source_reference',
    'reference': 'source_reference',
    'notes': 'notes',
    'note': 'notes',
    'first name': 'first_name',
    'last name': 'last_name',
    'full name': 'full_name',
    'name': 'full_name',
    'date of birth': 'date_of_birth',
    'dob': 'date_of_birth',
    'external id': 'external_id',
    'guardian phone': 'guardian_phone',
    'parent phone': 'guardian_phone',
}

PAYMENT_ALIASES = {
    'student id': 'student_id',
    'student_id': 'student_id',
    'admission number': 'student_id',
    'admission no': 'student_id',
    'pupil id': 'student_id',
    'payment reference': 'payment_reference',
    'reference': 'payment_reference',
    'payment_reference': 'payment_reference',
    'payment date': 'payment_date',
    'date': 'payment_date',
    'date paid': 'payment_date',
    'amount': 'amount',
    'payment method': 'payment_method',
    'method': 'payment_method',
    'academic year': 'academic_year',
    'year': 'academic_year',
    'term': 'term',
    'receipt number': 'legacy_receipt_number',
    'receipt': 'legacy_receipt_number',
    'receipt no': 'legacy_receipt_number',
    'legacy receipt number': 'legacy_receipt_number',
    'payment type': 'payment_type',
    'type': 'payment_type',
    'notes': 'notes',
    'note': 'notes',
    'first name': 'first_name',
    'last name': 'last_name',
    'full name': 'full_name',
    'name': 'full_name',
    'date of birth': 'date_of_birth',
    'dob': 'date_of_birth',
    'external id': 'external_id',
    'guardian phone': 'guardian_phone',
    'parent phone': 'guardian_phone',
}


def aliases_for(template='', role=''):
    if template == 'enrollment_history':
        return ENROLLMENT_ALIASES
    if template == 'opening_balances':
        return OPENING_ALIASES
    if template == 'historical_finance':
        if role == 'payments':
            return PAYMENT_ALIASES
        return CHARGE_ALIASES
    return HEADER_ALIASES
