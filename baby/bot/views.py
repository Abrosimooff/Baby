import json

from django.shortcuts import render

# Create your views here.
from django.urls import resolve


class BaseLine(object):

    def process_payload(self, data):
        payload = json.loads(data.payload)
        action = payload['action']

        match = resolve(action, urlconf='bot.urls')

        if match:
            view = match.view
            args = match.args
            kwargs = match.kwargs
            return view(*args, **kwargs)

    def answer_question(self, pk):
        print('answer_question', pk)
