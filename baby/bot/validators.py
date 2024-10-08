import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from bot.models import Baby, BabyHeight, BabyWeight


class BaseValidate(object):
    value = None             # Проверяемое значение -> после is_valid -> может быть преобразовано в более верное
    error_message = u''      # отдаваемое сообщение об ошибке
    cleaned_data = None      # полученный на входе dict с данными
    error_fields = []        # Список полей, в которых была ошибка, чтобы юзер перезаполнил все эти поля

    def __init__(self, value=None, cleaned_data=None):
        self.cleaned_data = cleaned_data
        self.value = value

    def is_valid(self):
        pass


class ValidateInList(BaseValidate):
    value_list = []

    def __init__(self, value=None, cleaned_data=None):
        super(ValidateInList, self).__init__(value=value, cleaned_data=cleaned_data)

    def is_valid(self):
        if self.value in self.value_list:
            return True
        self.error_message = u'Такое значение нельзя указать'
        return False


class ValidateGenderList(ValidateInList):
    """ Валидация пола """
    value_list = Baby.GENDER_CHOICES.keys()


class ValidateMonthList(ValidateInList):
    """ Валидация месяца """
    value_list = range(1, 13)


class ValidateYearList(ValidateInList):
    """ Валидация года """

    @property
    def year_list(self):
        """ Список доступных годов для регистрации"""
        return reversed(range(datetime.date.today().year - 3, datetime.date.today().year + 1))

    @property
    def max_year_list(self):
        """ Список доступных годов для проверки """
        return reversed(range(datetime.date.today().year - 10, datetime.date.today().year + 1))

    def __init__(self, value=None, cleaned_data=None):
        super().__init__(value=value, cleaned_data=cleaned_data)
        self.value_list = self.max_year_list


class ValidateBirthDate(BaseValidate):
    """ Валидация ДР """
    error_fields = ['year', 'month', 'day']

    def __init__(self, value=None, cleaned_data=None):
        super(ValidateBirthDate, self).__init__(value=value)
        try:
            self.birth_date = datetime.date(int(cleaned_data['year']), int(cleaned_data['month']), int(value))
        except Exception as e:
            print(e)
            self.birth_date = None

    def is_valid(self):
        if self.birth_date:
            if self.birth_date <= datetime.date.today():
                self.value = int(self.value)
                return True
            else:
                self.error_message = u'Нужна дата рождения не из будущего.'
                return False
        self.error_message = u'Дата рождения не верна'
        return False


class FirstNameValidate(BaseValidate):

    def is_valid(self):
        if not self.value.strip():
            self.error_message = u'Введите имя ребёнка.'
            return False
        if len(self.value) <= 100:
            return True
        self.error_message = u'Слишком длинное имя.'
        return False


class HeightValidate(BaseValidate):
    """ Валидатор Роста в см """

    def is_valid(self):
        if isinstance(self.value, str):
            if self.value.isdigit():
                val = int(self.value)
            else:
                self.error_message = u'Напишите просто цифру - рост в сантиметрах!'
                return False
        else:
            val = self.value

        if val < 30:
            self.error_message = u'Слишком маленькое значение - возможно вы ошиблись.\n' \
                                 u'Ещё раз напишите рост в сантиметрах'
            return False
        if val > 150:
            self.error_message = u'Слишком большое значение - возможно вы ошиблись.\n' \
                                 u'Ещё раз напишите рост в сантиметрах'
            return False

        last_measure = BabyHeight.objects.filter(baby=self.cleaned_data['baby']).order_by('date').last()
        if last_measure and last_measure.height == val:
            self.error_message = u'В предыдущий раз вы уже передавали такой рост!\n' \
                                 u'Подрастите ещё хоть на сантиметрик, тогда отметим)'
            return False

        self.value = val
        return True


class WeightValidate(BaseValidate):
    """ Валидатор веса в граммах  """

    def is_valid(self):
        if isinstance(self.value, str):
            if self.value.isdigit():
                val = int(self.value)
            else:
                self.error_message = u'Напишите просто цифру - вес в граммах!'
                return False
        else:
            val = self.value

        if val < 500:
            self.error_message = u'Слишком маленькое значение - возможно вы ошиблись.\nЕщё раз напишите вес в граммах'
            return False
        if val > 50000:
            self.error_message = u'Слишком большое значение - возможно вы ошиблись.\nЕщё раз напишите вес в граммах'
            return False

        last_measure = BabyWeight.objects.filter(baby=self.cleaned_data['baby']).order_by('date').last()
        if last_measure and last_measure.weight == val:
            self.error_message = u'В предыдущий раз вы уже передавали такой вес!\n' \
                                 u'Подрастите ещё хоть на пару грамм, тогда отметим)'
            return False
        self.value = val
        return True
