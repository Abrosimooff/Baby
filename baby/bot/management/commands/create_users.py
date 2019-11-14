from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from bot.models import UserVK


class Command(BaseCommand):

    def handle(self, *args, **options):
        for user_vk in UserVK.objects.filter(user=None):
            dj_user = User.objects.create_user(str(user_vk.user_vk_id))  # username = vk id, без пароля
            dj_user.first_name = user_vk.first_name
            dj_user.last_name = user_vk.last_name
            dj_user.save()
            user_vk.user = dj_user
            user_vk.save()
            print(user_vk.user_vk_id, 'ok')
        print('finish.')