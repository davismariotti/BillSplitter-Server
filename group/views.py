from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables


def index(request):
    return HttpResponse()


def create(request):
    return HttpResponse()


def delete(request):
    return HttpResponse()


def adduser(request):
    return HttpResponse()


def removeuser(request):
    return HttpResponse()
