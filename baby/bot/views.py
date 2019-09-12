import datetime
import json
import random
from functools import update_wrapper

from django.shortcuts import render

# Create your views here.
from django.urls import resolve
from django.utils.decorators import classonlymethod
from django.views import View

from bot.models import UserVK, Baby, BabyUserVK
from bot.validators import ValidateGenderList, FirstNameValidate, ValidateYearList, ValidateMonthList, ValidateBirthDate

DEFAULT_KEYBOARD = dict(
    one_time=True,
    buttons=[[
        dict(
            action=dict(
                type="text",
                label=u'Настройки',
                payload=dict(action='/settings/-1/')
            ),
            color="positive"
        )
     ]]
     )

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
            return '/welcome'

        # Если нажали на кнопку
        if hasattr(bot_request.event, 'payload'):
            payload = json.loads(bot_request.event.payload)
            return payload['action']

        # Если от пользователя ожидается action
        elif self.user_vk.wait_payload_dict:
            if self.user_vk.wait_payload_dict.get('action'):
                return self.user_vk.wait_payload_dict['action']

    def process_payload(self, bot_request):
        try:
            self.user_vk = UserVK.objects.get(user_vk_id=bot_request.event.user_id)
        except UserVK.DoesNotExist:
            self.user_vk = None

        action = self.get_action(bot_request)

        print('action', action)
        if action:
            match = resolve(action, urlconf='bot.urls')
            if match:
                func = match.func
                args = match.args
                kwargs = match.kwargs
                func(bot_request, *args, **kwargs)
        else:
            # Когда ничего не ожидаем от пользователя - отвечаем так))
            bot_request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                message=u'Информацию принял! Спасибо)',
                random_id=random.randint(0, 10000000)
            )


class AnswerQuestionLine(BaseLine):
    """ Ответ на вопрос """
    def bot_handler(self, request, *args, **kwargs):
        print('AnswerQuestionLine', request, args, kwargs)
        super().bot_handler(request, *args, **kwargs)


class Welcome(BaseLine):
    """ Первое приветственное сообщение и перенаправление на настройки """

    def bot_handler(self, request, *args, **kwargs):
        super().bot_handler(request, *args, **kwargs)
        if not self.user_vk:
            # Отправляем первое сообщение
            self.user_vk = UserVK.objects.create(user_vk_id=request.event.user_id)
            request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                message='Привет. Начнём создавать альбом для твоего ребёнка :)\n'
                        'Для начала немного расскажи о своём малыше.',
                random_id=random.randint(0, 10000000)
            )
            # Перенаправляем на настройки
            match = resolve('/settings/-1/', urlconf='bot.urls')
            match.func(request, *match.args, **match.kwargs)


