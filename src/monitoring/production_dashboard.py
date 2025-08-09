"""
Production-grade monitoring dashboard for OpenCode-Slack.
Implements real-time dashboards, role-based access, mobile-responsive interfaces,
and executive summary dashboards with comprehensive visualization.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from flask import Flask, render_template_string, jsonify, request, session, redirect, url_for
from flask_cors import CORS
import threading
import os

logger = logging.getLogger(__name__)


@dataclass
class DashboardUser:
    """Dashboard user with role-based access"""
    username: str
    role: str  # admin, operator, viewer, executive
    permissions: List[str]
    preferences: Dict[str, Any]


@dataclass
class DashboardWidget:
    """Dashboard widget configuration"""
    id: str
    title: str
    type: str  # chart, metric, table, alert, log
    config: Dict[str, Any]
    position: Dict[str, int]  # x, y, width, height
    refresh_interval: int = 30
    required_permission: str = "view"


class ProductionDashboard:
    """Production-grade monitoring dashboard system"""
    
    def __init__(self, metrics_collector, alerting_system, observability_system,
                 host: str = "0.0.0.0", port: int = 8083):
        """
        Initialize the production dashboard
        
        Args:
            metrics_collector: Production metrics collector instance
            alerting_system: Production alerting system instance
            observability_system: Production observability system instance
            host: Dashboard host
            port: Dashboard port
        """
        self.metrics_collector = metrics_collector
        self.alerting_system = alerting_system
        self.observability_system = observability_system
        self.host = host
        self.port = port
        
        # Dashboard state
        self.is_running = False
        self.dashboard_thread = None
        
        # User management
        self.users: Dict[str, DashboardUser] = {}
        self._setup_default_users()
        
        # Dashboard configurations
        self.dashboard_configs: Dict[str, List[DashboardWidget]] = {}
        self._setup_default_dashboards()
        
        # Flask app
        self.app = Flask(__name__)
        self.app.secret_key = os.environ.get('DASHBOARD_SECRET_KEY', 'dev-secret-key-change-in-production')
        CORS(self.app)
        
        # Setup routes
        self._setup_routes()
        
        logger.info(f"ProductionDashboard initialized on {host}:{port}")
    
    def _setup_default_users(self):
        """Setup default dashboard users"""
        default_users = [
            DashboardUser(
                username="admin",
                role="admin",
                permissions=["view", "edit", "admin", "alerts", "logs", "metrics"],
                preferences={"theme": "dark", "refresh_rate": 30}
            ),
            DashboardUser(
                username="operator",
                role="operator", 
                permissions=["view", "alerts", "logs", "metrics"],
                preferences={"theme": "light", "refresh_rate": 15}
            ),
            DashboardUser(
                username="viewer",
                role="viewer",
                permissions=["view", "metrics"],
                preferences={"theme": "light", "refresh_rate": 60}
            ),
            DashboardUser(
                username="executive",
                role="executive",
                permissions=["view", "metrics"],
                preferences={"theme": "light", "refresh_rate": 300}
            )
        ]
        
        for user in default_users:
            self.users[user.username] = user
    
    def _setup_default_dashboards(self):
        """Setup default dashboard configurations"""
        # Operations Dashboard
        self.dashboard_configs["operations"] = [
            DashboardWidget(
                id="system_overview",
                title="System Overview",
                type="metric",
                config={
                    "metrics": ["cpu_percent", "memory_percent", "disk_usage_percent"],
                    "thresholds": {"warning": 70, "critical": 85}
                },
                position={"x": 0, "y": 0, "width": 4, "height": 2}
            ),
            DashboardWidget(
                id="agent_status",
                title="Agent Status",
                type="chart",
                config={
                    "chart_type": "donut",
                    "data_source": "agent_status_distribution"
                },
                position={"x": 4, "y": 0, "width": 4, "height": 2}
            ),
            DashboardWidget(
                id="active_alerts",
                title="Active Alerts",
                type="alert",
                config={
                    "severity_filter": ["critical", "high"],
                    "max_items": 10
                },
                position={"x": 8, "y": 0, "width": 4, "height": 2}
            ),
            DashboardWidget(
                id="performance_metrics",
                title="Performance Metrics",
                type="chart",
                config={
                    "chart_type": "line",
                    "metrics": ["avg_response_time", "throughput"],
                    "time_range": "1h"
                },
                position={"x": 0, "y": 2, "width": 6, "height": 3}
            ),
            DashboardWidget(
                id="error_logs",
                title="Recent Errors",
                type="log",
                config={
                    "log_level": "ERROR",
                    "max_items": 20,
                    "time_range": "1h"
                },
                position={"x": 6, "y": 2, "width": 6, "height": 3}
            )
        ]
        
        # Executive Dashboard
        self.dashboard_configs["executive"] = [
            DashboardWidget(
                id="business_kpis",
                title="Business KPIs",
                type="metric",
                config={
                    "metrics": ["task_completion_rate", "agent_utilization", "system_uptime"],
                    "format": "percentage"
                },
                position={"x": 0, "y": 0, "width": 12, "height": 2}
            ),
            DashboardWidget(
                id="task_trends",
                title="Task Completion Trends",
                type="chart",
                config={
                    "chart_type": "area",
                    "metrics": ["tasks_completed", "tasks_assigned"],
                    "time_range": "24h"
                },
                position={"x": 0, "y": 2, "width": 8, "height": 3}
            ),
            DashboardWidget(
                id="system_health",
                title="System Health Score",
                type="metric",
                config={
                    "metric": "health_score",
                    "format": "gauge",
                    "thresholds": {"good": 80, "excellent": 95}
                },
                position={"x": 8, "y": 2, "width": 4, "height": 3}
            )
        ]
        
        # Performance Dashboard
        self.dashboard_configs["performance"] = [
            DashboardWidget(
                id="response_times",
                title="API Response Times",
                type="chart",
                config={
                    "chart_type": "line",
                    "metrics": ["p50_response_time", "p95_response_time", "p99_response_time"],
                    "time_range": "4h"
                },
                position={"x": 0, "y": 0, "width": 6, "height": 3}
            ),
            DashboardWidget(
                id="throughput",
                title="Request Throughput",
                type="chart",
                config={
                    "chart_type": "bar",
                    "metric": "requests_per_minute",
                    "time_range": "1h"
                },
                position={"x": 6, "y": 0, "width": 6, "height": 3}
            ),
            DashboardWidget(
                id="bottlenecks",
                title="Performance Bottlenecks",
                type="table",
                config={
                    "data_source": "performance_bottlenecks",
                    "columns": ["operation", "avg_duration", "bottleneck_type", "count"]
                },
                position={"x": 0, "y": 3, "width": 12, "height": 3}
            )
        ]
    
    def _setup_routes(self):
        """Setup Flask routes for dashboard"""
        
        @self.app.route('/')
        def index():
            """Main dashboard page"""
            if 'username' not in session:
                return redirect(url_for('login'))
            
            username = session['username']
            user = self.users.get(username)
            
            if not user:
                return redirect(url_for('login'))
            
            # Determine default dashboard based on role
            if user.role == "executive":
                default_dashboard = "executive"
            elif user.role in ["admin", "operator"]:
                default_dashboard = "operations"
            else:
                default_dashboard = "performance"
            
            return render_template_string(self._get_dashboard_template(), 
                                        user=user, 
                                        dashboard_type=default_dashboard)
        
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            """Login page"""
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                
                # Simple authentication (in production, use proper auth)
                if username in self.users and password == "demo":  # Demo password
                    session['username'] = username
                    return redirect(url_for('index'))
                else:
                    return render_template_string(self._get_login_template(), 
                                                error="Invalid credentials")
            
            return render_template_string(self._get_login_template())
        
        @self.app.route('/logout')
        def logout():
            """Logout"""
            session.pop('username', None)
            return redirect(url_for('login'))
        
        @self.app.route('/dashboard/<dashboard_type>')
        def dashboard(dashboard_type):
            """Specific dashboard page"""
            if 'username' not in session:
                return redirect(url_for('login'))
            
            username = session['username']
            user = self.users.get(username)
            
            if not user or dashboard_type not in self.dashboard_configs:
                return redirect(url_for('index'))
            
            return render_template_string(self._get_dashboard_template(), 
                                        user=user, 
                                        dashboard_type=dashboard_type)
        
        @self.app.route('/api/metrics')
        def api_metrics():
            """API endpoint for metrics data"""
            if not self._check_permission('metrics'):
                return jsonify({'error': 'Unauthorized'}), 403
            
            try:
                current_metrics = self.metrics_collector.get_current_metrics()
                return jsonify(current_metrics)
            except Exception as e:
                logger.error(f"Error getting metrics: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/alerts')
        def api_alerts():
            """API endpoint for alerts data"""
            if not self._check_permission('alerts'):
                return jsonify({'error': 'Unauthorized'}), 403
            
            try:
                active_alerts = self.alerting_system.get_active_alerts()
                return jsonify({'alerts': active_alerts})
            except Exception as e:
                logger.error(f"Error getting alerts: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/logs')
        def api_logs():
            """API endpoint for logs data"""
            if not self._check_permission('logs'):
                return jsonify({'error': 'Unauthorized'}), 403
            
            try:
                hours = int(request.args.get('hours', 1))
                level = request.args.get('level', 'ERROR')
                
                logs = self.observability_system.structured_logger.search_logs(
                    level=level, hours=hours
                )
                
                return jsonify({
                    'logs': [asdict(log) for log in logs[:100]]  # Limit to 100 entries
                })
            except Exception as e:
                logger.error(f"Error getting logs: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/performance')
        def api_performance():
            """API endpoint for performance data"""
            if not self._check_permission('metrics'):
                return jsonify({'error': 'Unauthorized'}), 403
            
            try:
                hours = int(request.args.get('hours', 4))
                performance_summary = self.observability_system.profiler.get_performance_summary(hours)
                return jsonify(performance_summary)
            except Exception as e:
                logger.error(f"Error getting performance data: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/health')
        def api_health():
            """API endpoint for system health"""
            if not self._check_permission('view'):
                return jsonify({'error': 'Unauthorized'}), 403
            
            try:
                health_data = self.observability_system.get_system_health()
                return jsonify(health_data)
            except Exception as e:
                logger.error(f"Error getting health data: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/dashboard/<dashboard_type>/config')
        def api_dashboard_config(dashboard_type):
            """API endpoint for dashboard configuration"""
            if not self._check_permission('view'):
                return jsonify({'error': 'Unauthorized'}), 403
            
            if dashboard_type not in self.dashboard_configs:
                return jsonify({'error': 'Dashboard not found'}), 404
            
            widgets = self.dashboard_configs[dashboard_type]
            return jsonify({
                'dashboard_type': dashboard_type,
                'widgets': [asdict(widget) for widget in widgets]
            })
        
        @self.app.route('/api/widget/<widget_id>/data')
        def api_widget_data(widget_id):
            """API endpoint for widget data"""
            if not self._check_permission('view'):
                return jsonify({'error': 'Unauthorized'}), 403
            
            try:
                # Find widget configuration
                widget = None
                for dashboard_widgets in self.dashboard_configs.values():
                    for w in dashboard_widgets:
                        if w.id == widget_id:
                            widget = w
                            break
                    if widget:
                        break
                
                if not widget:
                    return jsonify({'error': 'Widget not found'}), 404
                
                # Get widget data based on type
                data = self._get_widget_data(widget)
                return jsonify(data)
                
            except Exception as e:
                logger.error(f"Error getting widget data for {widget_id}: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/mobile')
        def mobile_dashboard():
            """Mobile-responsive dashboard"""
            if 'username' not in session:
                return redirect(url_for('login'))
            
            username = session['username']
            user = self.users.get(username)
            
            if not user:
                return redirect(url_for('login'))
            
            return render_template_string(self._get_mobile_template(), user=user)
    
    def _check_permission(self, permission: str) -> bool:
        """Check if current user has permission"""
        if 'username' not in session:
            return False
        
        username = session['username']
        user = self.users.get(username)
        
        return user and permission in user.permissions
    
    def _get_widget_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for a specific widget"""
        try:
            if widget.type == "metric":
                return self._get_metric_widget_data(widget)
            elif widget.type == "chart":
                return self._get_chart_widget_data(widget)
            elif widget.type == "alert":
                return self._get_alert_widget_data(widget)
            elif widget.type == "log":
                return self._get_log_widget_data(widget)
            elif widget.type == "table":
                return self._get_table_widget_data(widget)
            else:
                return {'error': f'Unknown widget type: {widget.type}'}
                
        except Exception as e:
            logger.error(f"Error getting data for widget {widget.id}: {e}")
            return {'error': str(e)}
    
    def _get_metric_widget_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for metric widget"""
        current_metrics = self.metrics_collector.get_current_metrics()
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'metrics': {}
        }
        
        for metric_name in widget.config.get('metrics', []):
            value = 0
            
            if metric_name == "cpu_percent":
                value = current_metrics.get('system', {}).get('cpu_percent', 0)
            elif metric_name == "memory_percent":
                value = current_metrics.get('system', {}).get('memory_percent', 0)
            elif metric_name == "disk_usage_percent":
                value = current_metrics.get('system', {}).get('disk_usage_percent', 0)
            elif metric_name == "agent_utilization":
                value = current_metrics.get('business', {}).get('agent_utilization_percent', 0)
            elif metric_name == "task_completion_rate":
                business = current_metrics.get('business', {})
                completed = business.get('tasks_completed', 0)
                assigned = business.get('total_tasks_assigned', 1)
                value = (completed / assigned * 100) if assigned > 0 else 0
            elif metric_name == "health_score":
                health_data = self.observability_system.get_system_health()
                value = health_data.get('health_score', 0)
            
            data['metrics'][metric_name] = {
                'value': value,
                'unit': '%' if 'percent' in metric_name or 'rate' in metric_name else '',
                'status': self._get_metric_status(value, widget.config.get('thresholds', {}))
            }
        
        return data
    
    def _get_chart_widget_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for chart widget"""
        time_range = widget.config.get('time_range', '1h')
        hours = self._parse_time_range(time_range)
        
        # Get historical metrics
        history = self.metrics_collector.get_metrics_history(hours)
        
        data = {
            'chart_type': widget.config.get('chart_type', 'line'),
            'time_range': time_range,
            'series': []
        }
        
        if widget.config.get('data_source') == 'agent_status_distribution':
            # Special case for agent status distribution
            current_metrics = self.metrics_collector.get_current_metrics()
            business = current_metrics.get('business', {})
            
            data['series'] = [
                {'name': 'Active', 'value': business.get('active_agents', 0)},
                {'name': 'Idle', 'value': business.get('idle_agents', 0)},
                {'name': 'Stuck', 'value': business.get('stuck_agents', 0)}
            ]
        else:
            # Time series data
            for metric_name in widget.config.get('metrics', []):
                series_data = []
                
                for entry in history.get('system', []):
                    timestamp = entry.get('timestamp')
                    value = entry.get(metric_name, 0)
                    series_data.append({'x': timestamp, 'y': value})
                
                data['series'].append({
                    'name': metric_name,
                    'data': series_data
                })
        
        return data
    
    def _get_alert_widget_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for alert widget"""
        active_alerts = self.alerting_system.get_active_alerts()
        
        # Filter by severity if specified
        severity_filter = widget.config.get('severity_filter', [])
        if severity_filter:
            active_alerts = [
                alert for alert in active_alerts
                if alert.get('severity') in severity_filter
            ]
        
        # Limit number of items
        max_items = widget.config.get('max_items', 10)
        active_alerts = active_alerts[:max_items]
        
        return {
            'alerts': active_alerts,
            'total_count': len(active_alerts)
        }
    
    def _get_log_widget_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for log widget"""
        time_range = widget.config.get('time_range', '1h')
        hours = self._parse_time_range(time_range)
        log_level = widget.config.get('log_level', 'ERROR')
        max_items = widget.config.get('max_items', 20)
        
        logs = self.observability_system.structured_logger.search_logs(
            level=log_level, hours=hours
        )
        
        return {
            'logs': [asdict(log) for log in logs[:max_items]],
            'total_count': len(logs)
        }
    
    def _get_table_widget_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for table widget"""
        data_source = widget.config.get('data_source')
        
        if data_source == 'performance_bottlenecks':
            # Get performance bottlenecks
            performance_summary = self.observability_system.profiler.get_performance_summary(4)
            operation_stats = performance_summary.get('operation_stats', {})
            
            rows = []
            for operation, stats in operation_stats.items():
                rows.append({
                    'operation': operation,
                    'avg_duration': f"{stats['avg_duration_ms']:.2f}ms",
                    'bottleneck_type': 'high_duration' if stats['avg_duration_ms'] > 1000 else 'normal',
                    'count': stats['count']
                })
            
            return {
                'columns': widget.config.get('columns', []),
                'rows': rows
            }
        
        return {'columns': [], 'rows': []}
    
    def _get_metric_status(self, value: float, thresholds: Dict[str, float]) -> str:
        """Get metric status based on thresholds"""
        if 'critical' in thresholds and value >= thresholds['critical']:
            return 'critical'
        elif 'warning' in thresholds and value >= thresholds['warning']:
            return 'warning'
        elif 'good' in thresholds and value >= thresholds['good']:
            return 'good'
        elif 'excellent' in thresholds and value >= thresholds['excellent']:
            return 'excellent'
        else:
            return 'normal'
    
    def _parse_time_range(self, time_range: str) -> int:
        """Parse time range string to hours"""
        if time_range.endswith('h'):
            return int(time_range[:-1])
        elif time_range.endswith('d'):
            return int(time_range[:-1]) * 24
        elif time_range.endswith('m'):
            return max(1, int(time_range[:-1]) // 60)
        else:
            return 1  # Default to 1 hour
    
    def _get_dashboard_template(self) -> str:
        """Get main dashboard HTML template"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenCode-Slack Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
        }
        .header {
            background: #2c3e50;
            color: white;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .nav {
            background: #34495e;
            padding: 0.5rem 2rem;
        }
        .nav a {
            color: #ecf0f1;
            text-decoration: none;
            margin-right: 2rem;
            padding: 0.5rem 1rem;
            border-radius: 4px;
        }
        .nav a:hover, .nav a.active {
            background: #3498db;
        }
        .dashboard {
            padding: 2rem;
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 1rem;
            max-width: 1400px;
            margin: 0 auto;
        }
        .widget {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 1.5rem;
            position: relative;
        }
        .widget h3 {
            margin-bottom: 1rem;
            color: #2c3e50;
            font-size: 1.1rem;
        }
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin: 0.5rem 0;
        }
        .metric-value.critical { color: #e74c3c; }
        .metric-value.warning { color: #f39c12; }
        .metric-value.good { color: #27ae60; }
        .metric-value.excellent { color: #2ecc71; }
        .metric-unit {
            font-size: 1rem;
            color: #7f8c8d;
            margin-left: 0.5rem;
        }
        .alert-item {
            padding: 0.75rem;
            margin: 0.5rem 0;
            border-radius: 4px;
            border-left: 4px solid;
        }
        .alert-critical { border-color: #e74c3c; background: #fdf2f2; }
        .alert-high { border-color: #f39c12; background: #fef9e7; }
        .alert-medium { border-color: #3498db; background: #ebf3fd; }
        .log-entry {
            font-family: monospace;
            font-size: 0.85rem;
            padding: 0.5rem;
            margin: 0.25rem 0;
            background: #f8f9fa;
            border-radius: 4px;
            border-left: 3px solid #e74c3c;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }
        .status-ok { background: #27ae60; }
        .status-warning { background: #f39c12; }
        .status-error { background: #e74c3c; }
        .refresh-indicator {
            position: absolute;
            top: 1rem;
            right: 1rem;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #27ae60;
        }
        @media (max-width: 768px) {
            .dashboard {
                grid-template-columns: 1fr;
                padding: 1rem;
            }
            .widget {
                grid-column: 1 !important;
                grid-row: auto !important;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 OpenCode-Slack Monitor</h1>
        <div>
            <span>{{ user.role.title() }}: {{ user.username }}</span>
            <a href="/logout" style="color: #ecf0f1; margin-left: 1rem;">Logout</a>
        </div>
    </div>
    
    <div class="nav">
        <a href="/dashboard/operations" class="{{ 'active' if dashboard_type == 'operations' else '' }}">Operations</a>
        <a href="/dashboard/performance" class="{{ 'active' if dashboard_type == 'performance' else '' }}">Performance</a>
        <a href="/dashboard/executive" class="{{ 'active' if dashboard_type == 'executive' else '' }}">Executive</a>
        <a href="/mobile">Mobile</a>
    </div>
    
    <div class="dashboard" id="dashboard">
        <!-- Widgets will be loaded here -->
    </div>
    
    <script>
        const dashboardType = '{{ dashboard_type }}';
        const refreshInterval = {{ user.preferences.get('refresh_rate', 30) }} * 1000;
        let widgets = [];
        
        async function loadDashboard() {
            try {
                const response = await fetch(`/api/dashboard/${dashboardType}/config`);
                const config = await response.json();
                widgets = config.widgets;
                
                renderWidgets();
                loadAllWidgetData();
            } catch (error) {
                console.error('Error loading dashboard:', error);
            }
        }
        
        function renderWidgets() {
            const dashboard = document.getElementById('dashboard');
            dashboard.innerHTML = '';
            
            widgets.forEach(widget => {
                const widgetEl = document.createElement('div');
                widgetEl.className = 'widget';
                widgetEl.id = `widget-${widget.id}`;
                widgetEl.style.gridColumn = `${widget.position.x + 1} / span ${widget.position.width}`;
                widgetEl.style.gridRow = `${widget.position.y + 1} / span ${widget.position.height}`;
                
                widgetEl.innerHTML = `
                    <div class="refresh-indicator" id="refresh-${widget.id}"></div>
                    <h3>${widget.title}</h3>
                    <div id="content-${widget.id}">Loading...</div>
                `;
                
                dashboard.appendChild(widgetEl);
            });
        }
        
        async function loadAllWidgetData() {
            for (const widget of widgets) {
                await loadWidgetData(widget);
            }
        }
        
        async function loadWidgetData(widget) {
            try {
                const response = await fetch(`/api/widget/${widget.id}/data`);
                const data = await response.json();
                
                renderWidgetData(widget, data);
                
                // Flash refresh indicator
                const indicator = document.getElementById(`refresh-${widget.id}`);
                if (indicator) {
                    indicator.style.background = '#3498db';
                    setTimeout(() => {
                        indicator.style.background = '#27ae60';
                    }, 200);
                }
            } catch (error) {
                console.error(`Error loading widget ${widget.id}:`, error);
                document.getElementById(`content-${widget.id}`).innerHTML = 'Error loading data';
            }
        }
        
        function renderWidgetData(widget, data) {
            const contentEl = document.getElementById(`content-${widget.id}`);
            
            if (widget.type === 'metric') {
                renderMetricWidget(contentEl, data);
            } else if (widget.type === 'chart') {
                renderChartWidget(contentEl, data, widget.id);
            } else if (widget.type === 'alert') {
                renderAlertWidget(contentEl, data);
            } else if (widget.type === 'log') {
                renderLogWidget(contentEl, data);
            } else if (widget.type === 'table') {
                renderTableWidget(contentEl, data);
            }
        }
        
        function renderMetricWidget(contentEl, data) {
            let html = '';
            
            for (const [metricName, metricData] of Object.entries(data.metrics)) {
                html += `
                    <div style="margin-bottom: 1rem;">
                        <div class="metric-value ${metricData.status}">
                            ${metricData.value.toFixed(1)}
                            <span class="metric-unit">${metricData.unit}</span>
                        </div>
                        <div style="font-size: 0.9rem; color: #7f8c8d;">
                            ${metricName.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}
                        </div>
                    </div>
                `;
            }
            
            contentEl.innerHTML = html;
        }
        
        function renderChartWidget(contentEl, data, widgetId) {
            if (data.chart_type === 'donut') {
                contentEl.innerHTML = `<canvas id="chart-${widgetId}" width="300" height="200"></canvas>`;
                
                const ctx = document.getElementById(`chart-${widgetId}`).getContext('2d');
                new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: data.series.map(s => s.name),
                        datasets: [{
                            data: data.series.map(s => s.value),
                            backgroundColor: ['#27ae60', '#3498db', '#e74c3c']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false
                    }
                });
            } else {
                contentEl.innerHTML = `<canvas id="chart-${widgetId}" width="400" height="200"></canvas>`;
                
                const ctx = document.getElementById(`chart-${widgetId}`).getContext('2d');
                new Chart(ctx, {
                    type: data.chart_type,
                    data: {
                        datasets: data.series.map((series, index) => ({
                            label: series.name,
                            data: series.data,
                            borderColor: ['#3498db', '#e74c3c', '#f39c12'][index % 3],
                            backgroundColor: ['#3498db20', '#e74c3c20', '#f39c1220'][index % 3],
                            fill: data.chart_type === 'area'
                        }))
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { type: 'time' },
                            y: { beginAtZero: true }
                        }
                    }
                });
            }
        }
        
        function renderAlertWidget(contentEl, data) {
            if (data.alerts.length === 0) {
                contentEl.innerHTML = '<div style="color: #27ae60;">✅ No active alerts</div>';
                return;
            }
            
            let html = '';
            data.alerts.forEach(alert => {
                html += `
                    <div class="alert-item alert-${alert.severity}">
                        <div style="font-weight: bold;">${alert.title}</div>
                        <div style="font-size: 0.9rem; margin-top: 0.25rem;">
                            ${alert.description}
                        </div>
                        <div style="font-size: 0.8rem; color: #7f8c8d; margin-top: 0.25rem;">
                            ${new Date(alert.timestamp).toLocaleString()}
                        </div>
                    </div>
                `;
            });
            
            contentEl.innerHTML = html;
        }
        
        function renderLogWidget(contentEl, data) {
            if (data.logs.length === 0) {
                contentEl.innerHTML = '<div style="color: #27ae60;">No recent errors</div>';
                return;
            }
            
            let html = '';
            data.logs.forEach(log => {
                html += `
                    <div class="log-entry">
                        <div style="font-weight: bold;">
                            ${new Date(log.timestamp).toLocaleTimeString()} - ${log.component}
                        </div>
                        <div>${log.message}</div>
                    </div>
                `;
            });
            
            contentEl.innerHTML = html;
        }
        
        function renderTableWidget(contentEl, data) {
            if (data.rows.length === 0) {
                contentEl.innerHTML = '<div>No data available</div>';
                return;
            }
            
            let html = '<table style="width: 100%; border-collapse: collapse;">';
            
            // Header
            html += '<thead><tr>';
            data.columns.forEach(col => {
                html += `<th style="text-align: left; padding: 0.5rem; border-bottom: 2px solid #ecf0f1;">${col}</th>`;
            });
            html += '</tr></thead>';
            
            // Rows
            html += '<tbody>';
            data.rows.forEach(row => {
                html += '<tr>';
                data.columns.forEach(col => {
                    html += `<td style="padding: 0.5rem; border-bottom: 1px solid #ecf0f1;">${row[col] || ''}</td>`;
                });
                html += '</tr>';
            });
            html += '</tbody></table>';
            
            contentEl.innerHTML = html;
        }
        
        // Auto-refresh
        setInterval(loadAllWidgetData, refreshInterval);
        
        // Initial load
        loadDashboard();
    </script>
</body>
</html>
        '''
    
    def _get_login_template(self) -> str:
        """Get login page HTML template"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenCode-Slack Monitor - Login</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
        }
        .login-container {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
        }
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .form-group {
            margin-bottom: 1rem;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
        }
        button {
            width: 100%;
            padding: 0.75rem;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 1rem;
            cursor: pointer;
        }
        button:hover {
            background: #2980b9;
        }
        .error {
            color: #e74c3c;
            margin-top: 1rem;
            text-align: center;
        }
        .demo-info {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            margin-top: 1rem;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1>🔍 OpenCode-Slack Monitor</h1>
            <p>Production Monitoring Dashboard</p>
        </div>
        
        <form method="post">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            
            <button type="submit">Login</button>
        </form>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        <div class="demo-info">
            <strong>Demo Accounts:</strong><br>
            • admin / demo (Full access)<br>
            • operator / demo (Operations access)<br>
            • viewer / demo (Read-only access)<br>
            • executive / demo (Executive dashboard)
        </div>
    </div>
</body>
</html>
        '''
    
    def _get_mobile_template(self) -> str:
        """Get mobile dashboard HTML template"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenCode-Slack Monitor - Mobile</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
        }
        .mobile-header {
            background: #2c3e50;
            color: white;
            padding: 1rem;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .mobile-content {
            padding: 1rem;
        }
        .mobile-card {
            background: white;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .mobile-metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 0;
            border-bottom: 1px solid #ecf0f1;
        }
        .mobile-metric:last-child {
            border-bottom: none;
        }
        .metric-name {
            font-weight: 500;
        }
        .metric-value {
            font-size: 1.2rem;
            font-weight: bold;
        }
        .status-good { color: #27ae60; }
        .status-warning { color: #f39c12; }
        .status-critical { color: #e74c3c; }
        .refresh-button {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: #3498db;
            color: white;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
    </style>
</head>
<body>
    <div class="mobile-header">
        <h1>🔍 Monitor</h1>
        <div style="font-size: 0.9rem; opacity: 0.8;">{{ user.username }} - {{ user.role.title() }}</div>
    </div>
    
    <div class="mobile-content">
        <div class="mobile-card">
            <h3>System Status</h3>
            <div id="system-metrics">Loading...</div>
        </div>
        
        <div class="mobile-card">
            <h3>Active Alerts</h3>
            <div id="active-alerts">Loading...</div>
        </div>
        
        <div class="mobile-card">
            <h3>Agent Status</h3>
            <div id="agent-status">Loading...</div>
        </div>
    </div>
    
    <button class="refresh-button" onclick="loadMobileData()">🔄</button>
    
    <script>
        async function loadMobileData() {
            try {
                // Load system metrics
                const metricsResponse = await fetch('/api/metrics');
                const metrics = await metricsResponse.json();
                
                const systemEl = document.getElementById('system-metrics');
                const system = metrics.system || {};
                systemEl.innerHTML = `
                    <div class="mobile-metric">
                        <span class="metric-name">CPU Usage</span>
                        <span class="metric-value ${getStatusClass(system.cpu_percent, 70, 85)}">${(system.cpu_percent || 0).toFixed(1)}%</span>
                    </div>
                    <div class="mobile-metric">
                        <span class="metric-name">Memory Usage</span>
                        <span class="metric-value ${getStatusClass(system.memory_percent, 70, 85)}">${(system.memory_percent || 0).toFixed(1)}%</span>
                    </div>
                    <div class="mobile-metric">
                        <span class="metric-name">Disk Usage</span>
                        <span class="metric-value ${getStatusClass(system.disk_usage_percent, 80, 90)}">${(system.disk_usage_percent || 0).toFixed(1)}%</span>
                    </div>
                `;
                
                // Load alerts
                const alertsResponse = await fetch('/api/alerts');
                const alertsData = await alertsResponse.json();
                
                const alertsEl = document.getElementById('active-alerts');
                if (alertsData.alerts && alertsData.alerts.length > 0) {
                    alertsEl.innerHTML = alertsData.alerts.slice(0, 3).map(alert => `
                        <div class="mobile-metric">
                            <span class="metric-name">${alert.title}</span>
                            <span class="metric-value status-${alert.severity}">${alert.severity.toUpperCase()}</span>
                        </div>
                    `).join('');
                } else {
                    alertsEl.innerHTML = '<div style="color: #27ae60; text-align: center;">✅ No active alerts</div>';
                }
                
                // Load agent status
                const business = metrics.business || {};
                const agentEl = document.getElementById('agent-status');
                agentEl.innerHTML = `
                    <div class="mobile-metric">
                        <span class="metric-name">Active Agents</span>
                        <span class="metric-value status-good">${business.active_agents || 0}</span>
                    </div>
                    <div class="mobile-metric">
                        <span class="metric-name">Idle Agents</span>
                        <span class="metric-value">${business.idle_agents || 0}</span>
                    </div>
                    <div class="mobile-metric">
                        <span class="metric-name">Stuck Agents</span>
                        <span class="metric-value ${business.stuck_agents > 0 ? 'status-critical' : 'status-good'}">${business.stuck_agents || 0}</span>
                    </div>
                `;
                
            } catch (error) {
                console.error('Error loading mobile data:', error);
            }
        }
        
        function getStatusClass(value, warning, critical) {
            if (value >= critical) return 'status-critical';
            if (value >= warning) return 'status-warning';
            return 'status-good';
        }
        
        // Auto-refresh every 30 seconds
        setInterval(loadMobileData, 30000);
        
        // Initial load
        loadMobileData();
    </script>
</body>
</html>
        '''
    
    def start(self):
        """Start the dashboard server"""
        if self.is_running:
            logger.warning("Dashboard server is already running")
            return
        
        self.is_running = True
        self.dashboard_thread = threading.Thread(target=self._run_server, daemon=True)
        self.dashboard_thread.start()
        
        logger.info(f"Production dashboard started on http://{self.host}:{self.port}")
        print(f"🎛️  Production Dashboard: http://{self.host}:{self.port}")
        print(f"📱 Mobile Dashboard: http://{self.host}:{self.port}/mobile")
    
    def stop(self):
        """Stop the dashboard server"""
        if not self.is_running:
            logger.warning("Dashboard server is not running")
            return
        
        self.is_running = False
        logger.info("Production dashboard stopped")
    
    def _run_server(self):
        """Run the Flask server"""
        try:
            self.app.run(
                host=self.host,
                port=self.port,
                debug=False,
                threaded=True,
                use_reloader=False
            )
        except Exception as e:
            logger.error(f"Error running dashboard server: {e}")
            self.is_running = False