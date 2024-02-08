import os
from functools import lru_cache

from requests.auth import HTTPBasicAuth

# https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/
jira_token = os.getenv("JIRA_API_TOKEN", "your-jira-api-token")
jira_email = os.getenv("JIRA_EMAIL", "your-jira-email")
JIRA_SERVER = os.getenv("JIRA_SERVER", "your-jira-server")


@lru_cache
def get_auth() -> HTTPBasicAuth:
    """Basic token based auth. Cached for optimization"""
    return HTTPBasicAuth(jira_email, jira_token)


HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


JIRA_API_BASE_URL = f"https://{JIRA_SERVER}/rest/api/2/"
GIRA_URL = f"https://{JIRA_SERVER}/rest/gira/1/"

OPEN_ISSUES_FILTER_ID = 10000
CLOSED_ISSUES_FILTER_ID = 20000

filter_ids = [
    OPEN_ISSUES_FILTER_ID,
    CLOSED_ISSUES_FILTER_ID,
]

REPROCESS_FILTER_IDS = {
    OPEN_ISSUES_FILTER_ID,
}


ENGINEERING_STATES = [
    "Engineering Triage",
    "In Progress",
]

FINISHED_STATES = [
    "done",
    "archive",
    "finish",
    "close",
    "resolve",
    "merge",
    "complete",
]
