"""
URL routing for research API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ResearchViewSet

router = DefaultRouter()
router.register(r'research', ResearchViewSet, basename='research')

urlpatterns = [
    path('', include(router.urls)),
]

