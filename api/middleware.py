"""
Middleware для обработки Telegram webhook без CSRF проверки
"""

class DisableCSRFMiddleware:
    """Отключает CSRF проверку для определенных путей"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Пути, для которых нужно отключить CSRF
        self.exempt_urls = [
            '/api/telegram-webhook/',
            '/api/test-webhook/',
        ]
    
    def __call__(self, request):
        # Проверяем, нужно ли отключить CSRF для этого пути
        for url in self.exempt_urls:
            if request.path.startswith(url):
                setattr(request, '_dont_enforce_csrf_checks', True)
                break
        
        response = self.get_response(request)
        return response
