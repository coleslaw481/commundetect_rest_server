"""Top-level package for commundetect_rest"""

__author__ = """Chris Churas"""
__email__ = "cchuras@ucsd.edu"
__version__ = "0.3.0"

import os
import shutil
import time
from datetime import datetime
import flask
from flask import Flask, jsonify, request
from flask_restplus import reqparse, Api, Resource, fields, marshal, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

from commundetect_rest.tasks import run_communitydetection
from commundetect_rest.tasks import celeryapp
from celery.result import AsyncResult


desc = """Community Detection REST Service

**NOTE:** This service is experimental. The interface is subject to change.
"""


NETANT_REST_SETTINGS_ENV = 'COMMUNDETECT_REST_SETTINGS'

JOB_PATH_KEY = 'JOB_PATH'
WAIT_COUNT_KEY = 'WAIT_COUNT'
SLEEP_TIME_KEY = 'SLEEP_TIME'
DISKFULL_CUTOFF_KEY = 'DISKFULL_CUTOFF'
DEFAULT_RATE_LIMIT_KEY = 'DEFAULT_RATE_LIMIT'
GET_RATE_LIMIT_KEY = 'GET_RATE_LIMIT'

LOCATION = 'Location'
RESULT = 'result.json'

# used in status endpoint, key
# in json for percentage disk is full
DISKFULL_KEY = "percent_disk_full"

STATUS_RESULT_KEY = 'status'
NOTFOUND_STATUS = 'notfound'
UNKNOWN_STATUS = 'unknown'
SUBMITTED_STATUS = 'submitted'
PROCESSING_STATUS = 'processing'
DONE_STATUS = 'done'
ERROR_STATUS = 'error'

# directory where token files named after tasks to delete
# are stored
DELETE_REQUESTS = 'delete_requests'

# key in result dictionary denoting the
# result data
RESULT_KEY = 'result'

# key in result dictionary denoting input parameters
PARAMETERS_KEY = 'parameters'

COMMUNDETECT_NS = 'cd'

REST_VERSION_KEY = 'rest_version'
ALGO_VERSION_KEY = 'algorithm_version'

REMOTEIP_PARAM = 'remoteip'
ERROR_PARAM = 'error'

# Task specific parameters
ALGO_PARAM = 'algorithm'

EDGE_PARAM = 'edgefile'

EDGE_FILE = 'edgefile.txt'

ROOTNETWORK_PARAM = 'rootnetwork'

GRAPHDIRECTED_PARAM = 'graphdirected'

RESULTKEY_KEY = 'resultkey'
RESULTVALUE_KEY = 'resultvalue'

ACCESS_CONTROL_ALLOW_METHODS = 'Access-Control-Allow-Methods'
uuid_counter = 1

app = Flask(__name__)
app.config[JOB_PATH_KEY] = '/tmp'
app.config[WAIT_COUNT_KEY] = 60
app.config[SLEEP_TIME_KEY] = 10
app.config[DISKFULL_CUTOFF_KEY] = 90
app.config[DEFAULT_RATE_LIMIT_KEY] = '360 per hour'
app.config[GET_RATE_LIMIT_KEY] = '3600 per hour'
app.config.from_envvar(NETANT_REST_SETTINGS_ENV, silent=True)
app.config.SWAGGER_UI_DOC_EXPANSION = 'list'

api = Api(app, version=str(__version__),
          title="Community Detection",
          description=desc,
          example="TODO")

# need to clear out the default namespace
api.namespaces.clear()

ns = api.namespace(
    COMMUNDETECT_NS,
    description='Runs Community Detection'
)

# enable rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=[app.config[DEFAULT_RATE_LIMIT_KEY]],
    headers_enabled=True
)

# add rate limiting logger to the regular app logger
for handler in app.logger.handlers:
    limiter.logger.addHandler(handler)


# enable CORS
CORS(app, origins=r'/*',
     methods=['GET', 'OPTIONS', 'HEAD', 'PUT', 'POST', 'DELETE'],
     allow_headers=['Origin', 'payload', 'Content-Type',
                    'Access-Control-Allow-Headers', 'Authorization',
                    'X-Requested-With'],
     expose_headers=['Location'])


class SimpleTask(object):
    """
    Simple task
    """
    def __init__(self, id):
        """
        Constructor
        """
        self.id = id


""" Creating a parser for the post object """

post_parser = reqparse.RequestParser()
post_parser.add_argument(
    ALGO_PARAM,
    type=str,
    choices=['infomap', 'louvain'],
    help='algorithm to use',
    default='infomap',
    required=True,
    location='form'
)

post_parser.add_argument(
    EDGE_PARAM,
    type=reqparse.FileStorage,
    help='Edge list as file in format of edge1\\tedge2\\nedge3\\tedge4\\n',
    required=True,
    location='files'
)

