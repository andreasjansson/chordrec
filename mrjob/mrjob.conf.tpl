# TODO:
# * start single --alive instance in emr
# * log in, do all the steps to get running for a single line of input
# * copy those steps to bootstrap script
# * launch cluster, hope for best

runners:
  emr:
    aws_access_key_id: {{ AWS_ACCESS_KEY_ID }}
    aws_secret_access_key: {{ AWS_SECRET_ACCESS_KEY }}
    ec2_key_pair: {{ AWS_KEYPAIR_NAME }}
    ec2_key_pair_file: {{ AWS_SSH_KEY_FILENAME }}
    aws_region: us-east-1
    ec2_instance_type: m1.medium
    ec2_master_instance_type: m1.medium
    ami_version: 3.1.1
    num_ec2_instances: 3
    s3_log_uri: s3://{{ AWS_S3_BUCKET }}/mrjob/logs
    s3_scratch_uri: s3://{{ AWS_S3_BUCKET }}/mrjob/scratch
    ssh_tunnel_is_open: true
    ssh_tunnel_to_job_tracker: true
    pool_emr_job_flows: true
    max_hours_idle: 2
    interpreter: python2.7
    cmdenv:
      AWS_ACCESS_KEY_ID: {{ AWS_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: {{ AWS_SECRET_ACCESS_KEY }}
      AWS_S3_BUCKET: {{ AWS_S3_BUCKET }}
