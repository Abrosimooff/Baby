import json
import random
from functools import update_wrapper

from django.shortcuts import render

# Create your views here.
from django.urls import resolve
from django.utils.decorators import classonlymethod
from django.views import View


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
        return self.bot_handler(request, *args, **kwargs)

    def bot_handler(self, request, *args, **kwargs):
        pass

    def process_payload(self, bot_request):
        response = None

        # разбираем
        if hasattr(bot_request.event, 'payload'):
            payload = json.loads(bot_request.event.payload)
            action = payload['action']
            print(action)
            match = resolve(action, urlconf='bot.urls')

            if match:
                func = match.func
                args = match.args
                kwargs = match.kwargs
                request = {}
                response = func(request, *args, **kwargs)

        # отвечаем
        bot_request.vk_api.messages.send(  # Отправляем сообщение
            user_id=bot_request.event.user_id,
            message='Сколько ты хочешь детей?',
            random_id=random.randint(0, 10000000),
            keyboard=json.dumps(dict(
                one_time=True,
                buttons=[[
                    dict(
                        action=dict(
                            type="text",
                            label=random.randrange(0, 100),
                            payload=dict(action='/answer_question/1/')),
                        color="positive"
                    ),
                    dict(
                        action=dict(
                            type="text",
                            label=random.randrange(0, 100),
                            payload=dict(action='/answer_question/1/')),
                        color="negative"
                    )
                ]]
            ))
        )


class AnswerQuestionLine(BaseLine):
    """ Ответ на вопрос """
    def bot_handler(self, request, *args, **kwargs):
        print('AnswerQuestionLine', request, args, kwargs)
        question_pk = kwargs.get('question_pk')

        question_list = [
            u'Давай для начала познакомимся. Расскажи немного о своём малыше. Кто у Вас? Мальчик? Девочка?',
            u'Ок. Как зовут вашу/вашего *** ?',
            u'Выберите год рождения:',
            u'Выберите месяц рождения:',
            u'Выберите день рождения:',
        ]

        super().bot_handler(request, *args, **kwargs)