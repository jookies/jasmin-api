from django.conf.urls import include, url
from django.contrib import admin

from rest_framework.routers import DefaultRouter

from rest_api import views

router = DefaultRouter()
router.register(r'groups', views.GroupViewSet, base_name='groups')
router.register(r'users', views.UserViewSet, base_name='users')

urlpatterns = [
    url(r'^api/', include(router.urls)),
    url(r'^docs/', include('rest_framework_swagger.urls')),
]

