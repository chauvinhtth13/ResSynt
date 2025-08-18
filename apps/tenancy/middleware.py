# apps/tenancy/middleware.py
import logging
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.conf import settings
from .models import StudyMembership, Permission
from .db_loader import load_study_dbs
from .db_router import set_current_db

logger = logging.getLogger('apps.tenancy')

class StudyRoutingMiddleware:
    """
    Middleware to set the current study, role, and permissions on the request object
    based on the user's session and memberships. This assumes that after login,
    a 'current_study' is set in the session (e.g., via a view that lets the user select a study).
    If no current study is set and the user has memberships, it redirects to a study selection page.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Ensure study DBs are loaded (cached, so efficient)
        load_study_dbs()

        # Exclude admin paths to prevent redirecting admin dashboard access
        excluded_paths = ('/select-study/', '/secure-auth/', '/admin/')
        if request.user.is_authenticated and not request.path.startswith(excluded_paths):
            current_study_id = request.session.get('current_study')

            if current_study_id:
                try:
                    membership = StudyMembership.objects.select_related('study', 'role').get(
                        user=request.user, study__id=current_study_id
                    )
                    setattr(request, 'study', membership.study)
                    setattr(request, 'role', membership.role)

                    # Load permissions for the role in this study
                    permissions = Permission.objects.filter(
                        role_permissions__role=membership.role
                    ).values_list('code', flat=True)
                    setattr(request, 'study_permissions', set(permissions))

                    # Set thread-local for DB routing
                    set_current_db(membership.study.db_name)

                except StudyMembership.DoesNotExist:
                    logger.warning(f"Invalid study ID {current_study_id} for user {request.user.pk}; clearing session.")
                    request.session.pop('current_study', None)
                    current_study_id = None

            if not current_study_id:
                # If no current study, check if user has any memberships
                memberships = StudyMembership.objects.filter(user=request.user)
                if memberships.exists():
                    logger.info(f"Redirecting user {request.user.pk} to select study.")
                    return redirect('select_study')
                else:
                    # No memberships; log and proceed (or forbid access)
                    logger.info(f"User {request.user.pk} has no study memberships.")
                    # Optionally: return HttpResponseForbidden("No study access.")

        response = self.get_response(request)

        # Clean up thread-local after response
        set_current_db('default')

        return response