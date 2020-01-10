from django.conf import settings
from django.utils.translation import LANGUAGE_SESSION_KEY


class LocaleForcedMiddleware(object):
    """
    This will force session language for authenticated API calls.

    Since Django gives priority to session language, and since for API
    calls, we use ``Accept-language`` header to obtain translations, we
    override it.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT')
        is_api_call = (user_agent is None or 'geotrek' in user_agent)
        forced_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if is_api_call and forced_language and hasattr(request, 'session'):
            request.session[LANGUAGE_SESSION_KEY] = forced_language
        return self.get_response(request)


class CorsMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return self.process_response(request, response)

    def process_response(self, request, response):
        if settings.DEBUG:
            response['Access-Control-Allow-Origin'] = "*"
        return response
