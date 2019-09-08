from django.db import models

# Create your models here.

# class VKUser

class Baby(models.Model):
    first_name = models.CharField(max_length=100, verbose_name=u'Имя младенца')
    birth_date = models.DateField(verbose_name=u'Дата рождения', null=True, blank=True)