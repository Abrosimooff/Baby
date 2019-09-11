from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from bot.models import Baby


class BaseValidate(object):
    value = None
    error_message = u''

    def __init__(self, value=None):
        self.value = value

    def is_valid(self):
        pass


class ValidateInList(BaseValidate):
    value_list = []

    def __init__(self, value=None, value_list=None):
        super(ValidateInList, self).__init__(value=value)
        if value_list:
            self.value_list = value_list

    def is_valid(self):
        if self.value in self.value_list:
            return True
        self.error_message = u'Такое значение нельзя указать'
        return False


class ValidateGenderList(ValidateInList):
    """ Валидация пола """
    value_list = Baby.GENDER_CHOICES.keys()
