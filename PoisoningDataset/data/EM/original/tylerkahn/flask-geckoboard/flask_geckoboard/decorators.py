""" Geckoboard decorators. """

import base64
from collections import OrderedDict
from functools import wraps
import json

try:
    from Crypto.Cipher import AES
    from Crypto import Random
    from hashlib import md5
    encryption_enabled = True
except ImportError:
    encryption_enabled = False

from flask import abort, request
from flask import current_app as app

TEXT_NONE = 0
TEXT_INFO = 2
TEXT_WARN = 1


class WidgetDecorator(object):
    """
    Geckoboard widget decorator.

    The decorated view must return a data structure suitable for
    serialization to XML or JSON for Geckoboard. See the Geckoboard
    API docs or the source of extending classes for details.

    If the ``GECKOBOARD_API_KEY`` setting is used, the request must
    contain the correct API key, or a 403 Forbidden response is
    returned.

    If the ``encrypted`` argument is set to True, then the data will be
    encrypted using ``GECKOBOARD_PASSWORD`` (JSON only).

    """
    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._encrypted = None
        if 'encrypted' in kwargs:
            if not encryption_enabled:
                raise GeckoboardException(
                    'Use of encryption requires the pycrypto package. ' +
                    'This package can be installed manually or by enabling ' +
                    'the encryption feature during installation.'
                )
            obj._encrypted = kwargs.pop('encrypted')
        obj._format = None
        if 'format' in kwargs:
            obj._format = kwargs.pop('format')
        obj.data = kwargs
        try:
            return obj(args[0])
        except IndexError:
            return obj

    def __call__(self, view_func):
        @wraps(view_func)
        def decorated_view(*args, **kwargs):
            if not _is_api_key_correct():
                abort(403)
            view_result = view_func(*args, **kwargs)
            data = self._convert_view_result(view_result)
            try:
                self.data.update(data)
            except ValueError:
                self.data = data
            content, content_type = _render(
                self.data, self._encrypted, self._format)
            return app.response_class(content, mimetype=content_type)
        return decorated_view

    def _convert_view_result(self, data):
        # Extending classes do view result mangling here.
        return data

widget = WidgetDecorator


class NumberWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Number widget decorator.

    The decorated view must return a tuple `(current, [previous])`, where
    `current` is the current value and `previous` is the previous value
    of the measured quantity.

    """
    def _convert_view_result(self, result):
        if not isinstance(result, (tuple, list)):
            result = [result]
        result = list(result)
        for k, v in enumerate(result):
            result[k] = v if isinstance(v, dict) else {'value': v}
        return {'item': result}

number_widget = NumberWidgetDecorator


class RAGWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Red-Amber-Green (RAG) widget decorator.

    The decorated view must return a tuple with three tuples `(value,
    [text])`. The `value` parameters are the numbers shown in red,
    amber and green (in that order).  The `text` parameters are optional
    and will be displayed next to the respective values in the
    dashboard.

    """
    def _convert_view_result(self, result):
        items = []
        for elem in result:
            if not isinstance(elem, (tuple, list)):
                elem = [elem]
            item = OrderedDict()
            if elem[0] is None:
                item['value'] = ''
            else:
                item['value'] = elem[0]
            if len(elem) > 1:
                item['text'] = elem[1]
            items.append(item)
        return {'item': items}

rag_widget = RAGWidgetDecorator


class TextWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Text widget decorator.

    The decorated view must return a list of tuples `(message, [type])`.
    The `message` parameters are strings that will be shown in the
    widget. The `type` parameters are optional and tell Geckoboard how
    to annotate the messages. Use ``TEXT_INFO`` for informational
    messages, ``TEXT_WARN`` for for warnings and ``TEXT_NONE`` for plain
    text (the default).

    """
    def _convert_view_result(self, result):
        items = []
        if not isinstance(result, (tuple, list)):
            result = [result]
        for elem in result:
            if not isinstance(elem, (tuple, list)):
                elem = [elem]
            item = OrderedDict()
            item['text'] = elem[0]
            if len(elem) > 1 and elem[1] is not None:
                item['type'] = elem[1]
            else:
                item['type'] = TEXT_NONE
            items.append(item)
        return {'item': items}

text_widget = TextWidgetDecorator


class PieChartWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Pie chart decorator.

    The decorated view must return a list of tuples `(value, label,
    color)`. The color parameter is a string 'RRGGBB[TT]' representing
    red, green, blue and optionally transparency.

    """
    def _convert_view_result(self, result):
        items = []
        for elem in result:
            if not isinstance(elem, (tuple, list)):
                elem = [elem]
            item = OrderedDict()
            item['value'] = elem[0]
            if len(elem) > 1:
                item['label'] = elem[1]
            if len(elem) > 2:
                item['colour'] = elem[2]
            items.append(item)
        return {'item': items}

