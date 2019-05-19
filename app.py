from flask import *
from flask_pymongo import PyMongo
from flask_restful import Resource, Api, reqparse
import datetime

parser = reqparse.RequestParser()
parser.add_argument('browser', type=str, help='Browser cannot be converted')
parser.add_argument('mobile', type=str, help='Mobile cannot be converted')
parser.add_argument('new', type=bool, help='New cannot be converted')
# parser.add_argument('token', type=str, help='Token cannot be converted')

app = Flask(__name__)
api = Api(app)
mongo = PyMongo(app, uri='mongodb://localhost:27017/charts')

'''
{
    data: {
        '$year' : {
            '$month' : {
                '$day' : {
                    all: Integer,
                    platforms: {
                        $browser: Integer,
                    }
                }, 
            }
        }
    },
    lastUpdate: Date
}
'''


def update(data, browser):
    year = str(data['lastUpdate'].year)
    if year in data['data']:
        month = str(data['lastUpdate'].month)
        if month in data['data'][year]:
            day = str(data['lastUpdate'].day)
            if day in data['data'][year][month]:
                data['data'][year][month][day]['all'] = data['data'][year][month][day]['all'] + 1

                if browser in data['data'][year][month][day]['platforms']:
                    data['data'][year][month][day]['platforms'][browser] = data['data'][year][month][day]['platforms'][browser] + 1
                else:
                    data['data'][year][month][day]['platforms'][browser] = 1

            else:
                data['data'][year][month][day] = {
                    'all': 0,
                    'platforms': {}
                }
                update(data, browser)
        else:
            data['data'][year][month] = {}
            update(data, browser)
    else:
        data['data'][year] = {}
        update(data, browser)


class Charts(Resource):
    def get(self):
        ret = mongo.db['col'].find_one({'lastUpdate': {'$exists': True}})
        del ret['_id']
        del ret['lastUpdate']

        if request.args.get('token') == 'token':
            return ret

        return {'status': 'failed', 'error': str(request.args.get('token'))}, 201

    def put(self):
        col = mongo.db['col']
        args = parser.parse_args()

        if args['new']:
            data = col.find_one({'lastUpdate': {'$exists': True}})
            replace = True
            if data == None: 
                data = {
                    'lastUpdate': 0,
                    'data': {

                    }
                }
                replace = False

            data['lastUpdate'] = datetime.datetime.utcnow()

            update(data, str(args['browser']))

            try:
                if replace:
                    col.replace_one({'_id': data['_id']}, data)
                else:
                    col.insert(data)
            except Exception as e:
                return {'status': 'failed', 'error': str(e)}, 201

        return {'status': 'ok'}


api.add_resource(Charts, '/charts')


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers',
                         'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT')
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
