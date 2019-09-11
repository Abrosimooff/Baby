import json

from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import EMPTY_VALUES
from django.db import models
from django import forms
from django.forms import ValidationError as FormValidationError


class JSONFormField(forms.CharField):
    def clean(self, value):

        if value in EMPTY_VALUES and not self.required:
            return None

        value = super(JSONFormField, self).clean(value)

        if isinstance(value, str):
            try:
                json.loads(value)
            except ValueError:
                raise FormValidationError("Enter valid JSON")
        return value

    def to_python(self, value):
        if isinstance(value, dict) or isinstance(value, list):
            return json.dumps(value)
        return super(JSONFormField, self).to_python(value)

class JSONField(models.TextField):

    description = "JsonField"

    # def contribute_to_class(self, cls, name, virtual_only=False):
    #     setattr(cls, name, Creator(self))
    #     super(JSONFieldBase, self).contribute_to_class(cls, name, virtual_only=virtual_only)

    def to_python(self, value):
        if value == "":
            return None

        try:
            if isinstance(value, str):
                return json.loads(value)
        except ValueError:
            pass
        return value

    def get_prep_value(self, value):
        print('get_prep_value', value)
        if value == "" or value is None:
            return None
        return json.dumps(value, cls=DjangoJSONEncoder)

    def formfield(self, **kwargs):
        defaults = {'form_class': JSONFormField}
        defaults.update(kwargs)
        return super(JSONField, self).formfield(**defaults)

########################


#
# class JSONFieldBase(object):
#
#     description = "JsonField"
#     from django.db.models.fields import Creator
#     def contribute_to_class(self, cls, name, virtual_only=False):
#         setattr(cls, name, Creator(self))
#         super(JSONFieldBase, self).contribute_to_class(cls, name, virtual_only=virtual_only)
#
#     def to_python(self, value):
#         if value == "":
#             return None
#
#         try:
#             if isinstance(value, str):
#                 return json.loads(value)
#         except ValueError:
#             pass
#         return value
#
#     def get_prep_value(self, value):
#         if value == "" or value is None:
#             return None
#         return json.dumps(value, cls=DjangoJSONEncoder)
#
#     def formfield(self, **kwargs):
#         defaults = {'form_class': JSONFormField}
#         defaults.update(kwargs)
#         return super(JSONFieldBase, self).formfield(**defaults)
#
#
# class JSONField(JSONFieldBase, models.TextField):
#     """JSONField is a generic textfield that serializes/unserializes JSON objects"""
