from django.conf.urls import include, url

from rest_framework.routers import DefaultRouter

from rest_api import groups, users

router = DefaultRouter()
router.register(r'groups', groups.ViewSet, base_name='groups')
router.register(r'users', users.ViewSet, base_name='users')

urlpatterns = [
    url(r'^api/', include(router.urls)),
    url(r'^docs/', include('rest_framework_swagger.urls')),
]
