"""
Rate limiting utilities to prevent blocking when scraping Google Scholar.
"""

import time
import random
import logging
from typing import Callable, Any, Optional
from functools import wraps
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter to control request frequency.
    """

    def __init__(
        self,
        requests_per_minute: int = 8,
        min_delay: float = 3.0,
        max_delay: float = 6.0,
        page_delay: float = 4.0
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            page_delay: Fixed delay after page loads
        """
        self.requests_per_minute = requests_per_minute
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.page_delay = page_delay
        self.timestamps: list[float] = []

    def wait_if_needed(self) -> None:
        """
        Wait if we've exceeded the rate limit using token bucket algorithm.
        """
        now = time.time()

        # Remove timestamps older than 60 seconds
        self.timestamps = [t for t in self.timestamps if now - t < 60]

        # Check if we've hit the rate limit
        if len(self.timestamps) >= self.requests_per_minute:
            oldest = self.timestamps[0]
            wait_time = 60 - (now - oldest)
            if wait_time > 0:
                logger.warning(
                    f"Rate limit reached ({self.requests_per_minute} requests/min). "
                    f"Waiting {wait_time:.1f} seconds..."
                )
                time.sleep(wait_time)
                now = time.time()

        self.timestamps.append(now)

    def random_delay(self) -> None:
        """
        Apply a random delay between min_delay and max_delay.
        """
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.debug(f"Random delay: {delay:.2f} seconds")
        time.sleep(delay)

    def page_load_delay(self) -> None:
        """
        Apply a fixed delay after page loads.
        """
        logger.debug(f"Page load delay: {self.page_delay:.2f} seconds")
        time.sleep(self.page_delay)

    def apply_delay(self, delay_type: str = "random") -> None:
        """
        Apply appropriate delay based on type.

        Args:
            delay_type: Type of delay ('random', 'page', or 'none')
        """
        if delay_type == "random":
            self.random_delay()
        elif delay_type == "page":
            self.page_load_delay()
        # 'none' means no additional delay


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    error_delay: float = 15.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry a function with exponential backoff on failure.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff
        error_delay: Base delay after an error
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt < max_retries - 1:
                        delay = error_delay * (backoff_factor ** attempt)
                        logger.warning(
                            f"Error in {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f} seconds... "
                            f"(Attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Failed after {max_retries} attempts in {func.__name__}: {e}"
                        )
                        raise
            return None
        return wrapper
    return decorator


def load_rate_limiter_from_config(config_path: Optional[Path] = None) -> RateLimiter:
    """
    Load rate limiter configuration from YAML file.

    Args:
        config_path: Path to configuration file (default: config/scraper_config.yaml)

    Returns:
        Configured RateLimiter instance
    """
    if config_path is None:
        # Default to config/scraper_config.yaml relative to project root
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "scraper_config.yaml"

    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}. Using default settings.")
        return RateLimiter()

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        rate_config = config.get('rate_limiting', {})

        return RateLimiter(
            requests_per_minute=rate_config.get('requests_per_minute', 8),
            min_delay=rate_config.get('min_delay', 3.0),
            max_delay=rate_config.get('max_delay', 6.0),
            page_delay=rate_config.get('page_delay', 4.0)
        )
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}. Using default settings.")
        return RateLimiter()


class RateLimitedSession:
    """
    Context manager for rate-limited scraping sessions.
    """

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize rate-limited session.

        Args:
            rate_limiter: RateLimiter instance (loads from config if None)
        """
        self.rate_limiter = rate_limiter or load_rate_limiter_from_config()
        self.request_count = 0
        self.start_time = None

    def __enter__(self):
        """Enter the context manager."""
        self.start_time = time.time()
        logger.info("Started rate-limited scraping session")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        elapsed = time.time() - self.start_time
        logger.info(
            f"Scraping session completed. "
            f"Total requests: {self.request_count}, "
            f"Duration: {elapsed:.1f}s, "
            f"Avg rate: {self.request_count / (elapsed / 60):.1f} req/min"
        )

    def make_request(self, request_func: Callable, *args, **kwargs) -> Any:
        """
        Make a rate-limited request.

        Args:
            request_func: Function to call for the request
            *args: Positional arguments for request_func
            **kwargs: Keyword arguments for request_func

        Returns:
            Result of request_func
        """
        self.rate_limiter.wait_if_needed()
        result = request_func(*args, **kwargs)
        self.request_count += 1
        return result

    def apply_delay(self, delay_type: str = "random") -> None:
        """
        Apply a delay.

        Args:
            delay_type: Type of delay to apply
        """
        self.rate_limiter.apply_delay(delay_type)
