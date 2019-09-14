from django.core.management.base import BaseCommand, CommandError
from bot.utils import Sender

class Command(BaseCommand):
    help = 'start vk sender'

    def handle(self, *args, **options):
        print('vk sender monthly started')
        # Запускать команду каждый день в 19.00
        Sender().month_process()