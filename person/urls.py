from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^imageupload/', views.imageupload, name='imageupload'),
    url(r'^avatar/', views.avatar, name='avatar'),
    url(r'^create/', views.create, name='create'),
    url(r'^update/', views.update, name='update'),
    url(r'^info/', views.info, name='info'),
    url(r'^exists/', views.exists, name='exists'),
]
