from django.core.management.base import BaseCommand, CommandError
from bot.base import VkHelp


class Command(BaseCommand):
    help = 'start bot vk'

    def handle(self, *args, **options):
        VkHelp(is_longpoll=True).process_longpoll()