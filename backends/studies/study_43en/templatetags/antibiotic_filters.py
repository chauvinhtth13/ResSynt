from django import template

register = template.Library()

@register.filter
def dict_item(dictionary, key):
    """Lấy giá trị từ dictionary với key được đưa vào"""
    if key in dictionary:
        return dictionary.get(key)
    return []
