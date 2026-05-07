"""
Task Automation and Scheduling Module.
Manages scraper scheduling, alert throttling, and health monitoring.
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading
import time
from src.utils.logger import get_logger

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False


class Platform(Enum):
    """Scraper platforms."""
    CLASSIC_COM = "CLASSIC.COM"
    PCARMARKET = "PCARMARKET"
    RMSOTHEBY = "RMSOTHEBY"
    ELFERSPOT = "ELFERSPOT"
    RENNLIST = "RENNLIST"


@dataclass
class ScheduleConfig:
    """Configuration for scraper scheduling."""
    platform: Platform
    frequency_hours: float = 12  # How often to run
    retry_on_failure: bool = True
    max_retries: int = 3
    retry_delay_minutes: int = 15
    enabled: bool = True
    timeout_seconds: int = 300


@dataclass
class AlertConfig:
    """Configuration for alert throttling."""
    max_alerts_per_hour: int = 10
    min_time_between_same_model: timedelta = field(default_factory=lambda: timedelta(hours=4))
    batch_alerts_seconds: int = 60  # Batch alerts within 60 seconds
    enabled: bool = True


@dataclass
class JobStatus:
    """Status of a scheduled job."""
    job_id: str
    platform: str
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: str = "idle"  # idle, running, success, failed
    error_message: Optional[str] = None
    run_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    last_duration_seconds: float = 0.0


class AlertThrottler:
    """
    Manages alert frequency and batching.
    Prevents alert fatigue while ensuring important alerts are sent.
    """

    def __init__(self, config: Optional[AlertConfig] = None):
        self.logger = get_logger("alert_throttler")
        self.config = config or AlertConfig()
        self.alert_history: Dict[str, List[datetime]] = {}  # model -> list of alert times
        self.pending_alerts: List[Dict] = []
        self.last_batch_sent: datetime = datetime.utcnow()
        self.lock = threading.Lock()

    def should_send_alert(self, model: str) -> bool:
        """
        Check if alert for this model should be sent.

        Returns:
            True if alert should be sent, False if throttled
        """
        if not self.config.enabled:
            return False

        with self.lock:
            now = datetime.utcnow()

            # Check per-model throttling
            if model in self.alert_history:
                last_alert = self.alert_history[model][-1]
                if now - last_alert < self.config.min_time_between_same_model:
                    self.logger.debug(f"Alert throttled for {model}")
                    return False

            # Check hourly limit
            hour_ago = now - timedelta(hours=1)
            recent_alerts = sum(
                1 for alerts in self.alert_history.values()
                for alert_time in alerts if alert_time > hour_ago
            )

            if recent_alerts >= self.config.max_alerts_per_hour:
                self.logger.debug(f"Hourly alert limit reached ({self.config.max_alerts_per_hour})")
                return False

            # Record alert
            if model not in self.alert_history:
                self.alert_history[model] = []
            self.alert_history[model].append(now)

            return True

    def queue_alert(self, alert_data: Dict) -> bool:
        """Queue an alert for batching."""
        with self.lock:
            if self.should_send_alert(alert_data.get('model', '')):
                self.pending_alerts.append(alert_data)
                return True
        return False

    def get_pending_alerts(self) -> List[Dict]:
        """Get and clear pending alerts if batching window has passed."""
        now = datetime.utcnow()

        with self.lock:
            if (now - self.last_batch_sent).total_seconds() >= self.config.batch_alerts_seconds:
                alerts = self.pending_alerts.copy()
                self.pending_alerts.clear()
                self.last_batch_sent = now
                return alerts

        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get throttler statistics."""
        with self.lock:
            return {
                'pending_alerts': len(self.pending_alerts),
                'alert_models': list(self.alert_history.keys()),
                'total_alerts_sent': sum(len(alerts) for alerts in self.alert_history.values()),
                'enabled': self.config.enabled,
            }


