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
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        load_study_dbs()
        excluded_paths = ['/select-study/', '/accounts/', '/admin/', '/i18n/', '/static/', '/media/']
        if request.user.is_authenticated and not any(request.path.startswith(p) for p in excluded_paths):
            if request.user.is_superuser:
                set_current_db('default')
                return self.get_response(request)

            current_study_id = request.session.get('current_study')
            if current_study_id:
                try:
                    membership = StudyMembership.objects.select_related('study', 'role').prefetch_related('role__role_permissions__permission').get(
                        user=request.user, study__id=current_study_id
                    )
                    setattr(request, 'study', membership.study)
                    setattr(request, 'role', membership.role)
                    permissions = [rp.permission.code for rp in membership.role.role_permissions.all()] # type: ignore
                    setattr(request, 'study_permissions', set(permissions))
                    set_current_db(membership.study.db_name)
                except StudyMembership.DoesNotExist:
                    logger.warning(f"Invalid study ID {current_study_id} for user {request.user.pk}; clearing session.")
                    request.session.pop('current_study', None)
                    current_study_id = None

            if not current_study_id:
                if StudyMembership.objects.filter(user=request.user).exists():
                    logger.info(f"Redirecting user {request.user.pk} to select study.")
                    return redirect('select_study')
                else:
                    logger.info(f"User {request.user.pk} has no study memberships.")
                    # Optionally: return HttpResponseForbidden("No study access.")

        response = self.get_response(request)
        set_current_db('default')
        return response