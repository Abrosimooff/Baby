import json

from django.db import models
from django.db.models import CASCADE
from bot.models_utils.jsonfield import JSONField


class UserVK(models.Model):
    """ Информация о пользователе ВК """
    user_vk_id = models.IntegerField(verbose_name=u'ID пользователя ВК')
    wait_payload = JSONField(null=True, blank=True, verbose_name=u'Инфо об ожидаемом ответе')

    @property
    def wait_payload_dict(self):
        """ Преобразовать в дикт """
        if self.wait_payload is not None:
            # print('type2', json.loads(json.loads(self.wait_payload)))
            return json.loads(self.wait_payload)


# class WaitUserVK(models.Model):
#     """ Ожидает ли сейчас программа ответа от юзера и на какой вопрос """
#     user_vk = models.OneToOneField(UserVK, on_delete=CASCADE)
#     payload = JSONField(max_length=100, verbose_name=u'Путь к вопросу')


# class TalkLineVK(models.Model):
#     """ Линия разговора """
#     name = models.CharField(verbose_name=u'Название линии разговора', max_length=100)
#     user_vk = models.ForeignKey(UserVK, on_delete=CASCADE)
#     path = models.CharField(max_length=100, verbose_name=u'Путь к вопросу')
#     answer = models.TextField(verbose_name=u'Ответ')

#
# class Baby(models.Model):
#     """ Младенец """
#     GENDER_CHOICES = {
#         1: u'Девочка',
#         2: u'Мальчик'
#     }
#     first_name = models.CharField(max_length=100, verbose_name=u'Имя младенца')
#     birth_date = models.DateField(verbose_name=u'Дата рождения', null=True, blank=True)
#     gender = models.PositiveSmallIntegerField(choices=GENDER_CHOICES.items(), verbose_name=u'Пол')
#
#
# class BabyUserVK(models.Model):
#     """ Привязка младенца к юзеру ВК. т.е кто может заполнять инфу о ребёнке """
#     user_vk = models.ForeignKey(UserVK, on_delete=CASCADE)
#     baby = models.ForeignKey(Baby, on_delete=CASCADE)
#     last_message_date = models.DateTimeField(verbose_name=u'Время последнего сообщения от юзера', null=True, blank=True)
#
#
# class BabyHistory(models.Model):
#     """ История-Хроника ребёнка """
#     baby = models.ForeignKey(Baby, on_delete=CASCADE, verbose_name=u'Младенец')
#     user_vk = models.ForeignKey(UserVK, on_delete=CASCADE, verbose_name=u'Автор заметки')
#     text = models.TextField(verbose_name=u'Текст заметки')
#     message_vk_id = models.IntegerField(verbose_name=u'ID сообщения ВК')
#     date = models.DateTimeField(verbose_name=u'Дата время заметки')
#
#
# class BabyHistoryAttachment(models.Model):
#     """ Вложения к хронике """
#     history = models.ForeignKey(BabyHistory, on_delete=CASCADE)
#     attachment_type = models.CharField(max_length=50)
#     link = models.URLField(verbose_name=u'Путь')