post_parser.add_argument(
    GRAPHDIRECTED_PARAM,
    type=bool,
    help='If set to True then graph is directed',
    default=False,
    location='form'
)
post_parser.add_argument(
    ROOTNETWORK_PARAM,
    type=str,
    help='Name of root network, will just be returned in result',
    location='form'
)

ERROR_RESP = api.model('ErrorResponseSchema', {
    'errorCode': fields.String(description='Error code to help identify '
                                           'issue'),
    'message': fields.String(description='Human readable description of '
                                         'error'),
    'description': fields.String(description='More detailed description '
                                             'of error'),
    'stackTrace': fields.String(description='stack trace of error'),
    'threadId': fields.String(description='Id of thread running process'),
    'timeStamp': fields.String(description='UTC Time stamp in '
                                           'YYYY-MM-DDTHH:MM.S')
})

TOO_MANY_REQUESTS = api.model('TooManyRequestsSchema', {
    'message': fields.String(description='Contains detailed message '
                                         'about exceeding request limits')
})

RATE_LIMIT_HEADERS = {
 'x-ratelimit-limit': 'Request rate limit',
 'x-ratelimit-remaining': 'Number of requests remaining',
 'x-ratelimit-reset': 'Request rate limit reset time'
}


class ErrorResponse(object):
    """Error response
    """
    def __init__(self):
        """
        Constructor
        """
        self.errorCode = ''
        self.message = ''
        self.description = ''
        self.stackTrace = ''
        self.threadId = ''
        self.timeStamp = ''

        dt = datetime.utcnow()
        self.timeStamp = dt.strftime('%Y-%m-%dT%H:%M.%s')


@api.doc('Runs Community Detection')
@ns.route('/v1', strict_slashes=False)
class TaskBasedRestApp(Resource):
    decorators = [limiter.limit(app.config[DEFAULT_RATE_LIMIT_KEY],
                                per_method=True, methods=['POST'])]
    POST_HEADERS = RATE_LIMIT_HEADERS.copy()
    POST_HEADERS['Location'] = 'URL containing resource/result generated ' \
                               'by this request'

    taskobj = api.model('Task', {
        'id': fields.String(description='id of task')})

    @api.response(202, 'The task was successfully submitted to the service. '
                       'Visit the URL'
                       ' specified in **Location** field in HEADERS to '
                       'status and results', taskobj, headers=POST_HEADERS)
    @api.response(429, 'Too many requests', TOO_MANY_REQUESTS,
                  headers=RATE_LIMIT_HEADERS)
    @api.response(500, 'Internal server error', headers=RATE_LIMIT_HEADERS)
    @api.expect(post_parser)
    def post(self):
        """
        Submits Community Detection task for processing
        """
        app.logger.debug("Post community detection received")

        try:
            params = post_parser.parse_args(request, strict=True)
            res = run_communitydetection.apply_async(args=[params[ALGO_PARAM],
                                                           app.config[JOB_PATH_KEY],
                                                           params[GRAPHDIRECTED_PARAM],
                                                           params[ROOTNETWORK_PARAM]],
                                                     retry=False, expires=120,
                                                     counter=1)

            jobdir = os.path.join(app.config[JOB_PATH_KEY], res.id)
            os.makedirs(jobdir, mode=0o775)

            counter = 0
            while not os.path.exists(jobdir):
                app.logger.debug('Waiting for directory to appear')
                time.sleep(0.1)
                if counter > 10:
                    raise Exception('Even after 10 seconds the directory: ' +
                                    jobdir + ' did not get created')
                counter = counter + 1

            os.chmod(jobdir, mode=0o775)

            edgefile = os.path.join(jobdir, EDGE_FILE)
            edgefiletmp = edgefile + '.tmp'
            with open(edgefiletmp, 'wb') as f:
                shutil.copyfileobj(params[EDGE_PARAM].stream, f)
                f.flush()
            os.chmod(edgefiletmp, mode=0o775)
            shutil.move(edgefiletmp, edgefile)

            task = SimpleTask(res.id)
            return marshal(task, TaskBasedRestApp.taskobj), 202,\
                   {'Location': request.url + '/' + task.id}
        except Exception as ea:
            app.logger.exception('Error creating task due to Exception ' +
                                 str(ea))
            abort(500, 'Unable to create task ' + str(ea))

    @api.hide
    def options(self):
        """
        Lets caller know what what HTTP request types are valid with
        request passed in. Used by CORS.

        :return:
        """
        resp = flask.make_response()
        resp.headers[ACCESS_CONTROL_ALLOW_METHODS] = 'POST, OPTIONS'
        resp.status_code = 204
        return resp


