from django.http import HttpResponse

import json


def index(request):
    return HttpResponse(json.dumps({'version': 1.0}))