#  BillSplitter Copyright (C) 2016  Davis Mariotti
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import MySQLdb
import json
import jwt
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


@csrf_exempt  # Allows POST requests without CSRF cookie handling
def index(request):
    params = request.POST
    if all(x in params for x in ['username', 'password']):
        # Login with username and password
        username = params['username']
        password = params['password']
        db = get_db()
        cur = db.cursor()

        sql = """
        SELECT `id`, `username`, password, email, first_name, last_name, phone_number
        FROM BillSplitter.`person`
        WHERE `username`=%s
        """

        cur.execute(sql, (username,))
        results = cur.fetchall()

        db.close()

        if len(results) == 0:
            error = create_error(1, 'Username/password incorrect')
            return HttpResponse(json.dumps(error, indent=4))
        else:
            for row in results:
                if row[1] == username:
                    if password == row[2]:
                        response = {'id': row[0],
                                    'username': row[1],
                                    'token': make_token(row[0]),
                                    'email': row[3],
                                    'firstName': row[4],
                                    'lastName': row[5],
                                    'phoneNumber': row[6]}
                        return HttpResponse(json.dumps(response, indent=4))
            error = create_error(1, 'Username/password incorrect')
            return HttpResponse(json.dumps(error, indent=4), status=401)
    elif 'token' in params:
        # Verify token is valid
        token = params['token']
        try:
            decoded = jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))

        # This point is only reached if no errors are thrown

        db = get_db()
        cur = db.cursor()

        sql = '''
        SELECT `id`, `username`
        FROM person
        WHERE `id` = %s
        '''

        cur.execute(sql, (decoded['sub'],))
        results = cur.fetchall()

        if len(results) == 0:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        else:
            for row in results:
                if row[0] == decoded['sub']:
                    return HttpResponse(json.dumps({'id': row[0]}, indent=4))

    else:
        error = create_error(1, 'Insufficient parameters')
        return HttpResponse(json.dumps(error, indent=4))


def create_error(error_code, error_description):
    return {'Error': {'Code': error_code, 'Description': error_description}}
