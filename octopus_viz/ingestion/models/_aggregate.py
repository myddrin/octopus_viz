from django.db.models import Aggregate, JSONField


class JsonGroupArray(Aggregate):
    function = 'JSON_GROUP_ARRAY'
    output_field = JSONField()
    template = '%(function)s(%(distinct)s%(expression)s)'
