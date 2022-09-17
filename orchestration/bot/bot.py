import configparser
import random
import json
import subprocess

import boto3
from botocore.config import Config

from github import Github
import logging
import string

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


class FuzzBot:
    """
    FuzzBot is used to poll the message queue, conduct fuzzing jobs,
    and report issues (TODO: currently directly to github)
    """

    def __init__(self, config_filename='env.conf'):
        #load config
        self.config = configparser.ConfigParser()
        section = self.config.read(config_filename)
        self.logger = logging.getLogger('fuzzied.FuzzBot')
        self.repo_path = self.config['DEFAULT']['repo_path']

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
        g = Github(self.config['DEFAULT']['github_access_token'])
        self.repo = g.get_repo(self.config['DEFAULT']['github_repo'])

    def _fuzz_output_location(self, project):
        return "{}/fuzz-output.json".format(self._project_location(project))

    def _project_location(self, project):
        return "{}/{}".format(self.repo_path, project)

    def _targets_location(self):
        return "{}/projects".format(self.repo_path)

    def _generate_seed(self):
        return int(''.join(random.choices(string.digits, k=10)))

    def poll_queue(self):

        messages = self.client.receive_message(QueueUrl=self.config['DEFAULT']['aws_sqs_url'])
        if 'Messages' in messages:
            for message in messages['Messages']:
                project = message['Body']
                self.client.delete_message(QueueUrl=self.config['DEFAULT']['aws_sqs_url'], ReceiptHandle=message['ReceiptHandle'])
                self.logger.info('fuzzing job has been taken for {}'.format(project))

                #TODO pull repo using git before doing anything

                #TODO ensure configuration for fuzzing is available
                fuzz_output = self._fuzz_output_location(project)
                targets_loc = self._targets_location()
                project_loc = self._project_location(project)
                build_script_loc = "compile.sh"
                config_file = "config"
                harness = "harness.sol"
                seed = self._generate_seed()

                #fuzz and process output
                cmd = "docker run -it -v {project_loc}:/src ghcr.io/crytic/echidna/echidna bash" +\
                      "-c \"chmod a+x ./{build_script_loc} && ./{build_script_loc} &&" +\
                      "cd /src/contracts/ && echidna-test {harness} --seed {seed} --config {config} --format json > {fuzz_output}\"".format(locals())
                print(cmd)
                """
                self.logger.info("running job: {}".format(cmd))
                with open("/tmp/output.log", "a") as output:
                    subprocess.call(cmd, shell=True, stdout=output, stderr=output)

                self.logger.info("fuzzing job has finished")


                print('checking if issue has to been reported')
                with open(fuzz_output) as f:
                    fuzz_results = json.load(f)
                    tests = fuzz_results['tests']
                    seed = fuzz_results['seed']
                    if tests:
                        print('report crashs to github repo')
                        issues_body = ""Crashs have been identified:
                        {}
                        "".format(json.dumps(tests))
                        print(repo.create_issue(title="project/dummyproject {}".format(seed), body=issues_body))
                """
                #require new poll to get a message
                return
        else:
            print('No fuzzing jobs scheduled')

if __name__ == '__main__':
    logging.basicConfig(level="INFO", format='%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S',)
    bot = FuzzBot()
    bot.poll_queue()
