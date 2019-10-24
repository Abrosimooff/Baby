import copy
import datetime
import json
import random
from collections import defaultdict
from urllib.parse import urljoin

import hashids
import pytz
from django.http import HttpResponseNotFound
from django.urls import resolve, reverse
from django.utils.functional import cached_property
from django.views.generic import TemplateView, DetailView

from baby.settings import CURRENT_HOST
from bot.base import BaseLine, DEFAULT_KEYBOARD
from bot.helpers import DateUtil
from bot.models import UserVK, Baby, BabyUserVK, BabyHistory, BabyHistoryAttachment, AttachType, BabyHeight, BabyWeight
from bot.utils.album import AlbumPager
from bot.validators import ValidateGenderList, FirstNameValidate, ValidateYearList, ValidateMonthList, \
    ValidateBirthDate, HeightValidate, WeightValidate


class IndexView(TemplateView):
    template_name = 'bot/index.jinja2'


class Welcome(BaseLine):
    """ Первое приветственное сообщение и перенаправление на настройки|код ребёнка """

    keyboard = dict(
        one_time=True,
        buttons=[
            [
                dict(
                    action=dict(
                        type="text",
                        label=u'Код ребёнка',
                        payload=dict(action='/sharing/get/')
                    ),
                    color="secondary"
                ),
                dict(
                    action=dict(
                        type="text",
                        label=u'Новый альбом',
                        payload=dict(action='/settings/-1/')
                    ),
                    color="secondary"
                ),
            ]
        ])

    def bot_handler(self, request, *args, **kwargs):
        super().bot_handler(request, *args, **kwargs)
        if not self.user_vk:
            # Отправляем первое сообщение
            user_data = request.vk_api.users.get(user_ids=request.message.user_id)
            self.user_vk = UserVK.objects.create(user_vk_id=request.message.user_id,
                                                 first_name=user_data[0]['first_name'],
                                                 last_name=user_data[0]['last_name'],
                                                 )

        if not self.user_vk.baby:
            self.user_vk.wait_payload = dict(action='/welcome')  # если чувак не нажмёт на кнопку, то будет /welcome
            self.user_vk.save()
            request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                keyboard=json.dumps(self.keyboard),
                message='Привет. Начнём создавать альбом для твоего ребёнка :)\n'
                        'Если стобой поделились кодом ребёнка - жми "Код ребёнка".\n'
                        'Если будем заводить новый альбом - жми "Новый альбом"',
                random_id=random.randint(0, 10000000)
            )
        else:
            self.user_vk.wait_payload = None
            self.user_vk.save()
            request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                message='Продолжайте вести ваш альбом :)',
                random_id=random.randint(0, 10000000)
            )

            # # Перенаправляем на настройки
            # match = resolve('/settings/-1/', urlconf='bot.urls')
            # match.func(request, *match.args, **match.kwargs)


class AlbumView(BaseLine):
    """ Получить альбом """

    def bot_handler(self, request, *args, **kwargs):
        self.request.vk_api.messages.send(
            user_id=self.user_vk.user_vk_id,
            message='Ссылка на ваш альбом:\n{}'.format(self.user_vk.album_url),
            random_id=random.randint(0, 10000000),
            keyboard=json.dumps(DEFAULT_KEYBOARD)
        )