pie_chart = PieChartWidgetDecorator


class LineChartLegacyWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Line chart (legacy) decorator.

    The decorated view must return a tuple `(values, x_axis, y_axis,
    [color])`. The `values` parameter is a list of data points. The
    `x-axis` parameter is a label string or a list of strings, that will
    be placed on the X-axis. The `y-axis` parameter works similarly for
    the Y-axis. If there are more than one axis label, they are placed
    evenly along the axis. The optional `color` parameter is a string
    ``'RRGGBB[TT]'`` representing red, green, blue and optionally
    transparency.

    """
    def _convert_view_result(self, result):
        data = OrderedDict()
        data['item'] = list(result[0])
        data['settings'] = OrderedDict()

        if len(result) > 1:
            x_axis = result[1]
            if x_axis is None:
                x_axis = ''
            if not isinstance(x_axis, (tuple, list)):
                x_axis = [x_axis]
            data['settings']['axisx'] = x_axis

        if len(result) > 2:
            y_axis = result[2]
            if y_axis is None:
                y_axis = ''
            if not isinstance(y_axis, (tuple, list)):
                y_axis = [y_axis]
            data['settings']['axisy'] = y_axis

        if len(result) > 3:
            data['settings']['colour'] = result[3]

        return data

line_chart_legacy = LineChartLegacyWidgetDecorator


class LineChartWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Line chart decorator.

    The decorated view must return a dict that contains at least a
    `series` entry which must be a list of dicts (one for each line) each
    containing a `data` entry with a list of the data to be plotted.

    Optional keys:

        x_axis: A dict with a `labels` entry for the x-axis labels.
        y_axis: A dict with a `labels` entry for the y-axis labels.

    The `series`, `x_axis`, and `y_axis` entries can have other optional keys.
    See https://developer.geckoboard.com/#line-chart for more information.

    """
    def _convert_view_result(self, result):
        data = OrderedDict()
        if not isinstance(result['series'], list) or 'series' not in result:
            raise RuntimeError('Key "series" (list) is required')
        for s in result.get('series'):
            if not isinstance(s, dict) or 'data' not in s:
                raise RuntimeError('Series must contain "data" entry')
        data['series'] = result.get('series')

        if 'x_axis' in result:
            data['x_axis'] = result.get('x_axis')

        if 'y_axis' in result:
            data['y_axis'] = result.get('x_axis')

        return data

line_chart = LineChartWidgetDecorator


class BarChartWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Bar chart decorator.

    The decorated view must return a dict that contains at least a
    `series` entry which must be a list  containing a single `data` entry
    with a list of datapoints to be plotted.

    Optional keys:

        x_axis: A dict with a `labels` entry for the x-axis labels.
        y_axis: A dict with a `labels` entry for the y-axis labels.

    The `series`, `x_axis`, and `y_axis` entries can have other optional keys.
    See https://developer.geckoboard.com/#bar-chart for more information.

    """
    def _convert_view_result(self, result):
        data = OrderedDict()
        if not isinstance(result['series'], list) or 'series' not in result:
            raise RuntimeError('Key "series" (list) is required')
        for s in result.get('series'):
            if not isinstance(s, dict) or 'data' not in s:
                raise RuntimeError('Series must contain "data" entry')
        data['series'] = result.get('series')

        if 'x_axis' in result:
            data['x_axis'] = result.get('x_axis')

        if 'y_axis' in result:
            data['y_axis'] = result.get('x_axis')

        return data

bar = BarChartWidgetDecorator


class GeckOMeterWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Geck-O-Meter decorator.

    The decorated view must return a tuple `(value, min, max)`. The
    `value` parameter represents the current value. The `min` and `max`
    parameters represent the minimum and maximum value respectively.
    They are either a value, or a tuple `(value, text)`. If used, the
    `text` parameter will be displayed next to the minimum or maximum
    value.

    """
    def _convert_view_result(self, result):
        value, min, max = result
        data = OrderedDict()
        data['item'] = value
        data['max'] = OrderedDict()
        data['min'] = OrderedDict()

        if not isinstance(max, (tuple, list)):
            max = [max]
        data['max']['value'] = max[0]
        if len(max) > 1:
            data['max']['text'] = max[1]

        if not isinstance(min, (tuple, list)):
            min = [min]
        data['min']['value'] = min[0]
        if len(min) > 1:
            data['min']['text'] = min[1]

        return data

