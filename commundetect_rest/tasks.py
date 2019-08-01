
import os
import tempfile
import shutil
import time
import logging
import subprocess
import numpy as np
from celery import Celery

celeryapp = Celery('tasks', broker='pyamqp://guest@localhost:5672//',
                   backend='redis://localhost')

celeryapp.conf.update(
    task_track_started=True,
    task_time_limit=120,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=1,
    task_routes={'commundetect_rest.*': {'queue': 'communitydetection'}}
)

logger = logging.getLogger(__name__)


def run_infomap_cmd(workdir, args):
    """
    Runs docker

    :param cmd_to_run: command to run as list
    :return:
    """
    # to run as current user add this to list below before
    # coleslawndex/infomap
    # '--user', str(os.getuid()) + ':' + str(os.getgid()),
    cmd = ['docker', 'run',
           '-v', workdir + ':' + workdir,
           'coleslawndex/infomap']
    cmd.extend(args)
    logger.info('Running command: ' + ' '.join(cmd))
    p = subprocess.Popen(cmd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)

    out, err = p.communicate()
    return p.returncode, out, err

def check_if_file_contains_zero(edgelistfile):
    with open(edgelistfile, 'r') as f:
        lines = f.read().splitlines()

    for line in lines:
        elts = line.split()
        if int(elts[0]) == 0:
            return True
        if int(elts[1]) == 0:
            return True
    return False

def run_infomap(edgelistfile, outdir='.', overlap=False, directed=False):
    """

    :param edgelistfile:
    :param outdir: the output directory to comprehend the output link file
    :param overlap: bool, whether to enable overlapping community detection
    :param directed
    :return
    """
    cmdargs = ['-i', 'link-list']

    if check_if_file_contains_zero(edgelistfile) is True:
        cmdargs.append('-z')
    if overlap is True:
        cmdargs.append('--overlapping')
    if directed is True:
        cmdargs.append('-d')

    cmdargs.append(edgelistfile)
    cmdargs.append(outdir)

    cmdecode, cmdout, cmderr = run_infomap_cmd(outdir, cmdargs)

    logger.info('Cmd exit: ' + str(cmdecode))
    logger.info('Cmd out: ' + str(cmdout))
    logger.info('Cmd err: ' + str(cmderr))
    if cmdecode != 0:
        logger.error('Command failed' + str(cmderr))
        return 'Command failed with non-zero exit code: ' + str(cmdecode), None

    tree_name = os.path.join(outdir, 'edgefile.tree')
    treef = open(tree_name, 'r')
    lines = treef.read().splitlines()
    non_zero_lines = []
    while '#' in lines[0]:
        lines.pop(0)
    for i in range(len(lines)):
        if 0 != float(lines[i].split()[1]):
            non_zero_lines.append(lines[i])
    lines = non_zero_lines
    nrow = len(lines)
    ncol_list = []
    for line in lines:
        ncol_list.append(len(line.split(':')))
    ncol = max(ncol_list)
    treef.close()

    A = np.zeros((nrow, ncol))
    for i in range(len(lines)):
        Elts = lines[i].split()
        leaf = Elts[2][1:-1]
        links = Elts[0].split(':')
        for j in range(len(links) - 1):
            A[i, j] = int(links[j])
        A[i, -1] = int(leaf)
    maxElt = max(A[:, -1])
    for j in range(A.shape[1] - 1):
        k = A.shape[1] - 2 - j
        lastone = A[0, k]
        A[0, k] = A[0, k] + maxElt
        maxElt = A[0, k]
        for i in range(1, A.shape[0]):
            if A[i, k] == 0:
                continue
            if lastone != A[i, k]:
                maxElt = maxElt + 1
            lastone = A[i, k]
            A[i, k] = maxElt
    root = maxElt + 1

    edges = set()
    for i in range(A.shape[0]):
        edges.add((int(root), int(A[i, 0]), 't-t'))
        last = int(A[i, A.shape[1] - 2])
        for j in range(0, A.shape[1] - 2):
            if A[i, j + 1] == 0:
                last = int(A[i, j])
                break
            else:
                edges.add((int(A[i, j]), int(A[i, j + 1]), 't-t'))
        edges.add((last, int(A[i, A.shape[1] - 1]), 't-g'))

    result = ''
    for edge in edges:
        result = result + str(edge[0]) + ',' + str(edge[1]) + ',' + edge[2] + ';'

    return None, result


@celeryapp.task(bind=True)
def run_communitydetection(self, algorithm, basedir, directed):
        """
        Runs community detection algorithm

        :param self:
        :param taskdict:
        :return:
        """
        logger.info('Starting task (' + self.request.id + ') ' + str(algorithm))

        taskdir = os.path.join(basedir, self.request.id)
        logger.debug('Created directory: ' + taskdir)
        try:
            if algorithm == 'infomap':
                self.update_state(state='PROCESSING',
                                  meta={'message': 'Creating temporary file to hold edge list'})
                edgelist_file = os.path.join(basedir, self.request.id,
                                             'edgefile.txt')
                while not os.path.exists(edgelist_file):
                    logger.debug('Waiting for file: ' + edgelist_file + ' to appear')
                    time.sleep(0.1)

                self.update_state(state='PROCESSING',
                                  meta={'message': 'Running infomap'})
                errmsg, finalresult = run_infomap(edgelist_file,
                                                  taskdir, directed=directed)
            else:
                errmsg = algorithm + ' is not yet supported'
            logger.debug('Done with task')

            resultdict = {}
            if errmsg is not None:
                resultdict['status'] = 'error'
                resultdict['message'] = errmsg
                resultdict['result'] = None
                return resultdict

            resultdict['status'] = 'done'
            resultdict['result'] = finalresult
            return resultdict
        finally:
            logger.debug('Deleting directory: ' + taskdir)
            shutil.rmtree(taskdir)
