#   Copyright 2018 getcarrier.io
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import argparse
import os
import re
import yaml
import requests
import logging
from copy import deepcopy
from traceback import format_exc
from time import time

from dusty import constants
from dusty.drivers.rp.report_portal_writer import ReportPortalDataWriter
from dusty.drivers.jira import JiraWrapper
from dusty.drivers.emails import EmailWrapper
from dusty.dustyWrapper import DustyWrapper
from dusty.sastyWrapper import SastyWrapper
from dusty.drivers.html import HTMLReport
from dusty.drivers.xunit import XUnitReport
from dusty.drivers.redis_file import RedisFile
from dusty.drivers.influx import InfluxReport
from dusty.utils import send_emails, common_post_processing, prepare_jira_mapping

requests.packages.urllib3.disable_warnings()


def arg_parse(suites):
    parser = argparse.ArgumentParser(description='Executor for DAST scanner')
    parser.add_argument('-s', '--suite', type=str, help="specify test suite from (%s)" % ','.join(suites))
    args, unknown = parser.parse_known_args()

    return args


def proxy_through_env(value):
    if isinstance(value, str) and value.startswith('$'):
        return os.environ.get(value.replace("$", ''))

    return value


def variable_substitution(obj):
    """ Allows to use environmental variables inside YAML/JSON config """
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            obj[variable_substitution(key)] = \
                variable_substitution(obj.pop(key))

    if isinstance(obj, list):
        for index, item in enumerate(obj):
            obj[index] = variable_substitution(item)

    if isinstance(obj, str) and re.match(r"^\$[a-zA-Z_][a-zA-Z0-9_]*$", obj) \
            and obj[1:] in os.environ:
        return os.environ[obj[1:]]

    return obj


def parse_jira_config(config):
    jira_url = proxy_through_env(config['jira'].get("url", None))
    jira_user = proxy_through_env(config['jira'].get("username", None))
    jira_pwd = proxy_through_env(config['jira'].get("password", None))
    jira_project = proxy_through_env(config['jira'].get("project", None))
    jira_fields = {}

    for field_name, field_value in proxy_through_env(config['jira'].get("fields", {})).items():
        value = proxy_through_env(field_value)
        if value:
            jira_fields[field_name] = value

    # tmp
    deprecated_fields = ["assignee", "issue_type", "labels", "watchers", "epic_link"]
    if any(deprecated_field in deprecated_fields for deprecated_field in config['jira']):
        logging.warning('WARNING: using deprecated config, please update!')
        jira_fields['assignee'] = proxy_through_env(config['jira'].get("assignee", None))
        jira_fields['issuetype'] = proxy_through_env(config['jira'].get("issue_type", 'Bug'))
        jira_fields['labels'] = proxy_through_env(config['jira'].get("labels", []))
        jira_fields['watchers'] = proxy_through_env(config['jira'].get("watchers", None))
        jira_fields['Epic Link'] = proxy_through_env(config['jira'].get("epic_link", None))

    # tmp
    if not (jira_url and jira_user and jira_pwd and jira_project):
        logging.warning("Jira integration configuration is messed up , proceeding without Jira")
    else:
        return JiraWrapper(jira_url, jira_user, jira_pwd, jira_project, jira_fields)


def parse_email_config(config):
    emails_service = None
    emails_smtp_server = proxy_through_env(config['emails'].get('smtp_server', None))
    emails_port = proxy_through_env(config['emails'].get('port', None))
    emails_login = proxy_through_env(config['emails'].get('login', None))
    emails_password = proxy_through_env(config['emails'].get('password', None))
    emails_receivers_email_list = proxy_through_env(
        config['emails'].get('receivers_email_list', '')).split(', ')
    emails_subject = proxy_through_env(config['emails'].get('subject', None))
    emails_body = proxy_through_env(config['emails'].get('body', None))
    email_attachments = proxy_through_env(config['emails'].get('attachments', []))

    if email_attachments:
        email_attachments = email_attachments.split(',')

    constants.JIRA_OPENED_STATUSES.extend(proxy_through_env(
        config['emails'].get('open_states', '')).split(', '))

    if not (emails_smtp_server and emails_login and emails_password and emails_receivers_email_list):
        logging.warning("Emails integration configuration is messed up , proceeding without Emails")
    else:
        emails_service = EmailWrapper(emails_smtp_server, emails_login, emails_password, emails_port,
                                      emails_receivers_email_list, emails_subject, emails_body)

    return emails_service, email_attachments


