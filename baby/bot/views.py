import json
from functools import update_wrapper

from django.shortcuts import render

# Create your views here.
from django.urls import resolve
from django.utils.decorators import classonlymethod
from django.views import View


class BaseLine(View):
    """ Базовый класс для обработчиков """
    @classonlymethod
    def as_view(cls, **initkwargs):
        """Main entry point for a request-response process."""
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError("You tried to pass in the %s method name as a "
                                "keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError("%s() received an invalid keyword %r. as_view "
                                "only accepts arguments that are already "
                                "attributes of the class." % (cls.__name__, key))

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get
            self.setup(request, *args, **kwargs)
            if not hasattr(self, 'request'):
                raise AttributeError(
                    "%s instance has no 'request' attribute. Did you override "
                    "setup() and forget to call super()?" % cls.__name__
                )
            return self.dispatch(request, *args, **kwargs)

        view.view_class = cls
        view.view_initkwargs = initkwargs

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())
        return view

    def dispatch(self, request, *args, **kwargs):
        return self.bot_handler(request, *args, **kwargs)

    def bot_handler(self, request, *args, **kwargs):
        pass

    def process_payload(self, data):
        payload = json.loads(data.payload)
        action = payload['action']
        print(action)
        match = resolve(action, urlconf='bot.urls')

        if match:
            func = match.func
            args = match.args
            kwargs = match.kwargs
            request = {}
            return func(request, *args, **kwargs)


class AnswerQuestionLine(BaseLine):
    """ Ответ на вопрос """
    def bot_handler(self, request, *args, **kwargs):
        print('AnswerQuestionLine', request, args, kwargs)
        super().bot_handler(request, *args, **kwargs)