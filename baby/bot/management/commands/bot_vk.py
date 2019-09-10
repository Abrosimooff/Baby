import json
import random
import time
import uuid
from django.core.management.base import BaseCommand, CommandError
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import requests

# VK_KEY = 'c22da69da2f2e751ae2246c4cd28b1b3641af15ed016535cb2518053a5e373bc01634afd5284410c97023'
from bot.views import BaseLine, BotRequest

VK_KEY = '2a41e2391b546114ebaf498df8b9fbf46d2fc8aae209200d038f80ca133f19f214b701d55befe7dbd9e6d'
VK_KEY_SERVICE = '1c5717281c5717281c5717288c1c3bd13a11c571c5717284122fb585071b42f664be884'

class Command(BaseCommand):
    help = ''

    # def add_arguments(self, parser):
    #     parser.add_argument('poll_ids', nargs='+', type=int)

    def get_photo(self, attachment_list):
        good_sizes = ['w', 'z', 'y']  # Размеры изображения, котоыре нас интересуют (от большего к меньшему)
        photo_url_list = []

        for item in attachment_list:
            size_dict = dict()
            if item['type'] == 'photo':
                for s in item['photo']['sizes']:
                    size_dict[s['type']] = s['url']
                for size in good_sizes:
                    url = size_dict.get(size)
                    if url:
                        photo_url_list.append(url)
                        break
        return photo_url_list



    def get_attach_list(self, user_id, message_id, media_type, start_from=None, count=30):
        """ получить вложения  """

        print('attachments:')
        attach_list = self.vk.messages.getHistoryAttachments(peer_id=user_id, preserve_order=True, media_type=media_type)#, count=count, start_from=start_from)  # , start_from='14/1'
        # print(attach_list)
        if attach_list['items']:
            by_message = []

            for item in filter(lambda x: x['message_id'] == message_id, attach_list['items']):
                by_message.append(item)
                print('message_id:', item['message_id'], 'next_from:', attach_list['next_from'])
                for s in item['attachment']['photo']['sizes']:
                    print(s)
            print('next_from:', attach_list['next_from'])
            # next_from -> start_from

            if by_message:
                return True
            else:
                return False



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
        self.vk = vk_session.get_api()
        for event in longpoll.listen():
            # print(event.type)
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                if event.from_user:  # Если написали в ЛС
                    ss = ['attachments', 'from_chat', 'from_group', 'from_me', 'from_user',
                          'message_id', 'peer_id', 'raw', 'timestamp', 'to_me', 'type', 'user_id', 'text']
                    for key in ss:
                        print(key, getattr(event, key) if hasattr(event, key) else u'NOT ATTR')

                    if 'photo' in event.attachments.values():
                        message_detail = self.vk.messages.getById(message_ids=event.message_id)
                        print('photo', self.get_photo(message_detail['items'][0]['attachments']))

                    print('**********************')
                    message_detail = self.vk.messages.getById(message_ids=event.message_id)
                    bot_request = BotRequest(message=message_detail, event=event, vk_api=self.vk)
                    BaseLine().process_payload(bot_request)