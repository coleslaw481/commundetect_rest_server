
import logging
import subprocess
from celery import Celery

celeryapp = Celery('tasks', broker='pyamqp://guest@localhost:5672//',
                   backend='redis://localhost')

celeryapp.conf.update(
    task_track_started=True,
    task_time_limit=1800,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=1,
    task_routes={'commundetect_rest.*': {'queue': 'communitydetection'}}
)


logger = logging.getLogger(__name__)


def run_docker(self):
    """
    Runs docker

    :param cmd_to_run: command to run as list
    :return:
    """
    cmd = ['docker', 'run', '-d', '-v',
           '/Users/churas:/Users/churas:ro', '-p', ':8500',
           'netant-2.0', '/netant/run_gunicorn.sh']

    p = subprocess.Popen(cmd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)

    out, err = p.communicate()
    return p.returncode, out, err


@celeryapp.task(bind=True)
def run_communitydetection(self, algorithm, edge_basedir, directed):
        """
        Runs community detection algorithm

        :param self:
        :param taskdict:
        :return:
        """
        logger.info('Starting task (' + self.request.id + ') ' + str(algorithm))
        logger.info(' basedir: ' + edge_basedir)
        logger.info(' directed:' + str(directed))
        self.update_state(state='PROCESSING', meta=algorithm)

        logger.info('Done with task: ')
        return 'hello there'