class MeasureView(BaseLine):
    model = None
    field_name = ''
    validator_class = None

    @cached_property
    def keyboard(self):
        return dict(
            one_time=True,
            buttons=[[dict(
                action=dict(
                    type="text",
                    label='Отмена',
                    payload=dict(action=reverse('exit'))
                ),
                color="negative"
            )]]
        )

    def get_message(self):
        return ''

    def finish_message(self):
        return 'Готово. Спасибо, что передали показания!)\n'\
               'Можете продолжать вести альбом :)'

    def bot_handler(self, request, *args, **kwargs):
        question_pk = kwargs.get('question_pk')
        # Пишем, что мол напишите цифру
        if question_pk == '0':
            self.user_vk.wait_payload = dict(action='/{}/1/'.format(self.field_name))
            self.user_vk.save()
            self.request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                message=self.get_message(),
                random_id=random.randint(0, 10000000),
                keyboard=json.dumps(self.keyboard)
            )

        # Разбироаем ответ
        elif question_pk == '1':
            answer = self.request.message.text
            validator_obj = self.validator_class(answer, cleaned_data=dict(baby=self.user_vk.baby))
            if validator_obj.is_valid():
                self.last_measure = self.model.objects.filter(baby=self.user_vk.baby).order_by('date').last()
                self.new_measure = self.model.objects.filter(baby=self.user_vk.baby, date=datetime.date.today()).first()
                if self.new_measure:
                    setattr(self.new_measure, self.field_name, validator_obj.value)
                    self.new_measure.save()
                else:
                    self.new_measure = self.model.objects.create(
                        baby=self.user_vk.baby, date=datetime.date.today(), **{self.field_name: validator_obj.value})

                # Отвечаем, что приняли показания
                self.user_vk.wait_payload = None
                self.user_vk.save()
                self.request.vk_api.messages.send(
                    user_id=self.user_vk.user_vk_id,
                    message=self.finish_message(),
                    random_id=random.randint(0, 10000000),
                    keyboard=json.dumps(DEFAULT_KEYBOARD)
                )
            else:
                # Отвечаем, что ОШИБКА! Ждём ответ ещё раз
                self.user_vk.wait_payload = dict(action='/{}/1/'.format(self.field_name))
                self.user_vk.save()
                self.request.vk_api.messages.send(
                    user_id=self.user_vk.user_vk_id,
                    message=validator_obj.error_message,
                    random_id=random.randint(0, 10000000),
                    keyboard=json.dumps(self.keyboard)
                )


class HeightView(MeasureView):
    """ Заполнить рост """
    model = BabyHeight
    field_name = 'height'
    validator_class = HeightValidate

    def get_message(self):
        gstr = 'доросла' if self.user_vk.baby.is_women else 'дорос'
        return 'Напишите до скольки сантиметров уже {} {}?'.format(gstr, self.user_vk.baby.first_name.capitalize())

    def finish_message(self):
        ctx = dict(first_name=self.user_vk.baby.first_name,
                   la='ла' if self.user_vk.baby.is_women else '',
                   measure_str=self.new_measure.height_str)
        if self.last_measure:
            delta = self.new_measure.height - self.last_measure.height
            ctx['days'] = (self.new_measure.date - self.last_measure.date).days
            ctx['cm'] = self.model.cm_to_str(delta)
            if ctx['days']:
                dinamic_text = 'Готово. Значит вы уже {measure_str} За {days} дн. {first_name} подрос{la} на {cm}\n'
            else:
                dinamic_text = 'Готово. Ваши сегодняшние показания роста заменены на {measure_str}\n'
            return dinamic_text.format(**ctx) + 'Спасибо, что передали показания!)\nМожете продолжать вести альбом :)'
        return 'Готово. Ваши первые показания роста ({measure_str}) приняты!\n' \
               'Спасибо, не забывайте периодически сообщать о новых сантиметрах)\n' \
               'А сейчас можете продолжать вести альбом :)'.format(**ctx)


class WeightView(MeasureView):
    """ Заполнить вес """
    model = BabyWeight
    field_name = 'weight'
    validator_class = WeightValidate

    def get_message(self):
        return 'Напишите cколько граммов уже весит {}?'.format(self.user_vk.baby.first_name.capitalize())

    def finish_message(self):
        ctx = dict(first_name=self.user_vk.baby.first_name,
                   la='ла' if self.user_vk.baby.is_women else '',
                   measure_str=self.new_measure.weight_str)
        if self.last_measure:
            delta = self.new_measure.weight - self.last_measure.weight
            ctx['days'] = (self.new_measure.date - self.last_measure.date).days
            ctx['g'] = self.model.gramm_to_str(delta)
            if ctx['days']:
                dinamic_text = 'Готово. Значит вы уже {measure_str} За {days} дн. {first_name} подрос{la} на {g}\n'
            else:
                dinamic_text = 'Готово. Ваши сегодняшние показания веса заменены на {measure_str}\n'

            return dinamic_text.format(**ctx) + 'Спасибо, что передали показания!)\n Можете продолжать вести альбом :)'
        return 'Готово. Ваши первые показания веса({measure_str}) приняты!\n' \
               'Спасибо, не забывайте периодически сообщать о новых граммах)\n' \
               'А сейчас можете продолжать вести альбом :)'.format(**ctx)


