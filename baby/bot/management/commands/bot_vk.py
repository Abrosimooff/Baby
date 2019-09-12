from django.core.management.base import BaseCommand, CommandError
from bot.utils import VkHelp

class Command(BaseCommand):
    help = 'start bot vk'

    def handle(self, *args, **options):
        print('vk process started')
        VkHelp().process()