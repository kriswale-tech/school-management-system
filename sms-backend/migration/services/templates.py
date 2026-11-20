import csv
from io import BytesIO, StringIO

from openpyxl import Workbook

from migration.targets import TEMPLATE_DOWNLOAD_FIELDS

EXAMPLES = {
    'student_information': [
        '',
        'Ama',
        'Mensah',
        '',
        'female',
        '2010-01-15',
        '2025-09-01',
        'yes',
        'JHS 1',
        '',
        'Ama Mensah',
        '0244000001',
        '',
        'mother',
        'active',
    ],
    'enrollment_history': [
        'STU-1',
        '2020/2021',
        'first',
        'JHS 1',
        '',
        '2020-09-01',
        'active',
    ],
    'opening_balances': [
        'STU-1',
        '2020/2021',
        'first',
        '150.00',
        '',
        '',
    ],
    'historical_charges': [
        'STU-1',
        '2020/2021',
        'first',
        'Tuition',
        '500.00',
        '',
        '',
    ],
    'historical_payments': [
        'STU-1',
        'PAY-1',
        '2020-01-15',
        '500.00',
        'cash',
        '2020/2021',
        'first',
        '',
        'ordinary',
        '',
    ],
}


def _template_lines(template):
    if template == 'student_information':
        return [
            'One row is one student.',
            'Gender, date of birth, and admission date are required for a new student.',
            'Class is the student\'s current class. Add the stream in its own column, or write both in Class, such as JHS 1A.',
            'Leave Class blank if you are not placing the student in the current term.',
            'Dates can be 2010-01-15 or 15/01/2010.',
        ]
    if template == 'opening_balances':
        return [
            'One row is one student\'s outstanding balance for one academic year and term.',
            'The student must already exist. This file does not create students.',
            'Delete the example row before you upload the file.',
            'Use a year such as 2020/2021 and a term such as first, second, or third.',
            'Amounts are in GHS, with up to two decimal places. A zero balance is left out.',
            'Do not put the same student, year, and term on more than one row.',
        ]
    if template == 'historical_charges':
        return [
            'One row is one fee for one student, year, and term.',
            'The student must already exist. This file does not create students.',
            'Delete the example row before you upload the file.',
            'The amount is what the student was meant to pay, after any old discount.',
            'Do not repeat the same student, year, term, and fee name.',
        ]
    if template == 'historical_payments':
        return [
            'One row is the share of a payment for one term.',
            'The same payment reference on two rows, with the same student, date, method, and receipt, is one payment split across those terms.',
            'Use ordinary for money applied to the term. Use advance for credit that is not applied to the term.',
            'Delete the example row before you upload the file.',
        ]
    return [
        'One row is one student in one term.',
        'The student ID must already exist. This file does not create students.',
        'Use the year label your school uses, such as 2020/2021, and term first, second, or third.',
        'A past class that the school no longer uses is kept as an inactive class.',
    ]


def build_template_csv(template):
    fields = TEMPLATE_DOWNLOAD_FIELDS[template]
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([label for _key, label, _required in fields])
    writer.writerow(EXAMPLES[template])
    return buffer.getvalue()


def build_template_xlsx(template):
    fields = TEMPLATE_DOWNLOAD_FIELDS[template]
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = {
        'student_information': 'Students',
        'opening_balances': 'Opening balances',
        'historical_charges': 'Charges',
        'historical_payments': 'Payments',
    }.get(template, 'Enrollments')
    sheet.append([label for _key, label, _required in fields])
    sheet.append(EXAMPLES[template])
    notes = workbook.create_sheet('Notes')
    notes.append(['How to use this file'])
    lines = _template_lines(template)
    for line in lines:
        notes.append([line])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
