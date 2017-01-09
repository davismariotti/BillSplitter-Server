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


# Returns base64 avatar image for user
# Takes user id and token as params
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

        try:
            user_id = int(params['id'])
        except ValueError:
            error = create_error(1, 'Invalid parameters')
            return HttpResponse(json.dumps(error, indent=4))

        subject = decoded['sub']

        # SQL: Get all groups that a user belongs to
        # then get all users in all of those groups
        sql = """
        SELECT DISTINCT `personId`
        FROM (
            SELECT `pg`.`groupId`
            FROM `pg`
            WHERE `pg`.`personId` = %s
        ) t2 INNER JOIN `pg`
        ON t2.`groupId` = `pg`.`groupId`
        """

        db = get_db()
        cur = db.cursor()

        cur.execute(sql, (subject,))
        results = cur.fetchall()

        users = []

        for result in results:
            users.append(result[0])

        if user_id not in users:
            error = create_error(2, 'Unauthorized')
            return HttpResponse(json.dumps(error, indent=4))

        cur.close()
        db.close()

        try:  # Get the image from file
            with open('media/avatar-images/%s.jpg' % user_id, 'rb') as image_file:
                encoded = image_file.read().encode('base64')
                return HttpResponse(json.dumps({'image': encoded}, indent=4))
        except IOError:  # Get default image
            with open('media/avatar-images/default.jpg', 'rb') as image_file:
                encoded = image_file.read().encode('base64')
                return HttpResponse(json.dumps({'image': encoded}, indent=4))
    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


# Stores avatar image from base64 data
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

        # Decode token and verify
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
            # Write image data to file
            with open(os.path.join(os.pardir, 'billsplitter/media/avatar-images/%s.jpg' % subject), 'w+') as fh:
                fh.write(image_data.decode('base64'))
        else:
            error = create_error(1, 'Insufficient parameters')
            return HttpResponse(json.dumps(error, indent=4))
    else:
        error = create_error(1, 'Insufficient parameters')
        return HttpResponse(json.dumps(error, indent=4))

    return HttpResponse(json.dumps({'hurray': 'yay'}, indent=4))


# Retrieves user information for multiple users
# Takes userIds and token as params
@csrf_exempt
def info(request):
    params = request.POST
    if all(x in params for x in ['token', 'userIds']):
        token = params['token']

        # Decode token and verify
        try:
            jwt.decode(token, secret)
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

        # SQL: Retrieve user information for all users in the userIds list
        sql = """
        SELECT id, username, first_name, last_name, email, phone_number
        FROM person
        WHERE id IN (""" + sql_commas + """);
        """

        cur.execute(sql, sql_tuple)
        results = cur.fetchall()

        people = []

        for result in results:
            # Build JSON dictionary for 'people'
            people.append({'id': result[0],
                           'username': result[1],
                           'first_name': result[2],
                           'last_name': result[3],
                           'email': result[4],
                           'phoneNumber': result[5]})

        return HttpResponse(json.dumps(people, indent=4))

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


@csrf_exempt
def exists(request):
    params = request.POST
    if all(x in params for x in ['token', 'username']):
        username = params['username']
        token = params['token']

        # Decode token and verify
        try:
            jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))

        # SQL: Retrieve the id from a person with a certain username
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

        # Determine if the user exists
        if len(results) == 0:
            error = create_error(2, "User does not exist")
            return HttpResponse(json.dumps(error, indent=4))
        else:
            # Return the user's id if so
            return HttpResponse(json.dumps({"id": results[0][0]}, indent=4))

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


# Creates a new user
@sensitive_variables('email', 'password')
@sensitive_post_parameters('email', 'password')
@csrf_exempt
def create(request):
    params = request.POST
    if all(x in params for x in ['firstName', 'lastName', 'username', 'email', 'phoneNumber', 'password']):

        # Get variables
        first_name = params['firstName']
        last_name = params['lastName']
        username = params['username'].lower()
        email = params['email'].lower()
        phone_number = params['phoneNumber'].lower()
        password = params['password']

        db = get_db()
        cur = db.cursor()

        # SQL: Check if username is taken
        sql = """
        SELECT `username`
        FROM `BillSplitter`.`person`
        WHERE `username` = %s
        """

        cur.execute(sql, (username,))
        results = cur.fetchall()

        for row in results:
            if row[0] == username:  # Username already exists
                return HttpResponse(json.dumps(create_error(2, 'Username taken'), indent=4))

        # Username is not taken

        # SQL: Add a new person to the table with specified data
        sql = """
        INSERT INTO `person` (`username`, `password`, `first_name`, `last_name`, `email`, `phone_number`)
        VALUES (%s, %s, %s, %s, %s, %s);
        """

        cur.execute(sql, (username, password, first_name, last_name, email, phone_number))
        db.commit()

        # SQL: Get the id of the user created
        sql = """
        SELECT LAST_INSERT_ID()
        FROM `person`
        """

        cur.execute(sql)

        results = cur.fetchall()
        cur.close()
        db.close()

        return HttpResponse(json.dumps({'id': results[0][0], 'token': make_token(results[0][0])}, indent=4))

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


# Update account information for user
# Takes token as param
@csrf_exempt
def update(request):
    params = request.POST

    # Decode token and verify
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
    # Update user information depending on which attributes specified
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
    if 'phoneNumber' in params:
        sql_set += '`phone_number`=%s, '
        sql_tuple += (params['phoneNumber'],)
    if 'password' in params:
        sql_set += '`password`=%s, '
        sql_tuple += (params['password'],)

    # Add the subject as a parameter to the SQL query
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
    # Update user information for specified data
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
