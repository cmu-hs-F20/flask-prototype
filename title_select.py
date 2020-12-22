from wtforms.widgets import HTMLString, html_params
from wtforms_components.widgets import SelectWidget
from wtforms_components._compat import html_escape

from wtforms_components.fields import SelectMultipleField as _SelectMultipleField

import six


class SelectTitleWidget(SelectWidget):
    @classmethod
    def render_option(cls, value, label, mixed):
        if isinstance(label, (list, tuple)):
            return cls.render_optgroup(value, label, mixed)

        try:
            coerce_func, data = mixed
        except TypeError:
            selected = mixed
        else:
            if isinstance(data, list) or isinstance(data, tuple):
                selected = coerce_func(value) in data
            else:
                selected = coerce_func(value) == data

        if isinstance(value, dict):
            options = value
        else:
            options = {"value": value}

        if selected:
            options["selected"] = True

        html = u"<option %s>%s</option>"
        data = (html_params(**options), html_escape(six.text_type(label)))

        return HTMLString(html % data)


class SelectMultipleField(_SelectMultipleField):
    widget = SelectTitleWidget()