class SharingView(BaseLine):
    """ Совместный доступ (Поделиться) :Инфо """

    def bot_handler(self, request, *args, **kwargs):
        super().bot_handler(request, *args, **kwargs)
        code = hashids.Hashids().encode(self.user_vk.user_vk_id, self.user_vk.baby.id)
        info = 'Совместный доступ.\n' \
               'Заполняйте альбом своего ребёнка всей семьёй :)\n' \
               'Поделитесь кодом с родственниками - они укажут этот код при первом знакомстве с ботом ' \
               'и будут вести альбом вместе с вами.\n' \
               'Сейчас вам придёт сообщение с кодом, чтобы вы могли им поделиться.'

        self.user_vk.wait_payload = None
        self.user_vk.save()
        self.request.vk_api.messages.send(
            user_id=self.user_vk.user_vk_id,
            message=info,
            random_id=random.randint(0, 10000000),
            keyboard=json.dumps(DEFAULT_KEYBOARD)
        )
        user_data = self.request.vk_api.users.get(user_ids=self.user_vk.user_vk_id)
        self.request.vk_api.messages.send(
            user_id=self.user_vk.user_vk_id,
            message='Поделился: @id{} ({} {})\n'
                    'Сообщество: @public186300624 (Альбом младенца. Бот)\n'
                    'Ребёнок: {}\n'
                    'Код доступа: {}'.format(self.user_vk.user_vk_id, user_data[0]['first_name'], user_data[0]['last_name'], self.user_vk.baby.first_name, code),
            random_id=random.randint(0, 10000000),
            keyboard=json.dumps(DEFAULT_KEYBOARD)
        )


class SharingGetView(BaseLine):
    """ Прикрепить себе альбом ребёнка по коду """

    keyboard = dict(
        one_time=True,
        buttons=[
            [
                dict(
                    action=dict(
                        type="text",
                        label=u'Отмена',
                        payload=dict(action='/welcome')
                    ),
                    color="negative"
                ),
            ]
        ])

    def send(self, message, payload=None, keyboard=None):
        self.user_vk.wait_payload = payload
        self.user_vk.save()
        self.request.vk_api.messages.send(
            user_id=self.user_vk.user_vk_id,
            message=message,
            random_id=random.randint(0, 10000000),
            keyboard=json.dumps(keyboard or self.keyboard)
        )

    def bot_handler(self, request, *args, **kwargs):
        super().bot_handler(request, *args, **kwargs)
        RESTART = dict(action='/sharing/get/')

        # Если нужно отправить первое сообщение, мол шлите код
        if self.request.message.payload:
            self.send('Ок, присылайте код.', payload=RESTART)
        else:
            text = self.request.message.text
            result_code = hashids.Hashids().decode(text)
            if not result_code:
                self.send('Не можем распознать такой код.', payload=RESTART)
                return

            baby = Baby.objects.filter(pk=result_code[1], babyuservk__user_vk__user_vk_id=result_code[0]).first()
            if not baby:
                self.send('Не можем найти такого ребёнка', payload=RESTART)
                return

            if not BabyUserVK.objects.filter(baby=baby, user_vk=self.user_vk).exists():
                BabyUserVK.objects.create(baby=baby, user_vk=self.user_vk)

            self.send(self.finish_message, payload=None, keyboard=DEFAULT_KEYBOARD)
            return

    @property
    def finish_message(self):
        message = 'Вы присоединились к ведению альбома.\n'
        if self.user_vk.baby.is_women:
             message += 'В альбоме - малышка {} и ей сейчас {}.\n\n'\
                 .format(self.user_vk.baby.first_name, self.user_vk.baby.get_birth_date_delta_string())
        else:
            message += 'В альбоме - малыш {} и ему сейчас {}.\n\n'\
                 .format(self.user_vk.baby.first_name, self.user_vk.baby.get_birth_date_delta_string())
        welcome_text = 'Далее - просто присылайте фотографии, ' \
                       'пишите сообщения, рассказывайте о новых эмоциях, реакциях, умениях, интересах ребёнка.\n' \
                       'В общем, описывайте всё, что хотите увидеть в будущем альбоме вашего ребёнка :)\n' \
                       'Это будет ваш мини-блог для наполнения альбома.\n' \
                       'А я не буду назойливым, и лишь иногда буду напоминать, если вы давно ничем не делились :)'
        return message + welcome_text


