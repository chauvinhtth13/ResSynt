from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Lấy giá trị từ dictionary theo key"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def count_performed(tests):
    """Đếm số lượng xét nghiệm đã thực hiện"""
    return len([t for t in tests if getattr(t, 'PERFORMED', False)])