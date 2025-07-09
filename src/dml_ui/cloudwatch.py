"""CloudWatch utilities for retrieving logs."""
import logging
from typing import Dict, Optional

import boto3

logger = logging.getLogger(__name__)


class CloudWatchLogs:
    """Client for CloudWatch Logs operations."""

    def __init__(self):
        """Initialize the CloudWatch logs client."""
        self.client = boto3.client("logs")
        # Extract region from client if available
        if self.client and hasattr(self.client, 'meta') and hasattr(self.client.meta, 'region_name'):
            self.region = self.client.meta.region_name
        else:
            self.region = 'us-east-1'  # Default region

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
        """Get log events from CloudWatch with optional time range and pagination."""
        print("=== CloudWatch get_log_events called ===")
        print(f"log_group_name: {log_group_name}")
        print(f"log_stream_name: {log_stream_name}")
        print(f"start_time: {start_time}")
        print(f"end_time: {end_time}")
        print(f"next_token: {next_token}")
        print(f"limit: {limit}")
        print(f"start_from_head: {start_from_head}")
        
        if not self.client:
            logger.warning("CloudWatch logs client unavailable")
            print("CloudWatch logs client unavailable - returning empty response")
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

        print(f"CloudWatch API params: {params}")
        
        try:
            response = self.client.get_log_events(**params)
            print(f"CloudWatch API response keys: {list(response.keys())}")
            print(f"Number of events: {len(response.get('events', []))}")
            print(f"nextForwardToken: {response.get('nextForwardToken')}")
            print(f"nextBackwardToken: {response.get('nextBackwardToken')}")
            
            result = {
                "events": response.get("events", []),
                "nextForwardToken": response.get("nextForwardToken"),
                "nextBackwardToken": response.get("nextBackwardToken")
            }
            
            if result["events"]:
                print(f"First event: {result['events'][0]}")
                print(f"Last event: {result['events'][-1]}")
            
            return result
        except Exception as e:
            logger.error(f"Failed to get CloudWatch logs: {e}")
            print(f"CloudWatch API error: {e}")
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
        """Get log streams from CloudWatch with optional filtering."""
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
