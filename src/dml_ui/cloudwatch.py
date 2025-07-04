"""CloudWatch utilities for retrieving logs."""

import logging
from typing import Dict, Optional

from dml_util.aws import maybe_get_client

logger = logging.getLogger(__name__)


class CloudWatchLogs:
    """Client for CloudWatch Logs operations."""

    def __init__(self):
        """Initialize the CloudWatch logs client."""
        self.client = maybe_get_client("logs")

    def get_log_events(
        self,
        log_group_name: str,
        log_stream_name: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        next_token: Optional[str] = None,
        limit: int = 1000,
        start_from_head: bool = True
    ) -> Dict:
        """
        Get log events from CloudWatch.

        Parameters
        ----------
        log_group_name : str
            Name of the CloudWatch log group
        log_stream_name : str
            Name of the CloudWatch log stream
        start_time : int, optional
            Start time in milliseconds since epoch
        end_time : int, optional
            End time in milliseconds since epoch
        next_token : str, optional
            Token for pagination
        limit : int, default=1000
            Maximum number of log events to return
        start_from_head : bool, default=True
            If True, read events from oldest to newest

        Returns
        -------
        Dict
            Dictionary containing the log events and pagination tokens
        """
        if not self.client:
            logger.warning("CloudWatch logs client unavailable")
            return {
                "events": [],
                "nextForwardToken": None,
                "nextBackwardToken": None
            }

        params = {
            "logGroupName": log_group_name,
            "logStreamName": log_stream_name,
            "limit": min(limit, 1000),  # CloudWatch API limit is 10000, but we use 1000 for better pagination
            "startFromHead": start_from_head
        }

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        if next_token:
            params["nextToken"] = next_token

        try:
            response = self.client.get_log_events(**params)
            return {
                "events": response.get("events", []),
                "nextForwardToken": response.get("nextForwardToken"),
                "nextBackwardToken": response.get("nextBackwardToken")
            }
        except Exception as e:
            logger.error(f"Failed to get CloudWatch logs: {e}")
            return {
                "events": [],
                "nextForwardToken": None,
                "nextBackwardToken": None,
                "error": str(e)
            }

    def get_log_streams(
        self,
        log_group_name: str,
        prefix: Optional[str] = None,
        next_token: Optional[str] = None,
        limit: int = 50,
    ) -> Dict:
        """
        Get log streams from CloudWatch.

        Parameters
        ----------
        log_group_name : str
            Name of the CloudWatch log group
        prefix : str, optional
            Filter by log stream name prefix
        next_token : str, optional
            Token for pagination
        limit : int, default=50
            Maximum number of log streams to return

        Returns
        -------
        Dict
            Dictionary containing the log streams and next token
        """
        if not self.client:
            logger.warning("CloudWatch logs client unavailable")
            return {
                "streams": [],
                "nextToken": None
            }

        params = {
            "logGroupName": log_group_name,
            "limit": min(limit, 50),
            "descending": True,
            "orderBy": "LastEventTime"
        }

        if prefix:
            params["logStreamNamePrefix"] = prefix
        if next_token:
            params["nextToken"] = next_token

        try:
            response = self.client.describe_log_streams(**params)
            return {
                "streams": response.get("logStreams", []),
                "nextToken": response.get("nextToken")
            }
        except Exception as e:
            logger.error(f"Failed to get CloudWatch log streams: {e}")
            return {
                "streams": [],
                "nextToken": None,
                "error": str(e)
            }
