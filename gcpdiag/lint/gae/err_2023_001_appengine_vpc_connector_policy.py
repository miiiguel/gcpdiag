#
# Copyright 2021 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python3
"""App Engine: VPC Connector creation failure due to Org Policy

Organizational policy is preventing the creation of a Serverless VPC Access Connector.
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

SEVERITY = 'ERROR'
METHOD_NAME = 'google.cloud.vpcaccess.v1.VpcAccessService.CreateConnector'
MESSAGE = 'An internal error occurred: VPC Access connector failed to get healthy'
LOG_ID = 'log_id("cloudaudit.googleapis.com/activity")'
RESOURCE_TYPE = 'audited_resource'

LOG_FILTER = [
    f'severity={SEVERITY}',
    f'protoPayload.methodName="{METHOD_NAME}"',
    f'protoPayload.status.message:"{MESSAGE}"',
]

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type=RESOURCE_TYPE,
      log_name=LOG_ID,
      filter_str=' AND '.join(LOG_FILTER))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  # skip entire rule if Logging API is disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  # skip entire rule if VPC Access API is disabled
  if not apis.is_enabled(context.project_id, 'vpcaccess'):
    report.add_skipped(project, 'vpc access api is disabled')
    return

  if logs_by_project.get(context.project_id) and \
     logs_by_project[context.project_id].entries:
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant log entries.
      if log_entry['severity'] != 'ERROR' or \
          METHOD_NAME not in get_path(log_entry,
                     ('protoPayload', 'methodName'), default='') or \
          MESSAGE not in get_path(log_entry,
                     ('protoPayload', 'status', 'message'), default=''):
        continue
      report.add_failed(
          project, 'There may have been a failed VPC \
        connector creation issue on App Engine due to the org policy')
      return

  # in case of there is no log or all logs are non-relevant
  report.add_ok(project)
