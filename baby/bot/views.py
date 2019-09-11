import datetime
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

    def get_action(self, bot_request):

        # Если первый раз - стартуем
        if not self.user_vk:
            return '/start/None/'

        # Если нажали на кнопку
        if hasattr(bot_request.event, 'payload'):
            payload = json.loads(bot_request.event.payload)
            return payload['action']

        # Если от пользователя ожидается action
        elif self.user_vk.wait_payload_dict:
            if self.user_vk.wait_payload_dict.get('action'):
                return self.user_vk.wait_payload_dict['action']

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
    month_list = [
        [(1, "Январь"), (2, "Февраль"), (3, "Март"),  (4, "Апрель")],
        [(5, "Май"), (6, "Июнь"), (7, "Июль"),  (8, "Август")],
        [(9, "Сентябрь"), (10, "Октябрь"), (11, "Ноябрь"),  (12, "Декабрь")]
    ]

    question_list = [
        {'message': u'Кто у Вас? Мальчик? Девочка?', 'field_name': 'gender',
         'keyboard': dict(
            one_time=True,
            buttons=[[
                dict(
                    action=dict(
                        type="text",
                        label=u'Девочка',
                        payload=dict(action='/start/0/', answer=1)),
                    color="positive"
                ),
                dict(
                    action=dict(
                        type="text",
                        label=u'Мальчик',
                        payload=dict(action='/start/0/', answer=2)),
                    color="positive"
                )
            ]]
            )
        },
        {'message': u'Ок. Как зовут вашу/вашего *** ?', 'field_name': 'first_name'},
        {'message': u'Выберите год рождения:', 'field_name': 'year',
         'keyboard': dict(
             one_time=True,
             buttons=[[
                 dict(
                     action=dict(
                         type="text",
                         label=year,
                         payload=dict(action='/start/2/', answer=year)),
                     color="positive"
                 ) for year in reversed(range(datetime.date.today().year-3, datetime.date.today().year+1))
             ]]
         )},
        {'message': u'Выберите месяц рождения:', 'field_name': 'month',
         'keyboard': dict(
             one_time=True,
             buttons=[[
                 dict(
                     action=dict(
                         type="text",
                         label=month[1],
                         payload=dict(action='/start/3/', answer=month[0])),
                     color="positive"
                 )for month in month_part] for month_part in month_list
             ]
         ),
         },
        {'message': u'Напишите какого числа родилась ваше ***:', 'field_name': 'day'},
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
            question = self.question_list[0]
            request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                message=question['message'],
                random_id=random.randint(0, 10000000),
                keyboard=json.dumps(question.get('keyboard', {}))
            )
        else:
            user_payload = self.user_vk.wait_payload_dict
            question_pk = int(kwargs.get('question_pk'))
            current_question = self.question_list[question_pk]
            if 'cleaned_data' not in user_payload:
                user_payload['cleaned_data'] = {}

            if question_pk < len(self.question_list):
                # разбираем ответ на вопрос
                print(current_question['message'])
                print(self.request.event.text)
                # сохраняем ответ на вопрос в user_paylaod
                if hasattr(self.request.event, 'payload'):
                    payload_dict = json.loads(self.request.event.payload)
                    user_payload['cleaned_data'][current_question['field_name']] = payload_dict['answer']
                else:
                    user_payload['cleaned_data'][current_question['field_name']] = self.request.event.text

                print('user_payload', user_payload)

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
                    next_question = self.question_list[question_pk + 1]
                    user_payload['action'] = '/start/{}/'.format(question_pk + 1)
                    self.user_vk.wait_payload = user_payload
                    self.user_vk.save()

                    # Отправляем след сообщение из линии настроек
                    request.vk_api.messages.send(
                        user_id=self.user_vk.user_vk_id,
                        message=u'Ок. %s' % next_question['message'],
                        random_id=random.randint(0, 10000000),
                        keyboard=json.dumps(next_question.get('keyboard', {}))
                    )
        super().bot_handler(request, *args, **kwargs)