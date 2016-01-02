from django.conf.urls import include, url
from django.contrib import admin

from rest_api import views

urlpatterns = [
    url(r'^$', views.TestView.as_view()),
    url(r'^admin/', include(admin.site.urls)),
]

