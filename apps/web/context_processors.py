from django.conf import settings
from django.utils.translation import get_language
from django.urls import translate_url

def redirect_to(request):
    current_path = request.path
    default_lang = settings.LANGUAGE_CODE
    current_lang = get_language()
    if current_lang != default_lang:
        redirect_path = translate_url(current_path, default_lang)
    else:
        redirect_path = current_path
    return {'redirect_to': redirect_path}