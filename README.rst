==========================================================
commundetect_rest
==========================================================


.. image:: https://img.shields.io/pypi/v/commundetect_rest.svg
        :target: https://pypi.python.org/pypi/commundetect_rest

.. image:: https://img.shields.io/travis/coleslaw481/commundetect_rest.svg
        :target: https://travis-ci.org/coleslaw481/commundetect_rest



Community Detection REST Server

`For more information please click here to visit our wiki <https://github.com/coleslaw481/commundetect_rest/wiki>`_


Compatibility
-------------

 * Tested with Python 3.6 in Anaconda_

Dependencies to run
-------------------

 * `flask <https://pypi.org/project/flask/>`_
 * `flask-restplus <https://pypi.org/project/flast-restplus>`_
 * numpy
 * celery
 * docker (needed to run the community detection algorithms)
 * redis (needed by celery to store results)
 * rabbitmq (needed by celery as a message broker)

Additional dependencies to build
--------------------------------

 * GNU make
 * `wheel <https://pypi.org/project/wheel/>`_
 * `setuptools <https://pypi.org/project/setuptools/>`_
 

Installation
------------

It is highly reccommended one use `Anaconda <https://www.anaconda.com/>`_ for Python environment

.. code:: bash

  git clone https://github.com/coleslaw481/commundetect_rest.git
  cd commundetect_rest
  make install

Running REST service in development mode
-----------------------------------------

**NOTE:** Example below runs the REST service and **NOT** the worker which involves steps in next section

**Step 1** Create configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open a terminal and create a configuration file denoting
where to write temporary files for processing

.. code:: bash

  mkdir -p foo/
  echo "JOB_PATH_KEY = `pwd`/foo" > myconfig.cfg

**Step 2** Run server
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

  # Set environment variable to config file just created
  export COMMUNDETECT_REST_SETTINGS=`pwd`/myconfig.cfg

  # It is assumed the application has been installed as described above
  export FLASK_APP=commundetect_rest
  flask run # --host=0.0.0.0 can be added to allow all access from interfaces
  
  # Service will be running on http://localhost:5000


Running worker in development mode
------------------------------------

Assuming rest service is up in previous step then the following operations
will spin up a worker capable of processing requests on the local machine


Step 1 Spin up redis and rabbitmq daemons
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open a new terminal and run the following commands to
use docker to spin up redis and rabbitmq services as daemons

.. code:: bash

   docker run -d -p 5672:5672 rabbitmq
   docker run -d -p 6379:6379 redis

To see these daemons invoke ``docker ps -a`` and to stop them you can run ``docker stop <container id>``


Step 2 Start worker
~~~~~~~~~~~~~~~~~~~~~~

In the terminal run this command and leave running to process tasks

.. code:: bash

   celery -A commundetect_rest.tasks worker -c 1  --loglevel=INFO -Q communitydetection

**NOTE:** The ``-c`` denotes number of workers to run concurrently



Example usage of service
------------------------

TODO

.. code:: bash
   
    TODO

Bugs
-----

Please report them `here <https://github.com/coleslaw481/commundetect_rest/issues>`_

Acknowledgements
----------------


* Initial template created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _Anaconda: https://www.anaconda.com/
