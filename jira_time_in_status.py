import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime as dt
from datetime import timezone as tz

import pandas as pd
import requests

from constants import (
    ENGINEERING_STATES,
    FINISHED_STATES,
    GIRA_URL,
    HEADERS,
    JIRA_API_BASE_URL,
    REPROCESS_FILTER_IDS,
    filter_ids,
    get_auth,
)
from query import gira_graphql_query as query

processed_issues = set()


def process_data(
    to_status,
    start_duration,
    last_history_date,
    issue_creation_date,
    last_state,
    time_in_status,
    time_in_status_data,
    statuses,
):
    """
    Process the data and compute the time spent in each status and other metrics.

    Args:
        to_status (str): The status to which the issue transitioned.
        start_duration (datetime): The start time of the current status.
        last_history_date (datetime): The date of the last history entry.
        issue_creation_date (datetime): The date when the issue was created.
        last_state (str): The last status of the issue.
        time_in_status (dict): Dictionary to store the time spent in each status.
        time_in_status_data (dict): Dictionary to store the raw data of time spent in each status.
        statuses (set): Set to store all the unique statuses.

    Returns:
        dict: Dictionary containing the computed metrics.
    """
    if to_status and start_duration:
        # Add the last status to the dictionary
        time_in_status_data[to_status] = time_in_status_data.get(to_status, []) + [(start_duration, last_history_date)]

    # Add the time spent in the last status
    time_in_status[last_state] = (
        time_in_status.get(last_state, 0) + (dt.now(tz.utc).replace(tzinfo=None) - start_duration).total_seconds()
    )

    # Convert the time spent in each status from seconds to days
    for key, value in time_in_status.items():
        if isinstance(value, (int, float)):
            # Code to handle numeric value
            time_in_status[key] = round(value / (24 * 60 * 60), 2)

    time_in_status["Total Time (Created to last history)"] = round(
        (last_history_date - issue_creation_date).total_seconds() / (24 * 60 * 60), 2
    )
    time_in_status["Created"] = issue_creation_date.strftime("%Y-%m-%d %H:%M:%S")

    # Find the finished date, default to current date
    finished_date = dt.now(tz.utc).replace(tzinfo=None)
    for status, data in time_in_status_data.items():
        if any(finished_state in status.lower() for finished_state in FINISHED_STATES):
            # Find the earliest date for the finished status
            finished_date = min(finished_date, data[0][0])

    # Add the finished date to the dictionary
    time_in_status["Finished"] = finished_date.strftime("%Y-%m-%d %H:%M:%S")

    # Convert the raw data to string for writing to excel
    for status, data in time_in_status_data.items():
        str_data = []
        for start, end in data:
            str_data.append(f'{start.strftime("%Y-%m-%d %H:%M:%S")} - {end.strftime("%Y-%m-%d %H:%M:%S")}')
        time_in_status_data[status] = str_data

    # Add the raw data to the dictionary
    time_in_status["Raw Data"] = time_in_status_data

    # Add the computed fields to the dictionary
    time_in_status["Created to Finished"] = round(
        (finished_date - issue_creation_date).total_seconds() / (24 * 60 * 60), 2
    )
    time_in_status["Engineering Time"] = sum(time_in_status.get(status, 0) for status in ENGINEERING_STATES)
    time_in_status["% of Eng time"] = round(
        time_in_status.get("Engineering Time", 0) / time_in_status.get("Created to Finished", 0) * 100, 2
    )

    return time_in_status, statuses


