import datetime
from collections import defaultdict

import hashids
import pytz
from django.contrib import auth
from django.http import HttpResponseNotFound, HttpResponseRedirect, JsonResponse
from django.urls import reverse

from django.utils.functional import cached_property
from django.views.generic import TemplateView, DetailView, UpdateView

from bot.base import VK_APP_ID
from bot.helpers import DateUtil
from bot.models import UserVK, Baby, BabyHistory, BabyHistoryAttachment, BabyHeight, BabyWeight, ALBUM_IDS
from web.utils.album import AlbumPager


def logout(request):
    """ Выйти из профиля """
    auth.logout(request)
    return HttpResponseRedirect(reverse('index'))


class IndexView(TemplateView):
    """  Главная страница сайта """
    template_name = 'web/index.jinja2'

    @cached_property
    def user(self):
        return self.request.user

    @cached_property
    def user_vk(self):
        if not self.user.is_anonymous:
            return UserVK.objects.filter(user=self.user).first()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['view'] = self
        ctx['VK_APP_ID'] = VK_APP_ID
        return ctx


class VkAuth(IndexView):
    """ Авторизация через ВК """
    def auth_user(self, user):
        from django.contrib.auth import login as auth_login, get_backends
        for backend in get_backends():
            user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
        auth_login(self.request, user)

    def get(self, request, *args, **kwargs):
        if self.request.GET.get('hash') and self.request.GET.get('uid'):
            user_vk_id = int(self.request.GET.get('uid'))
            user_vk = UserVK.objects.filter(user_vk_id=user_vk_id).first()
            if user_vk and user_vk.user:
                self.auth_user(user_vk.user)
                return HttpResponseRedirect(user_vk.album_url)
        return HttpResponseRedirect(reverse('index')+'?fail')


class BabyHistoryMix(object):

    def message_qs(self, baby):
        return BabyHistory.objects.select_related('baby').filter(baby=baby)

    def photo_qs(self, baby):
        return BabyHistoryAttachment.objects.select_related('history').filter(history__baby=baby)

    def measure_qs(self, model, baby):
        return model.objects.filter(baby=baby).order_by('date')

    def measure_chart(self, model, measure_attr, baby):
        """ График роста """
        measure_list = self.measure_qs(model, baby)
        min_height_mm = 20
        max_height_mm = 120
        delta_height_mm = max_height_mm - min_height_mm
        if measure_list:
            for num, item in enumerate(measure_list, 0):
                item.step = getattr(item, measure_attr) - getattr(measure_list[num-1], measure_attr) if num else 0

            # цена деления = 100мм / сумму всех шагов
            one_step = delta_height_mm / sum([x.step for x in measure_list])
            current_mm = min_height_mm
            for item in measure_list:
                current_mm += item.step * one_step
                item.mm = current_mm
        return measure_list

    def baby_history(self, baby):
        """ Вся история малыша """
        messages = self.message_qs(baby)
        photo_dict = defaultdict(list)
        for photo in self.photo_qs(baby):
            photo_dict[photo.history_id].append(photo)

        # Измерения

        measure_dict = defaultdict(list)
        for object in self.measure_qs(BabyHeight, baby):
            measure_dict[object.date].append(object)
        for object in self.measure_qs(BabyWeight, baby):
            measure_dict[object.date].append(object)

        today = datetime.date.today()
        baby_history = DateUtil().month_history(today, baby.birth_date)
        utc = pytz.UTC
        for period in baby_history:
            period_messages = []
            measure_dates_in_period = []
            for m in messages:
                # сообщения, добавленные в прошлое (по месяцам)
                if m.month is not None and m.month == period['month']:
                    period_messages.append(m)
                # сообщения, добавленные нормально
                if m.month is None and utc.localize(period['start']) <= m.date_vk < utc.localize(period['end']):
                    period_messages.append(m)
                for date in measure_dict.keys():
                    if period['start'].date() <= date < period['end'].date():
                        measure_dates_in_period.append(date)
            pager = AlbumPager()
            for history in period_messages:  # Ходим по всем истриям и фото и добавляем в пейджер
                for date in sorted(measure_dates_in_period):
                    if date <= history.date_vk.date():
                        if measure_dict.get(date):
                            pager.add_measure(measure_dict.pop(date))  # Добавляем в альбом и удаляем из словаря
                pager.add(history, photo_dict[history.id])

            # оставшиеся измерения  (если есть) вставляем в конец
            for date in sorted(measure_dates_in_period):
                if measure_dict.get(date):
                    pager.add_measure(measure_dict.pop(date))
            period['page_list'] = pager.page_list
        return baby_history


