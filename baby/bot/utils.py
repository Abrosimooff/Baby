from vk_api import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

from bot.views import BotRequest, BaseLine

VK_KEY = '2a41e2391b546114ebaf498df8b9fbf46d2fc8aae209200d038f80ca133f19f214b701d55befe7dbd9e6d'


class VkHelp(object):
    vk_api = None

    def __init__(self):
        vk_session = vk_api.VkApi(token=VK_KEY)
        self.longpoll = VkLongPoll(vk_session)
        self.vk_api = vk_session.get_api()

    def get_photo_list(self, event):
        good_sizes = ['w', 'z', 'y']  # Размеры изображения, котоыре нас интересуют (от большего к меньшему)
        photo_url_list = []

        if 'photo' in event.attachments.values():
            message_detail = self.vk_api.messages.getById(message_ids=event.message_id)
            attachment_list = message_detail['items'][0]['attachments']
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

    def process(self):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                if event.from_user:  # Если написали в ЛС и на бота

                    photo_list = self.get_photo_list(event)
                    message_detail = self.vk_api.messages.getById(message_ids=event.message_id)
                    bot_request = BotRequest(message=message_detail, photo_list=photo_list, event=event, vk_api=self.vk_api)
                    BaseLine().process_payload(bot_request)