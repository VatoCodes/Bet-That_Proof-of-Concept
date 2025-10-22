"""
API Key Rotator for The Odds API
Rotates through free API keys first, then falls back to paid tier key
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class APIKeyRotator:
    """Rotates through multiple API keys to distribute request load"""

    def __init__(self, api_keys: List[str], paid_key: Optional[str] = None,
                 free_tier_limit: int = 500, paid_tier_limit: int = 20000):
        """
        Initialize the API key rotator

        Args:
            api_keys: List of API keys to rotate through (free tier first, paid tier last)
            paid_key: Optional paid tier API key (20K requests/month)
            free_tier_limit: Request limit for free tier keys (default 500)
            paid_tier_limit: Request limit for paid tier key (default 20000)
        """
        if not api_keys:
            raise ValueError("At least one API key must be provided")

        self.api_keys = api_keys
        self.paid_key = paid_key  # The last key in the list if it exists
        self.current_index = 0
        self.request_counts = {key: 0 for key in api_keys}
        self.free_tier_limit = free_tier_limit
        self.paid_tier_limit = paid_tier_limit

        # Identify which key is the paid key (last one in list if paid_key is set)
        self.paid_key_index = len(api_keys) - 1 if paid_key and paid_key in api_keys else None

        logger.info(f"Initialized APIKeyRotator with {len(api_keys)} keys")
        if self.paid_key_index is not None:
            logger.info(f"Paid tier key available at index {self.paid_key_index} ({paid_tier_limit:,} requests/month limit)")

    def get_next_key(self) -> Optional[str]:
        """
        Get the next available API key
        Prioritizes free tier keys, then falls back to paid tier key

        Returns:
            API key string, or None if all keys are exhausted
        """
        # Try to find a key with available requests
        attempts = 0
        while attempts < len(self.api_keys):
            key = self.api_keys[self.current_index]

            # Check if this is the paid key (no limit) or has requests remaining
            is_paid_key = (self.paid_key_index is not None and
                          self.current_index == self.paid_key_index)

            if is_paid_key:
                # Check paid key limit (20K requests/month)
                if self.request_counts[key] < self.paid_tier_limit:
                    logger.debug(f"Using PAID tier API key (used {self.request_counts[key]}/{self.paid_tier_limit:,})")
                    return key
            elif self.request_counts[key] < self.free_tier_limit:
                # Free tier key with requests remaining
                logger.debug(f"Using FREE tier API key index {self.current_index} (used {self.request_counts[key]}/{self.free_tier_limit})")
                return key

            # Move to next key
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            attempts += 1

        # All keys exhausted (shouldn't happen if paid key exists)
        logger.error("All API keys have reached their request limit")
        return None

    def get_paid_key(self) -> Optional[str]:
        """
        Get the paid tier API key directly (for player props that require paid tier)

        Returns:
            Paid tier API key if available and under limit, None otherwise
        """
        if self.paid_key_index is None:
            logger.error("No paid tier API key available - player props require paid tier")
            return None

        key = self.api_keys[self.paid_key_index]

        if self.request_counts[key] >= self.paid_tier_limit:
            logger.error(f"Paid tier API key has reached monthly limit ({self.paid_tier_limit:,} requests)")
            return None

        logger.info(f"Using PAID tier API key for player props (used {self.request_counts[key]}/{self.paid_tier_limit:,})")
        return key

    def increment_usage(self, api_key: str) -> None:
        """
        Increment the usage counter for a specific API key

        Args:
            api_key: The API key that was used
        """
        if api_key in self.request_counts:
            self.request_counts[api_key] += 1
            # Determine which limit to show based on whether this is paid key
            is_paid = (self.paid_key_index is not None and
                      api_key == self.api_keys[self.paid_key_index])
            limit = self.paid_tier_limit if is_paid else self.free_tier_limit
            logger.debug(f"API key usage: {self.request_counts[api_key]}/{limit}")
        else:
            logger.warning(f"Attempted to increment unknown API key")

    def get_total_usage(self) -> int:
        """
        Get total number of requests made across all keys

        Returns:
            Total request count
        """
        return sum(self.request_counts.values())

    def get_remaining_requests(self) -> int:
        """
        Get total remaining requests across all keys

        Returns:
            Number of remaining requests
        """
        total_allowed = 0
        for i, key in enumerate(self.api_keys):
            if i == self.paid_key_index:
                total_allowed += self.paid_tier_limit
            else:
                total_allowed += self.free_tier_limit
        return total_allowed - self.get_total_usage()

    def reset_counts(self) -> None:
        """Reset all request counts (useful at the start of a new month)"""
        self.request_counts = {key: 0 for key in self.api_keys}
        self.current_index = 0
        logger.info("Reset all API key usage counts")

    def get_status_report(self) -> dict:
        """
        Get a detailed status report of API key usage

        Returns:
            Dictionary with usage statistics
        """
        # Calculate max requests across all keys
        max_requests = 0
        for i in range(len(self.api_keys)):
            if i == self.paid_key_index:
                max_requests += self.paid_tier_limit
            else:
                max_requests += self.free_tier_limit

        return {
            "total_keys": len(self.api_keys),
            "total_requests": self.get_total_usage(),
            "remaining_requests": self.get_remaining_requests(),
            "max_requests": max_requests,
            "per_key_usage": {
                f"key_{i+1}": count
                for i, (key, count) in enumerate(self.request_counts.items())
            }
        }
