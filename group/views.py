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
    params = request.POST

    # Check parameters
    if all(x in params for x in ['token', 'name']):

        # Decode token and verify
        token = params['token']
        try:
            decoded = jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))

        name = params['name']
        admin = decoded["sub"]

        db = get_db()
        cur = db.cursor()

        # Create a group
        sql = """
        INSERT INTO `group` (`name`, `admin`)
        VALUES (%s, %s);
        """

        cur.execute(sql, (name, admin))
        db.commit()

        # Get the id of the created group
        sql = """
        SELECT LAST_INSERT_ID()
        FROM `group`
        """

        cur.execute(sql)

        results = cur.fetchall()
        cur.close()
        db.close()

        return HttpResponse(json.dumps({'id': results[0][0]}, indent=4))

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


@csrf_exempt
def delete(request):
    params = request.POST

    # Check parameters
    if all(x in params for x in ['token', 'group_id']):

        # Variables
        token = params['token']
        group_id = params['group_id']

        # Decode token and verify
        try:
            decoded = jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))

        db = get_db()
        cur = db.cursor()

        # SQL: Check if group exists
        sql = """
                SELECT 1
                FROM `group`
                WHERE `id` = %s;
                """

        cur.execute(sql, (group_id,))

        # Check if the group exists
        if not cur.rowcount:
            db.close()
            error = create_error(5, 'Group does not exist')
            return HttpResponse(json.dumps(error, indent=4))

        # SQL: Check if current user is a group admin
        sql = """
        SELECT 1
        FROM `group`
        WHERE `admin` = %s;
        """

        # Get the user id from the token
        user_id = decoded['sub']
        cur.execute(sql, (user_id,))

        # Check if the user is an admin
        if not cur.rowcount:
            db.close()
            error = create_error(2, 'Invalid admin rights')
            return HttpResponse(json.dumps(error, indent=4))

        # SQL: Get the number of users in the group to check if it is empty
        sql = """
        SELECT COUNT(*)
        FROM pg
        WHERE groupId=%s;
        """

        cur.execute(sql, (group_id,))
        results = cur.fetchall()

        # Check if the group is empty
        num = results[0][0]
        if num != 1:  # The admin should be the only one in the group
            db.close()
            error = create_error(6, 'Group is not empty')
            return HttpResponse(json.dumps(error, indent=4))

        # User has admin rights
        # SQL: Delete the group
        sql = """
        DELETE FROM `group`
        WHERE `id` = %s;
        """

        cur.execute(sql, (group_id,))
        db.commit()
        cur.close()
        db.close()
        return HttpResponse(json.dumps({'Result': 'Success'}, indent=4))

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


@csrf_exempt
def adduser(request):
    params = request.POST

    # Check parameters
    if all(x in params for x in ['token', 'userId', 'groupId']):

        # Variables
        token = params['token']

        try:
            # Convert to integers
            user_id = int(params['userId'])
            group_id = int(params['groupId'])
        except ValueError:
            error = create_error(1, 'Invalid parameters')
            return HttpResponse(json.dumps(error, indent=4))

        # Decode token and verify
        try:
            jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))

        db = get_db()
        cur = db.cursor()

        # SQL: Check if user exists
        sql = """
        SELECT 1
        FROM `person`
        WHERE `id` = %s;
        """

        cur.execute(sql, (user_id,))

        # SQL: Check if user exists
        if not cur.rowcount:
            db.close()
            error = create_error(6, 'User does not exist')
            return HttpResponse(json.dumps(error, indent=4))

        # Check if group exists and get status data
        sql = """
        SELECT status
        FROM `group`
        WHERE `id` = %s;
        """

        cur.execute(sql, (group_id,))

        # Check if group exists
        if not cur.rowcount:
            db.close()
            error = create_error(5, 'Group does not exist')
            return HttpResponse(json.dumps(error))

        group_result = cur.fetchall()[0]

        # SQL: Check if user is already in group
        sql = """
        SELECT 1
        FROM `pg`
        WHERE `personId` = %s and `groupId` = %s;
        """

        cur.execute(sql, (user_id, group_id))

        # Check if the user is already in the group
        if cur.rowcount:
            db.close()
            error = create_error(7, 'User already in group')
            return HttpResponse(json.dumps(error, indent=4))

        # SQL: Insert user into group
        sql = """
        INSERT INTO `pg` (`personId`, `groupId`)
        VALUES (%s, %s);
        """

        cur.execute(sql, (user_id, group_id))

        # Update status
        statuses = json.loads(group_result[0])
        has_user = False
        ids = []
        for status_ in statuses:
            if status_['id'] == user_id:
                has_user = True
                continue

            # Check if contains specific recipient
            contains = False
            for recipient_set in status_['data']:
                if recipient_set['recipient'] == user_id:
                    contains = True
            # Don't change anything if the user already has some data
            if contains:
                break
            status_['data'].append({'recipient': user_id, 'amount': 0.00})
            ids.append(status_['id'])

        if not has_user:
            # Create new status data for users
            new_data = []
            for id_ in ids:
                new_data.append({'recipient': id_, 'amount': 0.00})
            statuses.append({'id': user_id, 'data': new_data})

        # SQL: Update status data in the group
        sql = '''
        UPDATE `group`
        SET status = %s
        WHERE id = %s
        '''

        cur.execute(sql, (json.dumps(statuses), group_id))
        db.commit()
        cur.close()
        db.close()

        return HttpResponse(json.dumps({"Result": "Success"}, indent=4))

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