def parse_rp_config(config, test_name, rp_service=None, launch_id=None, rp_config=None):
    rp_project = config['reportportal'].get("rp_project_name", "Dusty")
    rp_launch_name = config['reportportal'].get("rp_launch_name", test_name)
    rp_url = config['reportportal'].get("rp_host")
    rp_token = config['reportportal'].get("rp_token")
    rp_launch_tags = config["reportportal"].get("rp_launch_tags", None)

    if not (rp_launch_name and rp_project and rp_url and rp_token):
        logging.warning("ReportPortal configuration values missing, proceeding "
                        "without report portal integration ")
    else:
        rp_service = ReportPortalDataWriter(rp_url, rp_token, rp_project, rp_launch_name, rp_launch_tags)
        launch_id = rp_service.start_test()
        rp_config = dict(rp_url=rp_url, rp_token=rp_token, rp_project=rp_project,
                         rp_launch_name=rp_launch_name, rp_launch_tags=rp_launch_tags, launch_id=launch_id)

    return rp_service, launch_id, rp_config


def config_from_yaml():
    def default_ctor(loader, tag_suffix, node):
        return tag_suffix + node.value

    rp_service = None
    jira_service = None
    rp_config = None
    html_report = None
    email_service = None
    email_attachments = []
    path_to_config = os.environ.get('config_path', constants.PATH_TO_CONFIG)
    path_to_false_positive = os.environ.get('false_positive_path', constants.FALSE_POSITIVE_CONFIG)
    config_data = os.environ.get(constants.CONFIG_ENV_KEY)

    if not config_data:
        with open(path_to_config, "rb") as f:
            config_data = f.read()

    yaml.add_multi_constructor('', default_ctor)
    config = variable_substitution(yaml.load(config_data))
    suites = list(config.keys())
    args = arg_parse(suites)
    test_name = args.suite
    execution_config = config[test_name]
    generate_html = execution_config.get("html_report", False)
    generate_junit = execution_config.get("junit_report", False)
    code_path = proxy_through_env(execution_config.get("code_path", constants.PATH_TO_CODE))
    code_source = proxy_through_env(execution_config.get("code_source", constants.PATH_TO_CODE))

    if generate_html:
        logging.info("We are going to generate HTML Report")

    if generate_junit:
        logging.info("We are going to generate jUnit Report")

    for each in constants.READ_THROUGH_ENV:
        if each in execution_config:
            execution_config[each] = proxy_through_env(execution_config[each])

    if execution_config.get("reportportal", None):
        rp_service, launch_id, rp_config = parse_rp_config(execution_config, test_name)

    min_priority = proxy_through_env(
        execution_config.get("min_priority", constants.MIN_PRIORITY))

    if execution_config.get("jira", None):
        # basic_auth
        jira_service = parse_jira_config(execution_config)

    ptai_report_name = proxy_through_env(execution_config.get('ptai', {}).get('report_name', None))

    if execution_config.get('emails', None):
        email_service, email_attachments = parse_email_config(execution_config)

    default_config = dict(host=execution_config.get('target_host', None),
                          port=execution_config.get('target_port', None),
                          protocol=execution_config.get('protocol', None),
                          project_name=execution_config.get('project_name', 'None'),
                          environment=execution_config.get('environment', 'None'),
                          test_type=execution_config.get('test_type', 'None'),
                          rp_data_writer=rp_service,
                          jira_service=jira_service,
                          jira_mapping=execution_config.get('jira_mapping', prepare_jira_mapping(jira_service)),
                          min_priority=min_priority,
                          rp_config=rp_config,
                          influx=execution_config.get("influx", None),
                          generate_html=generate_html,
                          generate_junit=generate_junit,
                          html_report=html_report,
                          ptai_report_name=ptai_report_name,
                          code_path=code_path,
                          code_source=code_source,
                          path_to_false_positive=path_to_false_positive,
                          email_service=email_service,
                          email_attachments=email_attachments,
                          composition_analysis=execution_config.get('composition_analysis', None))

    tests_config = {}

    for each in execution_config:
        if each in constants.NON_SCANNERS_CONFIG_KEYS:
            continue

        config = deepcopy(default_config)

        if isinstance(execution_config[each], dict):
            for item in execution_config[each]:
                config[item] = execution_config[each][item]

        if execution_config.get('language'):
            config['language'] = execution_config['language']
            config['scan_opts'] = execution_config.get('scan_opts', '')

        tests_config[each] = config

    return default_config, tests_config