class HelpView(BaseLine):
    """  Страница помощи :Инфо"""

    def bot_handler(self, request, *args, **kwargs):
        super().bot_handler(request, *args, **kwargs)
        self.user_vk.wait_payload = None
        self.user_vk.save()
        self.request.vk_api.messages.send(
            user_id=self.user_vk.user_vk_id,
            message='Есть вопросы?\n'
                    'Можете написать администратору сообщества:\n'
                    'VK: @abrosimooff (Виктор Абросимов)\n'
                    'email: abrosimooff@gmail.com',
            random_id=random.randint(0, 10000000),
            keyboard=json.dumps(DEFAULT_KEYBOARD)
        )

class AddHistory(BaseLine):
    """ Добавление сообщения в историю ребёнка """
    history_action = 'add'
    keyboard = DEFAULT_KEYBOARD

    def get_month(self):
        """ Получить номер месяца, в которое добавляется "прошлое" (для PastMonthsAddView) """
        return None

    def update_payload(self):
        """ для PastMonthsAddView  """
        pass

    def create(self):
        if self.message_text or self.photo_list:
            # записываем в историю ребёнка
            history = BabyHistory.objects.create(
                baby=self.user_vk.baby,
                text=self.message_text,
                user_vk=self.user_vk,
                message_vk_id=self.message_id,
                date_vk=self.message_date,
                month=self.get_month(),
                other_attach_vk=self.other_attach_exist
            )
            # записываем вложения
            if self.photo_list:
                BabyHistoryAttachment.objects.bulk_create([BabyHistoryAttachment(
                    history=history,
                    attachment_type=AttachType.PHOTO,
                    url=url)
                for url in self.photo_list])

    def delete(self):
        pass
        # delete_history = BabyHistory.objects.filter(message_vk_id=self.message_id).first()
        # if delete_history:
        #     BabyHistoryAttachment.objects.filter(history=delete_history).delete()
        #     delete_history.delete()


    def bot_handler(self, request, *args, **kwargs):
        # в messages_dict есть:
        # 'date', 'from_id', 'id', 'out', 'peer_id', 'text', 'conversation_message_id', 'fwd_messages',
        # 'important', 'random_id', 'attachments', 'is_hidden']

        message_dict = request.message.message['items'][0]
        self.message_date = pytz.utc.localize(datetime.datetime.fromtimestamp(message_dict['date']))
        self.message_id = request.message.id
        self.message_text = request.message.text
        self.photo_list = request.message.photo_list
        self.small_photo_count = request.message.small_photo_count
        if not self.photo_list:  # Если нет фоток, то собираем текст (вдруг есть перисланные сообщения)
            self.message_text = request.message.all_text
        self.other_attach_exist = request.message.other_attach_exists

        # Если изменение сообщения, то удаляем сообщение и записываем новое
        # if self.history_action == 'edit':
        #     self.delete()

        self.create()
        self.update_payload()
        self.request.vk_api.messages.send(
            user_id=self.user_vk.user_vk_id,
            message=self.get_response_msg(),
            random_id=random.randint(0, 10000000),
            keyboard=json.dumps(self.keyboard)
        )
        super().bot_handler(request, *args, **kwargs)

    def get_response_msg(self):
        if self.history_action == 'edit':
            # response_msg = 'Вы изменили сообщение - мы применили эти изменения в альбоме :)'
            response_msg = 'Временно мы не может принять изменения сообщений.'
        else:
            msg = ''
            if self.photo_list:
                msg = u'Ок. Получил ваши фото ({}шт){}.'.format(len(self.photo_list), ' и описание' if self.message_text else '')
            elif self.message_text:
                msg = u'Ок. Информацию принял.'
            if self.small_photo_count:
                msg += '\nВнимание! Вы прикрепили фото маленького размера ({}шт).\n' \
                       'Такие фото в альбом не принимаются :('.format(self.small_photo_count)

            if self.other_attach_exist:
                msg += '\nИз вложений мы принимаем только фото!'
            response_msg = '{}\nЕсли есть что ещё - пиши :)'.format(msg)
        return response_msg


