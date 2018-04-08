#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 23 19:52:26 2018

@author: ajoo
"""

import boto3
from notebook.auth import passwd
import webbrowser
import subprocess
import base64

DRY_RUN = False#True
SPOT_PRICE = 0.2
BLOCK_DURATION = None
EBS_OPTIMIZED = False
INSTANCE_TYPE = 'c4.large'#'p2.xlarge' 

USER_DATA_TEMPLATE = 'user_data.sh'
#CONDA_ENV = 'pytorch_p36'
NOTEBOOK_PORT = 8888
NOTEBOOK_PASSWORD = 'notebook_password.txt'

AMI_ID = 'ami-0ebac377' #deep learning AMI
KEY_NAME = 'MyKeyPair'
GROUP_IDS = ['sg-5149652b'] #open ssh and 8888 for jupyter
# grant S3 full permission role for checkpointing
IAM_INSTANCE_PROFILE_ARN = 'arn:aws:iam::429186803383:instance-profile/S3Checkpointer'

START_NOTEBOOK_COMMAND = 'tmux new -s ML -d "jupyter notebook"'

ec2 = boto3.resource('ec2')

def setup_notebook(*args, terminate=True, **kwargs):
    instance = launch_notebook(*args, **kwargs)
    ssh_to_instance(instance)
    if terminate:
        instance.terminate()
    
    return instance

#TODO: add conda env as parameter
def launch_notebook(instance_type=INSTANCE_TYPE, 
                    spot_price=None, 
                    block_duration=None,
                    ebs_optimized=EBS_OPTIMIZED,
                    notebook_password=None,
                    region_name=None):
    
    if notebook_password is None:
        try:
            with open(NOTEBOOK_PASSWORD, 'r') as p:
                notebook_password = p.read()
        except:
            print("Unable to retrive a default password!")
            notebook_password = passwd()
    else:
        notebook_password = passwd(notebook_password)
    
    with open(USER_DATA_TEMPLATE, 'r') as f:
        user_data = f.read().format(notebook_port=NOTEBOOK_PORT,
                                    notebook_password=notebook_password)
    user_data = base64.encodestring(user_data.encode('utf-8')).decode('ascii')
        
    launch_specification = {
        'SecurityGroupIds': GROUP_IDS,
        'EbsOptimized': ebs_optimized,
        'ImageId': AMI_ID,
        'InstanceType': instance_type,
        'KeyName': KEY_NAME,
        'UserData': user_data
    }
    if IAM_INSTANCE_PROFILE_ARN is not None:
        launch_specification['IamInstanceProfile'] = {'Arn': IAM_INSTANCE_PROFILE_ARN}

    config={
        'DryRun': DRY_RUN,
        'InstanceCount': 1,
        'LaunchSpecification': launch_specification,
        'Type': 'one-time',
        'InstanceInterruptionBehavior': 'terminate'
    }
    if block_duration is not None:
        config['BlockDurationMinutes'] = block_duration
    if spot_price is not None:
        config['SpotPrice'] = str(spot_price)
        
    if region_name is None:
        client = boto3.client('ec2')
    else:
        client = boto3.client('ec2', region_name=region_name)
    response = client.request_spot_instances(**config)
    instance = wait_for_instance_ok(response, client)
    open_browser_to_instance(instance)
   
    #print("To ssh to your instance run:\n", get_ssh_command(instance))
    return instance

COMMAND = "ssh -i ~/.ssh/{key_name}.pem ubuntu@{public_dns}"
def get_ssh_command(instance):
    return COMMAND.format(key_name=KEY_NAME,
                          public_dns=instance.public_dns_name)
def ssh_to_instance(instance):
    subprocess.call(get_ssh_command(instance), shell=True)


def open_browser_to_instance(instance, port=NOTEBOOK_PORT):
    url = 'https://{public_ip}:{port}'.format(
        public_ip=instance.public_ip_address,
        port=port)
    webbrowser.open_new_tab(url)

def get_dl_instances():
    return ec2.instances.filter(
            Filters=[{'Name': 'image-id', 'Values': [AMI_ID]}])

def list_instances():
    for i in get_dl_instances():
        print(i.id, i.state)
        
def terminate_instances():
    for i in get_dl_instances():
        i.terminate()
    
def get_last_instance():
    return max(get_dl_instances(), key=lambda i: i.launch_time)

def wait_for_instance_ok(request_response, client=None):
    if client is None:
        client = boto3.client('ec2')
        
    requests = request_response['SpotInstanceRequests']
    #assert len(requests)==1, 'More than 1 request is active'
    
    #wait for requests to be fullfiled
    request_ids = [request['SpotInstanceRequestId'] for request in requests]
    print('Waiting for spot request to be fullfiled:', request_ids)
    waiter = client.get_waiter('spot_instance_request_fulfilled')
    waiter.wait(SpotInstanceRequestIds=request_ids)
        #Filters=[{'Name': 'launch.image-id', 'Values': [AMI_ID]}],
    
    #wait for instances to be ok
    instance = get_last_instance()
    print('Waiting for instance to be running:', instance.id)
    waiter = client.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance.id])
    
    return instance
    


#waiter = client.get_waiter('instance_status_ok')
# %%

