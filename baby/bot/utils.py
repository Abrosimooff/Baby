from django.utils.functional import cached_property
from vk_api import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from bot.base import BotRequest, Action
from bot.models import AttachType

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