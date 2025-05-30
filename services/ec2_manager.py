# ec2_manager.py
import boto3
from db.session import SessionLocal
from db import models

def get_boto_session(cred_id=None):
    db = SessionLocal()
    if cred_id:
        cred = db.query(models.S3Credential).filter(models.S3Credential.id == cred_id).first()
    else:
        cred = db.query(models.S3Credential).first()
    db.close()
    if not cred:
        raise Exception("AWS credentials not found for the given ID")
    return boto3.Session(
        aws_access_key_id=cred.access_key,
        aws_secret_access_key=cred.secret_key,
        region_name=cred.region
    )

def start_instance(instance_id, cred_id):
    ec2 = get_boto_session(cred_id).client('ec2')
    ec2.start_instances(InstanceIds=[instance_id])
    print(f"Starting EC2 instance {instance_id}...")

    # Wait until instance is in running state
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])
    
    # Then wait until status checks are passed
    print("Waiting for instance to pass system checks...")
    status_ok_waiter = ec2.get_waiter('instance_status_ok')
    status_ok_waiter.wait(InstanceIds=[instance_id])
    
    print(f"Instance {instance_id} is ready!")

def stop_instance(instance_id, cred_id):
    ec2 = get_boto_session(cred_id).client('ec2')
    ec2.stop_instances(InstanceIds=[instance_id])
    print(f"Stopped EC2 instance {instance_id}")

def is_instance_running(instance_id, cred_id):
    ec2 = get_boto_session(cred_id).client('ec2')
    response = ec2.describe_instances(InstanceIds=[instance_id])
    state = response['Reservations'][0]['Instances'][0]['State']['Name']
    return state == 'running'