def process_results(default_config, start_time, global_results=None,
                    html_report_file=None, xml_report_file=None,
                    other_results=None, global_errors=None):
    created_jira_tickets = []
    attachments = []
    if default_config.get('rp_data_writer', None):
        default_config['rp_data_writer'].finish_test()
    default_config['execution_time'] = int(time() - start_time)
    if other_results is None:
        other_results = []
    if default_config.get('generate_html', None):
        html_report_file = HTMLReport(sorted(global_results, key=lambda item: item.severity),
                                      default_config,
                                      other_findings=sorted(other_results, key=lambda item: item.severity)).report_name
    if default_config.get('generate_junit', None):
        xml_report_file = XUnitReport(global_results, default_config).report_name
    if os.environ.get("redis_connection"):
        RedisFile(os.environ.get("redis_connection"), html_report_file, xml_report_file)
    if default_config.get('jira_service', None):
        created_jira_tickets = default_config['jira_service'].get_created_tickets()
    if default_config.get('influx', None):
        InfluxReport(global_results, other_results, created_jira_tickets, default_config)
    if default_config.get('email_service', None):
        if html_report_file:
            attachments.append(html_report_file)
        for item in default_config.get('email_attachments', None):
            attachments.append('/attachments/' + item.strip())
        # TODO: Rework sending of emails to be not tiedly coupled with Jira
        send_emails(default_config['email_service'], True, jira_tickets_info=created_jira_tickets,
                    attachments=attachments, errors=global_errors)


def main():
    logging_level = logging.INFO

    if os.environ.get("debug", False):
        logging_level = logging.DEBUG

    logging.basicConfig(
        level=logging_level,
        datefmt='%Y.%m.%d %H:%M:%S',
        format='%(asctime)s - %(levelname)8s - %(message)s',
    )

    # Disable requests/urllib3 logging
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    # Disable qualysapi requests logging
    logging.getLogger("qualysapi.connector").setLevel(logging.WARNING)
    logging.getLogger("qualysapi.config").setLevel(logging.WARNING)
    logging.getLogger("qualysapi.util").setLevel(logging.WARNING)

    start_time = time()

    global_results = []
    global_other_results = []
    global_errors = dict()

    default_config, test_configs = config_from_yaml()

    for key in test_configs:
        results = []
        other_results = []
        config = test_configs[key]
        if key in constants.SASTY_SCANNERS_CONFIG_KEYS:
            if key == "scan_opts":
                continue
            attr_name = config[key] if 'language' in key else key
            try:
                results = getattr(SastyWrapper, attr_name)(config)
            except BaseException as e:
                logging.error("Exception during %s Scanning" % attr_name)
                global_errors[attr_name] = str(e)
                if os.environ.get("debug", False):
                    logging.error(format_exc())
        else:
            try:
                tool_name, result = getattr(DustyWrapper, key)(config)
                results, other_results = common_post_processing(config, result, tool_name, need_other_results=True,
                                                                global_errors=global_errors)
            except BaseException as e:
                logging.error("Exception during %s Scanning" % key)
                global_errors[key] = str(e)
                if os.environ.get("debug", False):
                    logging.error(format_exc())
        if default_config.get('jira_service', None) and config.get('jira_service', None) \
                and config.get('jira_service').valid:
            default_config['jira_service'].created_jira_tickets.extend(
                config.get('jira_service').get_created_tickets()
            )
        if default_config.get('generate_html', None) or default_config.get('generate_junit', None):
            global_results.extend(results)
            global_other_results.extend(other_results)
    process_results(default_config, start_time, global_results, other_results=global_other_results,
                    global_errors=global_errors)


if __name__ == "__main__":
    main()
