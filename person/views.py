import MySQLdb
import json
import jwt
import os
from datetime import datetime, timedelta

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables

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
    return HttpResponse(json.dumps({'id': person}, indent=4))


@csrf_exempt
def avatar(request):
    params = request.POST
    if all(x in params for x in ['token', 'id']):
        token = params['token']
        try:
            decoded = jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))

        # subject = decoded['sub']

        # TODO Check if the user should be able to access the avatar specified

        user_id = params['id']
        try:
            with open('media/avatar-images/%s.jpg' % user_id, 'rb') as image_file:
                encoded = image_file.read().encode('base64')
                return HttpResponse(json.dumps({'image': encoded}, indent=4))
        except IOError:
            with open('media/avatar-images/default.jpg', 'rb') as image_file:
                encoded = image_file.read().encode('base64')
                return HttpResponse(json.dumps({'image': encoded}, indent=4))
    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


@csrf_exempt
def imageupload(request):
    try:
        params = json.loads(request.body)
    except ValueError:
        error = create_error(1, 'Insufficient parameters')
        return HttpResponse(json.dumps(error))

    image = params['image']
    if all(x in params for x in ['token', 'image']):
        token = params['token']
        try:
            decoded = jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))

        subject = decoded['sub']

        if 'file_data' in image:
            image_data = image['file_data']
            with open(os.path.join(os.pardir, 'billsplitter/media/avatar-images/%s.jpg' % subject), 'w+') as fh:
                fh.write(image_data.decode('base64'))
        else:
            error = create_error(1, 'Insufficient parameters')
            return HttpResponse(json.dumps(error, indent=4))
    else:
        error = create_error(1, 'Insufficient parameters')
        return HttpResponse(json.dumps(error, indent=4))

    return HttpResponse(json.dumps({'hurray': 'yay'}, indent=4))


@csrf_exempt
def info(request):
    params = request.POST
    if all(x in params for x in ['token', 'userIds']):
        token = params['token']
        try:
            decoded = jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))

        try:
            ids = json.loads(params['userIds'])
        except ValueError:
            error = create_error(1, 'Invalid parameters')
            return HttpResponse(json.dumps(error, indent=4))

        db = get_db()
        cur = db.cursor()

        sql_tuple = ()
        sql_commas = ""
        for id_ in ids:
            sql_commas += "%s, "
            sql_tuple += (str(id_),)
        sql_commas = sql_commas[:-2]

        sql = """
        SELECT id, username, first_name, last_name, email, phonenumber
        FROM person
        WHERE id IN (""" + sql_commas + """);
        """

        cur.execute(sql, sql_tuple)
        results = cur.fetchall()

        people = []

        for result in results:
            people.append({'id': result[0],
                           'username': result[1],
                           'first_name': result[2],
                           'last_name': result[3],
                           'email': result[4],
                           'phonenumber': result[5]})

        return HttpResponse(json.dumps(people, indent=4))

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


@csrf_exempt
def exists(request):
    params = request.POST
    if all(x in params for x in ['token', 'username']):

        username = params['username']
        token = params['token']

        try:
            decoded = jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))

        sql = """
        SELECT id
        FROM person
        WHERE username=%s;
        """

        db = get_db()
        cur = db.cursor()
        cur.execute(sql, (username,))

        results = cur.fetchall()

        db.close()
        cur.close()

        if len(results) == 0:
            error = create_error(2, "User does not exist")
            return HttpResponse(json.dumps(error, indent=4))
        else:
            return HttpResponse(json.dumps({"id": results[0][0]}, indent=4))

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


@sensitive_variables('email', 'password')
@sensitive_post_parameters('email', 'password')
@csrf_exempt
def createuser(request):
    params = request.POST
    if all(x in params for x in ['first_name', 'last_name', 'username', 'email', 'phonenumber', 'password']):
        # Variables
        first_name = params['first_name']
        last_name = params['last_name']
        username = params['username'].lower()
        email = params['email'].lower()
        phone_number = params['phonenumber'].lower()
        password = params['password']

        db = get_db()
        cur = db.cursor()

        # Check if username is taken
        sql = """
        SELECT `username`
        FROM `BillSplitter`.`person`
        WHERE `username` = %s
        """

        cur.execute(sql, (username,))
        results = cur.fetchall()

        for row in results:
            if row[0] == username:  # User exists
                return HttpResponse(json.dumps(create_error(2, 'User already exists'), indent=4))

        # Username is not taken

        sql = """
        INSERT INTO `person` (`username`, `password`, `first_name`, `last_name`, `email`, `phonenumber`)
        VALUES (%s, %s, %s, %s, %s, %s);
        """

        cur.execute(sql, (username, password, first_name, last_name, email, phone_number))
        db.commit()
        results = cur.fetchall()
        db.close()

        return HttpResponse(results)

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


@csrf_exempt
def update(request):
    params = request.POST

    # Check token
    if 'token' in params:
        token = params['token']
        try:
            decoded = jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))
    else:
        error = create_error(1, 'Insufficient parameters')
        return HttpResponse(json.dumps(error, indent=4))

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
        return HttpResponse(json.dumps(error, indent=4))

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

    cur.execute(sql, sql_tuple)
    db.commit()

    return HttpResponse(json.dumps({'Result': 'Success!'}, indent=4))


def create_error(error_code, error_description):
    return {'Error': {'Code': error_code, 'Description': error_description}}