@csrf_exempt
def removeuser(request):
    params = request.POST

    # Check parameters
    if all(x in params for x in ['token', 'userId', 'groupId']):

        # Variables
        token = params['token']
        user_id = params['userId']
        group_id = params['groupId']

        # Decode token and verify
        try:
            jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))

        db = get_db()
        cur = db.cursor()

        # SQL: Check if user exists
        sql = """
        SELECT 1
        FROM `person`
        WHERE `id` = %s;
        """

        cur.execute(sql, (user_id,))

        # Check if user exists
        if not cur.rowcount:
            db.close()
            error = create_error(6, 'User does not exist')
            return HttpResponse(json.dumps(error, indent=4))

        # SQL: Check if the group exists
        sql = """
        SELECT 1
        FROM `group`
        WHERE `id` = %s;
        """

        cur.execute(sql, (group_id,))

        # Check if the group exists
        if not cur.rowcount:
            db.close()
            error = create_error(5, 'Group does not exist')
            return HttpResponse(json.dumps(error, indent=4))

        # SQL: Check if user is in group
        sql = """
        SELECT 1
        FROM `pg`
        WHERE `personId` = %s and `groupId` = %s;
        """

        cur.execute(sql, (user_id, group_id))

        if not cur.rowcount:
            db.close()
            error = create_error(8, 'User not in group')
            return HttpResponse(json.dumps(error, indent=4))

        # SQL: Delete user from group
        sql = """
        DELETE FROM `pg`
        WHERE `personId` = %s and `groupId` = %s;
        """

        cur.execute(sql, (user_id, group_id))
        db.commit()
        db.close()

        return HttpResponse(json.dumps({'Result': 'Success'}, indent=4))

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


@csrf_exempt
def info(request):
    params = request.POST

    # Check parameters
    if all(x in params for x in ['token', 'userId']):

        token = params['token']
        user_id = params['userId']

        # Decode token and verify
        try:
            jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))

        db = get_db()
        cur = db.cursor()

        # SQL: Get all group data that the user belongs to
        sql = """
              SELECT id, `name`, status
              FROM `pg`
              JOIN `group`
              WHERE pg.personId = %s
              AND pg.groupId = `group`.id;
        """

        cur.execute(sql, (user_id,))
        results = cur.fetchall()
        response = []

        # Build JSON dictionary with all group, transaction and user information
        for result in results:
            id_ = result[0]
            name = result[1]
            status_ = json.loads(result[2])

            # SQL: Get transaction data in each group
            sql = """
            SELECT payee, amount, split, description, date
            FROM transaction
            WHERE groupId = %s;
            """

            cur.execute(sql, (id_,))
            results_ = cur.fetchall()

            transactions = []

            for result_ in results_:
                transactions.append({'payee': result_[0],
                                     'amount': result_[1],
                                     'split': json.loads(result_[2]),
                                     'description': result_[3],
                                     'date': result_[4].strftime('%Y-%m-%d')})

            # SQL: Get a list of other members in the group
            sql = """
            SELECT personId
            FROM pg
            WHERE groupId = %s;
            """

            cur.execute(sql, (id_,))
            results_ = cur.fetchall()

            members = []

            for result_ in results_:
                members.append(result_[0])

            dict_ = {
                'id': id_,
                'name': name,
                'status': status_,
                'transactions': transactions,
                'members': members
            }
            response.append(dict_)

        db.close()

        return HttpResponse(json.dumps(response, indent=4))

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


@csrf_exempt
def status(request):
    params = request.POST
    if all(x in params for x in ['token', 'groupId']):
        token = params['token']
        group_id = params['groupId']

        # Decode token and verify
        try:
            jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))

        db = get_db()
        cur = db.cursor()

        # SQL: Get the status of the specified group
        sql = """
        SELECT status
        FROM `group`
        WHERE id=%s;
        """

        cur.execute(sql, (group_id,))

        results = cur.fetchall()

        # Check if the group exists
        if len(results) == 0:
            error = create_error(2, "Group does not exist")
            return HttpResponse(json.dumps(error, indent=4))

        return HttpResponse(json.dumps({'id': group_id, 'status': json.loads(results[0][0])}, indent=4))
    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


def create_error(error_code, error_description):
    return {'Error': {'Code': error_code, 'Description': error_description}}