class AlbumPrint(BabyHistoryMix, DetailView):
    """ Формируем альбом """
    page_num = 1
    baby = None
    pk_url_kwarg = 'baby_pk'
    model = Baby

    def page_num_add(self):
        self.page_num += 1
        return ''

    def get_template_names(self):
        return 'web/albums/landscape/{}.jinja2'.format(self.kwargs['album_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['baby'] = self.object
        ctx['view'] = self
        ctx['baby_history'] = self.baby_history(self.object)
        ctx['VK_APP_ID'] = VK_APP_ID
        # ctx['height_chart'] = self.measure_chart(BabyHeight, 'height', self.object)
        # ctx['weight_chart'] = self.measure_chart(BabyWeight, 'weight', self.object)
        return ctx


class AlbumPrintSecret(AlbumPrint):
    """ Ссылка на альбом """
    hash_params = ['user_vk_id', 'baby_pk']
    hash_params_old = ['user_vk_id', 'baby_pk', 'album_pk']

    def get(self, request, *args, **kwargs):
        codes = hashids.Hashids().decode(self.kwargs.get('hashids'))
        if codes and len(codes) == len(self.hash_params):
            self.kwargs = dict(zip(self.hash_params, codes))
            return super().get(request, *args, **kwargs)
        # для поддержки ссылок по-старому
        if codes and len(codes) == len(self.hash_params_old):
            self.kwargs = dict(zip(self.hash_params_old, codes))
            return super().get(request, *args, **kwargs)
        return HttpResponseNotFound()

    def get_template_names(self):
        return 'web/albums/landscape/{}.jinja2'.format(self.album_pk)

    @cached_property
    def user(self):
        return self.request.user

    @cached_property
    def is_my_album(self):
        """ Принадлежит ли альбом человеку, котоырй тут авторизован """
        return self.user_vk and self.user_vk.user == self.user

    @cached_property
    def user_vk(self):
        return UserVK.objects.filter(user_vk_id=self.kwargs['user_vk_id']).first()

    @cached_property
    def album_list(self):
        album_list = []
        for album_pk in ALBUM_IDS:
            album = dict(
                pk=album_pk,
                name='Альбом #{}'.format(album_pk),
                background_url='/static/img/albums/{}/bg.jpg'.format(album_pk),
            )
            album_list.append(album)
        return album_list

    @cached_property
    def baby(self):
        return Baby.objects.filter(pk=self.kwargs['baby_pk']).first()

    def get_object(self, queryset=None):
        return self.baby

    @cached_property
    def album_pk(self):
        try:
            album_pk = int(self.request.GET.get('album'))
        except:
            album_pk = self.user_vk.album_pk

        if album_pk not in ALBUM_IDS:
            album_pk = 1
        return album_pk

    def get_context_data(self, **kwargs):
        # Сохраняем ID альбома, на который пользователь перешёл
        if self.album_pk != self.user_vk.album_pk:
            self.user_vk.album_pk = self.album_pk
            self.user_vk.save()
        return super().get_context_data(**kwargs)


class AlbumPhotoEdit(UpdateView):
    pk_url_kwarg = 'photo_id'

    def get_queryset(self):
        if self.request.user.is_staff:
            return BabyHistoryAttachment.objects.all()
        user_vk = UserVK.objects.filter(user=self.request.user).first()
        if user_vk:
            return BabyHistoryAttachment.objects.filter(history__baby=user_vk.baby)
        return BabyHistoryAttachment.objects.none()

    @cached_property
    def background_position(self):
        return self.request.POST.get('background_position', 'center center')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.background_position = self.background_position
        self.object.save()
        return JsonResponse(dict(success=True))


class VkApp(BabyHistoryMix, DetailView):
    """  Полная версия приложения для ВК """
    template_name = 'web/albums/app/app.jinja2'
    page_num = 1
    model = Baby

    # def get(self, request, *args, **kwargs):
    #     if self.user_vk and self.user_vk.baby:
    #         return super().get(request, *args, **kwargs)
    #     return HttpResponseNotFound()

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        response['X-Frame-Options'] = 'allow-from: vk.com'
        return response

    @cached_property
    def user_vk(self):
        try:
            return UserVK.objects.get(user_vk_id=self.request.GET.get('vk_user_id'))
        except:
            return None

    def page_num_add(self):
        self.page_num += 1
        return ''

    def get_object(self, queryset=None):
        return self.user_vk and self.user_vk.baby

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['view'] = self
        ctx['user_vk'] = self.user_vk
        ctx['baby'] = self.object
        if self.user_vk and self.object:
            ctx['baby_history'] = self.baby_history(self.object)
        return ctx

    # https://vk.com/dev/vk_apps_docs3?f=6.%20%D0%9F%D0%B0%D1%80%D0%B0%D0%BC%D0%B5%D1%82%D1%80%D1%8B%20%D0%B7%D0%B0%D0%BF%D1%83%D1%81%D0%BA%D0%B0
    # https://baby-bot.na4u.ru/?
    # vk_access_token_settings=notify&
    # vk_app_id=7162935&
    # vk_are_notifications_enabled=0&
    # vk_is_app_user=1&
    # vk_language=ru&
    # vk_platform=desktop_web&
    # vk_ref=other&
    # vk_user_id=198163426&
    # sign=jFHTnOwRr220ScU77mem1NpwczhPOIm0bCt2uefNMLs