def extract_stats(issue):
    """
    Extracts the time spent in each status for the given issue
    Based on the changelog history from jira api

    Args:
        issue (dict): The issue for which to extract the stats.

    Returns:
        dict: Dictionary containing the time spent in each status and other metrics.
    """
    issue_key = issue["key"]
    if issue_key in processed_issues:
        print(f"Skipping {issue_key}. It has already been processed.")
        return

    print(f"Processing {issue_key}")
    changelog_url = f"{JIRA_API_BASE_URL}issue/{issue_key}/changelog"
    time_in_status = {}  # {status: time_in_days}
    time_in_status_data = {}  # {status: [(start, end)]} - Raw data
    start_duration = None  # Start time for the current status
    issue_creation_date = None
    last = False  # Flag to check if the last page of the changelog has been reached
    time_in_status["Issue Key"] = issue_key  # Add the issue key to the dictionary
    statuses = set()  # Set to store all the statuses

    while not last:
        try:
            response = requests.request(
                method="get",
                url=changelog_url,
                headers=HEADERS,
                auth=get_auth(),
            ).json()
        except Exception as e:
            # Workaround for the issue where the changelog api returns failure
            print(f"Error: {e}")
            print(f"Retrying {changelog_url} in 1 seconds")
            time.sleep(5)
            continue
        last = response.get("isLast", True)
        changelog_url = response.get("nextPage", None)
        for history in response["values"]:
            # Convert the created date to datetime object without timezone
            created = (
                dt.strptime(history["created"], "%Y-%m-%dT%H:%M:%S.%f%z").replace(tzinfo=tz.utc).replace(tzinfo=None)
            )
            if not issue_creation_date:
                issue_creation_date = created
            if not start_duration:
                start_duration = created
            field = history["items"][0]["field"]
            if field == "status":
                from_status = history["items"][0]["fromString"]
                to_status = history["items"][0]["toString"]

                statuses.add(from_status)
                statuses.add(to_status)

                time_in_status[from_status] = (
                    time_in_status.get(from_status, 0) + (created - start_duration).total_seconds()
                )
                time_in_status_data[from_status] = time_in_status_data.get(from_status, []) + [
                    (start_duration, created)
                ]

                start_duration = created
                last_state = to_status

    last_history_date = (
        dt.strptime(history["created"], "%Y-%m-%dT%H:%M:%S.%f%z").replace(tzinfo=tz.utc).replace(tzinfo=None)
    )

    print(f"Finished processing {issue_key}")
    return process_data(
        to_status=to_status,
        start_duration=start_duration,
        last_history_date=last_history_date,
        issue_creation_date=issue_creation_date,
        last_state=last_state,
        time_in_status=time_in_status,
        time_in_status_data=time_in_status_data,
        statuses=statuses,
    )


def extract_history(issue):
    """
    Extracts the time spent in each status for the given issue
    Based on the gira graphql query

    Args:
        issue (dict): The issue for which to extract the history.

    Returns:
        dict: Dictionary containing the time spent in each status and other metrics.
    """
    issue_key = issue["key"]
    if issue_key in processed_issues:
        print(f"Skipping {issue_key}. It has already been processed.")
        return

    print(f"Processing {issue_key}")
    time_in_status = {}  # {status: time_in_days}
    time_in_status_data = {}  # {status: [(start, end)]} - Raw data
    start_duration = None  # Start time for the current status
    issue_creation_date = None
    last = False  # Flag to check if the last page of the changelog has been reached
    time_in_status["Issue Key"] = issue_key  # Add the issue key to the dictionary
    statuses = set()  # Set to store all the statuses
    issue_key = issue["key"]
    if issue_key in processed_issues:
        print(f"Skipping {issue_key}. It has already been processed.")
        return

    retry_count = 0  # Retry count for the gira api
    max_results = 100000  # Maximum number of results to fetch
    history_page = 0  # Counter to keep track of the number of history pages processed
    while not last:
        json_data = {
            "variables": {
                "issueKey": issue_key,
                "startAt": history_page * max_results,
                "maxResults": max_results,
                "orderBy": "created",
            },
        }
        json_data |= query
        try:
            history = requests.request(
                method="post",
                url=GIRA_URL,
                headers=HEADERS,
                auth=get_auth(),
                json=json_data,
            ).json()["data"]["viewIssue"]["history"]
        except Exception as e:
            # Workaround for the issue where the gira api or other failure
            retry_count += 1
            print(f"Error: {e}")
            if retry_count > 5:
                print(f"Skipping {issue_key}")
                return
            print(f"Retrying {issue_key} in 1 seconds")
            time.sleep(5)
            continue
        history_page += 1
        last = history.get("isLast", True)
        for node in history["nodes"]:
            timestamps = node["timestamp"] / 1000
            # Convert the created date to datetime object without timezone
            created = dt.utcfromtimestamp(timestamps).replace(tzinfo=tz.utc).replace(tzinfo=None)

            if not issue_creation_date:
                issue_creation_date = created
            if not start_duration:
                start_duration = created
            field = node["fieldId"]
            if field == "status":
                from_status = node["from"]["displayValue"]
                to_status = node["to"]["displayValue"]

                statuses.add(from_status)
                statuses.add(to_status)

                time_in_status[from_status] = (
                    time_in_status.get(from_status, 0) + (created - start_duration).total_seconds()
                )
                time_in_status_data[from_status] = time_in_status_data.get(from_status, []) + [
                    (start_duration, created)
                ]

                start_duration = created
                last_state = to_status

    last_history_date = created

    print(f"Finished processing {issue_key}")
    return process_data(
        to_status=to_status,
        start_duration=start_duration,
        last_history_date=last_history_date,
        issue_creation_date=issue_creation_date,
        last_state=last_state,
        time_in_status=time_in_status,
        time_in_status_data=time_in_status_data,
        statuses=statuses,
    )


