import json
import jwt
import MySQLdb
from django.http import HttpResponse

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


def index(request):
    return HttpResponse()


def new(request):
    params = request.GET  # TODO Change to POST
    if ('token'
            and 'groupId'
            and 'payee'
            and 'split'
            and 'amount'
            and 'date'
            and 'description' in params):

        # Get parameters
        token = params['token']
        group_id = params['groupId']
        payee = params['payee']
        split = params['split']
        transaction_amount = params['amount']
        date = params['date']
        description = params['description']

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

        amount_to_pay = {}

        # Calculate how much each person should pay
        for user_id in split:
            amount_to_pay[user_id] = transaction_amount * split[user_id]

        # Modify group
        group_sql = '''
        SELECT `status`
        FROM `group`
        WHERE `id` = %s
        '''

        cur.execute(group_sql, (group_id,))
        results = cur.fetchall()

        if len(results) == 0:
            return HttpResponse("No results!")  # TODO

        status_array = json.loads(results[0][0])
        new_status = []

        for i in range(0, len(status_array)):
            status = status_array[i]
            status_data = status['data']
            if status['id'] == payee:
                for j in range(0, len(status_data)):
                    recipient = status_data[j]['amount']
                    if recipient in amount_to_pay:
                        amount = status_data[j]['amount']
                        amount -= amount_to_pay[recipient]
                        status_data[j]['amount'] = amount
            else:
                for j in range(0, len(status_data)):
                    recipient = status_data[j]['amount']
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
        cur.execute(group_sql, (group_id,))

        db.commit()

    return HttpResponse()


def payback(request):
    return HttpResponse()


def history(request):
    params = request.GET
    if 'token' and 'groupId' in params:

        token = params['token']
        try:
            group_id = params['groupId']
        except ValueError:
            error = create_error(1, 'Invalid parameters')
            return HttpResponse(json.dumps(error))

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
                                      result[2], result[3],
                                      result[4], result[5])
            transactions.append(transaction.output())

        data['transactions'] = transactions
        return HttpResponse(json.dumps(data))

    error = create_error(1, 'Insufficient parameters')
    return HttpResponse(json.dumps(error))


def create_error(error_code, error_description):
    return {'Error Code': error_code, 'Description': error_description}
