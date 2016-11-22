import MySQLdb
import json
import jwt
import os
from datetime import datetime, timedelta

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

f = open('../secrets.JSON', 'r')
secrets = json.load(f)

secret = secrets['secret']


def get_db():
    return MySQLdb.connect(host=secrets['host'],
                           user=secrets['user'],
                           passwd=secrets['passwd'],
                           db=secrets['db'])


def make_token(sub):
    payload = {'sub': sub,
               'iat': datetime.utcnow(),
               'exp': datetime.utcnow() + timedelta(days=30)}
    return jwt.encode(payload, secret, algorithm='HS256')

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


@csrf_exempt
def createuser(request):
    params = request.GET  # TODO POST
    if 'fname' and 'lname' and 'username' and 'email' and 'phonenumber' and 'password' in params:
        # TODO Sanitize input

        db = get_db()
        cur = db.cursor()
        sql = """
        INSERT INTO `person` (`username`, `password`, `first_name`, `last_name`, `email`, `phonenumber`)
        VALUES (%s, %s, %s, %s, %s, %s);
        """

        cur.execute(sql, (params['username'], params['password'], params['fname'],
                          params['lname'], params['email'], params['phonenumber']))
        db.commit()
        results = cur.fetchall()
        db.close()

        return HttpResponse(results)
    else:
        error = create_error(1, 'Insufficient parameters')
        return HttpResponse(json.dumps(error))

    return HttpResponse()


@csrf_exempt
def update(request):
    params = request.GET  # TODO POST

    # Check token
    if 'token' in params:
        token = params['token']
        try:
            decoded = jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error))
    else:
        error = create_error(1, 'Insufficient parameters')
        return HttpResponse(json.dumps(error))

    subject = decoded['sub']

    # Tuple with parameters to update
    sql_tuple = ()

    # Build sql query
    sql_set = ''
    if 'first_name' in params:
        sql_set += '`first_name`=%s, '
        sql_tuple += (params['first_name'],)
    if 'last_name' in params:
        sql_set += '`last_name`=%s, '
        sql_tuple += (params['last_name'],)
    if 'email' in params:
        sql_set += '`email`=%s, '
        sql_tuple += (params['email'],)
    if 'phonenumber' in params:
        sql_set += '`phonenumber`=%s, '
        sql_tuple += (params['phonenumber'],)
    if 'password' in params:
        sql_set += '`password`=%s, '
        sql_tuple += (params['password'],)

    sql_tuple += (subject,)

    # If no parameters are given, no update needs to be done
    if sql_set == '':
        error = create_error(1, 'Insufficient parameters')
        return HttpResponse(json.dumps(error))

    # Remove trailing comma
    sql_set = sql_set[:-2]

    # Get the connection
    db = get_db()
    cur = db.cursor()

    # Build full query
    sql = """
    UPDATE `BillSplitter`.`person`
    SET """ + sql_set + """
    WHERE `id` = %s
    """

    print sql
    print sql_tuple

    cur.execute(sql, sql_tuple)
    db.commit()

    return HttpResponse(json.dumps({'Result': 'Success!'}))


def create_error(error_code, error_description):
    return {'Error Code': error_code, 'Description': error_description}
