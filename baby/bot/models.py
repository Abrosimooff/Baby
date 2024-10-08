import datetime
import json
from urllib.parse import urljoin

import hashids
from django.contrib.auth.models import User
from django.db import models
from django.db.models import CASCADE
from django.urls import reverse
from django.utils.functional import cached_property

from baby.settings import CURRENT_HOST
from bot.models_utils.jsonfield import JSONField
from bot.helpers import DateUtil

ALBUM_COUNT = 6
ALBUM_IDS = range(1, ALBUM_COUNT + 1)


class UserVK(models.Model):
    """ Информация о пользователе ВК """
    ALBUM_CHOICES = [(album_pk, 'Альбом #{}'.format(album_pk)) for album_pk in ALBUM_IDS]

    user = models.ForeignKey(User, verbose_name='Пользователь', null=True, blank=True, on_delete=CASCADE)
    first_name = models.CharField(max_length=200, verbose_name='Имя', blank=True)
    last_name = models.CharField(max_length=200, verbose_name='Фамилия', blank=True)
    user_vk_id = models.IntegerField(verbose_name=u'ID пользователя ВК')
    wait_payload = JSONField(null=True, blank=True, verbose_name=u'Инфо об ожидаемом ответе')
    album_pk = models.PositiveSmallIntegerField(verbose_name=u'Выбраный альбом', default=1, choices=ALBUM_CHOICES)

    class Meta:
        verbose_name = ' Пользователь ВК'
        verbose_name_plural = ' Пользователи ВК'

    def __str__(self):
        return '{} {}'.format(self.first_name, self.last_name)

    @property
    def vk_url(self):
        return 'vk.com/id{}'.format(self.user_vk_id)

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

    @cached_property
    def album_url(self):
        if self.baby:
            hashids_code = hashids.Hashids().encode(self.user_vk_id, self.baby.id)
            return urljoin(base='http://' + CURRENT_HOST, url=reverse('album_print_secret', args=[hashids_code]))
        return 'http://' + CURRENT_HOST

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

    class Meta:
        verbose_name = 'Ребёнок'
        verbose_name_plural = 'Дети'

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

    class Meta:
        verbose_name = 'Связка пользователя с ребёнком'
        verbose_name_plural = 'Связки пользователей с детьми'

    def __str__(self):
        return '{} + {}'.format(self.user_vk, self.baby)


class BabyHistory(models.Model):
    """ История-Хроника ребёнка
        utf8mb4_unicode_ci - чтобы emoji можно было сохранять в таблицу
        https://900913.ru/2015/05/29/mysql-django-emoji/
    """
    baby = models.ForeignKey(Baby, on_delete=CASCADE, verbose_name=u'Младенец')
    text = models.TextField(verbose_name=u'Текст сообщения')
    user_vk = models.ForeignKey(UserVK, on_delete=CASCADE, verbose_name=u'Автор заметки')
    message_vk_id = models.IntegerField(verbose_name=u'ID сообщения ВК')
    date_vk = models.DateTimeField(verbose_name=u'Дата время сообщения')
    # если есть month - значит добавлено в прошлое и date_vk не учитывается
    month = models.PositiveSmallIntegerField(verbose_name='В какой месяц ребёнка добавлено', null=True, blank=True)
    other_attach_vk = models.BooleanField(verbose_name=u'Есть ли другие вложения в сообщении кроме фото', default=False)

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ('date_vk',)

    def __str__(self):
        return self.text


class AttachType(object):
    """ Виды вложений """
    PHOTO = 'photo'


class BabyHistoryAttachment(models.Model):
    """ Вложения к хронике """
    history = models.ForeignKey(BabyHistory, on_delete=CASCADE)
    attachment_type = models.CharField(max_length=50)
    url = models.URLField(verbose_name=u'Путь')
    background_position = models.CharField(max_length=200, verbose_name='Позиция фото', null=True, blank=True)

    class Meta:
        verbose_name = 'Вложение'
        verbose_name_plural = 'Вложения'

    def __str__(self):
        return self.url


class BabyHeight(models.Model):
    """ Рост ребёнка """
    baby = models.ForeignKey(Baby, on_delete=CASCADE)
    date = models.DateField(verbose_name=u'Дата измерения')
    height = models.PositiveSmallIntegerField(verbose_name=u'Рост в сантиметрах')

    class Meta:
        unique_together = ['baby', 'date']
        verbose_name = 'Показание роста'
        verbose_name_plural = 'Показания роста'

    def __str__(self):
        return self.height_str

    @cached_property
    def height_str(self):
        return self.cm_to_str(self.height)

    @staticmethod
    def cm_to_str(cm):
        m, cm = divmod(cm, 100)
        return '{}{}'.format('%sм. ' % m if m else '', '%sсм.' % cm if cm else '')


class BabyWeight(models.Model):
    """ Вес ребёнка """
    baby = models.ForeignKey(Baby, on_delete=CASCADE)
    date = models.DateField(verbose_name=u'Дата измерения')
    weight = models.PositiveSmallIntegerField(verbose_name=u'Вес в граммах')

    class Meta:
        verbose_name = 'Показание веса'
        verbose_name_plural = 'Показания веса'
        unique_together = ['baby', 'date']

    def __str__(self):
        return self.weight_str

    @cached_property
    def weight_str(self):
        return self.gramm_to_str(self.weight)

    @staticmethod
    def gramm_to_str(gramm):
        m, gm = divmod(gramm, 1000)
        return '{}{}'.format('%sкг. ' % m if m else '', '%sг.' % gm if gm else '')
