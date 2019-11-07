from django.core.management.base import BaseCommand
from bot.models import Baby
from bot.views import BabyHistoryMix


class Command(BaseCommand):
    help = 'Рассылка 1 раз всем кто сейчас ведёт альбом'

    def handle(self, *args, **options):
        count_page = 0
        for baby in Baby.objects.all():
            history = BabyHistoryMix().baby_history(baby)
            history = filter(lambda x: x['page_list'], history)
            for h in history:
                count_page += len(h['page_list']) + 1  # одна страница названия месяца
        print('count page:', count_page)  # не считая обложку