@ns.route('/v1/<string:id>', strict_slashes=False)
class GetTask(Resource):

    STATE_MAP = {'PENDING': 'submitted',
                 'STARTED': 'processing',
                 'PROCESSING': 'processing',
                 'SUCCESS': 'done',
                 'FAILURE': 'done',
                 'RETRY': 'processing',
                 'REVOKED': 'done'}

    decorators = [limiter.limit(app.config[GET_RATE_LIMIT_KEY],
                                per_method=True, methods=['GET', 'DELETE'])]

    @api.response('200', 'Success in asking server, but does not mean'
                         'processing has completed. See the json response'
                         'in body for status', headers=RATE_LIMIT_HEADERS)
    @api.response(429, 'Too many requests', TOO_MANY_REQUESTS,
                  headers=RATE_LIMIT_HEADERS)
    @api.response(500, 'Internal server error', headers=RATE_LIMIT_HEADERS)
    def get(self, id):
        """
        Gets result and status of netant task

        """
        res = celeryapp.AsyncResult(id)
        if res.ready() is True:
            return jsonify(res.get())

        res_dict = {}

        if res.state in GetTask.STATE_MAP:
            statusval = GetTask.STATE_MAP[res.state]
        else:
            statusval = res.state
        res_dict['status'] = statusval

        if res.info is not None:
            for key in res.info.keys():
                res_dict[key] = res.info[key]

        return jsonify(res_dict)

    @api.response(200, 'Delete request successfully received',
                  headers=RATE_LIMIT_HEADERS)
    @api.response(400, 'Invalid delete request',
                  headers=RATE_LIMIT_HEADERS)
    @api.response(429, 'Too many requests', TOO_MANY_REQUESTS,
                  headers=RATE_LIMIT_HEADERS)
    def delete(self, id):
        """
        Deletes task associated with {id} passed in
        """
        resp = flask.make_response()
        try:
            res = AsyncResult(id)
            res.revoke(terminate=True)
            res.forget()
            resp.status_code = 200
            return resp
        except Exception:
            app.logger.exception('Caught exception deleting result')
        resp.status_code = 500
        return resp

    @api.hide
    def options(self, id):
        """
        Lets caller know what what HTTP request types are valid with
        request passed in. Used by CORS.

        :return:
        """
        resp = flask.make_response()
        resp.headers[ACCESS_CONTROL_ALLOW_METHODS] = 'GET, OPTIONS, DELETE'
        resp.status_code = 204
        return resp


class ServerStatus(object):
    """Represents status of server
    """
    def __init__(self):
        """Constructor
        """

        self.status = 'ok'
        self.message = ''
        self.pcDiskFull = 0
        self.load = [0, 0, 0]
        self.restVersion = __version__

        self.pcDiskFull = -1
        try:
            s = os.statvfs('/')
            self.pcDiskFull = int(float(s.f_blocks - s.f_bavail) /
                                  float(s.f_blocks) * 100)
        except Exception:
            app.logger.exception('Caught exception checking disk space')
            self.pcDiskFull = -1

        if self.pcDiskFull >= app.config[DISKFULL_CUTOFF_KEY]:
            self.status = 'error'
            self.message = 'Disk is full'
        else:
            self.status = 'ok'
        loadavg = os.getloadavg()

        self.load[0] = loadavg[0]
        self.load[1] = loadavg[1]
        self.load[2] = loadavg[2]


@ns.route('/v1/status', strict_slashes=False)
class SystemStatus(Resource):
    """
    System status
    """
    statusobj = api.model('StatusSchema', {
        'status': fields.String(description='ok|error'),
        'pcDiskFull': fields.Integer(description='How full disk is in %'),
        'load': fields.List(fields.Float(description='server load'),
                            description='List of 3 floats containing 1 minute,'
                                        ' 5 minute, 15minute load'),
        'restVersion': fields.String(description='Version of REST service')
    })
    @api.doc('Gets status')
    @api.response(200, 'Success', statusobj, headers=RATE_LIMIT_HEADERS)
    @api.response(429, 'Too many requests', TOO_MANY_REQUESTS,
                  headers=RATE_LIMIT_HEADERS)
    @api.response(500, 'Internal server error', ERROR_RESP,
                  headers=RATE_LIMIT_HEADERS)
    def get(self):
        """
        Gets status of service

        """
        ss = ServerStatus()
        return marshal(ss, SystemStatus.statusobj), 200

    @api.hide
    def options(self):
        """
        Lets caller know what what HTTP request types are valid with
        request passed in. Used by CORS.

        :return:
        """
        resp = flask.make_response()
        resp.status_code = 204
        resp.headers[ACCESS_CONTROL_ALLOW_METHODS] = 'GET, OPTIONS'
        return resp
