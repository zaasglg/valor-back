"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""


from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from api.views import hello_world, register, login, get_countries, transactions_list, transaction_create, update_profile, historial_pagos_list, historial_pagos_create, get_user_info, refresh_token, use_first_bonus


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/hello/", hello_world, name="hello_world"),
    path("api/register/", register, name="register"),
    path("api/login/", login, name="login"),
    path("api/countries/", get_countries, name="get_countries"),
    path("api/transactions/", transactions_list, name="transactions_list"),
    path("api/transactions/create/", transaction_create, name="transaction_create"),
    path("api/profile/update/", update_profile, name="update_profile"),
    path("api/historial_pagos/", historial_pagos_list, name="historial_pagos_list"),
    path("api/historial_pagos/create/", historial_pagos_create, name="historial_pagos_create"),
    path("api/user/info/", get_user_info, name="get_user_info"),
    path("api/user/use-first-bonus/", use_first_bonus, name="use_first_bonus"),
    path("api/token/refresh/", refresh_token, name="refresh_token"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