if __name__ == "__main__":
    """
    Fetches the history of issues for the given filter ids
    Computes the time spent in each status and the percentage of time spent in engineering
    Writes the data to an excel file
    """
    for filter_id in filter_ids:
        start_time = dt.now()  # Start time for processing the filter
        print(f"Processing issue data for filter {filter_id}")

        filter_url = f"{JIRA_API_BASE_URL}filter/{filter_id}"
        issue_stats = []  # List to store the time spent in each status for each issue
        statuses = set()  # Set to store all the statuses
        search_url = requests.request(
            method="get",
            url=filter_url,
            headers=HEADERS,
            auth=get_auth(),
        ).json()["searchUrl"]
        issue_count = 0  # Counter to keep track of the number of issues processed
        search_data = {"total": 1}  # Starting value for while loop
        params = {"startAt": 0}  # Default start from 0

        filename = f"{filter_id}.xlsx"
        if os.path.isfile(filename):
            if filter_id in REPROCESS_FILTER_IDS:
                # Remove the file so relevant issues are reprocessed
                os.remove(filename)
            else:
                df_existing = pd.read_excel(filename, engine="openpyxl")

        # Keep track of processed issues for completed issues
        processed_issues = set(df_existing["Issue Key"].tolist()) if os.path.isfile(filename) else set()

        while issue_count < search_data["total"]:
            search_data = requests.request(
                method="get",
                url=search_url,
                headers=HEADERS,
                auth=get_auth(),
                params=params,
            ).json()
            params["startAt"] += len(search_data["issues"])  # Next page

            # Optimized to run in parallel
            with ThreadPoolExecutor() as executor:
                results = executor.map(extract_history, search_data["issues"])

            for result in results:
                issue_count += 1  # Required to exit the while loop
                if not result:
                    continue
                issue_stat, issue_states = result
                statuses.update(issue_states)  # Accumulate all the statuses
                if issue_stat:
                    issue_stats.append(issue_stat)

        # Create a DataFrame with the data
        df = pd.DataFrame(issue_stats)
        if not df.empty:
            column_order = (
                ["Issue Key"]
                + list(statuses)
                + ["Created", "Finished", "Created to Finished", "Engineering Time", "% of Eng time", "Raw Data"]
            )
            df = df[column_order]

            if os.path.isfile(filename):
                # Append the new data
                df_combined = pd.concat([df_existing, df], ignore_index=True)
                # Write the combined data back to the Excel file
                df_combined.to_excel(filename, index=False)
            else:
                # Persist data to Excel file
                df.to_excel(filename, index=False)

        print(f"Time taken to process {issue_count} issues from filter {filter_id}: {dt.now() - start_time}")