class EditHistory(AddHistory):
    """ Изменить сообщение """
    history_action = 'edit'


class SettingsLine(BaseLine):
    """ Стартовая линия - Настройки """
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

    @cached_property
    def cancel_button(self):
        return dict(
            action=dict(
                type="text",
                label=u'Отмена',
                payload=dict(action=reverse('exit'))),
            color="negative"
        )

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

        answer = self.request.message.text  # Ответом считаем то, что написал юзер
        if self.request.message.payload:  # но если есть payload, значит ответ в нём
            payload_dict = json.loads(self.request.message.payload)
            answer = payload_dict['answer']

        # print('question:', current_question['message'])
        # print('answer:', self.request.message.text)
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

            is_first_start = self.user_vk.baby is None  # Первый старт - если ребёнок ещё не создан
            # Сохраняем данные из всей линии вопросов
            self.save_cleaned_data()
            self.user_vk.wait_payload = None
            self.user_vk.save()

            message = 'Настройки сохранены. Можете продолжать вести альбом :)'
            if is_first_start:
                message = 'Спасибо. Теперь мы познакомились.\n'
                delta = self.user_vk.baby.get_birth_date_delta()
                delta_str = self.user_vk.baby.get_birth_date_delta_string()
                if self.user_vk.baby.is_women:
                    message += 'У вас малышка {} и ей сейчас {}.'.format(self.user_vk.baby.first_name, delta_str)
                else:
                    message += 'У вас малыш {} и ему сейчас {}.'.format(self.user_vk.baby.first_name, delta_str)
                context = dict(first_name=self.user_vk.baby.first_name, a='а' if self.user_vk.baby.is_women else '')
                welcome_text = \
                    '\n\nСпасибо, что решили создать Альбом - когда {first_name} вырастет - он{a} точно оценит;)\n\n'\
                    'Далее -  уделите время раз в неделю/месяц и присылайте фотографии,'\
                    'пишите сообщения, рассказывайте о новых эмоциях, реакциях, умениях, интересах ребёнка.\n'\
                    'В общем, описывайте всё, что хотите увидеть в будущем альбоме вашего ребёнка :)\n'\
                    'Это будет ваш мини-блог для наполнения альбома.\n' \
                    'А я не буду назойливым, и лишь иногда буду напоминать, если вы давно ничем не делились :)'.format(**context)

                # Если ребёнку сейчас 2 мес. или больше - предлагаем заполнить прошлое
                if delta.years or (delta.months > 1):
                    welcome_text += '\n\nP.S. Предлагаю немного заполнить альбом за более ранние месяца.\n' \
                               'Чтобы это сделать - нажмите "Добавить в прошлое" '.format(delta_str)
                message += welcome_text

            # Отправляем сообщение что линия закончена
            self.request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                message=message,
                random_id=random.randint(0, 10000000),
                keyboard=json.dumps(DEFAULT_KEYBOARD)
            )
        else:
            # задаём след вопрос
            # ожидаем след сообщение от пользователя как ответ на /settings/question_pk + 1/
            user_payload = self.user_vk.wait_payload_dict
            next_question = self.question_list[next_question_pk]
            user_payload['action'] = '/settings/{}/'.format(next_question_pk)
            self.user_vk.wait_payload = user_payload
            self.user_vk.save()

            # Если ребёнок уже создан, то можно дать кнопку - выйти из настроек
            keyboard = copy.deepcopy(next_question.get('keyboard', {}))
            if self.user_vk.baby:
                if keyboard:
                    keyboard['buttons'].append([self.cancel_button])
                else:
                    keyboard = dict(one_time=True, buttons=[[self.cancel_button]])

            # Отправляем след сообщение из линии настроек
            self.request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                message=u'Ок. %s' % next_question['message'],
                random_id=random.randint(0, 10000000),
                keyboard=json.dumps(keyboard)
            )

    def save_cleaned_data(self):
        data = self.user_vk.wait_payload_dict['cleaned_data']
        birth_date = datetime.date(data['year'], data['month'], data['day'])
        params = dict(first_name=data['first_name'], birth_date=birth_date, gender=data['gender'])

        # Если у юзера уже есть ребёнок, то обновляем инфу,
        # А если нет ребёнка, то создаём и привязываем
        if self.user_vk.baby:
            Baby.objects.filter(pk=self.user_vk.baby.pk).update(**params)
        else:
            baby = Baby.objects.create(**params)
            b2u = BabyUserVK.objects.create(user_vk=self.user_vk, baby=baby)


