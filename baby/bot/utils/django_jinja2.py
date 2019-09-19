# -*- coding:utf-8 -*-
from __future__ import absolute_import

import datetime
import json
import time

import six
# from bootstrap3.forms import render_form, render_formset, render_field
# from compressor.contrib.jinja2ext import CompressorExtension
from django.conf import settings
from django.template.response import TemplateResponse
from django.urls import NoReverseMatch, reverse
from django.db.models.query import QuerySet
from django.template import defaultfilters
from django.templatetags.static import static
from django.utils.translation import ugettext_lazy
from jinja2 import Environment, Markup, PackageLoader, ChoiceLoader
from jinja2.exceptions import TemplateNotFound


def _(text):
    return ugettext_lazy(str(text))


def url(*args, **kwargs):
    try:
        path = reverse(*args, **kwargs)
    except NoReverseMatch:
        path = "#"
    return path


# def bootstrap_form(*args, **kwargs):
#     return Markup(render_form(*args, **kwargs))


# def bootstrap_formset(*args, **kwargs):
#     return Markup(render_formset(*args, **kwargs))


# def bootstrap_field(*args, **kwargs):
#     return Markup(render_field(*args, **kwargs))


# def format_number(number, digits=1, decimal_delimiter=",", thousands_separator=" "):
#     from vist_core.utils.report_utils import SRound
#     rnd = SRound(digits=digits, decimal_delimiter=decimal_delimiter, thousands_separator=thousands_separator)
#     return rnd.value(number)


def do_safe_json(value):
    try:
        return Markup(json.dumps(value))
    except TypeError as e:
        if isinstance(value, QuerySet):
            return Markup(json.dumps(list(value)))
        raise


class ExtensionLoader(PackageLoader):
    def __init__(self, *args, **kwargs):
        self.extensions = kwargs.pop("extensions", [])
        self.excludes = kwargs.pop("exclude", [])
        if self.extensions and self.excludes:
            raise EnvironmentError("Extensions or exclude, not together")
        super(ExtensionLoader, self).__init__(*args, **kwargs)

    def get_source(self, environment, template):
        extension = template.rsplit(".", 1)[-1]
        if not extension:
            raise TemplateNotFound(template)
        if self.extensions and extension not in self.extensions:
            raise TemplateNotFound(template)
        if self.excludes and extension in self.excludes:
            raise TemplateNotFound(template)
        return super(ExtensionLoader, self).get_source(environment, template)


def environment(**options):
    loaders = []

    for app in getattr(settings, 'INSTALLED_APPS', []):
        loaders.append(ExtensionLoader(app, exclude=["html"]))

    env_kwargs = {
        'extensions': ['jinja2.ext.loopcontrols', 'jinja2.ext.with_'], # , CompressorExtension
        'line_comment_prefix': '# ',
        'loader': ChoiceLoader(loaders),
        'trim_blocks': True,
        'autoescape': True,
        'auto_reload': True,
        'cache_size': 1024
    }
    env_kwargs.update(getattr(settings, 'JINJA_ENVIRONMENT', {}))
    env = Environment(**env_kwargs)
    env.globals = {
        'url': url,
        'range': six.moves.range,
        'static': static,
        "_": _,
        "enumerate": enumerate,
        "utc_now": datetime.datetime.utcnow(),
        "timestamp": time.mktime(datetime.datetime.utcnow().timetuple())
    }

    env.globals.update(dict(
        all=all,
        unicode=str,
        isinstance=isinstance,
        format=format,
        sorted=sorted,
        min=min,
        max=max,
        zip=zip,
        pow=pow,
        divmod=divmod,
        map=map,
        str=str,
    ))

    env.globals.update(getattr(settings, 'JINJA_GLOBALS', {}))

    for f in ('capfirst', 'linebreaks', 'linebreaksbr', 'linenumbers',
              'pluralize', 'removetags', 'slugify', 'striptags',
              'timesince', 'timeuntil', 'title', 'truncatewords',
              'truncatewords_html', 'unordered_list', 'urlize',
              'urlizetrunc', 'yesno'):
        env.filters[f] = getattr(defaultfilters, f)
    env.filters['format_date'] = defaultfilters.date
    # env.filters['bootstrap_form'] = bootstrap_form
    # env.filters['bootstrap_formset'] = bootstrap_formset
    # env.filters['bootstrap_field'] = bootstrap_field
    env.filters['safejson'] = do_safe_json
    # env.filters['format_number'] = format_number
    env.filters.update(getattr(settings, 'JINJA_FILTERS', {}))
    return env


###################################
#
# from __future__ import absolute_import, unicode_literals
# from django.conf import settings
# from django.template import defaultfilters, Template as DjangoTemplate
# from django.template.context import get_standard_processors
# from django.template.response import TemplateResponse
# from jinja2.environment import Template as JinjaTemplate
# import jinja2
# import six
#
# class JinjaTemplateResponse(TemplateResponse):
#     @property
#     def _environment(self):
#         loaders = []
#         for path in getattr(settings, 'TEMPLATE_DIRS', []):
#             loaders.append(jinja2.FileSystemLoader(path))
#         for app in getattr(settings, 'INSTALLED_APPS', []):
#             loaders.append(jinja2.PackageLoader(app))
#
#         env_kwargs = {
#             'extensions': ['jinja2.ext.loopcontrols'],
#             'line_comment_prefix': '# ',
#             'loader': jinja2.ChoiceLoader(loaders),
#             'trim_blocks': True,
#         }
#         env_kwargs.update(getattr(settings, 'JINJA_ENVIRONMENT', {}))
#         env = jinja2.Environment(**env_kwargs)
#         env.globals = {
#             'url': reverse,
#             'range': six.moves.range,
#         }
#         env.globals.update(getattr(settings, 'JINJA_GLOBALS', {}))
#         for f in ('capfirst', 'linebreaks', 'linebreaksbr', 'linenumbers',
#                   'pluralize', 'removetags', 'slugify', 'striptags',
#                   'timesince', 'timeuntil', 'title', 'truncatewords',
#                   'truncatewords_html', 'unordered_list', 'urlize',
#                   'urlizetrunc', 'yesno'):
#             env.filters[f] = getattr(defaultfilters, f)
#         env.filters['format_date'] = defaultfilters.date
#         env.filters.update(getattr(settings, 'JINJA_FILTERS', {}))
#         return env
#
#     @property
#     def rendered_content(self):
#         template = self.resolve_template(self.template_name)
#         if isinstance(template, DjangoTemplate):
#             super_ = super(JinjaTemplateResponse, self)
#             context = super_.resolve_context(self.context_data)
#         else:
#             context = self.resolve_context(self.context_data)
#         content = template.render(context)
#
#         return content
#
#     def resolve_context(self, context):
#         if context:
#             self.context_data = dict(context)
#         else:
#             self.context_data = {}
#         for context_processor in get_standard_processors():
#             new_stuff = context_processor(self._request)
#             if new_stuff:
#                 self.context_data.update(dict(new_stuff))
#         return self.context_data
#
#     def resolve_template(self, template):
#         if isinstance(template, DjangoTemplate):
#             return template
#         if isinstance(template, JinjaTemplate):
#             return template
#         if isinstance(template, six.string_types):
#             return self._environment.get_template(template)
#         elif isinstance(template, (list, tuple)):
#             return self._environment.select_template(template)
#         raise TypeError('Unrecognized object sent as a template: {0}.'.format(
#             type(template).__name__,
#         ))