class ScraperScheduler:
    """
    Manages scheduled scraper execution.
    Handles scheduling, retries, health checks, and status monitoring.
    """

    def __init__(self):
        self.logger = get_logger("scheduler")
        self.scheduler = None
        self.jobs: Dict[str, JobStatus] = {}
        self.alert_throttler = AlertThrottler()
        self.config_by_platform: Dict[str, ScheduleConfig] = {}
        self._setup_default_schedules()

    def _setup_default_schedules(self):
        """Setup default schedules for each platform."""
        # CLASSIC.COM - 2x daily (best inventory turnover)
        self.config_by_platform['CLASSIC.COM'] = ScheduleConfig(
            platform=Platform.CLASSIC_COM,
            frequency_hours=12,
            enabled=True,
        )

        # PCARMARKET - Daily (German market, slower)
        self.config_by_platform['PCARMARKET'] = ScheduleConfig(
            platform=Platform.PCARMARKET,
            frequency_hours=24,
            enabled=True,
        )

        # RM SOTHEBY'S - 3x weekly (auctions, irregular)
        self.config_by_platform['RMSOTHEBY'] = ScheduleConfig(
            platform=Platform.RMSOTHEBY,
            frequency_hours=56,  # ~3x per week
            enabled=True,
        )

        # ELFERSPOT - Daily (European market, active)
        self.config_by_platform['ELFERSPOT'] = ScheduleConfig(
            platform=Platform.ELFERSPOT,
            frequency_hours=24,
            enabled=True,
        )

        # RENNLIST - 2x daily (forum, always updating)
        self.config_by_platform['RENNLIST'] = ScheduleConfig(
            platform=Platform.RENNLIST,
            frequency_hours=12,
            enabled=True,
        )

    def start(self):
        """Start the scheduler."""
        if not APSCHEDULER_AVAILABLE:
            self.logger.error("APScheduler not installed. Run: pip install APScheduler")
            return False

        if self.scheduler is None:
            self.scheduler = BackgroundScheduler(daemon=True)

        if not self.scheduler.running:
            self.scheduler.start()
            self.logger.info("Scheduler started")
            return True

        return True

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            self.logger.info("Scheduler stopped")

    def add_scraper_job(
        self,
        platform: str,
        scraper_func: Callable,
        config: Optional[ScheduleConfig] = None,
    ) -> bool:
        """
        Add a scraper job to the schedule.

        Args:
            platform: Platform name (CLASSIC.COM, etc.)
            scraper_func: Function to call for scraping
            config: Optional schedule configuration

        Returns:
            True if successfully added
        """
        if not self.scheduler:
            self.logger.error("Scheduler not started")
            return False

        config = config or self.config_by_platform.get(platform)
        if not config:
            self.logger.error(f"No configuration for platform {platform}")
            return False

        if not config.enabled:
            self.logger.info(f"Platform {platform} is disabled")
            return False

        job_id = f"scrape_{platform.lower().replace('.', '')}"

        # Create interval trigger
        trigger = IntervalTrigger(hours=config.frequency_hours)

        # Wrap function with error handling
        wrapped_func = self._create_wrapped_job(platform, scraper_func, job_id, config)

        try:
            job = self.scheduler.add_job(
                wrapped_func,
                trigger,
                id=job_id,
                name=f"Scrape {platform}",
                replace_existing=True,
            )

            self.jobs[job_id] = JobStatus(
                job_id=job_id,
                platform=platform,
                next_run=job.next_run_time,
                status="idle",
            )

            self.logger.info(f"Added job for {platform} (every {config.frequency_hours}h)")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add job for {platform}: {e}")
            return False

    def _create_wrapped_job(
        self,
        platform: str,
        scraper_func: Callable,
        job_id: str,
        config: ScheduleConfig,
    ) -> Callable:
        """Create wrapped job with error handling and retries."""

        def wrapped():
            status = self.jobs.get(job_id)
            if status:
                status.status = "running"
                status.last_run = datetime.utcnow()
                status.run_count += 1

            start_time = time.time()

            try:
                # Call scraper with timeout
                result = self._call_with_timeout(scraper_func, config.timeout_seconds)

                duration = time.time() - start_time

                if status:
                    status.status = "success"
                    status.success_count += 1
                    status.last_duration_seconds = duration
                    status.error_message = None

                self.logger.info(
                    f"Scraper {platform} completed successfully in {duration:.1f}s"
                )

            except Exception as e:
                duration = time.time() - start_time

                if status:
                    status.status = "failed"
                    status.fail_count += 1
                    status.error_message = str(e)

                self.logger.error(f"Scraper {platform} failed: {e}")

                # Implement retry logic
                if config.retry_on_failure and status and status.fail_count <= config.max_retries:
                    self.logger.info(
                        f"Will retry {platform} in {config.retry_delay_minutes} minutes "
                        f"({status.fail_count}/{config.max_retries})"
                    )
                    # Schedule retry
                    delay_trigger = IntervalTrigger(minutes=config.retry_delay_minutes)
                    self.scheduler.add_job(
                        wrapped_func,
                        delay_trigger,
                        id=f"{job_id}_retry_{status.fail_count}",
                        replace_existing=True,
                    )

        return wrapped

    def _call_with_timeout(self, func: Callable, timeout_seconds: int) -> Any:
        """Call function with timeout."""
        result = [None]
        exception = [None]

        def target():
            try:
                result[0] = func()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout_seconds)

        if thread.is_alive():
            raise TimeoutError(f"Function execution exceeded {timeout_seconds}s timeout")

        if exception[0]:
            raise exception[0]

        return result[0]

    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get status of a scheduled job."""
        return self.jobs.get(job_id)

    def get_all_job_statuses(self) -> Dict[str, JobStatus]:
        """Get status of all jobs."""
        return self.jobs.copy()

    def disable_platform(self, platform: str):
        """Disable scraping for a platform."""
        if platform in self.config_by_platform:
            self.config_by_platform[platform].enabled = False
            self.logger.info(f"Disabled platform: {platform}")

    def enable_platform(self, platform: str):
        """Enable scraping for a platform."""
        if platform in self.config_by_platform:
            self.config_by_platform[platform].enabled = True
            self.logger.info(f"Enabled platform: {platform}")

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall scheduler health status."""
        total_jobs = len(self.jobs)
        running = sum(1 for j in self.jobs.values() if j.status == "running")
        failed = sum(1 for j in self.jobs.values() if j.status == "failed")
        total_runs = sum(j.run_count for j in self.jobs.values())
        total_success = sum(j.success_count for j in self.jobs.values())
        total_failures = sum(j.fail_count for j in self.jobs.values())

        success_rate = (total_success / total_runs * 100) if total_runs > 0 else 0

        return {
            'scheduler_running': self.scheduler is not None and self.scheduler.running,
            'total_jobs': total_jobs,
            'running_jobs': running,
            'failed_jobs': failed,
            'total_runs': total_runs,
            'total_success': total_success,
            'total_failures': total_failures,
            'success_rate_pct': success_rate,
            'alert_throttler': self.alert_throttler.get_stats(),
        }


# Global instance
_scheduler = None


def get_scheduler() -> ScraperScheduler:
    """Get global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = ScraperScheduler()
    return _scheduler
