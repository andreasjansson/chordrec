import unittest2 as unittest
from testconfig import config
from chordrec import s3
import uuid

BUCKET = config.get('s3-bucket')

class TestS3(unittest.TestCase):

    def test_nopickle(self):
        filename = 'test/%s' % uuid.uuid4()
        data = str(uuid.uuid4())
        s3.put(BUCKET, filename, data)
        self.assertEquals(s3.ls(BUCKET, filename), [filename])
        self.assertEquals(s3.get(BUCKET, filename), data)
        s3.rm(BUCKET, filename)
        self.assertEquals(s3.ls(BUCKET, filename), [])

    def test_pickle(self):
        filename = 'test/%s' % uuid.uuid4()
        data = {'a': str(uuid.uuid4()), 'b': 1234.5678/9, 'c': [1,2,3]}
        s3.put(BUCKET, filename, data, pickle=True)
        self.assertEquals(s3.ls(BUCKET, filename), [filename])
        self.assertEquals(s3.get(BUCKET, filename, unpickle=True), data)
        s3.rm(BUCKET, filename)
        self.assertEquals(s3.ls(BUCKET, filename), [])
        
