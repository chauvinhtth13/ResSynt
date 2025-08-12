# apps/web/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from apps.tenancy.models import StudyMembership

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "default/dashboard.html"
    login_url = "login"  # optional, đã có LOGIN_URL trong settings

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["memberships"] = (
            StudyMembership.objects.using("db_management")
            .filter(user=self.request.user)
            .select_related("study", "role")
            .order_by("study__code")
        )
        return ctx