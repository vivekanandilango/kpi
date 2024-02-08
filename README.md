# Jira Time in Status Script

This Python script is used to calculate the time that issues have spent in each status in Jira.

## Requirements

`pip install -r requirements.txt`

## Usage

`python jira_time_in_status.py`

## Configuration
The script requires a Jira server and credentials. These can be set in the script file.
```
JIRA_SERVER = 'your-jira-server'
JIRA_EMAIL = 'your-email'
JIRA_API_TOKEN = 'your-api-token'
filter_ids = [1, 2, 3, 4, 5]
```

Replace 'your-jira-server', 'your-email', and 'your-api-token' with your actual Jira server URL and credentials.

## Output
The script writes the time in status for each issue of jira filter to an excel file of the format `filter_id.xlsx`.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
