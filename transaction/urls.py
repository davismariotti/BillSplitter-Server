from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^new/', views.new, name='new'),
    url(r'^payback/', views.payback, name='payback'),
    url(r'^history/', views.history, name='history'),
]
