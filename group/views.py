import MySQLdb
import json
import jwt

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


def index(request):
    return HttpResponse()


@csrf_exempt
def create(request):
    params = request.GET  # TODO POST

    # Check parameters
    if 'token' and 'name' in params:

        # Check token
        token = params['token']
        try:
            decoded = jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error))

        name = params['name']
        admin = decoded["sub"]

        # Create group
        db = get_db()
        cur = db.cursor()
        sql = """
        INSERT INTO `group` (`name`, `admin`)
        VALUES (%s, %s);
        """

        cur.execute(sql, (name, admin))
        db.commit()
        results = cur.fetchall()
        db.close()

        return HttpResponse(results)

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error))


@csrf_exempt
def delete(request):
    params = request.GET  # TODO POST

    # Check parameters
    if 'token' and 'group_id' in params:

        # Variables
        token = params['token']
        group_id = params['group_id']

        # Check token
        try:
            decoded = jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error))

        db = get_db()
        cur = db.cursor()

        # Check if group exists
        sql = """
                SELECT 1
                FROM `group`
                WHERE `id` = %s;
                """

        cur.execute(sql, (group_id,))

        if not cur.rowcount:
            db.close()
            error = create_error(5, 'Group does not exist')
            return HttpResponse(json.dumps(error))

        # Check if current user is a group admin
        sql = """
        SELECT 1
        FROM `group`
        WHERE `admin` = %s;
        """

        user_id = decoded["sub"]
        cur.execute(sql, (user_id,))

        if not cur.rowcount:
            db.close()
            error = create_error(2, 'Invalid admin rights')
            return HttpResponse(json.dumps(error))

        # User has admin rights - delete group
        sql = """
        DELETE FROM `group`
        WHERE `id` = %s;
        """

        cur.execute(sql, (group_id,))
        db.commit()
        results = cur.fetchall()
        db.close()
        return HttpResponse(results)

        error = create_error(5, "Group does not exist")
        return HttpResponse(json.dumps(error))

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error))


@csrf_exempt
def adduser(request):
    params = request.GET  # TODO POST

    # Check parameters
    if 'token' and 'user_id' and 'group_id' in params:

        # Variables
        token = params['token']
        user_id = params['user_id']
        group_id = params['group_id']

        # Check token
        try:
            jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error))

        db = get_db()
        cur = db.cursor()

        # Check if user exists
        sql = """
        SELECT 1
        FROM `person`
        WHERE `id` = %s;
        """

        cur.execute(sql, (user_id,))

        if not cur.rowcount:
            db.close()
            error = create_error(6, 'User does not exist')
            return HttpResponse(json.dumps(error))

        # Check if group exists
        sql = """
        SELECT 1
        FROM `group`
        WHERE `id` = %s;
        """

        cur.execute(sql, (group_id,))

        if not cur.rowcount:
            db.close()
            error = create_error(5, 'Group does not exist')
            return HttpResponse(json.dumps(error))

        # Check if user is already in group
        sql = """
        SELECT 1
        FROM `pg`
        WHERE `personId` = %s and `groupId` = %s;
        """

        cur.execute(sql, (user_id, group_id))

        if cur.rowcount:
            db.close()
            error = create_error(7, 'User already in group')
            return HttpResponse(json.dumps(error))

        # Insert user into group
        sql = """
        INSERT INTO `pg` (`personId`, `groupId`)
        VALUES (%s, %s);
        """

        cur.execute(sql, (user_id, group_id))
        db.commit()
        results = cur.fetchall()
        db.close()

        return HttpResponse(results)

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error))


@csrf_exempt
def removeuser(request):
    params = request.GET  # TODO POST

    # Check parameters
    if 'token' and 'user_id' and 'group_id' in params:

        # Variables
        token = params['token']
        user_id = params['user_id']
        group_id = params['group_id']

        # Check token
        try:
            jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error))

        db = get_db()
        cur = db.cursor()

        # Check if user exists
        sql = """
        SELECT 1
        FROM `person`
        WHERE `id` = %s;
        """

        cur.execute(sql, (user_id,))

        if not cur.rowcount:
            db.close()
            error = create_error(6, 'User does not exist')
            return HttpResponse(json.dumps(error))

        # Check if group exists
        sql = """
        SELECT 1
        FROM `group`
        WHERE `id` = %s;
        """

        cur.execute(sql, (group_id,))

        if not cur.rowcount:
            db.close()
            error = create_error(5, 'Group does not exist')
            return HttpResponse(json.dumps(error))

        # Check if user is in group
        sql = """
        SELECT 1
        FROM `pg`
        WHERE `personId` = %s and `groupId` = %s;
        """

        cur.execute(sql, (user_id, group_id))

        if not cur.rowcount:
            db.close()
            error = create_error(8, 'User not in group')
            return HttpResponse(json.dumps(error))

        # Delete user from group
        sql = """
        DELETE FROM `pg`
        WHERE `personId` = %s and `groupId` = %s;
        """

        cur.execute(sql, (user_id, group_id))
        db.commit()
        results = cur.fetchall()
        db.close()

        return HttpResponse(results)

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error))


def create_error(error_code, error_description):
    return {'Error Code': error_code, 'Description': error_description}