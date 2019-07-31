==========================================================
netant_rest
==========================================================


.. image:: https://img.shields.io/pypi/v/netant_rest.svg
        :target: https://pypi.python.org/pypi/netant_rest

.. image:: https://img.shields.io/travis/shfong/netant_rest.svg
        :target: https://travis-ci.org/shfong/netant_rest




NetAnt REST Server

`For more information please click here to visit our wiki <https://github.com/shfong/netant_rest/wiki>`_


Compatibility
-------------

 * Tested with Python 3.6 in Anaconda_

Dependencies to run
-------------------

 * `flask <https://pypi.org/project/flask/>`_
 * `flask-restplus <https://pypi.org/project/flast-restplus>`_

Additional dependencies to build
--------------------------------

 * GNU make
 * `wheel <https://pypi.org/project/wheel/>`_
 * `setuptools <https://pypi.org/project/setuptools/>`_
 

Installation
------------

It is highly reccommended one use `Anaconda <https://www.anaconda.com/>`_ for Python environment

.. code:: bash

  git clone https://github.com/shfong/netant_rest.git
  cd netant_rest
  make install

Running service in development mode
-----------------------------------


**NOTE:** Example below runs the REST service and not the task runner.

.. code:: bash

  mkdir -p foo/submitted foo/processing foo/done foo/delete_requests
  echo "JOB_PATH_KEY = `pwd`/foo" > myconfig.cfg
  echo "WAIT_COUNT_KEY = 600" >> myconfig.cfg
  echo "SLEEP_TIME_KEY = 10" >> myconfig.cfg

  # Set environment variable to config file just created
  export NETANT_REST_SETTINGS=`pwd`/myconfig.cfg

  # It is assumed the application has been installed as described above
  export FLASK_APP=netant_rest
  flask run # --host=0.0.0.0 can be added to allow all access from interfaces
  
  # Service will be running on http://localhost:5000

  # in another terminal run the following to start the task runner
  # the -vvvv increases log verbosity
  netant_taskrunner.py --nodaemon -vvvvv `pwd`/foo


Example usage of service
------------------------

TODO

.. code:: bash
   
    TODO

Bugs
-----

Please report them `here <https://github.com/shfong/netant_rest/issues>`_

Acknowledgements
----------------


* Initial template created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _Anaconda: https://www.anaconda.com/
