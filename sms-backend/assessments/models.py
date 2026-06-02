from django.db import models
from shared.models import BaseModel
# Create your models here.
class AssessmentConfig(BaseModel):
    pass

class AssessmentItem(BaseModel):
    pass

class AssessmentItemScore(BaseModel):
    pass

class StudentResult(BaseModel):
    pass

class SubjectScore(BaseModel):
    pass

class Report(BaseModel):
    pass

# tentative
class CorrectionRequest(BaseModel):
    pass