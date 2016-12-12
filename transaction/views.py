import json
import jwt
import MySQLdb
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

f = open('../secrets.JSON', 'r')
secrets = json.load(f)

secret = secrets['secret']


class Transaction:
    def __init__(self, payee, group_id, amount, split, description, date):
        self.payee = payee
        self.group_id = group_id
        self.amount = amount
        self.split = split
        self.description = description
        self.date = date

    def output(self):
        return {
            'payee': self.payee,
            'groupId': self.group_id,
            'amount': self.amount,
            'split': self.split,
            'description': self.description,
            'date': self.date.strftime('%Y-%m-%d')
        }


def get_db():
    return MySQLdb.connect(host=secrets['host'],
                           user=secrets['user'],
                           passwd=secrets['passwd'],
                           db=secrets['db'])


@csrf_exempt
def index(request):
    return HttpResponse()


@csrf_exempt
def new(request):
    params = request.POST
    if all(x in params for x in ['token', 'groupId', 'payee', 'split', 'amount', 'date', 'description']):

        # Get parameters
        try:
            token = params['token']
            split = params['split']
            json_split = json.loads(split)
            date = params['date']
            description = params['description']
        except ValueError:
            error = create_error(1, 'Invalid parameters')
            return HttpResponse(json.dumps(error))

        try:
            jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))

        try:
            group_id = int(params['groupId'])
            payee = int(params['payee'])
            transaction_amount = float(params['amount'])
        except ValueError:
            error = create_error(1, 'Invalid parameters')
            return HttpResponse(json.dumps(error, indent=4))

        db = get_db()
        cur = db.cursor()

        amount_to_pay = {}

        # Calculate how much each person should pay
        try:
            for user_id in json_split:
                amount_to_pay[int(user_id)] = transaction_amount * float(json_split[user_id])/100
        except ValueError:
            error = create_error(1, 'Invalid parameters')
            return HttpResponse(json.dumps(error, indent=4))

        # Modify group
        group_sql = '''
        SELECT `status`
        FROM `group`
        WHERE `id` = %s
        '''

        cur.execute(group_sql, (group_id,))
        results = cur.fetchall()

        if len(results) == 0:
            return HttpResponse("No results!")

        status_array = json.loads(results[0][0])
        new_status = []

        for i in range(0, len(status_array)):
            status = status_array[i]
            status_data = status['data']
            if status['id'] == payee:
                for j in range(0, len(status_data)):
                    recipient = status_data[j]['recipient']
                    if recipient in amount_to_pay:
                        amount = status_data[j]['amount']
                        amount -= amount_to_pay[recipient]
                        status_data[j]['amount'] = amount
            else:
                for j in range(0, len(status_data)):
                    recipient = status_data[j]['recipient']
                    if recipient == payee:
                        amount = status_data[j]['amount']
                        if amount is None:
                            amount = 0.0
                        amount += amount_to_pay[status['id']]
                        status_data[j]['amount'] = amount
            status['data'] = status_data
            new_status.append(status)
        status_string = json.dumps(new_status)

        transaction_sql = '''
        INSERT INTO `transaction` (`payee`, `groupId`, `amount`, `split`, `description`, `date`)
        VALUES (%s, %s, %s, %s, %s, %s)
        '''

        cur.execute(transaction_sql, (payee, group_id, transaction_amount, split, description, date))

        update_sql = '''
        UPDATE `group`
        SET status=%s
        WHERE id=%s
        '''

        cur.execute(update_sql, (status_string, group_id))

        db.commit()
        db.close()
        return HttpResponse()
    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


@csrf_exempt
def payback(request):
    params = request.POST
    if all(x in params for x in ['token', 'groupId', 'from', 'to', 'amount']):
        token = params['token']
        group_id = params['groupId']

        try:
            jwt.decode(token, secret)
        except jwt.DecodeError:
            error = create_error(3, 'Invalid token')
            return HttpResponse(json.dumps(error, indent=4))
        except jwt.ExpiredSignatureError:
            error = create_error(4, 'Token expired')
            return HttpResponse(json.dumps(error, indent=4))

        try:
            from_id = int(params['from'])
            to_id = int(params['to'])
            transaction_amount = float(params['amount'])
        except ValueError:
            error = create_error(1, 'Invalid parameters')
            return HttpResponse(json.dumps(error, indent=4))

        db = get_db()
        cur = db.cursor()

        # Modify group
        group_sql = '''
        SELECT `status`
        FROM `group`
        WHERE `id` = %s
        '''

        cur.execute(group_sql, (group_id,))
        results = cur.fetchall()

        if len(results) == 0:
            return HttpResponse(json.dumps(create_error(2, "Group does not exist"), indent=4))

        status_array = json.loads(results[0][0])
        new_status = []

        for i in range(0, len(status_array)):
            status = status_array[i]
            status_data = status['data']
            if status['id'] == int(to_id):
                for j in range(0, len(status_data)):
                    recipient = status_data[j]['recipient']
                    if recipient == from_id:
                        amount = status_data[j]['amount']
                        amount -= transaction_amount
                        status_data[j]['amount'] = amount
            elif status['id'] == int(from_id):
                for j in range(0, len(status_data)):
                    recipient = status_data[j]['recipient']
                    if recipient == to_id:
                        amount = status_data[j]['amount']
                        amount += transaction_amount
                        status_data[j]['amount'] = amount
            status['data'] = status_data
            new_status.append(status)
        status_string = json.dumps(new_status)

        update_sql = '''
        UPDATE `group`
        SET status=%s
        WHERE id=%s
        '''

        cur.execute(update_sql, (status_string, group_id))
        db.commit()
        db.close()
        return HttpResponse(json.dumps(new_status, indent=4))

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


@csrf_exempt
def history(request):
    params = request.POST
    if all(x in params for x in ['token', 'groupId']):
        token = params['token']
        group_id = params['groupId']

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

        sql = '''
        SELECT payee, groupId, amount, split, description, date
        FROM transaction
        WHERE groupId = %s
        '''

        cur.execute(sql, (group_id,))

        results = cur.fetchall()

        data = {}
        amount = len(results)
        data['amount'] = amount

        transactions = []

        for result in results:
            transaction = Transaction(result[0], result[1],
                                      result[2], json.loads(result[3]),
                                      result[4], result[5])
            transactions.append(transaction.output())

        data['transactions'] = transactions
        return HttpResponse(json.dumps(data, indent=4))

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error, indent=4))


def create_error(error_code, error_description):
    return {'Error': {'Code': error_code, 'Description': error_description}}
