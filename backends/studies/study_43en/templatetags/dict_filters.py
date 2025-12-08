"""
Dictionary filters for accessing dict values in templates
"""
from django import template

register = template.Library()


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Get item from dictionary by key
    
    Usage in template:
        {{ my_dict|get_item:key_variable }}
        {{ my_dict|get_item:"literal_key" }}
    
    Args:
        dictionary: Dictionary object
        key: Key to lookup
        
    Returns:
        Value from dictionary or empty string if not found
    """
    if dictionary is None:
        return ''
    
    if not isinstance(dictionary, dict):
        return ''
    
    return dictionary.get(key, '')


@register.filter(name='get_item_safe')
def get_item_safe(dictionary, key):
    """
    Get item from dictionary with None check
    
    Returns None instead of empty string if key not found
    """
    if dictionary is None:
        return None
    
    if not isinstance(dictionary, dict):
        return None
    
    return dictionary.get(key)


@register.filter(name='has_key')
def has_key(dictionary, key):
    """
    Check if dictionary has key
    
    Usage:
        {% if my_dict|has_key:"some_key" %}
    """
    if dictionary is None:
        return False
    
    if not isinstance(dictionary, dict):
        return False
    
    return key in dictionary