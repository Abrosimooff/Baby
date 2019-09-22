import datetime
import json
import random
from collections import defaultdict

import hashids
import pytz
from django.urls import resolve, reverse
from django.utils.functional import cached_property
from django.views.generic import TemplateView

from bot.base import BaseLine, DEFAULT_KEYBOARD
from bot.helpers import DateUtil
from bot.models import UserVK, Baby, BabyUserVK, BabyHistory, BabyHistoryAttachment, AttachType, BabyHeight, BabyWeight
from bot.utils.album import AlbumPager
from bot.validators import ValidateGenderList, FirstNameValidate, ValidateYearList, ValidateMonthList, \
    ValidateBirthDate, HeightValidate, WeightValidate


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
            message=u'А это пока рано..',
            random_id=random.randint(0, 10000000),
            keyboard=json.dumps(DEFAULT_KEYBOARD)
        )


class MeasureView(BaseLine):
    model = None
    field_name = ''
    validator_class = None

    def get_message(self):
        return ''

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
                # keyboard=json.dumps(DEFAULT_KEYBOARD)
            )

        # Разбироаем ответ
        elif question_pk == '1':
            answer = self.request.message.text
            validator_obj = self.validator_class(answer)
            if validator_obj.is_valid():
                measure = self.model.objects.filter(baby=self.user_vk.baby, date=datetime.date.today()).first()
                if measure:
                    setattr(measure, self.field_name, validator_obj.value)
                    measure.save()
                else:
                    measure = self.model.objects.create(
                        baby=self.user_vk.baby, date=datetime.date.today(), **{self.field_name: validator_obj.value})

                # Отвечаем, что приняли показания
                self.user_vk.wait_payload = None
                self.user_vk.save()
                self.request.vk_api.messages.send(
                    user_id=self.user_vk.user_vk_id,
                    message='Готово. Спасибо, что передали показания!)\n'
                            'Можете продолжать вести альбом :)',
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
                    # keyboard=json.dumps(DEFAULT_KEYBOARD)
                )


class HeightView(MeasureView):
    """ Заполнить рост """
    model = BabyHeight
    field_name = 'height'
    validator_class = HeightValidate

    def get_message(self):
        gstr = 'доросла' if self.user_vk.baby.is_women else 'дорос'
        return 'Напишите до скольки сантиметров уже {} {}?'.format(gstr, self.user_vk.baby.first_name.capitalize())


class WeightView(MeasureView):
    """ Заполнить вес """
    model = BabyWeight
    field_name = 'weight'
    validator_class = WeightValidate

    def get_message(self):
        return 'Напишите cколько граммов уже весит {}?'.format(self.user_vk.baby.first_name.capitalize())


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
                    color="secondary"
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
        if not self.user_vk.wait_payload:
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
        self.message_date = datetime.datetime.fromtimestamp(message_dict['date'])
        self.message_id = request.message.id
        self.message_text = request.message.text
        self.photo_list = request.message.photo_list
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

            is_first_start = self.user_vk.baby is None # Первый старт - если ребёнок ещё не создан
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
                welcome_text = '\n\nДалее - просто присылайте фотографии, ' \
                       'пишите сообщения, рассказывайте о новых эмоциях, реакциях, умениях, интересах ребёнка.\n' \
                       'В общем, описывайте всё, что хотите увидеть в будущем альбоме вашего ребёнка :)\n' \
                       'Это будет ваш мини-блог для наполнения альбома.\n' \
                       'А я не буду назойливым, и лишь иногда буду напоминать, если вы давно ничем не делились :)'

                # Если ребёнку сейчас 2 мес. или больше - предлагаем заполнить прошлое
                if delta.years or (delta.months > 1):
                    welcome_text += '\n\nP.S. Чтобы заполнить альбом за более ранние месяца, чем {} - ' \
                               'нажмите "Добавить в прошлое" '.format(delta_str)
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
            Baby.objects.filter(pk=self.user_vk.baby.pk).update(**params)
        else:
            baby = Baby.objects.create(**params)
            b2u = BabyUserVK.objects.create(user_vk=self.user_vk, baby=baby)


class AlbumPrint(TemplateView):
    """ Формируем альбом """
    page_num = 1

    def page_num_add(self):
        self.page_num += 1
        return ''

    def get_template_names(self):
        return 'bot/album{}_landscape.jinja2'.format(self.kwargs['album_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        baby_id = kwargs['baby_pk']
        baby = Baby.objects.filter(pk=baby_id).first()

        messages = BabyHistory.objects.select_related().prefetch_related('babyhistoryattachment_set').filter(baby=baby)
        photo_dict = defaultdict(list)
        for photo in BabyHistoryAttachment.objects.select_related().filter(history__baby=baby):
            photo_dict[photo.history_id].append(photo.url)

        today = datetime.date.today()
        baby_history = DateUtil().month_history(today, baby.birth_date)
        utc = pytz.UTC
        for period in baby_history:
            period_messages = []
            for m in messages:
                # сообщения, добавленные в прошлое (по месяцам)
                if m.month is not None and m.month == period['month']:
                    period_messages.append(m)
                # сообщения, добавленные нормально
                if m.month is None and utc.localize(period['start']) <= m.date_vk < utc.localize(period['end']):
                    period_messages.append(m)
            pager = AlbumPager()
            for history in period_messages:  # Ходим по всем истриям и фото и добавляем в пейджер
                pager.add(history, photo_dict[history.id])
            period['page_list'] = pager.page_list

        ctx['baby'] = baby
        ctx['view'] = self
        ctx['baby_history'] = baby_history
        return ctx


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
                    payload=dict(action=reverse('past_exit'))
                ),
                color="secondary"
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


class PastMonthsExitView(BaseLine):
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
                            payload=dict(action=reverse('past_exit'))
                        ),
                        color="secondary"
                    )
                ]
            ]
        )
        # self.user_vk.wait_payload = dict(action='/past/months/add/{}/'.format(self.get_month()))
        self.user_vk.wait_payload = dict(action=reverse('past_month_add', args=[self.get_month()]))
        self.user_vk.save()

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

