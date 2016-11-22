from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^imageupload/', views.imageupload, name='imageupload'),
    url(r'^avatar/', views.avatar, name='avatar'),
    url(r'^createuser/', views.createuser, name='createuser'),
    url(r'^update/', views.update, name='update'),
    url(r'^(?P<person>[-\w]+)/$', views.idprovided, name='id'),
]
