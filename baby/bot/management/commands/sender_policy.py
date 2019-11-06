import datetime
import json
import random

from django.core.management.base import BaseCommand, CommandError
from bot.base import Sender, VkHelp
from bot.base_utils.keyboards import DEFAULT_KEYBOARD
from bot.models import UserVK


class Command(BaseCommand):
    help = 'Рассылка 1 раз всем кто сейчас ведёт альбом'

    def handle(self, *args, **options):
        message = 'Здравствуйте. &#128522; \n' \
                  'Мы очень рады, что Вы создаёте альбом с помощью нашего бота.\n' \
                  'Наш проект развивается, к нам присоединяется всё больше родителей &#127881;\n' \
                  'Данные, которые вы отправляете боту, используются только для создания ваших альбомчиков.\n' \
                  'По закону РФ рассказываю, что прочитать о политике обработке персональных данных ' \
                  'можно здесь: https://vk.com/dev/uprivacy и, продолжая работу с нашим чат-ботом, ' \
                  'Вы соглашаетесь с политикой обработки персональных данных.\n\n' \
                  'Можете дальше продолжать вести свой альбом в обычном режиме &#128522;'

        for user_vk in UserVK.objects.all():
            user_vk.wait_payload = None
            user_vk.save()
            VkHelp().vk_api.messages.send(
                user_id=user_vk.user_vk_id,
                message=message,
                random_id=random.randint(0, 10000000),
                keyboard=json.dumps(DEFAULT_KEYBOARD)
            )
