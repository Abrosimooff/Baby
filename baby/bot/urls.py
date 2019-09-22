from django.conf.urls import url
from django.urls import path

from bot.base import VkCallback
from bot.views import SettingsLine, Welcome, AddHistory, AlbumView, EditHistory, HeightView, WeightView, SharingView, \
    HelpView, SharingGetView, AlbumPrint, PastMonthsView, PastMonthsAddView, ExitView

urlpatterns = [
    url(r'^welcome', Welcome.as_view()),
    url(r'^settings/(?P<question_pk>.+)/', SettingsLine.as_view()),
    url(r'^add_history', AddHistory.as_view()),
    url(r'^edit_history', EditHistory.as_view()),
    url(r'^album$', AlbumView.as_view()),
    url(r'^height/(?P<question_pk>.+)/', HeightView.as_view()),
    url(r'^weight/(?P<question_pk>.+)/', WeightView.as_view()),
    url(r'^sharing/$', SharingView.as_view()),
    url(r'^sharing/get/$', SharingGetView.as_view()),
    url(r'^help/', HelpView.as_view()),
    path('past/months/<int:keyboard>/', PastMonthsView.as_view(), name='past_month_list'),
    path('past/months/add/<int:month>/', PastMonthsAddView.as_view(), name='past_month_add'),

    path('exit', ExitView.as_view(), name='exit'),  # Выход в режим обычного заполнения

    url(r'^vk/callback/', VkCallback.as_view()),

    url(r'^album/print/(?P<album_pk>.+)/(?P<baby_pk>.+)/$', AlbumPrint.as_view())
]