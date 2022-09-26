import configparser
import random
import json
import time
import subprocess
import hashlib
import yaml

import boto3
from botocore.config import Config
import urllib.parse

from github import Github
import logging
import string

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


class FuzzBot:
    """
    FuzzBot is used to poll the message queue, conduct fuzzing jobs,
    and report issues
    """

    def __init__(self, config_filename='bot.conf'):
        #load config
        self.config = configparser.ConfigParser()
        section = self.config.read(config_filename)
        self.logger = logging.getLogger('fuzzied.FuzzBot')
        self.repo_path = self.config['DEFAULT']['repo_path']

        self.report_queue = self.config['DEFAULT']['aws_sqs_report_url']
        self.job_queue = self.config['DEFAULT']['aws_sqs_job_url']

        #get the service resource
        my_config = Config(
            region_name=self.config['DEFAULT']['aws_sqs_region'],
            signature_version='v4'
        )

        #create aws client
        self.client = boto3.client(
            'sqs',
            aws_access_key_id=self.config['DEFAULT']['aws_access_key'],
            aws_secret_access_key=self.config['DEFAULT']['aws_secret_key'],
            config=my_config
        )

        # using an access token
        _github_access_token = self.config['DEFAULT']['github_access_token']
        if _github_access_token:
            self.trusted = True
            self.github = Github(_github_access_token)
            self.repo = self.github.get_repo(self.config['DEFAULT']['github_repo'])
        else:
            self.trusted = False

    def _fuzz_output_location(self, project):
        return "{}/fuzz-output.txt".format(self._project_location(project))

    def _project_location(self, project):
        return "{}/{}".format(self.repo_path, project)

    def _targets_location(self):
        return "{}/projects".format(self.repo_path)

    def _generate_seed(self):
        return int(''.join(random.choices(string.digits, k=10)))

    def poll_queue(self):

        messages = self.client.receive_message(QueueUrl=self.job_queue)
        if 'Messages' in messages:
            for message in messages['Messages']:
                project = message['Body']
                self.client.delete_message(QueueUrl=self.job_queue, ReceiptHandle=message['ReceiptHandle'])
                self.logger.info('fuzzing job has been taken for {}'.format(project))

                #retrieve configuration for project
                fuzz_output = self._fuzz_output_location(project)
                targets_loc = self._targets_location()
                project_loc = self._project_location(project)
                build_script_loc = "compile.sh"
                config_file = "config.yaml"
                harness = "harness.sol"

                # pull repo using git before doing anything
                # besides pulling, we need to reset github state (i.e. corpus)
                cmd = "cd {} && git reset --hard HEAD && git pull -q".format(targets_loc)
                self.logger.info("updating local git repo: {}".format(cmd))

                #generate seed, fuzz, and process output
                seed = self._generate_seed()

                cmd = ("cd {project_loc}/contracts &&" +\
                        " echidna-test {harness} --corpus-dir {project_loc}/corpus/ --seed {seed} --contract Harness " +\
                        "--config {project_loc}/{config_file} --format text > {project_loc}/fuzz-output.txt\"").format(**locals())

                self.logger.info("running job: {}".format(cmd))
                with open("/tmp/output.log", "a") as output:
                    subprocess.call(cmd, shell=True, stdout=output, stderr=output)

                self.logger.info("fuzzing job has finished")

                self.logger.info('checking if issue identified')
                with open(fuzz_output) as f:
                    fuzz_results = f.read().rstrip()
                    failed_tests = [failed.split(":")[0] for failed in fuzz_results.splitlines() if "failed!💥" in failed]
                    if failed_tests:
                        self.logger.info('crash needs to be reported')
                        with open('{}/fuzz-output.txt'.format(project_loc)) as f:
                            self.client.send_message(MessageBody=f.read(), \
                                                MessageGroupId=self.config['DEFAULT']['aws_message_group_id'], \
                                                QueueUrl=self.report_queue)

                if self.trusted:
                    #TODO: commit and push new corpus if trusted bot
                    pass

                #require new poll to get a fresh message
                return
        else:
            print('No fuzzing jobs scheduled')

if __name__ == '__main__':
    logging.basicConfig(level="INFO", format='%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S',)
    bot = FuzzBot()
    while True:
        bot.poll_queue()
        time.sleep(1)
