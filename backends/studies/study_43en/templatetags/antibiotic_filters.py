from django import template

# Import dict filters from centralized location
from backends.studies.study_43en.templatetags.dict_filters import get_item

register = template.Library()

# dict_item is deprecated - use get_item from dict_filters.py instead
# Keeping for backwards compatibility
@register.filter
def dict_item(dictionary, key):
    """DEPRECATED: Use get_item from dict_filters.py instead"""
    return get_item(dictionary, key)
