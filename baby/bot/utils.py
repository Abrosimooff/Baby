import datetime
import json
import random

import pytz
from django.db.models import Max
from django.utils.functional import cached_property
from vk_api import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from bot.base import BotRequest, Action, DEFAULT_KEYBOARD
from bot.helpers import DateUtil
from bot.messages import MONTH_MESSAGES
from bot.models import AttachType, Baby, BabyHistory

VK_KEY = '2a41e2391b546114ebaf498df8b9fbf46d2fc8aae209200d038f80ca133f19f214b701d55befe7dbd9e6d'


class Message(object):
    """ Обёртка для сообщения """
    message = None
    vk_api = None

    def __init__(self, message_id, vk_api):
        self.vk_api = vk_api
        self.message = self.vk_api.messages.getById(message_ids=message_id)

    @cached_property
    def fwd_messages(self):
        return self.message['items'][0]['fwd_messages']

    @cached_property
    def attachment_list(self):
        """ Есть ли вложения в сообщении """
        attachments = self.message['items'][0]['attachments']
        for msg in self.fwd_messages:  # проверяем вложения перисланных сообщений
            attachments.extend(msg['attachments'])
        return attachments

    @cached_property
    def photo_list(self):
        """ Список вложенных фото """
        good_sizes = ['w', 'z', 'y']  # Размеры изображения, которые нас интересуют (от большего к меньшему)
        url_list = []
        for item in self.attachment_list:
            size_dict = dict()
            if item['type'] == AttachType.PHOTO:
                for s in item[AttachType.PHOTO]['sizes']:
                    size_dict[s['type']] = s['url']
                for size in good_sizes:
                    url = size_dict.get(size)
                    if url:
                        url_list.append(url)
                        break
        return url_list

    @cached_property
    def all_text(self):
        # Собираем текст и текст пересланных сообщений в один текст
        message_text = self.message['items'][0]['text']
        if self.fwd_messages:
            for msg in self.fwd_messages:
                if message_text:
                    message_text += '\n{}'.format(msg['text'])
                else:
                    message_text = msg['text']
        return message_text

    @cached_property
    def other_attach_exists(self):
        """ Есть ли в сообщении другие вложения """
        return bool([x for x in filter(lambda x: x['type'] != AttachType.PHOTO, self.attachment_list)])


class VkHelp(object):
    vk_api = None
    # https://vk.com/dev/emoji

    def __init__(self):
        vk_session = vk_api.VkApi(token=VK_KEY)
        self.longpoll = VkLongPoll(vk_session)
        self.vk_api = vk_session.get_api()

    def process(self):
        for event in self.longpoll.listen():
            # Теперь пускаем в Action с разными видами событий, а там уже разбирать их)
            if event.message_id:
                _message = Message(event.message_id, self.vk_api)
                bot_request = BotRequest(message=_message, event=event, vk_api=self.vk_api)
                Action(event, bot_request).run_action()


class Sender(object):
    """ Рассылка сообщений """
    on_date = None
    MAX_CALM_DAYS = 10  # количество дней спокойствия, потом напомним что давно ничего не писали в альбом

    def __init__(self, on_date=None):
        self.on_date = on_date or datetime.date.today()

    def month_count(self, birth_date):
        """ Получить количество месяцев прошедших от дня рождения """
        delta = DateUtil.delta(self.on_date, birth_date)
        return (delta.years * 12) + delta.months

    def month_process(self):
        """ Рассылка в ДЕНЬ рождения каждый месяц """
        baby_list = list(Baby.objects.filter(birth_date__day=self.on_date.day))

        # если сегодня 1 число, а вчера было меньше чем 31 - то надо не упустить детей с ДР 31 числа (29, 30, 31)
        if self.on_date.day == 1 and (self.on_date - datetime.timedelta(days=1)).day < 31:
            last_day = (self.on_date - datetime.timedelta(days=1)).day
            day_range = range(last_day + 1, 32)  # 1 марта поздравляем тех, у кого ДЕНЬ 29,30,31
            baby_list.extend(list(Baby.objects.filter(birth_date__day__in=day_range)))

        print('date: {}, baby count: {}'.format(self.on_date, len(baby_list)))
        for baby in baby_list:
            month_count = self.month_count(baby.birth_date)
            message = MONTH_MESSAGES.get(month_count)
            print(self.on_date, baby, month_count, message)
            if message:
                for user_vk in baby.parent_list:
                    user_vk.wait_payload = None
                    user_vk.save()
                    VkHelp().vk_api.messages.send(
                        user_id=user_vk.user_vk_id,
                        message=message,
                        random_id=random.randint(0, 10000000),
                        keyboard=json.dumps(DEFAULT_KEYBOARD)
                    )

    def saturday_process(self):
        """ Субботние напоминания, что давно ничего не постили  """
        baby_ids = []
        for baby_id, max_date in BabyHistory.objects.values_list('baby').annotate(max=Max('date_vk')):
            if DateUtil().delta(self.on_date, max_date.date()).days > self.MAX_CALM_DAYS:
                baby_ids.append(baby_id)

        for baby in Baby.objects.filter(id__in=baby_ids):
            if baby.is_women:
                message = 'Привет!\nВы уже давно ничего не отправляли в альбом своей малышки. \n'
            else:
                message = 'Привет!\nВы уже давно ничего не отправляли в альбом своего малыша. \n'
            message += 'Ждём от вас новых фоточек и сообщений :)\n' \
                       'P.S. Альбом сам себя не заполнит ;)'
            for user_vk in baby.parent_list:
                user_vk.wait_payload = None
                user_vk.save()
                VkHelp().vk_api.messages.send(
                    user_id=user_vk.user_vk_id,
                    message=message,
                    random_id=random.randint(0, 10000000),
                    keyboard=json.dumps(DEFAULT_KEYBOARD)
                )
