from django.db import models
from shared.models import BaseModel
from django.contrib.auth.models import AbstractUser
# Create your models here.
class User(BaseModel, AbstractUser):
    pass


class Role(BaseModel):
    pass