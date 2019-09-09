from django.conf.urls import url

from bot.views import BaseLine

url_patterns = [
    url(r'^answer_question/(?P<question_pk>).+/', BaseLine.answer_question)
]