class StartLine(BaseLine):
    """ Стартовая линия """
    month_list = [
        [(1, "Январь"), (2, "Февраль"), (3, "Март"),  (4, "Апрель")],
        [(5, "Май"), (6, "Июнь"), (7, "Июль"),  (8, "Август")],
        [(9, "Сентябрь"), (10, "Октябрь"), (11, "Ноябрь"),  (12, "Декабрь")]
    ]

    question_list = [
        {'message': u'Кто у Вас? Мальчик? Девочка?', 'field_name': 'gender', 'validator': ValidateGenderList,
         'keyboard': dict(
            one_time=True,
            buttons=[[
                dict(
                    action=dict(
                        type="text",
                        label=u'Девочка',
                        payload=dict(action='/settings/0/', answer=1)),
                    color="positive"
                ),
                dict(
                    action=dict(
                        type="text",
                        label=u'Мальчик',
                        payload=dict(action='/settings/0/', answer=2)),
                    color="positive"
                )
            ]]
            )
        },
        {'message': u'Как зовут вашего малыша?', 'field_name': 'first_name', 'validator': FirstNameValidate},
        {'message': u'Выберите год рождения:', 'field_name': 'year', 'validator': ValidateYearList,
         'keyboard': dict(
             one_time=True,
             buttons=[[
                 dict(
                     action=dict(
                         type="text",
                         label=year,
                         payload=dict(action='/settings/2/', answer=year)),
                     color="positive"
                 ) for year in ValidateYearList().year_list
             ]]
         )},
        {'message': u'Выберите месяц рождения:', 'field_name': 'month', 'validator': ValidateMonthList,
         'keyboard': dict(
             one_time=True,
             buttons=[[
                 dict(
                     action=dict(
                         type="text",
                         label=month[1],
                         payload=dict(action='/settings/3/', answer=month[0])),
                     color="positive"
                 )for month in month_part] for month_part in month_list
             ]
         ),
         },
        {'message': u'Напишите какого числа родился малыш :)', 'field_name': 'day', 'validator': ValidateBirthDate},
    ]    

    def bot_handler(self, request, *args, **kwargs):
        question_pk = kwargs.get('question_pk')
        question_pk = int(question_pk)
        if question_pk == -1:
            self.next_message(0)
        else:
            if self.parse_answer(question_pk):
                self.next_message(question_pk + 1)
        super().bot_handler(request, *args, **kwargs)

    def get_question_pk(self, field_name_list):
        """ Получить индекс вопроса, в котором встретилось поле из field_name_list """
        for index, q in enumerate(self.question_list):
            if q['field_name'] in field_name_list:
                return index

    def error_response(self, question_pk, error_message=u'Ошибка!'):
        current_question = self.question_list[question_pk]
        user_payload = self.user_vk.wait_payload_dict
        user_payload['action'] = '/settings/{}/'.format(question_pk)
        self.user_vk.wait_payload = user_payload
        self.user_vk.save()
        self.request.vk_api.messages.send(
            user_id=self.user_vk.user_vk_id,
            message=u'{}\n{}'.format(error_message, current_question['message']),
            random_id=random.randint(0, 10000000),
            keyboard=json.dumps(current_question.get('keyboard', {}))
        )

    def get_validator(self, question_pk, payload, answer):
        if 'validator' in self.question_list[question_pk]:
            validator_class = self.question_list[question_pk]['validator']
            field_name = self.question_list[question_pk]['field_name']
            return validator_class(value=answer, cleaned_data=payload['cleaned_data'])

    def parse_answer(self, question_pk):
        """
         Этап разбора ответа от пользователя
        :param question_pk:
        :return: bool Пускаем ли дальше к следующему сообщению или ошибка
        """

        user_payload = self.user_vk.wait_payload_dict
        current_question = self.question_list[question_pk]
        if 'cleaned_data' not in user_payload:
            user_payload['cleaned_data'] = {}

        answer = self.request.event.text  # Ответом считаем то, что написал юзер
        if hasattr(self.request.event, 'payload'):  # но если есть payload, значит ответ в нём
            payload_dict = json.loads(self.request.event.payload)
            answer = payload_dict['answer']

        # print('question:', current_question['message'])
        # print('answer:', self.request.event.text)
        # print('user_payload:', user_payload)

        # Валидируем ответ, если валидатор указан
        validator = self.get_validator(question_pk=question_pk, payload=user_payload, answer=answer)
        if validator and not validator.is_valid():
            error_question_pk = question_pk  # На какой вопрос будем возвращать/переспрашивать при ошибке
            if validator.error_fields:
                error_question_pk = self.get_question_pk(validator.error_fields)
            self.error_response(question_pk=error_question_pk, error_message=validator.error_message)
            return False
        else:
            # Если првоерка прошла успешно - сохраняем верное значенеи в user_payload
            user_payload['cleaned_data'][current_question['field_name']] = validator.value
            self.user_vk.wait_payload = user_payload
            self.user_vk.save()
            return True

    def next_message(self, next_question_pk):
        if len(self.question_list) == next_question_pk:  # Если все вопросы отвечены

            # Сохраняем данные из всей линии вопросов
            self.save_cleaned_data()
            self.user_vk.wait_payload = None
            self.user_vk.save()

            # Отправляем сообщение что линия закончена
            self.request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                message=u'Спасибо. Теперь мы познакомились. Далее немного расскажу о себе :)',
                random_id=random.randint(0, 10000000)
            )
        else:
            # задаём след вопрос
            # ожидаем след сообщение от пользователя как ответ на /settings/question_pk + 1/
            user_payload = self.user_vk.wait_payload_dict
            next_question = self.question_list[next_question_pk]
            user_payload['action'] = '/settings/{}/'.format(next_question_pk)
            self.user_vk.wait_payload = user_payload
            self.user_vk.save()

            # Отправляем след сообщение из линии настроек
            self.request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                message=u'Ок. %s' % next_question['message'],
                random_id=random.randint(0, 10000000),
                keyboard=json.dumps(next_question.get('keyboard', {}))
            )

    def save_cleaned_data(self):
        data = self.user_vk.wait_payload_dict['cleaned_data']
        birth_date = datetime.date(data['year'], data['month'], data['day'])
        params = dict(first_name=data['first_name'], birth_date=birth_date, gender=data['gender'])

        # Если у юзера уже есть ребёнок, то обновляем инфу,
        # А если нет ребёнка, то создаём и привязываем
        if self.user_vk.baby:
            self.user_vk.baby.update(**params)
        else:
            baby = Baby.objects.create(**params)
            b2u = BabyUserVK.objects.create(user_vk=self.user_vk, baby=baby, last_message_date=datetime.datetime.now())
