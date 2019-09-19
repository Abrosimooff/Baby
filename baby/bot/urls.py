from django.conf.urls import url

from bot.base import VkCallback
from bot.views import StartLine, Welcome, AddHistory, AlbumView, EditHistory, HeightView, WeightView, SharingView, \
    HelpView, SharingGetView, AlbumPrint

urlpatterns = [
    url(r'^welcome', Welcome.as_view()),
    url(r'^settings/(?P<question_pk>.+)/', StartLine.as_view()),
    url(r'^add_history', AddHistory.as_view()),
    url(r'^edit_history', EditHistory.as_view()),
    url(r'^album$', AlbumView.as_view()),
    url(r'^height/(?P<question_pk>.+)/', HeightView.as_view()),
    url(r'^weight/(?P<question_pk>.+)/', WeightView.as_view()),
    url(r'^sharing/$', SharingView.as_view()),
    url(r'^sharing/get/$', SharingGetView.as_view()),
    url(r'^help/', HelpView.as_view()),

    url(r'^vk/callback/', VkCallback.as_view()),

    url(r'^album/print/(?P<album_pk>.+)/$', AlbumPrint.as_view())
]