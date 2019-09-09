from django.conf.urls import url

from bot.views import BaseLine, AnswerQuestionLine

urlpatterns = [
    # url(r'^answer_question/(?P<question_pk>.+)/', BaseLine.answer_question)
    url(r'^answer_question/(?P<question_pk>.+)/', AnswerQuestionLine.as_view())
]