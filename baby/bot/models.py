import datetime
import json

from django.db import models
from django.db.models import CASCADE
from django.utils.functional import cached_property

from bot.models_utils.jsonfield import JSONField
from bot.helpers import DateUtil


class UserVK(models.Model):
    """ Информация о пользователе ВК """
    user_vk_id = models.IntegerField(verbose_name=u'ID пользователя ВК')
    wait_payload = JSONField(null=True, blank=True, verbose_name=u'Инфо об ожидаемом ответе')

    @property
    def wait_payload_dict(self):
        """ Преобразовать в дикт """
        if self.wait_payload is not None:
            if isinstance(self.wait_payload, dict):
                return self.wait_payload
            return json.loads(self.wait_payload)
        return {}

    @property
    def baby(self):
        """ Ребёнок пользователя, если есть """
        return Baby.objects.filter(babyuservk__user_vk=self).first()

    @property
    def baby2user(self):
        return BabyUserVK.objects.filter(user_vk=self).first()


class Baby(models.Model):
    """ Младенец """
    GENDER_CHOICES = {
        1: u'Девочка',
        2: u'Мальчик'
    }
    first_name = models.CharField(max_length=100, verbose_name=u'Имя младенца')
    birth_date = models.DateField(verbose_name=u'Дата рождения', null=True, blank=True)
    gender = models.PositiveSmallIntegerField(choices=GENDER_CHOICES.items(), verbose_name=u'Пол')

    def __str__(self):
        return u'{} {}'.format(self.first_name, str(self.birth_date))

    @cached_property
    def is_women(self):
        """ девочка ли? """
        return self.gender == 1

    def get_birth_date_delta(self, on_date=None):
        """ Вернуть разницу между ДР ребёнка и выбранной датой в классном формате relativedelta """
        on_date = on_date or datetime.date.today()
        return DateUtil().delta(on_date, self.birth_date)

    def get_birth_date_delta_string(self, on_date=None):
        """ Вернуть разницу между ДР ребёнка и выбранной датой хорошой строкой """
        on_date = on_date or datetime.date.today()
        return DateUtil().delta_string(on_date, self.birth_date)

    @cached_property
    def parent_list(self):
        """ Кому доступен этот ребёнок """
        return UserVK.objects.filter(babyuservk__baby=self)


class BabyUserVK(models.Model):
    """ Привязка младенца к юзеру ВК. т.е кто может заполнять инфу о ребёнке """
    user_vk = models.ForeignKey(UserVK, on_delete=CASCADE)
    baby = models.ForeignKey(Baby, on_delete=CASCADE)


class BabyHistory(models.Model):
    """ История-Хроника ребёнка """
    baby = models.ForeignKey(Baby, on_delete=CASCADE, verbose_name=u'Младенец')
    text = models.TextField(verbose_name=u'Текст сообщения')
    user_vk = models.ForeignKey(UserVK, on_delete=CASCADE, verbose_name=u'Автор заметки')
    message_vk_id = models.IntegerField(verbose_name=u'ID сообщения ВК')
    date_vk = models.DateTimeField(verbose_name=u'Дата время сообщения')
    other_attach_vk = models.BooleanField(verbose_name=u'Есть ли другие вложения в сообщении кроме фото', default=False)

    class Meta:
        ordering = ('date_vk',)


class AttachType(object):
    """ Виды вложений """
    PHOTO = 'photo'


class BabyHistoryAttachment(models.Model):
    """ Вложения к хронике """
    history = models.ForeignKey(BabyHistory, on_delete=CASCADE)
    attachment_type = models.CharField(max_length=50)
    url = models.URLField(verbose_name=u'Путь')


class BabyHeight(models.Model):
    """ Рост ребёнка """
    baby = models.ForeignKey(Baby, on_delete=CASCADE)
    date = models.DateField(verbose_name=u'Дата измерения')
    height = models.PositiveSmallIntegerField(verbose_name=u'Рост в сантиметрах')

    class Meta:
        unique_together = ['baby', 'date']


class BabyWeight(models.Model):
    """ Вес ребёнка """
    baby = models.ForeignKey(Baby, on_delete=CASCADE)
    date = models.DateField(verbose_name=u'Дата измерения')
    weight = models.PositiveSmallIntegerField(verbose_name=u'Вес в граммах')

    class Meta:
        unique_together = ['baby', 'date']