class BabyHistoryMix(object):

    def message_qs(self, baby):
        return BabyHistory.objects.select_related('baby').filter(baby=baby)

    def photo_qs(self, baby):
        return BabyHistoryAttachment.objects.select_related('history').filter(history__baby=baby)

    def measure_qs(self, model, baby):
        return model.objects.filter(baby=baby).order_by('date')

    def baby_history(self, baby):
        """ Вся история малыша """
        messages = self.message_qs(baby)
        photo_dict = defaultdict(list)
        for photo in self.photo_qs(baby):
            photo_dict[photo.history_id].append(photo.url)

        # Измерения

        measure_dict = defaultdict(list)
        for object in self.measure_qs(BabyHeight, baby):
            measure_dict[object.date].append(object)
        for object in self.measure_qs(BabyWeight, baby):
            measure_dict[object.date].append(object)

        today = datetime.date.today()
        baby_history = DateUtil().month_history(today, baby.birth_date)
        utc = pytz.UTC
        for period in baby_history:
            period_messages = []
            measure_dates_in_period = []
            for m in messages:
                # сообщения, добавленные в прошлое (по месяцам)
                if m.month is not None and m.month == period['month']:
                    period_messages.append(m)
                # сообщения, добавленные нормально
                if m.month is None and utc.localize(period['start']) <= m.date_vk < utc.localize(period['end']):
                    period_messages.append(m)
                for date in measure_dict.keys():
                    if period['start'].date() <= date < period['end'].date():
                        measure_dates_in_period.append(date)
            pager = AlbumPager()
            for history in period_messages:  # Ходим по всем истриям и фото и добавляем в пейджер
                for date in sorted(measure_dates_in_period):
                    if date <= history.date_vk.date():
                        if measure_dict.get(date):
                            pager.add_measure(measure_dict.pop(date))  # Добавляем в альбом и удаляем из словаря
                pager.add(history, photo_dict[history.id])

            # оставшиеся измерения  (если есть) вставляем в конец
            for date in sorted(measure_dates_in_period):
                if measure_dict.get(date):
                    pager.add_measure(measure_dict.pop(date))
            period['page_list'] = pager.page_list
        return baby_history


