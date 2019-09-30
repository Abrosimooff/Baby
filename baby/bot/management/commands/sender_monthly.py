import datetime

from django.core.management.base import BaseCommand, CommandError
from bot.base import Sender


class Command(BaseCommand):
    help = 'start vk sender'

    def add_arguments(self, parser):
        parser.add_argument('-d', '--date', action='store', help='На какую дату осуществить рассылку, YYYY-MM-DD')

    @staticmethod
    def date(date_str):
        try:
            return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            return None

    def handle(self, *args, **options):
        # Запускать команду каждый день в 19.00
        print('vk sender monthly started')
        date = self.date(options['date'])
        Sender(on_date=date).month_process()