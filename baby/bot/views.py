import json
import random
from functools import update_wrapper

from django.shortcuts import render

# Create your views here.
from django.urls import resolve
from django.utils.decorators import classonlymethod
from django.views import View

from bot.models import UserVK


class BotRequest(object):
    message = None
    event = None
    vk_api = None

    def __init__(self, message=None, event=None, vk_api=None):
        self.message = message
        self.event = event
        self.vk_api = vk_api


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

    # def process_start(self, bot_request):
    #     match = resolve('/start/None/', urlconf='bot.urls')
    #     return StartLine().as_view(bot_request, question_pk=None)

    def get_action(self, bot_request):
        if not self.user_vk:
            return '/start/None/'
        if self.user_vk.wait_payload_dict:
            return self.user_vk.wait_payload_dict['action']
        elif hasattr(bot_request.event, 'payload'):
            payload = json.loads(bot_request.event.payload)
            return payload['action']

    def process_payload(self, bot_request):
        response = None
        try:
            self.user_vk = UserVK.objects.get(user_vk_id=bot_request.event.user_id)
        except UserVK.DoesNotExist:
            self.user_vk = None

        action = self.get_action(bot_request)

        # разбираем
        # action = None
        # if self.user_vk.wait_payload:
        #     action = self.user_vk.wait_payload['action']
        # elif hasattr(bot_request.event, 'payload'):
        #     payload = json.loads(bot_request.event.payload)
        #     action = payload['action']

        print('action', action)
        if action:
            match = resolve(action, urlconf='bot.urls')
            if match:
                func = match.func
                args = match.args
                kwargs = match.kwargs
                response = func(bot_request, *args, **kwargs)
        else:
            # Когда ничего не ожидаем от пользователя - отвечаем так))
            bot_request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                message=u'Информацию принял! Спасибо)',
                random_id=random.randint(0, 10000000)
            )
        # # отвечаем
        # bot_request.vk_api.messages.send(  # Отправляем сообщение
        #     user_id=bot_request.event.user_id,
        #     message='Сколько ты хочешь детей?',
        #     random_id=random.randint(0, 10000000),
        #     keyboard=json.dumps(dict(
        #         one_time=True,
        #         buttons=[[
        #             dict(
        #                 action=dict(
        #                     type="text",
        #                     label=random.randrange(0, 100),
        #                     payload=dict(action='/answer_question/1/')),
        #                 color="positive"
        #             ),
        #             dict(
        #                 action=dict(
        #                     type="text",
        #                     label=random.randrange(0, 100),
        #                     payload=dict(action='/answer_question/1/')),
        #                 color="negative"
        #             )
        #         ]]
        #     ))
        # )


class AnswerQuestionLine(BaseLine):
    """ Ответ на вопрос """
    def bot_handler(self, request, *args, **kwargs):
        print('AnswerQuestionLine', request, args, kwargs)
        super().bot_handler(request, *args, **kwargs)


class StartLine(BaseLine):
    """ Стартовая линия """

    question_list = [
        u'Кто у Вас? Мальчик? Девочка?',
        u'Ок. Как зовут вашу/вашего *** ?',
        u'Выберите год рождения:',
        u'Выберите месяц рождения:',
        u'Выберите день рождения:',
    ]

    def bot_handler(self, request, *args, **kwargs):

        if not self.user_vk:

            # Отправляем первое сообщение
            self.user_vk = UserVK.objects.create(user_vk_id=request.event.user_id)
            request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                message='Привет. Начнём создавать альбом для твоего ребёнка :)\n'
                        'Для начала немного расскажи о своём малыше.',
                random_id=random.randint(0, 10000000)
            )

            # ожидаем след сообщение от пользователя как ответ на /start/0/
            payload = dict(action='/start/0/')
            self.user_vk.wait_payload = payload
            self.user_vk.save()

            # Отправляем первое сообщение из линии настроек
            request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                message=self.question_list[0],
                random_id=random.randint(0, 10000000)
            )
        else:
            question_pk = int(kwargs.get('question_pk'))
            if question_pk < len(self.question_list):
                # разбираем ответ на вопрос
                print(self.question_list[question_pk])
                print(self.request.event.text)

                # Если это был послдений вопрос
                if question_pk + 1 == len(self.question_list):
                    self.user_vk.wait_payload = None
                    self.user_vk.save()

                    # Отправляем сообщение что линия закончена
                    request.vk_api.messages.send(
                        user_id=self.user_vk.user_vk_id,
                        message=u'Спасибо. Теперь мы познакомились. Далее немного расскажу о себе :)',
                        random_id=random.randint(0, 10000000)
                    )
                else:
                    # задаём след вопрос
                    # ожидаем след сообщение от пользователя как ответ на /start/question_pk + 1/
                    payload = dict(action='/start/{}/'.format(question_pk + 1))
                    self.user_vk.wait_payload = payload
                    self.user_vk.save()

                    # Отправляем первое сообщение из линии настроек
                    request.vk_api.messages.send(
                        user_id=self.user_vk.user_vk_id,
                        message=u'Ок. %s' % self.question_list[question_pk + 1],
                        random_id=random.randint(0, 10000000)
                    )
        super().bot_handler(request, *args, **kwargs)