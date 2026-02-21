import asyncio
import logging
import os
import time
from collections import defaultdict

from fastapi import HTTPException, status

from microservices.user_service.src.core.security import pwd_context

logger = logging.getLogger(__name__)

# A pre-computed hash for dummy verification to ensure CPU work is done
# Optimization: Skip heavy computation in test environments
if os.getenv("TESTING", "False").lower() == "true":
    DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$QaH8hQ"  # Mock hash
else:
    try:
        DUMMY_HASH = pwd_context.hash("phantom_verification_string_for_timing_protection")
    except Exception as e:
        logger.warning(f"ChronoShield: Could not pre-compute DUMMY_HASH ({e}). Using fallback.")
        DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$QaH8hQ"


class ChronoShield:
    """
    The Chrono-Kinetic Defense Shield (Advanced Authentication Protection).

    This system implements a "Neuronal Defense Matrix" to protect authentication endpoints.
    It uses:
    1. **Adaptive Exponential Backoff (Temporal Dilation):** Increasing delays for repeated failures.
    2. **Dual-Vector Tracking:** Tracks threats by both Source IP and Target Identity (Email).
    3. **Phantom Verification:** Performs real cryptographic work on invalid users to mask timing oracles.
    4. **Hard Lockout (Event Horizon):** Completely blocks traffic after a threshold.
    5. **Self-Cleaning (Entropy Management):** Automatically purges stale threat records to prevent memory exhaustion.
    """

    def __init__(self):
        # Stores failure timestamps: failures[key] = [timestamp1, timestamp2, ...]
        self._failures: defaultdict[str, list[float]] = defaultdict(list)

        # Configuration - "The Physics Constants of the Shield"
        self.WINDOW = 300.0  # 5 minutes memory horizon
        self.MAX_FREE_ATTEMPTS = 5  # Attempts before Temporal Dilation begins
        self.LOCKOUT_THRESHOLD = 20  # Attempts before Event Horizon (Hard Block)
        self.MAX_DELAY = 5.0  # Maximum time dilation in seconds

        # Memory Management
        self.MAX_KEYS = 10000  # Max number of tracked keys before forced purge
        self.last_cleanup = time.time()
        self.CLEANUP_INTERVAL = 60.0  # Cleanup every minute

    def _manage_entropy(self) -> None:
        """
        Manages the entropy of the system (Memory Cleanup).
        Prevents the 'Grey Goo' scenario where memory grows infinitely.
        """
        now = time.time()

        # Periodic cleanup
        if now - self.last_cleanup > self.CLEANUP_INTERVAL:
            keys_to_delete = []
            for key, timestamps in self._failures.items():
                # Filter valid timestamps
                valid_timestamps = [t for t in timestamps if now - t < self.WINDOW]
                if not valid_timestamps:
                    keys_to_delete.append(key)
                else:
                    self._failures[key] = valid_timestamps

            for key in keys_to_delete:
                del self._failures[key]

            self.last_cleanup = now

        # Emergency purge if under attack (Too many keys)
        if len(self._failures) > self.MAX_KEYS:
            logger.warning("ChronoShield: ENTROPY LIMIT REACHED. Initiating Emergency Purge.")
            self._failures.clear()

    async def check_allowance(self, ip: str, identifier: str) -> None:
        """
        Verifies if the request is allowed to proceed through the Chrono-Shield.
        Raises 429 if blocked, or sleeps if dilated.
        """
        # Maintenance cycle
        self._manage_entropy()

        if not ip:
            ip = "unknown"

        # Dual-Vector keys
        ip_key = f"ip:{ip}"
        target_key = f"target:{identifier}"

        ip_fails = len(self._failures[ip_key])
        target_fails = len(self._failures[target_key])

        # Calculate Threat Level (Max of vectors)
        threat_level = max(ip_fails, target_fails)

        # Phase 1: Event Horizon (Hard Lockout)
        if threat_level >= self.LOCKOUT_THRESHOLD:
            logger.warning(f"ChronoShield: EVENT HORIZON REACHED for IP={ip} Target={identifier}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Security protocol activated. Access suspended due to anomalous kinetic energy.",
            )

        # Phase 2: Temporal Dilation (Exponential Backoff)
        if threat_level > self.MAX_FREE_ATTEMPTS:
            # Formula: 0.1 * 2^(overage)
            exponent = threat_level - self.MAX_FREE_ATTEMPTS
            delay = 0.1 * (2**exponent)
            delay = min(delay, self.MAX_DELAY)

            logger.info(f"ChronoShield: Dilating time by {delay:.2f}s for IP={ip}")
            await asyncio.sleep(delay)

    def record_failure(self, ip: str, identifier: str) -> None:
        """Records a failed authentication attempt (Kinetic Impact)."""
        if not ip:
            ip = "unknown"
        now = time.time()
        self._failures[f"ip:{ip}"].append(now)
        self._failures[f"target:{identifier}"].append(now)

    def reset_target(self, identifier: str) -> None:
        """
        Resets the threat level for a specific target upon success.
        """
        target_key = f"target:{identifier}"
        if target_key in self._failures:
            del self._failures[target_key]

    async def phantom_verify(self, password: str) -> bool:
        """
        Performs a 'Phantom Verification' to protect against Timing Oracles.
        This consumes CPU cycles equivalent to a real password check.
        """
        # Verify against the dummy hash. Always returns False (hopefully),
        # but takes the same time as a real verify.
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, pwd_context.verify, password, DUMMY_HASH)


# Singleton Instance
chrono_shield = ChronoShield()
