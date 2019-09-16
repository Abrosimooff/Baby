from django.core.management.base import BaseCommand, CommandError
from bot.base import Sender

class Command(BaseCommand):
    help = 'start vk sender'

    def handle(self, *args, **options):
        print('vk sender saturday started')
        # Запускать команду каждую субботу в 19.00
        Sender().saturday_process()