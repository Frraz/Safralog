from django.utils.functional import SimpleLazyObject


def get_tenant(request):
    if not hasattr(request, "_cached_tenant"):
        user = request.user
        if user.is_authenticated and user.tenant_id:
            from apps.tenants.models import Tenant

            try:
                request._cached_tenant = Tenant.objects.get(pk=user.tenant_id)
            except Tenant.DoesNotExist:
                request._cached_tenant = None
        else:
            request._cached_tenant = None
    return request._cached_tenant


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = SimpleLazyObject(lambda: get_tenant(request))
        return self.get_response(request)
