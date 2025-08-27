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
def study_db_context(db_alias):
    prev_db = get_current_db()
    set_current_db(db_alias)
    yield
    set_current_db(prev_db)


class StudyRoutingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        protected_paths = ("/secret-admin/", "/rosetta/")
        if any(request.path.startswith(p) for p in protected_paths) and request.user.is_authenticated and not request.user.is_superuser:
            raise Http404("Page not found")

        excluded_paths = [
            "/select-study/",
            "/accounts/",
            "/admin/",
            "/rosetta/",
            "/i18n/",
            "/static/",
            "/media/",
        ]
        if request.user.is_authenticated:
            if request.user.is_superuser:
                set_current_db("default")
            else:
                if any(request.path.startswith(p) for p in excluded_paths):
                    set_current_db("default")
                else:
                    current_study_id = request.session.get("current_study")
                    if current_study_id:
                        if not StudyMembership.objects.filter(user=request.user, study__id=current_study_id).exists():
                            logger.warning(f"Invalid study ID {current_study_id} for user {request.user.pk}; clearing session.")
                            request.session.pop("current_study", None)
                            if StudyMembership.objects.filter(user=request.user).exists():
                                logger.info(f"Redirecting user {request.user.pk} to select study.")
                                return redirect("select_study")
                            else:
                                raise Http404("You have no access to any studies.")
                        # Optimized prefetch for perf (includes permissions early)
                        qs = StudyMembership.objects.select_related("study", "role", "study_site__site").prefetch_related(
                            "role__role_permissions__permission"
                        )
                        memberships = qs.filter(user=request.user, study__id=current_study_id)
                        request.study = memberships[0].study # type: ignore[attr-defined]
                        study = getattr(request, "study", None)
                        if study and study.status != Study.Status.ACTIVE:
                            logger.warning(f"Inactive study {study.code} accessed by user {request.user.pk}; clearing session.")
                            request.session.pop("current_study", None)
                            return redirect("select_study")
                        if study:
                            add_study_db(study.db_name)
                            request.study_memberships = memberships # type: ignore[attr-defined]
                            request.study_permissions = set() # type: ignore[attr-defined]
                            for membership in memberships:
                                for rp in membership.role.role_permissions.all(): # type: ignore[attr-defined]
                                    request.study_permissions.add(rp.permission.code) # type: ignore[attr-defined]
                            site_codes = {m.study_site.site.code for m in memberships if m.study_site}
                            request.site_codes = list(site_codes) if site_codes else [] # type: ignore[attr-defined]
                            logger.debug(
                                f"Accessed study DB {request.study.db_name} for user {request.user.pk} with permissions {request.study_permissions}" # type: ignore[attr-defined]
                            )
                            with study_db_context(request.study.db_name): # type: ignore[attr-defined]
                                response = self.get_response(request)
                            return response
                    else:
                        if StudyMembership.objects.filter(user=request.user).exists():
                            logger.info(f"Redirecting user {request.user.pk} to select study.")
                            return redirect("select_study")
                        else:
                            raise Http404("You have no access to any studies.")

        response = self.get_response(request)
        set_current_db("default")
        return response


class NoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
        return response