class AlbumPrint(BabyHistoryMix, DetailView):
    """ Формируем альбом """
    page_num = 1
    baby = None
    pk_url_kwarg = 'baby_pk'
    model = Baby

    def page_num_add(self):
        self.page_num += 1
        return ''

    def get_template_names(self):
        return 'bot/albums/landscape/{}.jinja2'.format(self.kwargs['album_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['baby'] = self.object
        ctx['view'] = self
        ctx['baby_history'] = self.baby_history(self.object)
        return ctx


class AlbumPrintSecret(AlbumPrint):
    """ Ссылка на альбом """
    hash_params = ['user_vk_id', 'baby_pk', 'album_pk']
    album_count = 3

    def get(self, request, *args, **kwargs):
        codes = hashids.Hashids().decode(self.kwargs.get('hashids'))
        if codes and len(codes) == len(self.hash_params):
            self.kwargs = dict(zip(self.hash_params, codes))
            return super().get(request, *args, **kwargs)
        return HttpResponseNotFound()

    @cached_property
    def user_vk(self):
        return UserVK.objects.filter(user_vk_id=self.kwargs['user_vk_id']).first()

    @cached_property
    def album_list(self):
        album_list = []
        for album_pk in range(1, self.album_count + 1):
            album = dict(
                name='Альбом #{}'.format(album_pk),
                link=self.user_vk.get_album_url(album_pk=album_pk),
                background_url='/static/img/albums/{}/bg.jpg'.format(album_pk),
            )
            album_list.append(album)
        return album_list

    @cached_property
    def baby(self):
        return Baby.objects.filter(pk=self.kwargs['baby_pk']).first()

    def get_object(self, queryset=None):
        return self.baby

#
# class AlbumPreview(BabyHistoryMix, TemplateView):
#     """ Показать превьюшку альбома """
#     hash_params = ['user_vk_id', 'baby_id', 'album_id']
#     hash_values = {}
#
#     def get(self, request, *args, **kwargs):
#         codes = hashids.Hashids().decode(self.kwargs.get('hashids'))
#         if codes and len(codes) == len(self.hash_params):
#             self.hash_values = dict(zip(self.hash_params, codes))
#             return super().get(request, *args, **kwargs)
#         return HttpResponseNotFound()
#
#     def get_template_names(self):
#         return 'bot/preview/preview{}_landscape.jinja2'.format(self.hash_values['album_id'])
#
#     @cached_property
#     def baby(self):
#         return Baby.objects.filter(pk=self.hash_values['baby_id']).first()
#
#     def message_qs(self, baby):
#         return sorted(BabyHistory.objects.select_related('baby').filter(baby=baby).order_by('-date_vk')[:5], key=lambda x: x.date_vk)
#
#     def photo_qs(self, baby):
#         return sorted(BabyHistoryAttachment.objects.select_related('history')
#                       .filter(history__baby=baby).order_by('-history__date_vk')[:100],
#                       key=lambda x: x.history.date_vk)
#
#     def measure_qs(self, model, baby):
#         return sorted(model.objects.filter(baby=baby).order_by('-date')[:1], key=lambda x: x.date)
#
#     def get_context_data(self, **kwargs):
#         ctx = super().get_context_data(**kwargs)
#         ctx['baby'] = self.baby
#         ctx['view'] = self
#         ctx['baby_history'] = self.baby_history(self.baby)
#         return ctx


class PastMonthsView(BaseLine):
    """ Показать список месяцев для заполнения прошлого """

    def chunks(self, object_list, count):
        result = []
        for i in range(0, len(object_list), count):
            result.append(object_list[i:i + count])
        return result

    @cached_property
    def keyboard_list(self):
        """ Cписок клавиатур с месяцами """
        today = datetime.date.today()
        baby_history = DateUtil().month_history(today, self.user_vk.baby.birth_date)
        buttons = []
        for btn in baby_history:
            label = '{}{}'.format('%sг. '  % btn['delta'].years if btn['delta'].years else '',
                                  '%sмес.' % btn['delta'].months if btn['delta'].months else '') or 'Первые дни'
            month = (btn['delta'].years * 12) + btn['delta'].months
            buttons.append(dict(
                action=dict(
                    type="text",
                    label=label,
                    payload=dict(action=reverse('past_month_add', args=[month]))
                ),
                color="secondary"
            ))

        keyboard_list = []
        for btn_12 in self.chunks(buttons, 12):
            keyboard_list.append(dict(one_time=True, buttons=self.chunks(btn_12, 4)))
        # Добавление нижней панели МЛАДШЕ | ОТМЕНА | СТАРШЕ
        for index, keyboard in enumerate(keyboard_list):
            bottom_buttons = []
            if index > 0:
                bottom_buttons.append(dict(
                    action=dict(
                        type="text",
                        label='Младше',
                        payload=dict(action=reverse('past_month_list', args=[index-1]))
                    ),
                    color="secondary"
                ))
            bottom_buttons.append(dict(
                action=dict(
                    type="text",
                    label='Отмена',
                    payload=dict(action=reverse('exit'))
                ),
                color="negative"
            ))
            if index + 1 < len(keyboard_list):
                bottom_buttons.append(dict(
                    action=dict(
                        type="text",
                        label='Старше',
                        payload=dict(action=reverse('past_month_list', args=[index+1]))
                    ),
                    color="secondary"
                ))
            keyboard['buttons'].append(bottom_buttons)

        return keyboard_list

    def bot_handler(self, request, *args, **kwargs):
        super().bot_handler(request, *args, **kwargs)
        keyboard_index = int(kwargs.get('keyboard', 0))
        keyboard = self.keyboard_list[keyboard_index]
        self.user_vk.wait_payload = dict(action=reverse('past_month_list', args=[0]))
        self.user_vk.save()
        self.request.vk_api.messages.send(
            user_id=self.user_vk.user_vk_id,
            message=u'Выберите месяц, в который вы хотите добавить фотки/описание/текст',
            random_id=random.randint(0, 10000000),
            keyboard=json.dumps(keyboard)
        )


class ExitView(BaseLine):
    """ выйти из режима заполнения "прошлого" """

    def bot_handler(self, request, *args, **kwargs):
        super().bot_handler(request, *args, **kwargs)
        self.user_vk.wait_payload = None
        self.user_vk.save()
        self.request.vk_api.messages.send(
            user_id=self.user_vk.user_vk_id,
            message=u'Готово.\n'
                    u'Можете дальше продолжать вести свой альбом в обычном режиме :)',
            random_id=random.randint(0, 10000000),
            keyboard=json.dumps(DEFAULT_KEYBOARD)
        )


class PastMonthsAddView(AddHistory):
    """ Активировать выбранный месяц, если не активирован и принять фото, текст """

    def get_month(self):
        """ Номер месяца, куда добавляем фото """
        month = self.kwargs.get('month')
        if month is not None:
            return int(month)

    def update_payload(self):
        self.keyboard = dict(
            one_time=True,
            buttons=[
                [
                    dict(
                        action=dict(
                            type="text",
                            label=u'Выйти из заполнения "прошлого" ',
                            payload=dict(action=reverse('exit'))
                        ),
                        color="secondary"
                    )
                ]
            ]
        )
        self.user_vk.wait_payload = dict(action=reverse('past_month_add', args=[self.get_month()]))
        self.user_vk.save()

    def get_response_msg(self):
        message = super().get_response_msg()
        return message + '\nА когда закончите наполнять месяц - нажмите кнопку "Выйти из заполнения прошлого".'

    def bot_handler(self, request, *args, **kwargs):
        if request.message.payload: # Если пришло сообщение, которое = нажатие на кнопку
            self.update_payload()
            self.request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                message=u'Окей! Вы выбрали месяц, который будете наполнять :)\n'
                        u'Сейчас присылайте фото/описание/текст.\n'
                        u'А когда закончите наполнять месяц - нажмите "Выйти из заполнения прошлого". ',
                random_id=random.randint(0, 10000000),
                keyboard=json.dumps(self.keyboard)
            )
        else:
            super().bot_handler(request, *args, **kwargs)


class VkApp(BabyHistoryMix, DetailView):
    """  Полная версия приложения для ВК """
    template_name = 'bot/albums/app/app.jinja2'
    page_num = 1
    model = Baby

    # def get(self, request, *args, **kwargs):
    #     if self.user_vk and self.user_vk.baby:
    #         return super().get(request, *args, **kwargs)
    #     return HttpResponseNotFound()

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        response['X-Frame-Options'] = 'allow-from: vk.com'
        return response

    @cached_property
    def user_vk(self):
        try:
            return UserVK.objects.get(user_vk_id=self.request.GET.get('vk_user_id'))
        except:
            return None

    def page_num_add(self):
        self.page_num += 1
        return ''

    def get_object(self, queryset=None):
        return self.user_vk and self.user_vk.baby

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['view'] = self
        ctx['user_vk'] = self.user_vk
        ctx['baby'] = self.object
        if self.user_vk and self.object:
            ctx['baby_history'] = self.baby_history(self.object)
        return ctx

    # https://vk.com/dev/vk_apps_docs3?f=6.%20%D0%9F%D0%B0%D1%80%D0%B0%D0%BC%D0%B5%D1%82%D1%80%D1%8B%20%D0%B7%D0%B0%D0%BF%D1%83%D1%81%D0%BA%D0%B0
    # https://baby-bot.na4u.ru/?
    # vk_access_token_settings=notify&
    # vk_app_id=7162935&
    # vk_are_notifications_enabled=0&
    # vk_is_app_user=1&
    # vk_language=ru&
    # vk_platform=desktop_web&
    # vk_ref=other&
    # vk_user_id=198163426&
    # sign=jFHTnOwRr220ScU77mem1NpwczhPOIm0bCt2uefNMLs