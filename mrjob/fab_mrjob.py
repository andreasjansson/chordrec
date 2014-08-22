import os
import fabric.network
import multiprocessing
import datetime

from headintheclouds.tasks import *
from headintheclouds.tasks import terminate as hitc_terminate
from headintheclouds import ec2

env.forward_agent = True
env.name_prefix = ''
env.user = 'hadoop'

# tar czvf chordrec.tgz ../python && tar czvf andreasmusic.tgz ~/phd/andreasmusic2 && head index | MRJOB_CONF=./mrjob.conf python cqt.py -r emr --emr-job-flow-id=j-1J9J7K4YCZXU1 -v --output-dir=s3://$AWS_S3_BUCKET/mrjob/output3

def everywhere(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with provider_settings():
            func(*args, **kwargs)
            for slave in env.slaves:
                with inside(slave):
                    func(*args, **kwargs)
    return task(wrapper)

def on_slaves(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with provider_settings():
            for slave in env.slaves:
                with inside(slave):
                    func(*args, **kwargs)
    return task(wrapper)

@cloudtask
def tunnel_resourcemanager(local_port=9026, jobtracker_port=9026):
    ssh_cmd = [
        'ssh',
        '-o', 'VerifyHostKeyDNS=no',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ExitOnForwardFailure=yes',
        '-L', '%d:ip-10-137-30-141.ec2.internal:%d' % (local_port, jobtracker_port),
        '-i', env.key_filename,
        '-N',
        '%s@%s' % (env.user, env.host)
    ]
        
    local(' '.join(ssh_cmd))

@task
@runs_once
def create_job_flow():
    local('MRJOB_CONF=./mrjob.conf mrjob create-job-flow')

@cloudtask
def upload_private_key():
    put(env.key_filename, '~/.ssh/private_key.pem')

@cache.cached
def get_master():
    for host in env.hosts:
        if has_open_port(host, 22):
            return host
    raise Exception('No master found')

@on_slaves
def error_logs(application=None):
    with cd('/mnt/var/log/hadoop/userlogs'):
        if application is None:
            with hide('everything'):
                application = run('ls -t | head -n1')
        with cd(application):
            run('find . -name stderr | xargs cat')

def get_slaves(master):
    slaves = set()
    nodes = ec2.all_nodes()
    for node in nodes:
        if node['ip'] != master:
            slaves.add(node['internal_ip'])
    return slaves

def has_open_port(host, port, timeout=1):
    with settings(hide('everything'), warn_only=True):
        return not local('nc -w%d -z %s %s' % (timeout, host, port)).failed

def inside(slave):
    # paramiko caches connections by ip. different containers often have
    # the same ip.
    fabric.network.disconnect_all() 

    return fabric.context_managers.settings(gateway='%s@%s:%s' % (env.user, env.host, env.port),
                                            host=slave, host_string='hadoop@%s' % slave, user='hadoop',
                                            allow_agent=False, key_filename=env.key_filename)

@task
def bootstrap(directory='bootstrap', use_envtpl=False):
    processes = ([BootstrapProcessMaster(directory, use_envtpl)] +
                 [BootstrapProcessSlave(directory, use_envtpl, slave) for slave in env.slaves])
    for p in processes:
        p.start()
    for p in processes:
        p.join()

@task
def setup(directory='setup', use_envtpl=False):
    bootstrap(directory, use_envtpl)

@task
def terminate():
    nodes = ec2.all_nodes()
    hosts = [n['ip'] for n in nodes]
    with settings(hosts=hosts):
        execute(hitc_terminate)

@task
def run_job(script, input, output=None):
    s3_bucket = os.environ['AWS_S3_BUCKET']
    if output is None:
        output = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = 's3://%s/mrjob/output/%s' % (s3_bucket, output)
    local('envtpl --keep-template mrjob.conf.tpl')
    local('MRJOB_CONF=./mrjob.conf python %s -r emr --no-output --output-dir=%s %s' % (script, output_dir, input))
    local('rm mrjob.conf')

class BootstrapProcess(multiprocessing.Process):

    def __init__(self, directory, use_envtpl):
        super(BootstrapProcess, self).__init__()
        self.directory = directory
        self.use_envtpl = use_envtpl

class BootstrapProcessMaster(BootstrapProcess):
    def run(self):
        fabric.network.disconnect_all()
        with master_settings():
            do_bootstrap(self.directory, self.use_envtpl)

class BootstrapProcessSlave(BootstrapProcess):
    def __init__(self, directory, use_envtpl, slave):
        super(BootstrapProcessSlave, self).__init__(directory, use_envtpl)
        self.slave = slave

    def run(self):
        fabric.network.disconnect_all()
        with master_settings():
            with inside(self.slave):
                do_bootstrap(self.directory, self.use_envtpl)

def master_settings():
    return settings(
        host=master,
        host_string=master,
        user='hadoop',
        key_filename=ec2.settings['key_filename']
    )

master = get_master()
env.slaves = get_slaves(master)
env.hosts = [master]
