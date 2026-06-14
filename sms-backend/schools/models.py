from django.db import models
from shared.models import BaseModel

# Create your models here.
class School(BaseModel):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, null=True, blank=True)
    gps_address = models.CharField(max_length=15, null=True, blank=True)
    box_address = models.CharField(max_length=15, null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    phone_number_alt = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    logo = models.ImageField(upload_to='schools/logos/', null=True, blank=True)
    motto = models.TextField(null=True, blank=True)

class AcademicYear(BaseModel):
    pass


class Term(BaseModel):
    pass

class Level(BaseModel):
    pass

class Class(BaseModel):
    pass