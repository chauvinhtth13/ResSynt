# apps/tenancy/middleware.py - OPTIMIZED
import logging
from typing import Optional
from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import redirect
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db import transaction
from .models import StudyMembership, Study
from .db_loader import add_study_db, remove_study_db
from .db_router import set_current_db, get_current_db
from contextlib import contextmanager

logger = logging.getLogger("apps.tenancy")

@contextmanager
def study_db_context(db_alias: str):
    """Thread-safe context manager for DB switching."""
    prev_db = get_current_db()
    try:
        set_current_db(db_alias)
        yield
    except Exception as e:
        logger.error(f"Error in study_db_context: {e}")
        raise
    finally:
        set_current_db(prev_db)

class StudyRoutingMiddleware:
    EXCLUDED_PATHS = (
        "/select-study/", "/accounts/", "/admin/", "/secret-admin/",
        "/rosetta/", "/i18n/", "/static/", "/media/", "/favicon.ico"
    )
    PROTECTED_PATHS = ("/secret-admin/", "/rosetta/")
    CACHE_KEY_USER_STUDY = "user_study_{user_id}_{study_id}"
    CACHE_TTL = 300

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Security check first
        if self._is_protected_path(request):
            raise Http404("Page not found")

        # Handle excluded paths
        if self._should_use_default_db(request):
            set_current_db("default")
            return self.get_response(request)

        # Handle unauthenticated
        if not request.user.is_authenticated:
            set_current_db("default")
            return self.get_response(request)

        # Superusers use default
        if request.user.is_superuser:
            set_current_db("default")
            return self.get_response(request)

        # Get and validate study
        study = self._get_validated_study(request)
        if not study:
            return self._handle_no_study(request)

        # Setup study context
        self._setup_study_context(request, study)

        # Process with study DB
        try:
            with study_db_context(study.db_name):
                response = self.get_response(request)
        except Exception as e:
            logger.error(f"Error processing request for study {study.code}: {e}")
            raise

        set_current_db("default")
        return response

    def _is_protected_path(self, request: HttpRequest) -> bool:
        """Check if path is protected for non-superusers."""
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return False
        return any(request.path.startswith(p) for p in self.PROTECTED_PATHS)

    def _should_use_default_db(self, request: HttpRequest) -> bool:
        """Check if request should use default DB."""
        return any(request.path.startswith(p) for p in self.EXCLUDED_PATHS)

    def _get_validated_study(self, request: HttpRequest) -> Optional[Study]:
        """Get and validate current study from session."""
        study_id = request.session.get("current_study")
        if not study_id:
            return None

        # Check cache first
        cache_key = self.CACHE_KEY_USER_STUDY.format(
            user_id=request.user.pk, study_id=study_id
        )
        is_valid = cache.get(cache_key)
        
        if is_valid is None:
            # Validate membership
            with transaction.atomic():
                exists = StudyMembership.objects.select_for_update(
                    nowait=True
                ).filter(
                    user=request.user, 
                    study__id=study_id,
                    study__status=Study.Status.ACTIVE
                ).exists()
            
            if exists:
                cache.set(cache_key, True, self.CACHE_TTL)
            else:
                request.session.pop("current_study", None)
                return None
        elif not is_valid:
            request.session.pop("current_study", None)
            return None

        try:
            return Study.objects.select_related().get(
                id=study_id, status=Study.Status.ACTIVE
            )
        except Study.DoesNotExist:
            request.session.pop("current_study", None)
            return None

    def _handle_no_study(self, request: HttpRequest) -> HttpResponse:
        """Handle case when no valid study is selected."""
        # Check if user has ANY active studies
        if StudyMembership.objects.filter(
            user=request.user,
            study__status=Study.Status.ACTIVE
        ).exists():
            return redirect("select_study")
        
        # No active studies - show error
        messages.error(request, "You have no access to any active studies.")
        return redirect("login")

    def _setup_study_context(self, request: HttpRequest, study: Study) -> None:
        """Setup request attributes for study context."""
        add_study_db(study.db_name)
        request.study = study  # type: ignore

        # Optimized query with select/prefetch
        memberships = (
            StudyMembership.objects
            .select_related("study", "role", "study_site__site")
            .prefetch_related("role__role_permissions__permission")
            .filter(user=request.user, study=study)
        )
        
        request.study_memberships = list(memberships)  # type: ignore
        
        # Extract permissions and sites
        permissions = set()
        site_codes = set()
        for m in request.study_memberships:  # type: ignore
            for rp in m.role.role_permissions.all(): # type: ignore
                permissions.add(rp.permission.code)
            if m.study_site:
                site_codes.add(m.study_site.site.code)
        
        request.study_permissions = permissions  # type: ignore
        request.site_codes = list(site_codes)  # type: ignore

class NoCacheMiddleware:
    """Prevent caching for authenticated users."""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if request.user.is_authenticated:
            response["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
        return response