from boto.s3.connection import S3Connection
from boto.s3.key import Key
import cPickle
import tempfile
import os

def put(bucket, path, data, pickle=False):
    key = Key(_bucket(bucket))
    key.key = path
    if pickle:
        data = cPickle.dumps(data, protocol=cPickle.HIGHEST_PROTOCOL)
    key.set_contents_from_string(data)

def get(bucket, path, unpickle=False):
    key = Key(_bucket(bucket))
    key.key = path
    data = key.get_contents_as_string()
    if unpickle:
        data = cPickle.loads(data)
    return data

def download(bucket, path, local_path):
    key = Key(_bucket(bucket))
    key.key = path
    key.get_contents_to_filename(local_path)

def download_tmp(bucket, path):
    _, suffix = os.path.splitext(path)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.close()
    local_path = tmp.name
    download(bucket, path, local_path)
    return local_path

def rm(bucket, path):
    key = Key(_bucket(bucket))
    key.key = path
    key.delete()

def ls(bucket, prefix):
    keys = [k.key for k in _bucket(bucket).list(prefix=prefix)]
    return keys

def _conn():
    if _conn.conn is None:
        _conn.conn = S3Connection()
    return _conn.conn
_conn.conn = None
    
def _bucket(bucket):
    return _conn().get_bucket(bucket)
