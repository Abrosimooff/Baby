import random
import uuid
from django.core.management.base import BaseCommand, CommandError
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import requests

# VK_KEY = 'c22da69da2f2e751ae2246c4cd28b1b3641af15ed016535cb2518053a5e373bc01634afd5284410c97023'
VK_KEY = '2a41e2391b546114ebaf498df8b9fbf46d2fc8aae209200d038f80ca133f19f214b701d55befe7dbd9e6d'


class Command(BaseCommand):
    help = ''

    # def add_arguments(self, parser):
    #     parser.add_argument('poll_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        # session = requests.Session()
        # login, password = 'Ваш логин, email или телефон', 'Ваш пароль'
        # vk_session = vk_api.VkApi(login, password)
        # try:
        #     vk_session.auth(token_only=True)
        # except vk_api.AuthError as error_msg:
        #     print('error:', error_msg)
        #     return
        vk_session = vk_api.VkApi(token=VK_KEY)
        longpoll = VkLongPoll(vk_session)
        vk = vk_session.get_api()
        for event in longpoll.listen():
            if event.from_user:
                ss =['attachments', 'extra', 'extra_values', 'flags', 'from_chat', 'from_group', 'from_me', 'from_user',
                     'message_data', 'message_id', 'peer_id', 'raw', 'timestamp', 'to_me', 'type', 'type_id', 'user_id', 'text']
                for key in ss:
                    print(key, getattr(event, key) if hasattr(event, key) else u'NOT ATTR')
                print('**********************')
                # import ipdb
                # ipdb.set_trace()
                # photo = vk.photos.getById(event.message_id)
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
                # Слушаем longpoll, если пришло сообщение то:

                # if event.text == 'Первый вариант фразы' or event.text == 'Второй вариант фразы':  # Если написали заданную фразу
                if event.from_user:  # Если написали в ЛС
                    vk.messages.send(  # Отправляем сообщение
                        user_id=event.user_id,
                        message='Прям в ЛС ? Продолжай..',
                        random_id=random.randint(0, 10000000)
                    )

                # if event.from_chat:  # Если написали в Беседе
                #     vk.messages.send(  # Отправляем собщение
                #         chat_id=event.chat_id,
                #         message='Супер! Продолжай',
                #         random_id=random.randint(0, 10000000)
                #     )