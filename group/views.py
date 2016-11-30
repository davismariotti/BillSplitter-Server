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
    if all(x in params for x in ['token', 'name']):

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

        sql = """
        SELECT LAST_INSERT_ID()
        FROM `group`
        """

        cur.execute(sql)

        results = cur.fetchall()
        cur.close()
        db.close()

        return HttpResponse(json.dumps({'id': results[0][0]}))

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

        user_id = decoded['sub']
        cur.execute(sql, (user_id,))

        if not cur.rowcount:
            db.close()
            error = create_error(2, 'Invalid admin rights')
            return HttpResponse(json.dumps(error))

        # TODO Check if group is empty?

        # User has admin rights - delete group
        sql = """
        DELETE FROM `group`
        WHERE `id` = %s;
        """

        cur.execute(sql, (group_id,))
        db.commit()
        results = cur.fetchall()
        cur.close()
        db.close()
        return HttpResponse(results)

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error))


@csrf_exempt
def adduser(request):
    params = request.GET  # TODO POST

    # Check parameters
    if all(x in params for x in ['token', 'user_id', 'group_id']):

        # Variables
        token = params['token']

        try:
            user_id = int(params['user_id'])
            group_id = int(params['group_id'])
        except ValueError:
            error = create_error(1, 'Invalid parameters')
            return HttpResponse(json.dumps(error))

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
        SELECT status
        FROM `group`
        WHERE `id` = %s;
        """

        cur.execute(sql, (group_id,))

        if not cur.rowcount:
            db.close()
            error = create_error(5, 'Group does not exist')
            return HttpResponse(json.dumps(error))

        group_result = cur.fetchall()[0]

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

        # Update status
        statuses = json.loads(group_result[0])
        has_user = False
        ids = []
        for status in statuses:
            if status['id'] == user_id:
                has_user = True
                continue

            # Check if contains specific recipient
            contains = False
            for recipient_set in status['data']:
                if recipient_set['recipient'] == user_id:
                    contains = True
            # Don't change anything if the user already has some data
            if contains:
                break
            status['data'].append({'recipient': user_id, 'amount': 0.00})
            ids.append(status['id'])

        if not has_user:
            new_data = []
            for id_ in ids:
                new_data.append({'recipient': id_, 'amount': 0.00})
            statuses.append({'id': user_id, 'data': new_data})

        sql = '''
        UPDATE `group`
        SET status = %s
        WHERE id = %s
        '''

        cur.execute(sql, (json.dumps(statuses), group_id))
        db.commit()
        cur.close()
        db.close()

        return HttpResponse()

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
