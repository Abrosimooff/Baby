import json
from functools import update_wrapper

from django.http import HttpResponse, HttpResponseForbidden
from django.urls import resolve
from django.utils.decorators import classonlymethod
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import BaseUpdateView
from vk_api.longpoll import VkEventType

from bot.models import UserVK

VK_GROUP_ID = 186300624
VK_SECRET_KEY = '08a48e9e691f4700b70ae37d09ddcbe7'

# Процесс работы:
# 1. Команда vk_bot
# 2. VkHelp.process() обрабатывает события от ВК
# 3. При нужном событии создаётся BotRequest и данными о событии, сообщении и тд
# 4. Создаётся Action(bot_request), определяется view, которую нужно исполнить и .run_action()
# 5. Далее запускается View(BaseLine) где есть def bot_handler(self, bot_request, *args, **kwargs)


DEFAULT_KEYBOARD = dict(
    one_time=True,
    buttons=[[
        dict(
            action=dict(
                type="text",
                label=u'Настройки',
                payload=dict(action='/settings/-1/')
            ),
            color="secondary"
        ),
        dict(
            action=dict(
                type="text",
                label=u'Получить альбом',
                payload=dict(action='/album')
            ),
            color="secondary"
        )
     ]]
     )



class BotRequest(object):
    message = None
    event = None
    vk_api = None

    def __init__(self, message=None, photo_list=None, event=None, vk_api=None):
        self.message = message
        self.photo_list = photo_list or []
        self.event = event
        self.vk_api = vk_api


class Action(object):
    """ Класс принимает bot_request и перенаправляет на конкретный action """
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
            return UserVK.objects.get(user_vk_id=self.bot_request.event.user_id)
        except UserVK.DoesNotExist:
            return None

    def get_action(self):
        if self.event.type == VkEventType.MESSAGE_NEW and self.event.to_me and self.event.from_user:
            # Если первый раз - стартуем
            if not self.user_vk:
                return '/welcome'

            # Если нажали на кнопку
            if hasattr(self.bot_request.event, 'payload'):
                payload = json.loads(self.bot_request.event.payload)
                return payload['action']

            # Если от пользователя ожидается action
            elif self.user_vk.wait_payload_dict:
                if self.user_vk.wait_payload_dict.get('action'):
                    return self.user_vk.wait_payload_dict['action']

            # Если от пользователя ничего не ожидается, то следующее сообщение пойдёт в историю ребёнка
            return '/add_history'

        if self.event.type == VkEventType.MESSAGE_EDIT and self.event.from_user:
            return '/edit_history'

    def run_action(self):
        print('action', self.action)
        if self.action:
            match = resolve(self.action, urlconf='bot.urls')
            if match:
                func = match.func
                args = match.args
                kwargs = match.kwargs
                func(self.bot_request, *args, **kwargs)


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
        try:
            self.user_vk = UserVK.objects.get(user_vk_id=request.event.user_id)
        except UserVK.DoesNotExist:
            self.user_vk = None
        return self.bot_handler(request, *args, **kwargs)

    def bot_handler(self, request, *args, **kwargs):
        pass


class VkCallback(BaseUpdateView):

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return HttpResponse('OK')

    def post(self, request, *args, **kwargs):
        if request.content_type == 'application/json':
            self.data = json.loads(request.body)
            if self.data['secret'] != VK_SECRET_KEY:
                return HttpResponseForbidden()

            print('VK DATA:', self.data)
            if self.data.get('type') == 'confirmation' and self.data.get('group_id') == VK_GROUP_ID:
                return HttpResponse('6ade2c54')
        return HttpResponse('OK')
