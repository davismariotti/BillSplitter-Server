import json, jwt, os, base64

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

f = open('../secrets.JSON', 'r')
secrets = json.load(f)

secret = secrets['secret']


@csrf_exempt
def index(request):
    return HttpResponse()


@csrf_exempt
def idprovided(request, person=None):
    return HttpResponse(json.dumps({'id':person}))


@csrf_exempt
def avatar(request):
    params = request.GET  # TODO Change to POST
    if 'token' and 'id' in params:
        token = params['token']
        try:
            decoded = jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error))

        # TODO Check if the user should be able to access the avatar specified

        user_id = params['id']
        try:
            with open('media/avatar-images/%s.jpg' % user_id, 'rb') as image_file:
                encoded = image_file.read().encode('base64')
                return HttpResponse(json.dumps({'image': encoded}))
        except IOError:
            with open('media/avatar-images/default.jpg', 'rb') as image_file:
                encoded = image_file.read().encode('base64')
                return HttpResponse(json.dumps({'image': encoded}))

    else:
        error = create_error(1, 'Insufficient parameters')
        return HttpResponse(json.dumps(error))
    return HttpResponse()


@csrf_exempt
def imageupload(request):
    try:
        params = json.loads(request.body)
    except ValueError:
        error = create_error(1, 'Insufficient parameters')
        return HttpResponse(json.dumps(error))

    image = params['image']
    if 'token' and 'image' in params:
        token = params['token']
        try:
            decoded = jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error))

        subject = decoded['sub']

        if 'file_data' in image:
            image_data = image['file_data']
            with open(os.path.join(os.pardir, 'billsplitter/media/avatar-images/%s.jpg' % subject), 'w+') as fh:
                fh.write(image_data.decode('base64'))
        else:
            error = create_error(1, 'Insufficient parameters')
            return HttpResponse(json.dumps(error))
    else:
        error = create_error(1, 'Insufficient parameters')
        return HttpResponse(json.dumps(error))

    return HttpResponse(json.dumps({'hurray':'yay'}))


def create_error(error_code, error_description):
    return {'Error Code': error_code, 'Description': error_description}
