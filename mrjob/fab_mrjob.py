import os
import fabric.network
import multiprocessing
import datetime
from boto.emr.connection import EmrConnection

from headintheclouds.tasks import *
from headintheclouds.tasks import terminate as hitc_terminate
from headintheclouds.tasks import nodes as hitc_nodes
from headintheclouds.util import print_table
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
def tunnel_hadoop(ports=[9026, 9046, 19888]):
    master_node = get_node(master)
    cmd = [
        'ssh',
        '-o', 'VerifyHostKeyDNS=no',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ExitOnForwardFailure=yes',
    ]
    for port in ports:
        cmd += ['-L', '%d:%s:%d' % (port, master_node['internal_address'], port)]

    cmd += [
        '-i', env.key_filename,
        '-N',
        '%s@%s' % (env.user, env.host)
    ]
        
    local(' '.join(cmd))

@task
@runs_once
def create_job_flow():
    local('envtpl --keep-template mrjob.conf.tpl')
    local('MRJOB_CONF=./mrjob.conf mrjob create-job-flow')
    local('rm mrjob.conf')
    cache.uncache(get_master)

@task
@runs_once
def list_jobflows():
    conn = EmrConnection()
    table = []
    for jf in conn.describe_jobflows():
        if jf.state not in ('TERMINATED', 'FAILED'):
            table.append({
                'id': jf.jobflowid,
                'created': jf.creationdatetime,
                'state': jf.state,
            })
    print_table(table)

@task
@runs_once
def terminate_jobflow(id):
    conn = EmrConnection()
    conn.terminate_jobflow(id)

@cloudtask
def upload_private_key():
    put(env.key_filename, '~/.ssh/private_key.pem')

@task
def run_job(script, input, output=None, jobflow=None):
    s3_bucket = os.environ['AWS_S3_BUCKET']
    if output is None:
        output = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = 's3://%s/mrjob/output/%s' % (s3_bucket, output)
    local('envtpl --keep-template mrjob.conf.tpl')
    cmd = [
        'MRJOB_CONF=./mrjob.conf',
        'python', script,
        '-r', 'emr',
        '--no-output',
        '--output-dir', output_dir,
    ]
    if jobflow:
        cmd += ['--emr-job-flow-id', jobflow]
    cmd += [input]

    local(' '.join(cmd))
    local('rm mrjob.conf')

@cache.cached
def get_master():
    for host in env.hosts:
        if has_open_port(host, 22):
            return host
    return None

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

def get_node(ip):
    nodes = ec2.all_nodes()
    for node in nodes:
        if node['ip'] == ip:
            return node
    return None

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
    execute(upload_private_key)
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
    cache.uncache(get_master)

@task
def nodes():
    hitc_nodes()
    cache.uncache(get_master)

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
if master:
    env.slaves = get_slaves(master)
    env.hosts = [master]
else:
    env.hosts = []
