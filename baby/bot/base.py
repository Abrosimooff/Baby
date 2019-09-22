import datetime
import json
import random
import time
from functools import update_wrapper

from django.db.models import Max
from django.utils.functional import cached_property
from django.http import HttpResponse, HttpResponseForbidden
from django.urls import resolve, Resolver404
from django.utils.decorators import classonlymethod
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import BaseUpdateView

from vk_api.bot_longpoll import VkBotEvent, VkBotEventType
from vk_api.longpoll import VkEventType, Event
from vk_api import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

from bot.base_utils.keyboards import DEFAULT_KEYBOARD
from bot.helpers import DateUtil
from bot.messages import MONTH_MESSAGES
from bot.models import AttachType, Baby, BabyHistory, UserVK

VK_KEY = '2a41e2391b546114ebaf498df8b9fbf46d2fc8aae209200d038f80ca133f19f214b701d55befe7dbd9e6d'

VK_GROUP_ID = 186300624
VK_SECRET_KEY = '08a48e9e691f4700b70ae37d09ddcbe7'

# Процесс работы:
# 1. Команда vk_bot
# 2. VkHelp.process_longpoll() обрабатывает события от ВК
# 3. При нужном событии создаётся BotRequest и данными о событии, сообщении и тд
# 4. Создаётся Action(bot_request), определяется view, которую нужно исполнить и .run_action()
# 5. Далее запускается View(BaseLine) где есть def bot_handler(self, bot_request, *args, **kwargs)




class BotRequest(object):
    message = None
    event = None
    vk_api = None

    def __init__(self, message=None, photo_list=None, event=None, vk_api=None):
        self.message = message
        self.photo_list = photo_list or []
        self.event = event  # event может быть и от callbackAPI и от LongpollAPI (и они разные :( )
        self.vk_api = vk_api


class Action(object):
    """ Класс (для LongPollAPI) принимает bot_request и перенаправляет на конкретный action """
    bot_request = None
    action = None
    event = None

    def __init__(self, event, bot_request):
        self.event = event
        self.bot_request = bot_request
        self.action = self.get_action()

    @property
    def user_vk(self):
        try:
            return UserVK.objects.get(user_vk_id=self.bot_request.message.user_id)
        except UserVK.DoesNotExist:
            return None

    @property
    def is_message_new(self):
        return self.event.type == VkEventType.MESSAGE_NEW and self.event.to_me and self.event.from_user

    @property
    def is_message_edit(self):
        return self.event.type == VkEventType.MESSAGE_EDIT and self.event.from_user

    def get_action(self):

        if self.is_message_new:
            # Если первый раз - стартуем
            if not self.user_vk:
                return '/welcome'

            # Если нажали на кнопку
            if self.bot_request.message.payload:
                payload = json.loads(self.bot_request.message.payload)
                return payload['action']

            # Если от пользователя ожидается action
            elif self.user_vk.wait_payload_dict:
                if self.user_vk.wait_payload_dict.get('action'):
                    return self.user_vk.wait_payload_dict['action']

            # Если после предыдущих шагов всё ещё нет ребёнка - редирект
            if not self.user_vk.baby:
                return '/welcome'

            # Если от пользователя ничего не ожидается, то следующее сообщение пойдёт в историю ребёнка
            return '/add_history'

        if self.is_message_edit:
            return '/edit_history'

    def run_action(self):
        print('{}: user_vk: {}, action: {}'.format(datetime.datetime.now(), self.bot_request.message.user_id, self.action))
        if self.action:
            try:
                if self.action[0] != '/':
                    self.action = '/' + self.action
                match = resolve(self.action, urlconf='bot.urls')
                if match:
                    func = match.func
                    args = match.args
                    kwargs = match.kwargs
                    func(self.bot_request, *args, **kwargs)
            except Resolver404:
                self.bot_request.vk_api.messages.send(
                    user_id=self.bot_request.message.user_id,
                    message=u'Упс.. команда не распознана.. ',
                    random_id=random.randint(0, 10000000),
                    # keyboard=json.dumps(DEFAULT_KEYBOARD)
                )


class CallbackAction(Action):
    """ Класс (для CallbackAPI) принимает bot_request и перенаправляет на конкретный action """

    @property
    def is_message_new(self):
        return self.event.type == VkBotEventType.MESSAGE_NEW

    @property
    def is_message_edit(self):
        return self.event.type == VkBotEventType.MESSAGE_EDIT


