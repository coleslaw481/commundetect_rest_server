#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `commundetect_rest_server` package."""

import os
import json
import unittest
import shutil
import tempfile
import io
import uuid
import re
from werkzeug.datastructures import FileStorage
import commundetect_rest


class TestDdot_rest(unittest.TestCase):
    """Tests for `commundetect_rest` package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        self._temp_dir = tempfile.mkdtemp()
        commundetect_rest.app.testing = True
        commundetect_rest.app.config[commundetect_rest.JOB_PATH_KEY] = self._temp_dir
        commundetect_rest.app.config[commundetect_rest.WAIT_COUNT_KEY] = 1
        commundetect_rest.app.config[commundetect_rest.SLEEP_TIME_KEY] = 0
        self._app = commundetect_rest.app.test_client()

    def tearDown(self):
        """Tear down test fixtures, if any."""
        shutil.rmtree(self._temp_dir)

    def test_baseurl(self):
        """Test something."""
        rv = self._app.get('/')
        self.assertEqual(rv.status_code, 200)
        self.assertTrue('Community Detection' in str(rv.data))

    def test_options_on_post_endpoint(self):
        rv = self._app.options(commundetect_rest.COMMUNDETECT_NS + '/v1')
        self.assertEqual(rv.status_code, 204)
        self.assertEqual('POST, OPTIONS',
                         rv.headers[commundetect_rest.ACCESS_CONTROL_ALLOW_METHODS])

    def test_options_on_getwith_idendpoint(self):
        rv = self._app.options(commundetect_rest.COMMUNDETECT_NS + '/v1/123')
        self.assertEqual(rv.status_code, 204)
        self.assertEqual('GET, OPTIONS, DELETE',
                         rv.headers[commundetect_rest.ACCESS_CONTROL_ALLOW_METHODS])

    def test_options_on_statuswith_idendpoint(self):
        rv = self._app.options(commundetect_rest.COMMUNDETECT_NS + '/v1/status')
        self.assertEqual(rv.status_code, 204)
        self.assertEqual('GET, OPTIONS',
                         rv.headers[commundetect_rest.ACCESS_CONTROL_ALLOW_METHODS])

    def test_delete(self):
        rv = self._app.delete(commundetect_rest.COMMUNDETECT_NS +
                              '/v1/hehex')

        self.assertEqual(rv.status_code, 200)
        hehefile = os.path.join(self._temp_dir,
                                commundetect_rest.DELETE_REQUESTS,
                                'hehex')
        self.assertTrue(os.path.isfile(hehefile))

        # try with not set path
        rv = self._app.delete(commundetect_rest.COMMUNDETECT_NS + '/v1')
        self.assertEqual(rv.status_code, 405)

        # try with path greater then 40 characters
        rv = self._app.delete(commundetect_rest.COMMUNDETECT_NS +
                              '/v1/' + 'a' * 41)
        self.assertEqual(rv.status_code, 400)

        # try where we get os error
        xdir = os.path.join(self._temp_dir,
                            commundetect_rest.DELETE_REQUESTS,
                            'hehe')
        os.makedirs(xdir, mode=0o755)
        rv = self._app.delete(commundetect_rest.COMMUNDETECT_NS +
                              '/v1/hehe')
        self.assertEqual(rv.status_code, 500)

    def test_post_create_task_fails(self):
        open(commundetect_rest.get_submit_dir(), 'a').close()
        pdict = {}
        rv = self._app.post(commundetect_rest.COMMUNDETECT_NS + '/v1',
                            data=pdict,
                            follow_redirects=True)
        self.assertEqual(rv.status_code, 500)
        self.assertTrue('Unable' in rv.json['message'])

    def test_post_ndex(self):
        pdict = {'disease': 'foo'}
        rv = self._app.post(commundetect_rest.COMMUNDETECT_NS + '/v1',
                            data=pdict,
                            follow_redirects=True)
        self.assertEqual(rv.status_code, 202)
        res = rv.headers['Location']
        self.assertTrue(res is not None)
        self.assertTrue(commundetect_rest.COMMUNDETECT_NS in res)

        uuidstr = re.sub('^.*/', '', res)
        commundetect_rest.app.config[commundetect_rest.JOB_PATH_KEY] = self._temp_dir

        tpath = commundetect_rest.get_task(uuidstr,
                                          basedir=commundetect_rest.get_submit_dir())
        self.assertTrue(os.path.isdir(tpath))
        jsonfile = os.path.join(tpath, commundetect_rest.TASK_JSON)
        self.assertTrue(os.path.isfile(jsonfile))
        with open(jsonfile, 'r') as f:
            jdata = json.load(f)

        self.assertEqual(jdata['tasktype'], 'netant_task')

    def test_get_status_no_submidir(self):
        rv = self._app.get(commundetect_rest.COMMUNDETECT_NS + '/v1/status')
        data = json.loads(rv.data)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['restVersion'],
                         commundetect_rest.__version__)
        self.assertEqual(len(data['load']), 3)
        self.assertTrue(data['pcDiskFull'], -1)
        self.assertEqual(rv.status_code, 200)

    def test_get_status(self):
        submitdir = commundetect_rest.get_submit_dir()
        os.makedirs(submitdir, mode=0o755)
        rv = self._app.get(commundetect_rest.COMMUNDETECT_NS + '/v1/status')
        data = json.loads(rv.data)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['restVersion'],
                         commundetect_rest.__version__)
        self.assertEqual(len(data['load']), 3)
        self.assertTrue(data['pcDiskFull'] is not None)
        self.assertEqual(rv.status_code, 200)

    def test_get_id_none(self):
        rv = self._app.get(commundetect_rest.COMMUNDETECT_NS + '/v1')
        self.assertEqual(rv.status_code, 405)

    def test_get_id_not_found(self):
        done_dir = os.path.join(self._temp_dir,
                                commundetect_rest.DONE_STATUS)
        os.makedirs(done_dir, mode=0o755)
        rv = self._app.get(commundetect_rest.COMMUNDETECT_NS +
                           '/v1/1234')
        data = json.loads(rv.data)
        self.assertEqual(data[commundetect_rest.STATUS_RESULT_KEY],
                         commundetect_rest.NOTFOUND_STATUS)
        self.assertEqual(rv.status_code, 410)

    def test_get_id_found_in_submitted_status(self):
        task_dir = os.path.join(self._temp_dir,
                                commundetect_rest.SUBMITTED_STATUS,
                                '45.67.54.33', 'qazxsw')
        os.makedirs(task_dir, mode=0o755)
        rv = self._app.get(commundetect_rest.COMMUNDETECT_NS +
                           '/v1/qazxsw')
        data = json.loads(rv.data)
        self.assertEqual(data[commundetect_rest.STATUS_RESULT_KEY],
                         commundetect_rest.SUBMITTED_STATUS)
        self.assertEqual(rv.status_code, 200)

    def test_get_id_found_in_processing_status(self):
        task_dir = os.path.join(self._temp_dir,
                                commundetect_rest.PROCESSING_STATUS,
                                '45.67.54.33', 'qazxsw')
        os.makedirs(task_dir, mode=0o755)
        rv = self._app.get(commundetect_rest.COMMUNDETECT_NS +
                           '/v1/qazxsw')
        data = json.loads(rv.data)
        self.assertEqual(data[commundetect_rest.STATUS_RESULT_KEY],
                         commundetect_rest.PROCESSING_STATUS)
        self.assertEqual(rv.status_code, 200)

    def test_get_id_found_in_done_status_with_result_file_no_task_file(self):
        task_dir = os.path.join(self._temp_dir,
                                commundetect_rest.DONE_STATUS,
                                '45.67.54.33', 'qazxsw')
        os.makedirs(task_dir, mode=0o755)
        resfile = os.path.join(task_dir, commundetect_rest.RESULT)
        with open(resfile, 'w') as f:
            f.write('{ "hello": "there"}')
            f.flush()

        rv = self._app.get(commundetect_rest.COMMUNDETECT_NS +
                           '/v1/qazxsw')
        data = json.loads(rv.data)
        self.assertEqual(data[commundetect_rest.STATUS_RESULT_KEY],
                         commundetect_rest.DONE_STATUS)
        self.assertEqual(data[commundetect_rest.RESULT_KEY]['hello'], 'there')
        self.assertEqual(rv.status_code, 200)

    def test_get_id_found_in_done_status_with_result_file_with_task_file(self):
        task_dir = os.path.join(self._temp_dir,
                                commundetect_rest.DONE_STATUS,
                                '45.67.54.33', 'qazxsw')
        os.makedirs(task_dir, mode=0o755)
        resfile = os.path.join(task_dir, commundetect_rest.RESULT)
        with open(resfile, 'w') as f:
            f.write('{ "hello": "there"}')
            f.flush()
        tfile = os.path.join(task_dir, commundetect_rest.TASK_JSON)
        with open(tfile, 'w') as f:
            f.write('{"task": "yo"}')
            f.flush()

        rv = self._app.get(commundetect_rest.COMMUNDETECT_NS +
                           '/v1/qazxsw')
        data = json.loads(rv.data)
        self.assertEqual(data[commundetect_rest.STATUS_RESULT_KEY],
                         commundetect_rest.DONE_STATUS)
        self.assertEqual(data[commundetect_rest.RESULT_KEY]['hello'], 'there')
        self.assertEqual(rv.status_code, 200)

    def test_log_task_json_file_with_none(self):
        self.assertEqual(commundetect_rest.log_task_json_file(None), None)
