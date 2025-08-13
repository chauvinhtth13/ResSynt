# apps/tenancy/middleware.py
# This defines StudyRoutingMiddleware to set the current DB based on the request's study context.
# Assumptions:
# - Study is determined from URL path, e.g., if path starts with /studies/<code>/, extract code.
# - Validate user's permission to the study (from UserStudyPermission model).
# - If no study in path, or invalid, fallback to 'db_management' or raise 403/404.
# - Lazy-load: If DB alias not in DATABASES, add it dynamically using study's db_name.
# - Requires models like Study and UserStudyPermission to be imported (circular import safe via string).
# - For simplicity, assume URL pattern like /studies/<study_code>/...; adjust as needed.
# - This middleware should be after AuthenticationMiddleware to access request.user.

from django.conf import settings
from django.http import Http404, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.db import connections
from .db_router import set_current_db
from .models import Study, UserStudyPermission  # Assuming models in apps/tenancy/models.py

class StudyRoutingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Reset to default
        set_current_db('db_management')

        if not settings.TENANCY_ENABLED:
            return None

        # Extract study_code from path (example: /studies/STUDY001/...)
        path = request.path_info.lstrip('/')
        if not path.startswith('studies/'):
            return None  # Not a study-specific path, use default DB

        parts = path.split('/')
        if len(parts) < 2:
            raise Http404("Study not specified")

        study_code = parts[1].upper()  # Assuming code is uppercase
        try:
            study = Study.objects.get(code=study_code, status='active')
        except Study.DoesNotExist:
            raise Http404("Study not found or inactive")

        # Check user permission
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Authentication required")
        
        if not UserStudyPermission.objects.filter(user=request.user, study=study).exists():
            return HttpResponseForbidden("No permission for this study")

        # Set DB alias (study.db_name from model)
        db_alias = study.db_name

        # Lazy-load if not in DATABASES
        if db_alias not in settings.DATABASES:
            settings.DATABASES[db_alias] = {
                'ENGINE': settings.STUDY_DB_ENGINE,
                'NAME': db_alias,  # Or construct as f"{settings.STUDY_DB_PREFIX}{study.code.lower()}"
                'USER': settings.STUDY_DB_USER,
                'PASSWORD': settings.STUDY_DB_PASSWORD,
                'HOST': settings.STUDY_DB_HOST,
                'PORT': settings.STUDY_DB_PORT,
                'OPTIONS': {'options': f"-c search_path={settings.STUDY_DB_SEARCH_PATH}"},
                'TIME_ZONE': settings._DB_MANAGEMENT.get('TIME_ZONE'),
                'ATOMIC_REQUESTS': settings._DB_MANAGEMENT.get('ATOMIC_REQUESTS', False),
                'AUTOCOMMIT': settings._DB_MANAGEMENT.get('AUTOCOMMIT', True),
                'CONN_MAX_AGE': settings._DB_MANAGEMENT.get('CONN_MAX_AGE', 600),
                'CONN_HEALTH_CHECKS': settings._DB_MANAGEMENT.get('CONN_HEALTH_CHECKS', False),
            }
            # Ensure connection is registered
            connections[db_alias].ensure_connection()

        set_current_db(db_alias)

    def process_response(self, request, response):
        # Optional: Clean up thread-local after response
        set_current_db('db_management')
        return response