# apps/tenancy/middleware.py
import logging
from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import redirect
from django.conf import settings
from .models import StudyMembership, Study
from .db_loader import add_study_db
from .db_router import set_current_db, get_current_db
from contextlib import contextmanager

logger = logging.getLogger("apps.tenancy")

@contextmanager
def study_db_context(db_alias: str):
    prev_db = get_current_db()
    set_current_db(db_alias)
    try:
        yield
    finally:
        set_current_db(prev_db)

class StudyRoutingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Protect sensitive paths for non-superusers
        protected_paths = ("/secret-admin/", "/rosetta/")
        if any(request.path.startswith(p) for p in protected_paths) and request.user.is_authenticated and not request.user.is_superuser:
            raise Http404("Page not found")

        # Exclude paths that should always use default DB
        excluded_paths = [
            "/select-study/",
            "/accounts/",
            "/admin/",
            "/rosetta/",
            "/i18n/",
            "/static/",
            "/media/",
        ]
        if any(request.path.startswith(p) for p in excluded_paths):
            set_current_db("default")
            return self.get_response(request)

        # Handle unauthenticated users
        if not request.user.is_authenticated:
            set_current_db("default")
            return self.get_response(request)

        # Superusers always use default DB
        if request.user.is_superuser:
            set_current_db("default")
            return self.get_response(request)

        # Get current study from session
        current_study_id = request.session.get("current_study")
        if not current_study_id:
            if StudyMembership.objects.filter(user=request.user).exists():
                logger.info(f"Redirecting user {request.user.pk} to select study.")
                return redirect("select_study")
            else:
                raise Http404("You have no access to any studies.")

        # Validate membership in the current study
        if not StudyMembership.objects.filter(user=request.user, study__id=current_study_id).exists():
            logger.warning(f"Invalid study ID {current_study_id} for user {request.user.pk}; clearing session.")
            request.session.pop("current_study", None)
            if StudyMembership.objects.filter(user=request.user).exists():
                logger.info(f"Redirecting user {request.user.pk} to select study.")
                return redirect("select_study")
            else:
                raise Http404("You have no access to any studies.")

        # Fetch study and check status
        try:
            study = Study.objects.get(id=current_study_id)
            if study.status != Study.Status.ACTIVE:
                logger.warning(f"Inactive study {study.code} accessed by user {request.user.pk}; clearing session.")
                request.session.pop("current_study", None)
                return redirect("select_study")
        except Study.DoesNotExist:
            logger.error(f"Study ID {current_study_id} does not exist; clearing session.")
            request.session.pop("current_study", None)
            return redirect("select_study")

        # Add study DB and prepare request attributes
        add_study_db(study.db_name)
        request.study = study  # type: ignore[attr-defined]

        # Optimized prefetch for memberships, roles, permissions
        qs = StudyMembership.objects.select_related("study", "role", "study_site__site").prefetch_related(
            "role__role_permissions__permission"
        )
        memberships = qs.filter(user=request.user, study=study)
        request.study_memberships = memberships  # type: ignore[attr-defined]

        # Collect permissions and site codes
        permissions = set()
        site_codes = set()
        for membership in memberships:
            for rp in membership.role.role_permissions.all(): # type: ignore[attr-defined]
                permissions.add(rp.permission.code)
            if membership.study_site:
                site_codes.add(membership.study_site.site.code)
        request.study_permissions = permissions  # type: ignore[attr-defined]
        request.site_codes = list(site_codes)  # type: ignore[attr-defined]

        logger.debug(
            f"Accessed study DB {study.db_name} for user {request.user.pk} with permissions {permissions}"
        )

        # Route to study DB and get response
        with study_db_context(study.db_name):
            response = self.get_response(request)

        # Reset to default DB after response
        set_current_db("default")
        return response

class NoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if request.user.is_authenticated:
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
        return response