from django.conf.urls import url

from bot.views import StartLine, Welcome, AddHistory, AlbumView, EditHistory

urlpatterns = [
    url(r'^welcome', Welcome.as_view()),
    url(r'^settings/(?P<question_pk>.+)/', StartLine.as_view()),
    url(r'^add_history', AddHistory.as_view()),
    url(r'^edit_history', EditHistory.as_view()),
    url(r'^album', AlbumView.as_view())
]