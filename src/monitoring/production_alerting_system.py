# SPDX-License-Identifier: MIT
"""
Production-grade alerting system for OpenCode-Slack.
Implements intelligent alerting with severity levels, escalation, correlation,
noise reduction, and integration with email/Slack notifications.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
import json
import logging
import os
import requests
import smtplib
import threading
import time

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return self.value

    @classmethod
    def from_string(cls, value: str):
        """Create from string value"""
        for severity in cls:
            if severity.value == value:
                return severity
        return cls.INFO


class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return self.value

    @classmethod
    def from_string(cls, value: str):
        """Create from string value"""
        for status in cls:
            if status.value == value:
                return status
        return cls.ACTIVE


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    source: str
    component: str
    timestamp: datetime
    tags: List[str]
    metadata: Dict[str, Any]
    escalation_level: int = 0
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    suppressed_until: Optional[datetime] = None

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'severity': self.severity.value if isinstance(self.severity, AlertSeverity) else self.severity,
            'status': self.status.value if isinstance(self.status, AlertStatus) else self.status,
            'source': self.source,
            'component': self.component,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'tags': self.tags,
            'metadata': self.metadata,
            'escalation_level': self.escalation_level,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'suppressed_until': self.suppressed_until.isoformat() if self.suppressed_until else None
        }


@dataclass
class AlertRule:
    """Alert rule configuration"""
    id: str
    name: str
    description: str
    severity: AlertSeverity
    condition: str
    threshold: float
    duration_minutes: int
    enabled: bool = True
    tags: List[str] = None
    escalation_rules: List[Dict[str, Any]] = None

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'severity': self.severity.value if isinstance(self.severity, AlertSeverity) else self.severity,
            'condition': self.condition,
            'threshold': self.threshold,
            'duration_minutes': self.duration_minutes,
            'enabled': self.enabled,
            'tags': self.tags or [],
            'escalation_rules': self.escalation_rules or []
        }


@dataclass
class NotificationChannel:
    """Notification channel configuration"""
    id: str
    name: str
    type: str  # email, slack, webhook
    config: Dict[str, Any]
    enabled: bool = True
    severity_filter: List[AlertSeverity] = None

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'config': self.config,
            'enabled': self.enabled,
            'severity_filter': [s.value if isinstance(s, AlertSeverity) else s for s in (self.severity_filter or [])]
        }


class ProductionAlertingSystem:
    """Production-grade alerting system with intelligent features"""

    def __init__(self, metrics_collector, config_path: str = "alerting_config.json"):
        """
        Initialize the production alerting system

        Args:
            metrics_collector: Production metrics collector instance
            config_path: Path to alerting configuration file
        """
        self.metrics_collector = metrics_collector
        self.config_path = config_path

        # Alert storage
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=10000)

        # Alert rules and channels
        self.alert_rules: Dict[str, AlertRule] = {}
        self.notification_channels: Dict[str, NotificationChannel] = {}

        # Correlation and noise reduction
        self.alert_correlations: Dict[str, Set[str]] = defaultdict(set)
        self.suppression_rules: Dict[str, Dict[str, Any]] = {}
        self.rate_limits: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Escalation tracking
        self.escalation_timers: Dict[str, threading.Timer] = {}
        self.on_call_rotation: List[Dict[str, Any]] = []

        # Processing state
        self.is_processing = False
        self.processing_thread = None

        # Load configuration
        self._load_configuration()

        # Initialize default rules and channels
        self._setup_default_rules()
        self._setup_default_channels()

        logger.info("ProductionAlertingSystem initialized")

    def _load_configuration(self):
        """Load alerting configuration from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)

                # Load alert rules
                for rule_data in config.get('alert_rules', []):
                    rule = AlertRule(**rule_data)
                    self.alert_rules[rule.id] = rule

                # Load notification channels
                for channel_data in config.get('notification_channels', []):
                    channel = NotificationChannel(**channel_data)
                    self.notification_channels[channel.id] = channel

                # Load on-call rotation
                self.on_call_rotation = config.get('on_call_rotation', [])

                # Load suppression rules
                self.suppression_rules = config.get('suppression_rules', {})

                logger.info(f"Loaded alerting configuration from {self.config_path}")
            else:
                logger.info("No alerting configuration file found, using defaults")

        except Exception as e:
            logger.error(f"Error loading alerting configuration: {e}")

    def _setup_default_rules(self):
        """Setup default alert rules"""
        default_rules = [
            AlertRule(
                id="high_cpu_usage",
                name="High CPU Usage",
                description="CPU usage is above 80% for more than 5 minutes",
                severity=AlertSeverity.HIGH,
                condition="cpu_percent > 80",
                threshold=80.0,
                duration_minutes=5,
                tags=["system", "performance"]
            ),
            AlertRule(
                id="high_memory_usage",
                name="High Memory Usage",
                description="Memory usage is above 85% for more than 3 minutes",
                severity=AlertSeverity.HIGH,
                condition="memory_percent > 85",
                threshold=85.0,
                duration_minutes=3,
                tags=["system", "memory"]
            ),
            AlertRule(
                id="agent_stuck",
                name="Agent Stuck",
                description="Agent has been stuck for more than 10 minutes",
                severity=AlertSeverity.CRITICAL,
                condition="agent_stuck_duration > 10",
                threshold=10.0,
                duration_minutes=1,
                tags=["agent", "critical"]
            ),
            AlertRule(
                id="high_error_rate",
                name="High Error Rate",
                description="API error rate is above 5% for more than 2 minutes",
                severity=AlertSeverity.MEDIUM,
                condition="error_rate_percent > 5",
                threshold=5.0,
                duration_minutes=2,
                tags=["api", "errors"]
            ),
            AlertRule(
                id="low_agent_utilization",
                name="Low Agent Utilization",
                description="Agent utilization is below 20% for more than 30 minutes",
                severity=AlertSeverity.LOW,
                condition="agent_utilization_percent < 20",
                threshold=20.0,
                duration_minutes=30,
                tags=["business", "utilization"]
            ),
            AlertRule(
                id="disk_space_low",
                name="Low Disk Space",
                description="Disk usage is above 90%",
                severity=AlertSeverity.HIGH,
                condition="disk_usage_percent > 90",
                threshold=90.0,
                duration_minutes=1,
                tags=["system", "disk"]
            ),
            AlertRule(
                id="slow_api_response",
                name="Slow API Response",
                description="Average API response time is above 2 seconds",
                severity=AlertSeverity.MEDIUM,
                condition="avg_api_response_time > 2000",
                threshold=2000.0,
                duration_minutes=5,
                tags=["api", "performance"]
            )
        ]

        for rule in default_rules:
            if rule.id not in self.alert_rules:
                self.alert_rules[rule.id] = rule

        logger.info(f"Setup {len(default_rules)} default alert rules")

    def _setup_default_channels(self):
        """Setup default notification channels"""
        default_channels = []

        # Email channel
        if os.environ.get('ALERT_EMAIL_SMTP_HOST'):
            default_channels.append(NotificationChannel(
                id="email_alerts",
                name="Email Alerts",
                type="email",
                config={
                    'smtp_host': os.environ.get('ALERT_EMAIL_SMTP_HOST'),
                    'smtp_port': int(os.environ.get('ALERT_EMAIL_SMTP_PORT', 587)),
                    'smtp_user': os.environ.get('ALERT_EMAIL_SMTP_USER'),
                    'smtp_password': os.environ.get('ALERT_EMAIL_SMTP_PASSWORD'),
                    'from_email': os.environ.get('ALERT_EMAIL_FROM'),
                    'to_emails': os.environ.get('ALERT_EMAIL_TO', '').split(',')
                },
                severity_filter=[AlertSeverity.CRITICAL, AlertSeverity.HIGH]
            ))

        # Slack channel
        if os.environ.get('ALERT_SLACK_WEBHOOK_URL'):
            default_channels.append(NotificationChannel(
                id="slack_alerts",
                name="Slack Alerts",
                type="slack",
                config={
                    'webhook_url': os.environ.get('ALERT_SLACK_WEBHOOK_URL'),
                    'channel': os.environ.get('ALERT_SLACK_CHANNEL', '#alerts'),
                    'username': os.environ.get('ALERT_SLACK_USERNAME', 'OpenCode-Slack Monitor')
                },
                severity_filter=[AlertSeverity.CRITICAL, AlertSeverity.HIGH, AlertSeverity.MEDIUM]
            ))

        # Webhook channel
        if os.environ.get('ALERT_WEBHOOK_URL'):
            default_channels.append(NotificationChannel(
                id="webhook_alerts",
                name="Webhook Alerts",
                type="webhook",
                config={
                    'url': os.environ.get('ALERT_WEBHOOK_URL'),
                    'headers': json.loads(os.environ.get('ALERT_WEBHOOK_HEADERS', '{}'))
                }
            ))

        for channel in default_channels:
            if channel.id not in self.notification_channels:
                self.notification_channels[channel.id] = channel

        logger.info(f"Setup {len(default_channels)} default notification channels")

    def start_processing(self):
        """Start alert processing"""
        if self.is_processing:
            logger.warning("Alert processing is already running")
            return

        self.is_processing = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()

        logger.info("Production alerting system started")

    def stop_processing(self):
        """Stop alert processing"""
        if not self.is_processing:
            logger.warning("Alert processing is not running")
            return

        self.is_processing = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)

        # Cancel all escalation timers
        for timer in self.escalation_timers.values():
            timer.cancel()
        self.escalation_timers.clear()

        logger.info("Production alerting system stopped")

    def _processing_loop(self):
        """Main alert processing loop"""
        logger.info("Starting alert processing loop")

        while self.is_processing:
            try:
                # Get current metrics
                current_metrics = self.metrics_collector.get_current_metrics()

                if current_metrics:
                    # Evaluate alert rules
                    self._evaluate_alert_rules(current_metrics)

                    # Process alert correlations
                    self._process_alert_correlations()

                    # Clean up resolved alerts
                    self._cleanup_resolved_alerts()

                # Sleep for processing interval
                time.sleep(30)  # Process every 30 seconds

            except Exception as e:
                logger.error(f"Error in alert processing loop: {e}")
                time.sleep(30)

    def _evaluate_alert_rules(self, metrics: Dict[str, Any]):
        """Evaluate alert rules against current metrics"""
        try:
            for rule_id, rule in self.alert_rules.items():
                if not rule.enabled:
                    continue

                # Check if rule condition is met
                if self._evaluate_rule_condition(rule, metrics):
                    # Check if alert already exists
                    existing_alert = self.active_alerts.get(rule_id)

                    if existing_alert:
                        # Update existing alert
                        self._update_existing_alert(existing_alert, metrics)
                    else:
                        # Create new alert
                        self._create_new_alert(rule, metrics)
                else:
                    # Condition not met, resolve alert if it exists
                    if rule_id in self.active_alerts:
                        self._resolve_alert(rule_id)

        except Exception as e:
            logger.error(f"Error evaluating alert rules: {e}")

    def _evaluate_rule_condition(self, rule: AlertRule, metrics: Dict[str, Any]) -> bool:
        """Evaluate if a rule condition is met"""
        try:
            # Extract relevant metrics based on rule condition
            if "cpu_percent" in rule.condition:
                value = metrics.get('system', {}).get('cpu_percent', 0)
            elif "memory_percent" in rule.condition:
                value = metrics.get('system', {}).get('memory_percent', 0)
            elif "disk_usage_percent" in rule.condition:
                value = metrics.get('system', {}).get('disk_usage_percent', 0)
            elif "error_rate_percent" in rule.condition:
                value = metrics.get('business', {}).get('error_rate_percent', 0)
            elif "agent_utilization_percent" in rule.condition:
                value = metrics.get('business', {}).get('agent_utilization_percent', 0)
            elif "avg_api_response_time" in rule.condition:
                # Calculate average API response time from performance metrics
                api_times = metrics.get('performance', {}).get('api_response_times', {})
                if api_times:
                    avg_times = [times.get('avg', 0) for times in api_times.values()]
                    value = sum(avg_times) / len(avg_times) if avg_times else 0
                else:
                    value = 0
            else:
                return False

            # Evaluate condition
            if ">" in rule.condition:
                return value > rule.threshold
            elif "<" in rule.condition:
                return value < rule.threshold
            elif "==" in rule.condition:
                return value == rule.threshold
            else:
                return False

        except Exception as e:
            logger.error(f"Error evaluating rule condition for {rule.id}: {e}")
            return False

    def _create_new_alert(self, rule: AlertRule, metrics: Dict[str, Any]):
        """Create a new alert"""
        try:
            alert_id = f"{rule.id}_{int(time.time())}"

            alert = Alert(
                id=alert_id,
                title=rule.name,
                description=rule.description,
                severity=rule.severity,
                status=AlertStatus.ACTIVE,
                source="monitoring_system",
                component=rule.tags[0] if rule.tags else "unknown",
                timestamp=datetime.now(),
                tags=rule.tags or [],
                metadata={
                    'rule_id': rule.id,
                    'threshold': rule.threshold,
                    'current_metrics': metrics
                }
            )

            # Apply noise reduction
            if self._should_suppress_alert(alert):
                alert.status = AlertStatus.SUPPRESSED
                alert.suppressed_until = datetime.now() + timedelta(minutes=30)
                logger.info(f"Alert {alert_id} suppressed due to noise reduction")
                return

            # Store alert
            self.active_alerts[rule.id] = alert
            self.alert_history.append(alert)

            # Send notifications
            self._send_alert_notifications(alert)

            # Setup escalation timer
            self._setup_escalation_timer(alert)

            logger.info(f"Created new alert: {alert_id} - {alert.title}")

        except Exception as e:
            logger.error(f"Error creating new alert for rule {rule.id}: {e}")

    def _update_existing_alert(self, alert: Alert, metrics: Dict[str, Any]):
        """Update an existing alert"""
        try:
            # Update metadata with current metrics
            alert.metadata['current_metrics'] = metrics
            alert.metadata['last_updated'] = datetime.now()

            logger.debug(f"Updated existing alert: {alert.id}")

        except Exception as e:
            logger.error(f"Error updating existing alert {alert.id}: {e}")

    def _resolve_alert(self, rule_id: str):
        """Resolve an alert"""
        try:
            if rule_id in self.active_alerts:
                alert = self.active_alerts[rule_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()

                # Cancel escalation timer
                if alert.id in self.escalation_timers:
                    self.escalation_timers[alert.id].cancel()
                    del self.escalation_timers[alert.id]

                # Send resolution notification
                self._send_resolution_notification(alert)

                # Remove from active alerts
                del self.active_alerts[rule_id]

                logger.info(f"Resolved alert: {alert.id} - {alert.title}")

        except Exception as e:
            logger.error(f"Error resolving alert for rule {rule_id}: {e}")

    def _should_suppress_alert(self, alert: Alert) -> bool:
        """Check if alert should be suppressed due to noise reduction"""
        try:
            # Rate limiting - check if too many similar alerts recently
            alert_key = f"{alert.component}_{alert.severity.value}"
            recent_alerts = self.rate_limits[alert_key]

            # Count alerts in last 10 minutes
            cutoff_time = time.time() - 600  # 10 minutes
            recent_count = sum(1 for timestamp in recent_alerts if timestamp > cutoff_time)

            if recent_count >= 5:  # More than 5 similar alerts in 10 minutes
                return True

            # Add current alert to rate limit tracking
            recent_alerts.append(time.time())

            # Check suppression rules
            for rule_pattern, rule_config in self.suppression_rules.items():
                if rule_pattern in alert.title or rule_pattern in alert.component:
                    if rule_config.get('enabled', False):
                        return True

            return False

        except Exception as e:
            logger.error(f"Error checking alert suppression: {e}")
            return False

    def _process_alert_correlations(self):
        """Process alert correlations to group related alerts"""
        try:
            # Group alerts by component and time window
            component_alerts = defaultdict(list)

            for alert in self.active_alerts.values():
                if alert.status == AlertStatus.ACTIVE:
                    component_alerts[alert.component].append(alert)

            # Look for correlation patterns
            for component, alerts in component_alerts.items():
                if len(alerts) > 1:
                    # Multiple alerts for same component - potential correlation
                    alert_ids = [alert.id for alert in alerts]
                    self.alert_correlations[component].update(alert_ids)

                    logger.debug(f"Correlated {len(alerts)} alerts for component {component}")

        except Exception as e:
            logger.error(f"Error processing alert correlations: {e}")

    def _cleanup_resolved_alerts(self):
        """Clean up old resolved alerts"""
        try:
            # Remove alerts resolved more than 24 hours ago from history
            cutoff_time = datetime.now() - timedelta(hours=24)

            # Filter alert history
            self.alert_history = deque([
                alert for alert in self.alert_history
                if not (alert.status == AlertStatus.RESOLVED and
                       alert.resolved_at and alert.resolved_at < cutoff_time)
            ], maxlen=10000)

        except Exception as e:
            logger.error(f"Error cleaning up resolved alerts: {e}")

    def _setup_escalation_timer(self, alert: Alert):
        """Setup escalation timer for an alert"""
        try:
            # Get escalation rules for the alert
            rule = self.alert_rules.get(alert.metadata.get('rule_id'))
            if not rule or not rule.escalation_rules:
                return

            # Setup timer for first escalation level
            escalation_delay = rule.escalation_rules[0].get('delay_minutes', 15) * 60

            timer = threading.Timer(escalation_delay, self._escalate_alert, args=[alert.id])
            timer.start()

            self.escalation_timers[alert.id] = timer

            logger.debug(f"Setup escalation timer for alert {alert.id}")

        except Exception as e:
            logger.error(f"Error setting up escalation timer for alert {alert.id}: {e}")

    def _escalate_alert(self, alert_id: str):
        """Escalate an alert to the next level"""
        try:
            # Find the alert
            alert = None
            for active_alert in self.active_alerts.values():
                if active_alert.id == alert_id:
                    alert = active_alert
                    break

            if not alert or alert.status != AlertStatus.ACTIVE:
                return

            # Increase escalation level
            alert.escalation_level += 1

            # Get rule escalation configuration
            rule = self.alert_rules.get(alert.metadata.get('rule_id'))
            if rule and rule.escalation_rules and alert.escalation_level < len(rule.escalation_rules):
                escalation_config = rule.escalation_rules[alert.escalation_level]

                # Send escalation notification
                self._send_escalation_notification(alert, escalation_config)

                # Setup next escalation timer if needed
                if alert.escalation_level + 1 < len(rule.escalation_rules):
                    next_delay = rule.escalation_rules[alert.escalation_level + 1].get('delay_minutes', 30) * 60
                    timer = threading.Timer(next_delay, self._escalate_alert, args=[alert_id])
                    timer.start()
                    self.escalation_timers[alert_id] = timer

            logger.info(f"Escalated alert {alert_id} to level {alert.escalation_level}")

        except Exception as e:
            logger.error(f"Error escalating alert {alert_id}: {e}")

    def _send_alert_notifications(self, alert: Alert):
        """Send notifications for a new alert"""
        try:
            for channel_id, channel in self.notification_channels.items():
                if not channel.enabled:
                    continue

                # Check severity filter
                if channel.severity_filter and alert.severity not in channel.severity_filter:
                    continue

                # Send notification based on channel type
                if channel.type == "email":
                    self._send_email_notification(channel, alert)
                elif channel.type == "slack":
                    self._send_slack_notification(channel, alert)
                elif channel.type == "webhook":
                    self._send_webhook_notification(channel, alert)

        except Exception as e:
            logger.error(f"Error sending alert notifications for {alert.id}: {e}")

    def _send_email_notification(self, channel: NotificationChannel, alert: Alert):
        """Send email notification"""
        try:
            config = channel.config

            # Create message
            msg = MIMEMultipart()
            msg['From'] = config['from_email']
            msg['To'] = ', '.join(config['to_emails'])
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"

            # Create email body
            body = f"""
Alert: {alert.title}
Severity: {alert.severity.value.upper()}
Component: {alert.component}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

Description:
{alert.description}

Tags: {', '.join(alert.tags)}

Metadata:
{json.dumps(alert.metadata, indent=2, default=str)}
"""

            msg.attach(MIMEText(body, 'plain'))

            # Send email
            with smtplib.SMTP(config['smtp_host'], config['smtp_port']) as server:
                server.starttls()
                server.login(config['smtp_user'], config['smtp_password'])
                server.send_message(msg)

            logger.info(f"Sent email notification for alert {alert.id}")

        except Exception as e:
            logger.error(f"Error sending email notification for alert {alert.id}: {e}")

    def _send_slack_notification(self, channel: NotificationChannel, alert: Alert):
        """Send Slack notification"""
        try:
            config = channel.config

            # Determine color based on severity
            color_map = {
                AlertSeverity.CRITICAL: "#FF0000",
                AlertSeverity.HIGH: "#FF8C00",
                AlertSeverity.MEDIUM: "#FFD700",
                AlertSeverity.LOW: "#32CD32",
                AlertSeverity.INFO: "#87CEEB"
            }

            # Create Slack message
            payload = {
                "channel": config['channel'],
                "username": config['username'],
                "attachments": [{
                    "color": color_map.get(alert.severity, "#808080"),
                    "title": f"🚨 {alert.title}",
                    "text": alert.description,
                    "fields": [
                        {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                        {"title": "Component", "value": alert.component, "short": True},
                        {"title": "Time", "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'), "short": True},
                        {"title": "Tags", "value": ', '.join(alert.tags), "short": True}
                    ],
                    "footer": "OpenCode-Slack Monitor",
                    "ts": int(alert.timestamp.timestamp())
                }]
            }

            # Send to Slack
            response = requests.post(config['webhook_url'], json=payload, timeout=10)
            response.raise_for_status()

            logger.info(f"Sent Slack notification for alert {alert.id}")

        except Exception as e:
            logger.error(f"Error sending Slack notification for alert {alert.id}: {e}")

    def _send_webhook_notification(self, channel: NotificationChannel, alert: Alert):
        """Send webhook notification"""
        try:
            config = channel.config

            # Create webhook payload
            payload = {
                "alert": asdict(alert),
                "timestamp": alert.timestamp.isoformat(),
                "source": "opencode-slack-monitor"
            }

            # Send webhook
            headers = config.get('headers', {})
            headers['Content-Type'] = 'application/json'

            response = requests.post(
                config['url'],
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()

            logger.info(f"Sent webhook notification for alert {alert.id}")

        except Exception as e:
            logger.error(f"Error sending webhook notification for alert {alert.id}: {e}")

    def _send_resolution_notification(self, alert: Alert):
        """Send notification when alert is resolved"""
        try:
            # Create resolution message for each channel
            for channel_id, channel in self.notification_channels.items():
                if not channel.enabled:
                    continue

                if channel.type == "slack":
                    self._send_slack_resolution(channel, alert)
                elif channel.type == "email":
                    self._send_email_resolution(channel, alert)

        except Exception as e:
            logger.error(f"Error sending resolution notification for {alert.id}: {e}")

    def _send_slack_resolution(self, channel: NotificationChannel, alert: Alert):
        """Send Slack resolution notification"""
        try:
            config = channel.config

            payload = {
                "channel": config['channel'],
                "username": config['username'],
                "attachments": [{
                    "color": "#32CD32",
                    "title": f"✅ RESOLVED: {alert.title}",
                    "text": f"Alert has been resolved",
                    "fields": [
                        {"title": "Component", "value": alert.component, "short": True},
                        {"title": "Duration", "value": str(alert.resolved_at - alert.timestamp), "short": True}
                    ],
                    "footer": "OpenCode-Slack Monitor",
                    "ts": int(alert.resolved_at.timestamp())
                }]
            }

            response = requests.post(config['webhook_url'], json=payload, timeout=10)
            response.raise_for_status()

        except Exception as e:
            logger.error(f"Error sending Slack resolution for alert {alert.id}: {e}")

    def _send_email_resolution(self, channel: NotificationChannel, alert: Alert):
        """Send email resolution notification"""
        try:
            config = channel.config

            msg = MIMEMultipart()
            msg['From'] = config['from_email']
            msg['To'] = ', '.join(config['to_emails'])
            msg['Subject'] = f"[RESOLVED] {alert.title}"

            duration = alert.resolved_at - alert.timestamp
            body = f"""
Alert RESOLVED: {alert.title}
Component: {alert.component}
Duration: {duration}
Resolved at: {alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S')}
"""

            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(config['smtp_host'], config['smtp_port']) as server:
                server.starttls()
                server.login(config['smtp_user'], config['smtp_password'])
                server.send_message(msg)

        except Exception as e:
            logger.error(f"Error sending email resolution for alert {alert.id}: {e}")

    def _send_escalation_notification(self, alert: Alert, escalation_config: Dict[str, Any]):
        """Send escalation notification"""
        try:
            # Get on-call person for this escalation level
            on_call_person = self._get_on_call_person(escalation_config.get('escalation_level', 1))

            logger.info(f"Escalating alert {alert.id} to {on_call_person}")

            # Send escalation notifications (implementation depends on escalation config)

        except Exception as e:
            logger.error(f"Error sending escalation notification for alert {alert.id}: {e}")

    def _get_on_call_person(self, escalation_level: int) -> str:
        """Get on-call person for escalation level"""
        try:
            if self.on_call_rotation and escalation_level <= len(self.on_call_rotation):
                return self.on_call_rotation[escalation_level - 1].get('name', 'Unknown')
            return 'Default On-Call'
        except Exception:
            return 'Unknown'

    # Public API methods

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        try:
            for alert in self.active_alerts.values():
                if alert.id == alert_id:
                    alert.status = AlertStatus.ACKNOWLEDGED
                    alert.acknowledged_by = acknowledged_by
                    alert.acknowledged_at = datetime.now()

                    # Cancel escalation timer
                    if alert_id in self.escalation_timers:
                        self.escalation_timers[alert_id].cancel()
                        del self.escalation_timers[alert_id]

                    logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return False

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        try:
            return [alert.to_dict() for alert in self.active_alerts.values()]
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []

    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            recent_alerts = [
                alert.to_dict() for alert in self.alert_history
                if alert.timestamp >= cutoff_time
            ]

            return recent_alerts

        except Exception as e:
            logger.error(f"Error getting alert history: {e}")
            return []

    def get_alerting_statistics(self) -> Dict[str, Any]:
        """Get alerting system statistics"""
        try:
            active_count = len(self.active_alerts)

            # Count by severity
            severity_counts = defaultdict(int)
            for alert in self.active_alerts.values():
                severity_counts[alert.severity.value] += 1

            # Count by status
            status_counts = defaultdict(int)
            for alert in self.alert_history:
                status_counts[alert.status.value] += 1

            return {
                'active_alerts': active_count,
                'total_rules': len(self.alert_rules),
                'enabled_rules': sum(1 for rule in self.alert_rules.values() if rule.enabled),
                'notification_channels': len(self.notification_channels),
                'enabled_channels': sum(1 for channel in self.notification_channels.values() if channel.enabled),
                'severity_distribution': dict(severity_counts),
                'status_distribution': dict(status_counts),
                'escalation_timers_active': len(self.escalation_timers),
                'correlations_active': len(self.alert_correlations)
            }

        except Exception as e:
            logger.error(f"Error getting alerting statistics: {e}")
            return {}