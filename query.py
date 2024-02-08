gira_graphql_query = {
    "query": """
        query IssueHistoryQuery($issueKey: String!, $startAt: Long, $maxResults: Int, $orderBy: String) {
            viewIssue(issueKey: $issueKey) {
                history(orderBy: $orderBy, startAt: $startAt, maxResults: $maxResults) {
                    isLast
                    totalCount
                    startIndex
                    nodes {
                        fieldId
                        fieldType
                        fieldSchema {
                            type
                            customFieldType
                        }
                        timestamp
                        actor {
                            avatarUrls {
                                large
                            }
                            displayName
                            accountId
                        }
                        fieldDisplayName
                        from {
                            ... on GenericFieldValue {
                                displayValue
                                value
                            }
                            ... on AssigneeFieldValue {
                                displayValue
                                value
                                avatarUrl
                            }
                            ... on PriorityFieldValue {
                                displayValue
                                value
                                iconUrl
                            }
                            ... on StatusFieldValue {
                                displayValue
                                value
                                categoryId
                            }
                            ... on WorkLogFieldValue {
                                displayValue
                                value
                                worklog {
                                    id
                                    timeSpent
                                }
                            }
                            ... on RespondersFieldValue {
                                displayValue
                                value
                                responders {
                                    ari
                                    name
                                    type
                                    avatarUrl
                                }
                            }
                        }
                        to {
                            ... on GenericFieldValue {
                                displayValue
                                value
                            }
                            ... on AssigneeFieldValue {
                                displayValue
                                value
                                avatarUrl
                            }
                            ... on PriorityFieldValue {
                                displayValue
                                value
                                iconUrl
                            }
                            ... on StatusFieldValue {
                                displayValue
                                value
                                categoryId
                            }
                            ... on WorkLogFieldValue {
                                displayValue
                                value
                                worklog {
                                    id
                                    timeSpent
                                }
                            }
                            ... on RespondersFieldValue {
                                displayValue
                                value
                                responders {
                                    ari
                                    name
                                    type
                                    avatarUrl
                                }
                            }
                        }
                    }
                }
            }
        }
    """
}
