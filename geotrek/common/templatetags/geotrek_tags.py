from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def settings_value(name):
    return getattr(settings, name, "")


@register.simple_tag
def is_topology_model(model):
    return hasattr(model, 'kind') and hasattr(model, 'offset')
