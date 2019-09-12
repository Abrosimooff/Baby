from django.conf.urls import url

from bot.views import BaseLine, AnswerQuestionLine, StartLine, Welcome

urlpatterns = [
    # url(r'^answer_question/(?P<question_pk>.+)/', BaseLine.answer_question)
    url(r'^answer_question/(?P<question_pk>.+)/', AnswerQuestionLine.as_view()),

    url(r'^welcome', Welcome.as_view()),
    url(r'^settings/(?P<question_pk>.+)/', StartLine.as_view())

]