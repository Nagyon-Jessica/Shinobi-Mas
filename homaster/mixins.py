from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect

class LoginRequiredCustomMixin(AccessMixin):
    """Verify that the current user is authenticated."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(to='index')
        return super().dispatch(request, *args, **kwargs)