geck_o_meter = GeckOMeterWidgetDecorator


class FunnelWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Funnel decorator.

    The decorated view must return a dictionary with at least an `items`
    entry: `{'items': [(100, '100 %'), (50, '50 %')]}`.

    Optional keys are:

        type:       'standard' (default) or 'reverse'. Determines the
                    order of the colours.
        percentage: 'show' (default) or 'hide'. Determines whether or
                    not the percentage value is shown.
        sort:       `False` (default) or `True`. Sort the entries by
                    value or not.

    """
    def _convert_view_result(self, result):
        data = OrderedDict()
        items = result.get('items', [])

        # sort the items in order if so desired
        if result.get('sort'):
            items.sort(reverse=True)

        data['item'] = [dict(zip(('value', 'label'), item)) for item in items]
        data['type'] = result.get('type', 'standard')
        data['percentage'] = result.get('percentage', 'show')
        return data

funnel = FunnelWidgetDecorator


class BulletWidgetDecorator(WidgetDecorator):
    """
    The decorated method must return a dictionary containing these keys:

    Required keys:
    label:          Main label, eg. "Revenue 2011 YTD".
    axis_points:    Points on the axis, eg. [0, 200, 400, 600, 800, 1000].
    current:        Current value range, eg. 500 or [100, 500]. A singleton
                    500 is internally converted to [0, 500].
    comparative:    Comparative value, eg. 600.

    Optional keys:
    orientation:    One of 'horizontal' or 'vertical'. Defaults to horizontal.
    sublabel:       Appears below main label.
    range:          Ordered list of color ranges:
                    [{'color': 'red', 'start': 0, 'end': 1},
                     {'color': 'amber', 'start': 1, 'end': 5},
                     {'color': 'green', 'start': 5, 'end': 10}]
                    Defaults are calculated from axis_points.
    projected:      Projected value range, eg. 900 or [100, 900]. A singleton
                    900 is internally converted to [0, 900].

    auto_scale:     If true then values will be scaled down if they
                    do not fit into Geckoboard's UI, eg. a value of 1100
                    is represented as 1.1. If scaling takes place the sublabel
                    is suffixed with that information. Default is true.

    """
    def _convert_view_result(self, results):
        # Check required keys. We do not do type checking since this level of
        # competence is assumed.
        if not isinstance(results, list):
            results = [results]
        items = []
        for result in results:
            for key in ('label', 'axis_points', 'current'):
                if key not in result:
                    raise RuntimeError('Key {} is required'.format(key))

            # Handle singleton current and projected
            current = result['current']
            projected = result.get('projected', None)
            if not isinstance(current, (list, tuple)):
                current = [0, current]
            if (projected is not None) and not isinstance(
                    projected, (list, tuple)):
                projected = [0, projected]

            # If red, amber and green are not *all* supplied calculate defaults
            axis_points = result['axis_points']
            _range = result.get('range', [])
            if not _range:
                if axis_points:
                    max_point = max(axis_points)
                    min_point = min(axis_points)
                    third = (max_point - min_point) / 3
                    range.append({'color': 'red',
                                  'start': min_point,
                                  'end': min_point + third - 1})
                    range.append({'color': 'amber',
                                  'start': min_point + third,
                                  'end': max_point - third - 1})
                    range.append({'color': 'red',
                                  'start': max_point - third,
                                  'end': max_point})
                else:
                    _range = [{'color': 'red', 'start': 0, 'end': 0},
                              {'color': 'amber', 'start': 0, 'end': 0},
                              {'color': 'green', 'start': 0, 'end': 0}]

            # Scan axis points for largest value and scale to avoid overflow in
            # Geckoboard's UI.
            auto_scale = result.get('auto_scale', True)
            if auto_scale and axis_points:
                scale_label_map = {1000000000: 'billions', 1000000: 'millions',
                                   1000: 'thousands'}
                scale = 1
                value = max(axis_points)
                for n in (1000000000, 1000000, 1000):
                    if value >= n:
                        scale = n
                        break

                # Little fixedpoint helper.
                # todo: use a fixedpoint library
                def scaler(value, scale):
                    return float('%.2f' % (value*1.0 / scale))

                # Apply scale to all values
                if scale > 1:
                    axis_points = [scaler(v, scale) for v in axis_points]
                    current = (scaler(current[0], scale),
                               scaler(current[1], scale))
                    if projected is not None:
                        projected = (scaler(projected[0], scale),
                                     scaler(projected[1], scale))
                    # red = (scaler(red[0], scale), scaler(red[1], scale))
                    # amber = (scaler(amber[0], scale), scaler(amber[1], scale))
                    # green = (scaler(green[0], scale), scaler(green[1], scale))
                    if 'comparative' in result:
                        result['comparative'] = scaler(
                            result['comparative'], scale)

                    # Suffix sublabel
                    sublabel = result.get('sublabel', '')
                    if sublabel:
                        result['sublabel'] = '{} ({})'.format(
                            sublabel, scale_label_map[scale])
                    else:
                        result['sublabel'] = scale_label_map[scale].capitalize()

            # Assemble structure
            data = dict(
                label=result['label'],
                axis=dict(point=axis_points),
                range=_range,
                measure=dict(current=dict(start=current[0], end=current[1])))
            if 'comparative' in result:
                data['comparative'] = dict(point=result['comparative'])

            # Add optional items
            if 'sublabel' in result:
                data['sublabel'] = result['sublabel']
            if projected is not None:
                data['measure']['projected'] = dict(start=projected[0],
                                                    end=projected[1])

            items.append(data)
        return dict(item=items,
                    orientation=result.get('orientation', 'horizontal'),)

bullet = BulletWidgetDecorator


class LeaderboardWidgetDecorator(WidgetDecorator):
    """
    Leaderboard decorator.

    The decorated view must return a tuple that looks like the following:

        (labels, values, previous_ranks, 'ascending')

    The first three entries are lists with the corresponding labels, values, and
    previous rank in the leaderboard. If 'ascending' is provided as the last
    entry, the leaderboard is sorted in ascending order, else descending.

    The only required entries are labels and values, hence the minimal returned
    tuple must be like this:

        (labels, values)

    """
    def _convert_view_result(self, result):
        data = OrderedDict()
        sort_arg = 'descending'
        if len(result) > 3:
            sort_arg = result[-1]
            result = result[:-1]
        zipped = zip(*result)
        if len(result) > 2:
            items = [{'label': x[0], 'value': x[1],
                      'previous_rank': x[2]} for x in zipped]
        else:
            items = [{'label': x[0], 'value': x[1]} for x in zipped]
        # Sort the items by value
        if sort_arg == 'ascending':
            data['items'] = sorted(items, key=lambda k: k['value'])
        else:
            data['items'] = sorted(items, key=lambda k: k['value'],
                                   reverse=True)
        return data

leaderboard = LeaderboardWidgetDecorator


def _is_api_key_correct():
    """ Return whether the Geckoboard API key on the request is correct. """
    api_key = app.config.get('GECKOBOARD_API_KEY')
    if api_key is None:
        return True
    auth = request.authorization
    if auth:
        if auth.type == 'basic':
            return auth.username == api_key and auth.password == 'X'
    return False


def _derive_key_and_iv(password, salt, key_length, iv_length):
    d = d_i = ''
    while len(d) < key_length + iv_length:
        d_i = md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length+iv_length]


def _encrypt(data):
    """ Equivalent to OpenSSL using 256 bit AES in CBC mode. """
    BS = AES.block_size
    pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
    password = app.config.get('GECKOBOARD_PASSWORD')
    salt = Random.new().read(BS - len('Salted__'))
    key, iv = _derive_key_and_iv(password, salt, 32, BS)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = 'Salted__' + salt + cipher.encrypt(pad(data))
    return base64.b64encode(encrypted)


def _render(data, encrypted, format=None):
    """
    Render the data to Geckoboard. If the `format` parameter is passed
    to the widget it defines the output format. Otherwise the output
    format is based on the `format` request parameter.

    A `format` paramater of ``json`` or ``2`` renders JSON output, any
    other value renders XML.

    """
    return _render_json(data, encrypted)


def _render_json(data, encrypted=False):
    data_json = json.dumps(data)
    if encrypted:
        data_json = _encrypt(data_json)
    return data_json, 'application/json'


class GeckoboardException(Exception):
    """
    Represents an error with the Geckoboard decorators.

    """
