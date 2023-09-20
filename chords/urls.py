"""chords URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
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
import debug_toolbar
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path

urlpatterns = [
    path("accounts/", include("django.contrib.auth.urls")),
    re_path(r"^markdownx/", include("markdownx.urls")),
    path("i18n/", include("django.conf.urls.i18n")),
    path("pdf/", include(("pdf.urls", "pdf"), namespace="pdf")),
    path("categories/", include(("category.urls", "category"), namespace="category")),
    path("analytics/", include(("analytics.urls", "analytics"), namespace="analytics")),
    path("tenants/", include(("tenants.urls", "tenants"), namespace="tenants")),
    re_path(r"^", include(("backend.urls", "backend"), namespace="chords")),
    path("admin/", admin.site.urls),
    path("__debug__/", include(debug_toolbar.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
