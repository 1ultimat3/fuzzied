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
        self.github = g

    def _fuzz_output_location(self, project):
        return "{}/fuzz-output.txt".format(self._project_location(project))

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

                #retrieve configuration for project
                fuzz_output = self._fuzz_output_location(project)
                targets_loc = self._targets_location()
                project_loc = self._project_location(project)
                build_script_loc = "compile.sh"
                config_file = "config.yaml"
                harness = "harness.sol"

                #pull repo using git before doing anything
                cmd = "cd {} && git pull -q".format(targets_loc)
                self.logger.info("updating local git repo: {}".format(cmd))

                #generate seed, fuzz, and process output
                seed = self._generate_seed()

                cmd = ("docker run --rm -it -v {project_loc}:/src ghcr.io/crytic/echidna/echidna bash" +\
                      " -c \"chmod a+x /src/{build_script_loc} && /src/{build_script_loc} &&" +\
                      " cd /src/contracts/ && echidna-test {harness} --seed {seed} --config /src/{config_file} --format text > /src/fuzz-output.txt\"").format(**locals())

                self.logger.info("running job: {}".format(cmd))
                with open("/tmp/output.log", "a") as output:
                    subprocess.call(cmd, shell=True, stdout=output, stderr=output)

                self.logger.info("fuzzing job has finished")

                self.logger.info('checking if issue identified')
                with open(fuzz_output) as f:
                    fuzz_results = f.read().rstrip()
                    failed_tests = [failed.split(":")[0] for failed in fuzz_results.splitlines() if "failed!💥" in failed]
                    if failed_tests:
                        self.logger.info('evaluate {} crashs to be reported in github repo'.format(len(failed_tests)))
                        issues_body = fuzz_results
                        if len(failed_tests) > 1:
                            hash = hashlib.md5(("+".join(failed_tests)).encode('utf-8')).hexdigest()
                            title = "{}: {} crashes {}".format(project, len(failed_tests), hash[:4])
                        else:
                            title = "{}: {}".format(project, failed_tests[0])

                        #add assignee based on spec.yaml
                        with open("{}/spec.yaml".format(project_loc), 'r') as f:
                            try:
                                spec = yaml.safe_load(f)
                                assignees = spec['assignees']
                            except yaml.YAMLError as exc:
                                self.logger.error(exc)
                                assignees = []

                        #dedup issues based on title - if same title, don't create issue
                        issue_query = "repo:{} is:open \"{}\"".format(self.config['DEFAULT']['github_repo'], title)
                        self.logger.info(issue_query)
                        similar_issues = self.github.search_issues(query=issue_query)
                        len_similar_issues = len(list(similar_issues))

                        self.logger.info("similar issues open: {}".format(len_similar_issues))
                        if len_similar_issues == 0:
                            #https://pygithub.readthedocs.io/en/latest/github.html?highlight=search#github.MainClass.Github.search_issues

                            crash_label = self.repo.get_label("crash")
                            self.logger.log("creating issue: {}".format(self.repo.create_issue(title=title, \
                                body="seed: {}\n\n{}".format(seed, issues_body), \
                                assignees=assignees,
                                labels=[crash_label])))

                #require new poll to get a fresh message
                return
        else:
            print('No fuzzing jobs scheduled')

if __name__ == '__main__':
    logging.basicConfig(level="INFO", format='%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S',)
    bot = FuzzBot()
    while True:
        bot.poll_queue()
        time.sleep(5)
