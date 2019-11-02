from django.template.backends.jinja2 import Jinja2
from django.template import defaultfilters
from django.urls import reverse

class CustomJinja2(Jinja2):

    def __init__(self, params):
        # params = params.copy()
        # options = params.pop('OPTIONS').copy()
        # options = options.pop('filters')
        super().__init__(params)
        self.env.filters['date'] = defaultfilters.date
        self.env.filters['linebreaks'] = defaultfilters.linebreaks
        self.env.filters['linebreaksbr'] = defaultfilters.linebreaksbr

        self.env.globals.update({
            # 'static': staticfiles_storage.url,
            'url': reverse,
        })