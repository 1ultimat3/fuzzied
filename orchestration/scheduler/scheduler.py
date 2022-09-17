import configparser
import random
import logging

import boto3
from botocore.config import Config
import botocore
import time
import uuid

from github import Github

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


class FuzzScheduler:
    """
    FuzzScheduler is used to poll the github repo for fuzzing projects
    and to fill the work queue for bots in a somewhat smart way.
    """


    def __init__(self, config_filename='env.conf'):
        #load config
        self.config = configparser.ConfigParser()
        section = self.config.read(config_filename)
        self.logger = logging.getLogger('fuzzied.FuzzScheduler')

        #get the service resource
        my_config = Config(
            region_name=self.config['DEFAULT']['aws_sqs_region'],
            signature_version='v4'
        )

        self.throttle_queue_size = int(self.config['DEFAULT']['throttle_queue_size'])

        #create aws client
        self.client = boto3.client(
            'sqs',
            aws_access_key_id=self.config['DEFAULT']['aws_access_key'],
            aws_secret_access_key=self.config['DEFAULT']['aws_secret_key'],
            config=my_config
        )

        # using an access token
        g = Github(self.config['DEFAULT']['github_access_token'])
        self.repo = g.get_repo(self.config['DEFAULT']['github_repo'])

        # build initial list of known projects
        self.projects = list(self.list_fuzzing_projects())


    def list_fuzzing_projects(self):
        """
        List all projects from github repo
        """
        contents = self.repo.get_contents('projects')
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                yield(file_content)


    def get_new_projects(self):
        """
        Check if there are new projects in the github repo
        and update projects state accordingly
        """
        current_projects = list(self.list_fuzzing_projects())
        new_projects = list(set(current_projects) - set(self.projects))
        self.logger.debug("projects: " + ", ".join(s.path for s in scheduler.projects))
        return new_projects, current_projects

    def commit_new_job(self, project):
        """
        send message into sqs
        """
        return self.client.send_message(MessageBody=project.path, \
                            MessageGroupId=self.config['DEFAULT']['aws_message_group_id'], \
                            QueueUrl=self.config['DEFAULT']['aws_sqs_url'], \
                            MessageDeduplicationId=str(uuid.UUID(int=random.getrandbits(128))))

    def get_queue_size(self):
        attributes = self.client.get_queue_attributes(QueueUrl=self.config['DEFAULT']['aws_sqs_url'], \
                            AttributeNames=["ApproximateNumberOfMessages"])
        queue_size = int(attributes["Attributes"]["ApproximateNumberOfMessages"])
        self.logger.debug("Current queue size: {}".format(queue_size))
        return queue_size


if __name__ == '__main__':
    logging.basicConfig(level="INFO", format='%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S',)
    scheduler = FuzzScheduler()
    next_index = 0
    while True:
        try:
            queue_size = scheduler.get_queue_size()
            if queue_size < scheduler.throttle_queue_size:
                # fill queue with project, prefer new projects
                new_projects, curr_projects = scheduler.get_new_projects()
                if new_projects:
                    target_projects = new_projects
                    project = random.choice(target_projects)
                else:
                    target_projects = scheduler.projects = curr_projects
                    project = target_projects[next_index]
                    next_index = (next_index + 1) % len(target_projects)

                scheduler.logger.info("Add project to fuzz queue: " + project.path)
                response = scheduler.commit_new_job(project)
                scheduler.logger.info("Job commited ({} {})".format(response["ResponseMetadata"]["HTTPStatusCode"], response["MessageId"]))
                if new_projects:
                    #only after new project has been processed add it to the updated state
                    scheduler.projects.append(project)
            else:
                scheduler.logger.debug("Waiting for fuzz queue capacity")

        except botocore.exceptions.ClientError as e:
            print(e)

        finally:
            #temp safeguard to limit requests per cycle
            time.sleep(5)
