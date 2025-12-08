# # backends/studies/study_43en/templatetags/audit_filters.py
# """
# Custom template filters for audit log
# """
# from django import template

# register = template.Library()


# @register.filter
# def get_item(dictionary, key):
#     """
#     Get item from dictionary by key
    
#     Usage in template:
#         {{ my_dict|get_item:key_variable }}
    
#     Args:
#         dictionary: Dictionary to get value from
#         key: Key to lookup
        
#     Returns:
#         Value from dictionary or None
#     """
#     if not dictionary:
#         return None
    
#     if not isinstance(dictionary, dict):
#         return None
    
#     return dictionary.get(key, None)


# @register.filter
# def get_dict_item(dictionary, key):
#     """
#     Alias for get_item
#     """
#     return get_item(dictionary, key)