class BaseLine(View):
    """ Базовый класс для обработчиков """
    user_vk = None

    @classonlymethod
    def as_view(cls, **initkwargs):
        """Main entry point for a request-response process."""
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError("You tried to pass in the %s method name as a "
                                "keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError("%s() received an invalid keyword %r. as_view "
                                "only accepts arguments that are already "
                                "attributes of the class." % (cls.__name__, key))

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get
            self.setup(request, *args, **kwargs)
            if not hasattr(self, 'request'):
                raise AttributeError(
                    "%s instance has no 'request' attribute. Did you override "
                    "setup() and forget to call super()?" % cls.__name__
                )
            return self.dispatch(request, *args, **kwargs)

        view.view_class = cls
        view.view_initkwargs = initkwargs

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())
        return view

    def dispatch(self, request, *args, **kwargs):
        if request.message.user_id < 0:
            print('SKIP MESSAGE:', request.message.item)  # если сюда попало исходящее сообщение от группы
            return HttpResponse('OK')
        try:
            self.user_vk = UserVK.objects.get(user_vk_id=request.message.user_id)
        except UserVK.DoesNotExist:
            self.user_vk = None
        return self.bot_handler(request, *args, **kwargs)

    def bot_handler(self, request, *args, **kwargs):
        pass


class VkCallback(BaseUpdateView):
    event = None
    data = None

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return HttpResponse('OK')

    @cached_property
    def is_test_mode(self):
        """ Если тестовый юзер, то при сallback API - бот ничего не делает  """
        try:
            from baby.settings_local import TEST_USERS_VK
            return self.event.object['user_id'] in TEST_USERS_VK
        except ImportError:
            return False

    def post(self, request, *args, **kwargs):
        if request.content_type == 'application/json':
            self.data = json.loads(request.body)
            if self.data['secret'] != VK_SECRET_KEY:
                return HttpResponseForbidden()

            print('VK DATA:', self.data)
            if self.data.get('type') == 'confirmation' and self.data.get('group_id') == VK_GROUP_ID:
                return HttpResponse('6ade2c54')

            self.event = VkBotEvent(raw=self.data)

            if self.is_test_mode:  # Если тестовый юзер
                return HttpResponse('OK')

            VkHelp().process_callback(self.event)
            # todo при Exception создать модель ErrorEvent
        return HttpResponse('OK')


###############################################

class Message(object):
    """ Обёртка для сообщения """
    message = None
    vk_api = None

    def __init__(self, message_id, vk_api):
        self.vk_api = vk_api
        self.message = self.vk_api.messages.getById(message_ids=message_id)
        print('MESSAGE:', self.item)


    @cached_property
    def item(self):
        """ Дикт со всеми полями сообщения """
        return self.message['items'][0]

    @cached_property
    def fwd_messages(self):
        """ Перисланные сообщеняи внутри этого """
        return self.item['fwd_messages']

    @cached_property
    def id(self):
        """ id сообщения vk """
        return self.item['id']

    @cached_property
    def user_id(self):
        """ vk id отправителя """
        return self.item['from_id']

    @cached_property
    def payload(self):
        return self.item.get('payload')

    @cached_property
    def text(self):
        return self.item['text']

    @cached_property
    def attachment_list(self):
        """ Вложения в сообщении """
        attachments = self.item['attachments']
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
        message_text = self.item['text']
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
    longpoll = None
    vk_session = None
    is_longpoll = False
    # https://vk.com/dev/emoji

    def __init__(self, is_longpoll=False):
        self.is_longpoll = is_longpoll
        self.connect()

    def connect(self):
        self.vk_session = vk_api.VkApi(token=VK_KEY)
        self.vk_api = self.vk_session.get_api()
        print('{}: vk connected.'.format(datetime.datetime.now()))

    def process_longpoll(self):
        self.longpoll = VkLongPoll(self.vk_session, wait=3)
        print('{}: vk process started.'.format(datetime.datetime.now()))
        for event in self.longpoll.listen():
            try:
                # Теперь пускаем в Action с разными видами событий, а там уже разбирать их)
                if event.message_id:
                    _message = Message(event.message_id, self.vk_api)
                    bot_request = BotRequest(message=_message, event=event, vk_api=self.vk_api)
                    Action(event, bot_request).run_action()
            # except (ConnectionResetError, urllib3.exceptions.ProtocolError, requests.exceptions.ConnectionError) \
            except Exception as request_error:
                print('{}: Request Exception: {}'.format(datetime.datetime.now(), request_error))
                time.sleep(3)
                self.connect()
                self.process_longpoll()

    def process_callback(self, event):
        _message = Message(event.object.id, self.vk_api)
        bot_request = BotRequest(message=_message, event=event, vk_api=self.vk_api)
        CallbackAction(event, bot_request).run_action()


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
