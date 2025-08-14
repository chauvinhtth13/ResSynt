import logging
from django.http import HttpResponseForbidden
from django.conf import settings
from apps.tenancy.models import Study, StudyMembership
from apps.tenancy.db_loader import load_study_dbs  # Assuming db_loader.py exists as per previous setup

logger = logging.getLogger('apps.tenancy')

class StudyRoutingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Load dynamic study DBs (cached, so low overhead)
        load_study_dbs()

        current_db = 'default'  # Fallback
        if request.user.is_authenticated:
            study_code = request.session.get('current_study')  # Use 'current_study' for code; adjust if using ID
            if study_code:
                try:
                    study = Study.objects.get(code=study_code, status=Study.Status.ACTIVE)
                    # Check permission
                    if StudyMembership.objects.filter(user=request.user, study=study).exists():
                        current_db = study.db_name
                        logger.debug(f"Set current DB to {current_db} for user {request.user.username} in study {study_code}")
                    else:
                        logger.warning(f"User {request.user.username} lacks permission for study {study_code}")
                        return HttpResponseForbidden("You do not have permission to access this study.")
                except Study.DoesNotExist:
                    logger.warning(f"Study {study_code} not found or inactive for user {request.user.username}")
                    # Optionally unset session: del request.session['current_study']

        # Set thread-local for router
        settings.THREAD_LOCAL.current_db = current_db

        response = self.get_response(request)

        # Clear thread-local after request
        settings.THREAD_LOCAL.current_db = None

        return response