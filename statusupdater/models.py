from django.db import models

# Create your models here.

class User(models.Model):
    username = models.CharField(max_length=200)
    access_token = models.CharField(max_length=200)
    hook_id = models.CharField(max_length=36)
    login_count = models.BigIntegerField()
    hook_count = models.BigIntegerField()

