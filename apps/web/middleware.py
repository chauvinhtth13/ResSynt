class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        resp = self.get_response(request)
        # Add only if not already set by a proxy
        resp.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        resp.setdefault('Cross-Origin-Embedder-Policy', 'require-corp')
        resp.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        resp.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        return resp