"""
Scheduler lock file system to prevent duplicate scheduler instances
"""

import os
import fcntl
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SchedulerLock:
    """Prevents duplicate scheduler instances using file locks"""

    def __init__(self, lock_file: str):
        """
        Initialize scheduler lock

        Args:
            lock_file: Path to lock file (e.g., /tmp/bet_that_scheduler.lock)
        """
        self.lock_file = Path(lock_file)
        self.lock_fd = None

    def acquire(self) -> bool:
        """
        Try to acquire lock

        Returns:
            True if lock acquired, False if already locked (another instance running)
        """
        try:
            # Create lock file if it doesn't exist
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)

            # Open file for writing
            self.lock_fd = open(self.lock_file, 'w')

            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Write our PID to the lock file
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()

            logger.info(f"✓ Acquired lock: {self.lock_file}")
            return True

        except (IOError, OSError) as e:
            # Lock is already held by another process
            logger.error(f"✗ Failed to acquire lock: {self.lock_file}")
            logger.error(f"  Another scheduler instance is already running")
            if self.lock_fd:
                self.lock_fd.close()
            return False

    def release(self):
        """Release lock and clean up lock file"""
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                self.lock_fd.close()
                logger.info(f"✓ Released lock: {self.lock_file}")
            except Exception as e:
                logger.error(f"Error releasing lock: {e}")

            # Remove lock file
            try:
                if self.lock_file.exists():
                    self.lock_file.unlink()
            except Exception as e:
                logger.error(f"Error removing lock file: {e}")

    def __enter__(self):
        """Context manager entry"""
        if not self.acquire():
            raise RuntimeError("Failed to acquire scheduler lock")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()


# Lock file paths for each scheduler
SCHEDULER_LOCKS = {
    'main': '/tmp/bet_that_scheduler_main.lock',
    'odds': '/tmp/bet_that_scheduler_odds.lock'
}


if __name__ == "__main__":
    # Test the lock system
    logging.basicConfig(level=logging.INFO)

    print("\nTesting scheduler lock system...")

    # Test acquiring lock
    lock = SchedulerLock(SCHEDULER_LOCKS['main'])
    if lock.acquire():
        print("✓ Lock acquired successfully")
        print(f"  Lock file: {lock.lock_file}")
        print(f"  PID: {os.getpid()}")

        # Try to acquire same lock again (should fail)
        print("\nTrying to acquire same lock again (should fail)...")
        lock2 = SchedulerLock(SCHEDULER_LOCKS['main'])
        if not lock2.acquire():
            print("✓ Second lock acquisition correctly failed (lock is held)")

        # Release lock
        lock.release()
        print("\n✓ Lock released")

        # Now second acquisition should succeed
        print("\nTrying to acquire lock after release (should succeed)...")
        if lock2.acquire():
            print("✓ Lock acquired after release")
            lock2.release()
    else:
        print("✗ Failed to acquire lock")

    print("\n✓ Lock system test complete")
