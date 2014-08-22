import os
from glob import glob

from headintheclouds.tasks import *
from headintheclouds import ec2

from fab_mrjob import *

# tar czvf chordrec.tgz ../python && tar czvf andreasmusic.tgz ~/phd/andreasmusic2 && head index | MRJOB_CONF=./mrjob.conf python cqt.py -r emr --emr-job-flow-id=j-1J9J7K4YCZXU1 -v --output-dir=s3://$AWS_S3_BUCKET/mrjob/output3

