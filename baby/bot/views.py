import datetime
import json
import random
from django.urls import resolve

from bot.base import BaseLine, DEFAULT_KEYBOARD
from bot.models import UserVK, Baby, BabyUserVK, BabyHistory, BabyHistoryAttachment, AttachType, BabyHeight, BabyWeight
from bot.validators import ValidateGenderList, FirstNameValidate, ValidateYearList, ValidateMonthList, \
    ValidateBirthDate, HeightValidate, WeightValidate


class Welcome(BaseLine):
    """ Первое приветственное сообщение и перенаправление на настройки """

    def bot_handler(self, request, *args, **kwargs):
        super().bot_handler(request, *args, **kwargs)
        if not self.user_vk:
            # Отправляем первое сообщение
            self.user_vk = UserVK.objects.create(user_vk_id=request.message.user_id)
            request.vk_api.messages.send(
                user_id=self.user_vk.user_vk_id,
                message='Привет. Начнём создавать альбом для твоего ребёнка :)\n'
                        'Для начала немного расскажи о своём малыше.',
                random_id=random.randint(0, 10000000)
            )
            # Перенаправляем на настройки
            match = resolve('/settings/-1/', urlconf='bot.urls')
            match.func(request, *match.args, **match.kwargs)


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

    # def error_response(self, question_pk, error_message=u'Ошибка!'):
    #     current_question = self.question_list[question_pk]
    #     user_payload = self.user_vk.wait_payload_dict
    #     user_payload['action'] = '/settings/1/'.format(question_pk)
    #     self.user_vk.wait_payload = user_payload
    #     self.user_vk.save()
    #     self.request.vk_api.messages.send(
    #         user_id=self.user_vk.user_vk_id,
    #         message=u'{}\n{}'.format(error_message, current_question['message']),
    #         random_id=random.randint(0, 10000000),
    #         keyboard=json.dumps(current_question.get('keyboard', {}))
    #     )


    def bot_handler(self, request, *args, **kwargs):
        question_pk = kwargs.get('question_pk')

        # Пишем, что мол напишите цифру
        if question_pk == '0':
            self.user_vk.wait_payload = dict(action='{}/1/'.format(self.field_name))
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
                    self.model.objects.create(
                        baby=self.user_vk.baby,
                        date=datetime.date.today(), **{self.field_name: validator_obj.value})

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
                self.user_vk.wait_payload = dict(action='{}/1/'.format(self.field_name))
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


class AddHistory(BaseLine):
    """ Добавление сообщения в историю ребёнка """
    history_action = 'add'

    def bot_handler(self, request, *args, **kwargs):

        # в messages_dict есть:
        # 'date', 'from_id', 'id', 'out', 'peer_id', 'text', 'conversation_message_id', 'fwd_messages',
        # 'important', 'random_id', 'attachments', 'is_hidden']

        message_dict = request.message.message['items'][0]
        message_date = datetime.datetime.fromtimestamp(message_dict['date'])
        message_id = request.message.id
        message_text = request.message.all_text
        photo_list = request.message.photo_list
        other_attach_exist = request.message.other_attach_exists

        # Если изменение сообщения, то удаляем сообщение и записываем новое
        if self.history_action == 'edit':
            delete_history = BabyHistory.objects.filter(message_vk_id=message_id).first()
            if delete_history:
                BabyHistoryAttachment.objects.filter(history=delete_history).delete()
                delete_history.delete()

        if message_text or photo_list:
            # записываем в историю ребёнка
            history = BabyHistory.objects.create(
                baby=self.user_vk.baby,
                text=message_text,
                user_vk=self.user_vk,
                message_vk_id=message_id,
                date_vk=message_date,
                other_attach_vk=other_attach_exist
            )
            # записываем вложения
            if photo_list:
                BabyHistoryAttachment.objects.bulk_create([BabyHistoryAttachment(
                    history=history,
                    attachment_type=AttachType.PHOTO,
                    url=url)
                for url in photo_list])

        if self.history_action == 'edit':
            response_msg = 'Вы изменили сообщение - мы применили эти изменения в альбоме :)'
        else:
            msg = ''
            if photo_list:
                msg = u'Ок. Получил ваши фото ({}шт){}.'.format(len(photo_list), ' и описание' if message_text else '')
            elif message_text:
                msg = u'Ок. Информацию принял.'

            if other_attach_exist:
                msg += '\nИз вложений мы принимаем только фото!'
            response_msg = '{}\nЕсли есть что ещё - пиши :)'.format(msg)

        self.request.vk_api.messages.send(
            user_id=self.user_vk.user_vk_id,
            message=response_msg,
            random_id=random.randint(0, 10000000),
            keyboard=json.dumps(DEFAULT_KEYBOARD)
        )
        super().bot_handler(request, *args, **kwargs)


class EditHistory(AddHistory):
    """ Изменить сообщение """
    history_action = 'edit'


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
                if self.user_vk.baby.is_women:
                    message += 'У вас малышка {} и ей сейчас {}.\n\n'.format(self.user_vk.baby.first_name,
                                                                        self.user_vk.baby.get_birth_date_delta_string())
                else:
                    message += 'У вас малыш {} и ему сейчас {}.\n\n'.format(self.user_vk.baby.first_name,
                                                                        self.user_vk.baby.get_birth_date_delta_string())
                welcome_text = 'Далее - просто присылайте фотографии, ' \
                       'пишите сообщения, рассказывайте о новых эмоциях, реакциях, умениях, интересах ребёнка.\n' \
                       'В общем, описывайте всё, что хотите увидеть в будущем альбоме вашего ребёнка :)\n' \
                       'Это будет ваш мини-блог для наполнения альбома.\n' \
                       'А я не буду назойливым, и лишь иногда буду напоминать, если вы давно ничем не делились :)'

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
