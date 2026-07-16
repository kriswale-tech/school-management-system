GRADE_TYPE_LETTER = 'letter'
GRADE_TYPE_NUMERICAL = 'numerical'

GES_INTERNAL_LETTER_GRADES = [
    {
        'grade': 'A',
        'min_score': 80,
        'max_score': 100,
        'remark': 'Excellent',
    },
    {
        'grade': 'B',
        'min_score': 70,
        'max_score': 79,
        'remark': 'Very Good',
    },
    {
        'grade': 'C',
        'min_score': 60,
        'max_score': 69,
        'remark': 'Good',
    },
    {
        'grade': 'D',
        'min_score': 50,
        'max_score': 59,
        'remark': 'Credit',
    },
    {
        'grade': 'E',
        'min_score': 40,
        'max_score': 49,
        'remark': 'Pass',
    },
    {
        'grade': 'F',
        'min_score': 0,
        'max_score': 39,
        'remark': 'Fail',
    },
]

BECE_STANDARD_NUMERICAL_GRADES = [
    {
        'grade': '1',
        'min_score': 90,
        'max_score': 100,
        'remark': 'Highest/Excellent',
    },
    {
        'grade': '2',
        'min_score': 80,
        'max_score': 89,
        'remark': 'Very Good',
    },
    {
        'grade': '3',
        'min_score': 70,
        'max_score': 79,
        'remark': 'Good',
    },
    {
        'grade': '4',
        'min_score': 60,
        'max_score': 69,
        'remark': 'High Average',
    },
    {
        'grade': '5',
        'min_score': 55,
        'max_score': 59,
        'remark': 'Average',
    },
    {
        'grade': '6',
        'min_score': 50,
        'max_score': 54,
        'remark': 'Low Average',
    },
    {
        'grade': '7',
        'min_score': 40,
        'max_score': 49,
        'remark': 'Fair',
    },
    {
        'grade': '8',
        'min_score': 35,
        'max_score': 39,
        'remark': 'Pass',
    },
    {
        'grade': '9',
        'min_score': 0,
        'max_score': 34,
        'remark': 'Lowest/Fail',
    },
]

GRADE_TEMPLATES = {
    GRADE_TYPE_LETTER: GES_INTERNAL_LETTER_GRADES,
    GRADE_TYPE_NUMERICAL: BECE_STANDARD_NUMERICAL_GRADES,
}
