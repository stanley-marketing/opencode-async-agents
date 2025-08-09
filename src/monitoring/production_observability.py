"""
Production-grade observability system for OpenCode-Slack.
Implements distributed tracing, structured logging with correlation IDs,
performance profiling, and bottleneck identification.
"""

import logging
import threading
import time
import json
import uuid
import traceback
import functools
import inspect
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
from contextlib import contextmanager
import sys
import os

logger = logging.getLogger(__name__)


@dataclass
class TraceSpan:
    """Distributed tracing span"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"  # ok, error, timeout
    error_message: Optional[str] = None


@dataclass
class StructuredLogEntry:
    """Structured log entry with correlation"""
    timestamp: datetime
    level: str
    message: str
    correlation_id: str
    trace_id: Optional[str]
    span_id: Optional[str]
    service: str
    component: str
    tags: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceProfile:
    """Performance profiling data"""
    profile_id: str
    operation: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    cpu_time_ms: float
    memory_usage_mb: float
    call_stack: List[str]
    bottlenecks: List[Dict[str, Any]]
    tags: Dict[str, Any] = field(default_factory=dict)


class CorrelationContext:
    """Thread-local correlation context"""
    
    def __init__(self):
        self._local = threading.local()
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for current thread"""
        self._local.correlation_id = correlation_id
    
    def get_correlation_id(self) -> Optional[str]:
        """Get correlation ID for current thread"""
        return getattr(self._local, 'correlation_id', None)
    
    def set_trace_context(self, trace_id: str, span_id: str):
        """Set trace context for current thread"""
        self._local.trace_id = trace_id
        self._local.span_id = span_id
    
    def get_trace_context(self) -> tuple:
        """Get trace context for current thread"""
        trace_id = getattr(self._local, 'trace_id', None)
        span_id = getattr(self._local, 'span_id', None)
        return trace_id, span_id
    
    def clear(self):
        """Clear correlation context"""
        for attr in ['correlation_id', 'trace_id', 'span_id']:
            if hasattr(self._local, attr):
                delattr(self._local, attr)


class DistributedTracer:
    """Distributed tracing implementation"""
    
    def __init__(self, service_name: str = "opencode-slack"):
        self.service_name = service_name
        self.active_spans: Dict[str, TraceSpan] = {}
        self.completed_spans: deque = deque(maxlen=10000)
        self.span_stack: Dict[str, List[str]] = defaultdict(list)  # Thread ID -> span stack
        
    def start_span(self, operation_name: str, parent_span_id: Optional[str] = None,
                   tags: Optional[Dict[str, Any]] = None) -> TraceSpan:
        """Start a new trace span"""
        span_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4()) if not parent_span_id else self._get_trace_id(parent_span_id)
        
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=self.service_name,
            start_time=datetime.now(),
            tags=tags or {}
        )
        
        self.active_spans[span_id] = span
        
        # Add to span stack for current thread
        thread_id = threading.get_ident()
        self.span_stack[thread_id].append(span_id)
        
        return span
    
    def finish_span(self, span_id: str, status: str = "ok", error_message: Optional[str] = None):
        """Finish a trace span"""
        if span_id in self.active_spans:
            span = self.active_spans[span_id]
            span.end_time = datetime.now()
            span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
            span.status = status
            span.error_message = error_message
            
            # Move to completed spans
            self.completed_spans.append(span)
            del self.active_spans[span_id]
            
            # Remove from span stack
            thread_id = threading.get_ident()
            if thread_id in self.span_stack and span_id in self.span_stack[thread_id]:
                self.span_stack[thread_id].remove(span_id)
    
    def add_span_tag(self, span_id: str, key: str, value: Any):
        """Add tag to span"""
        if span_id in self.active_spans:
            self.active_spans[span_id].tags[key] = value
    
    def add_span_log(self, span_id: str, message: str, level: str = "info", **kwargs):
        """Add log entry to span"""
        if span_id in self.active_spans:
            log_entry = {
                'timestamp': datetime.now(),
                'level': level,
                'message': message,
                **kwargs
            }
            self.active_spans[span_id].logs.append(log_entry)
    
    def get_current_span(self) -> Optional[TraceSpan]:
        """Get current active span for thread"""
        thread_id = threading.get_ident()
        if thread_id in self.span_stack and self.span_stack[thread_id]:
            span_id = self.span_stack[thread_id][-1]
            return self.active_spans.get(span_id)
        return None
    
    def _get_trace_id(self, span_id: str) -> str:
        """Get trace ID for a span"""
        if span_id in self.active_spans:
            return self.active_spans[span_id].trace_id
        
        # Search in completed spans
        for span in self.completed_spans:
            if span.span_id == span_id:
                return span.trace_id
        
        return str(uuid.uuid4())  # Fallback
    
    @contextmanager
    def trace(self, operation_name: str, tags: Optional[Dict[str, Any]] = None):
        """Context manager for tracing operations"""
        current_span = self.get_current_span()
        parent_span_id = current_span.span_id if current_span else None
        
        span = self.start_span(operation_name, parent_span_id, tags)
        
        try:
            yield span
            self.finish_span(span.span_id, "ok")
        except Exception as e:
            self.finish_span(span.span_id, "error", str(e))
            raise
    
    def get_trace_data(self, trace_id: str) -> List[TraceSpan]:
        """Get all spans for a trace"""
        spans = []
        
        # Check active spans
        for span in self.active_spans.values():
            if span.trace_id == trace_id:
                spans.append(span)
        
        # Check completed spans
        for span in self.completed_spans:
            if span.trace_id == trace_id:
                spans.append(span)
        
        return sorted(spans, key=lambda s: s.start_time)


class StructuredLogger:
    """Structured logging with correlation IDs"""
    
    def __init__(self, service_name: str = "opencode-slack", 
                 correlation_context: Optional[CorrelationContext] = None):
        self.service_name = service_name
        self.correlation_context = correlation_context or CorrelationContext()
        self.log_entries: deque = deque(maxlen=50000)
        
        # Setup structured logging formatter
        self._setup_structured_logging()
    
    def _setup_structured_logging(self):
        """Setup structured logging formatter"""
        class StructuredFormatter(logging.Formatter):
            def __init__(self, structured_logger):
                super().__init__()
                self.structured_logger = structured_logger
            
            def format(self, record):
                # Get correlation context
                correlation_id = self.structured_logger.correlation_context.get_correlation_id()
                trace_id, span_id = self.structured_logger.correlation_context.get_trace_context()
                
                # Create structured log entry
                log_entry = StructuredLogEntry(
                    timestamp=datetime.fromtimestamp(record.created),
                    level=record.levelname,
                    message=record.getMessage(),
                    correlation_id=correlation_id or "unknown",
                    trace_id=trace_id,
                    span_id=span_id,
                    service=self.structured_logger.service_name,
                    component=record.name,
                    tags={
                        'filename': record.filename,
                        'lineno': record.lineno,
                        'funcName': record.funcName
                    },
                    metadata=getattr(record, 'metadata', {})
                )
                
                # Store log entry
                self.structured_logger.log_entries.append(log_entry)
                
                # Format for console output
                correlation_part = f"[{correlation_id[:8] if correlation_id else 'unknown'}]"
                trace_part = f"[{trace_id[:8] if trace_id else 'no-trace'}]"
                
                return f"{log_entry.timestamp.isoformat()} {correlation_part}{trace_part} {record.levelname} {record.name}: {record.getMessage()}"
        
        # Apply formatter to root logger
        formatter = StructuredFormatter(self)
        
        # Get or create console handler
        console_handler = None
        for handler in logging.root.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                console_handler = handler
                break
        
        if not console_handler:
            console_handler = logging.StreamHandler(sys.stdout)
            logging.root.addHandler(console_handler)
        
        console_handler.setFormatter(formatter)
    
    def log_with_correlation(self, level: str, message: str, correlation_id: Optional[str] = None,
                           component: str = "unknown", **metadata):
        """Log message with correlation ID"""
        if correlation_id:
            self.correlation_context.set_correlation_id(correlation_id)
        
        # Get logger for component
        component_logger = logging.getLogger(component)
        
        # Add metadata to log record
        extra = {'metadata': metadata}
        
        # Log at appropriate level
        if level.upper() == 'DEBUG':
            component_logger.debug(message, extra=extra)
        elif level.upper() == 'INFO':
            component_logger.info(message, extra=extra)
        elif level.upper() == 'WARNING':
            component_logger.warning(message, extra=extra)
        elif level.upper() == 'ERROR':
            component_logger.error(message, extra=extra)
        elif level.upper() == 'CRITICAL':
            component_logger.critical(message, extra=extra)
    
    def search_logs(self, correlation_id: Optional[str] = None, 
                   trace_id: Optional[str] = None,
                   component: Optional[str] = None,
                   level: Optional[str] = None,
                   hours: int = 24) -> List[StructuredLogEntry]:
        """Search log entries by criteria"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        results = []
        for entry in self.log_entries:
            if entry.timestamp < cutoff_time:
                continue
            
            if correlation_id and entry.correlation_id != correlation_id:
                continue
            
            if trace_id and entry.trace_id != trace_id:
                continue
            
            if component and entry.component != component:
                continue
            
            if level and entry.level != level:
                continue
            
            results.append(entry)
        
        return sorted(results, key=lambda e: e.timestamp, reverse=True)


class PerformanceProfiler:
    """Performance profiling and bottleneck identification"""
    
    def __init__(self):
        self.profiles: deque = deque(maxlen=1000)
        self.active_profiles: Dict[str, Dict[str, Any]] = {}
        
    def start_profiling(self, operation: str, tags: Optional[Dict[str, Any]] = None) -> str:
        """Start performance profiling for an operation"""
        profile_id = str(uuid.uuid4())
        
        self.active_profiles[profile_id] = {
            'operation': operation,
            'start_time': datetime.now(),
            'start_cpu_time': time.process_time(),
            'start_memory': self._get_memory_usage(),
            'tags': tags or {},
            'call_stack': self._get_call_stack()
        }
        
        return profile_id
    
    def finish_profiling(self, profile_id: str) -> Optional[PerformanceProfile]:
        """Finish performance profiling"""
        if profile_id not in self.active_profiles:
            return None
        
        profile_data = self.active_profiles[profile_id]
        end_time = datetime.now()
        end_cpu_time = time.process_time()
        end_memory = self._get_memory_usage()
        
        duration_ms = (end_time - profile_data['start_time']).total_seconds() * 1000
        cpu_time_ms = (end_cpu_time - profile_data['start_cpu_time']) * 1000
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(duration_ms, cpu_time_ms, profile_data)
        
        profile = PerformanceProfile(
            profile_id=profile_id,
            operation=profile_data['operation'],
            start_time=profile_data['start_time'],
            end_time=end_time,
            duration_ms=duration_ms,
            cpu_time_ms=cpu_time_ms,
            memory_usage_mb=end_memory - profile_data['start_memory'],
            call_stack=profile_data['call_stack'],
            bottlenecks=bottlenecks,
            tags=profile_data['tags']
        )
        
        self.profiles.append(profile)
        del self.active_profiles[profile_id]
        
        return profile
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            return 0.0
    
    def _get_call_stack(self) -> List[str]:
        """Get current call stack"""
        stack = []
        frame = inspect.currentframe()
        
        try:
            # Skip profiler frames
            for _ in range(3):
                frame = frame.f_back
                if not frame:
                    break
            
            # Collect call stack
            while frame and len(stack) < 10:
                filename = frame.f_code.co_filename
                function = frame.f_code.co_name
                lineno = frame.f_lineno
                
                # Skip system/library frames
                if not any(skip in filename for skip in ['/lib/', '/site-packages/', '<frozen']):
                    stack.append(f"{os.path.basename(filename)}:{function}:{lineno}")
                
                frame = frame.f_back
        finally:
            del frame
        
        return stack
    
    def _identify_bottlenecks(self, duration_ms: float, cpu_time_ms: float, 
                            profile_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # High duration bottleneck
        if duration_ms > 1000:  # More than 1 second
            bottlenecks.append({
                'type': 'high_duration',
                'severity': 'high' if duration_ms > 5000 else 'medium',
                'description': f"Operation took {duration_ms:.2f}ms",
                'recommendation': 'Consider optimizing algorithm or adding caching'
            })
        
        # High CPU usage bottleneck
        cpu_ratio = cpu_time_ms / duration_ms if duration_ms > 0 else 0
        if cpu_ratio > 0.8:  # More than 80% CPU bound
            bottlenecks.append({
                'type': 'cpu_bound',
                'severity': 'medium',
                'description': f"Operation is {cpu_ratio*100:.1f}% CPU bound",
                'recommendation': 'Consider algorithm optimization or parallelization'
            })
        
        # I/O bound detection
        if cpu_ratio < 0.2 and duration_ms > 500:  # Less than 20% CPU, more than 500ms
            bottlenecks.append({
                'type': 'io_bound',
                'severity': 'medium',
                'description': f"Operation appears I/O bound (CPU: {cpu_ratio*100:.1f}%)",
                'recommendation': 'Consider async operations or connection pooling'
            })
        
        return bottlenecks
    
    @contextmanager
    def profile(self, operation: str, tags: Optional[Dict[str, Any]] = None):
        """Context manager for profiling operations"""
        profile_id = self.start_profiling(operation, tags)
        
        try:
            yield profile_id
        finally:
            self.finish_profiling(profile_id)
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_profiles = [p for p in self.profiles if p.start_time >= cutoff_time]
        
        if not recent_profiles:
            return {}
        
        # Calculate statistics
        durations = [p.duration_ms for p in recent_profiles]
        cpu_times = [p.cpu_time_ms for p in recent_profiles]
        
        # Group by operation
        by_operation = defaultdict(list)
        for profile in recent_profiles:
            by_operation[profile.operation].append(profile)
        
        operation_stats = {}
        for operation, profiles in by_operation.items():
            op_durations = [p.duration_ms for p in profiles]
            operation_stats[operation] = {
                'count': len(profiles),
                'avg_duration_ms': sum(op_durations) / len(op_durations),
                'max_duration_ms': max(op_durations),
                'min_duration_ms': min(op_durations)
            }
        
        # Count bottlenecks
        bottleneck_counts = defaultdict(int)
        for profile in recent_profiles:
            for bottleneck in profile.bottlenecks:
                bottleneck_counts[bottleneck['type']] += 1
        
        return {
            'total_profiles': len(recent_profiles),
            'avg_duration_ms': sum(durations) / len(durations),
            'max_duration_ms': max(durations),
            'avg_cpu_time_ms': sum(cpu_times) / len(cpu_times),
            'operation_stats': operation_stats,
            'bottleneck_counts': dict(bottleneck_counts),
            'period_hours': hours
        }


class ProductionObservabilitySystem:
    """Production-grade observability system"""
    
    def __init__(self, service_name: str = "opencode-slack"):
        self.service_name = service_name
        
        # Initialize components
        self.correlation_context = CorrelationContext()
        self.tracer = DistributedTracer(service_name)
        self.structured_logger = StructuredLogger(service_name, self.correlation_context)
        self.profiler = PerformanceProfiler()
        
        # Decorator cache
        self._decorator_cache = {}
        
        logger.info(f"ProductionObservabilitySystem initialized for {service_name}")
    
    def trace_operation(self, operation_name: Optional[str] = None, 
                       tags: Optional[Dict[str, Any]] = None):
        """Decorator for tracing operations"""
        def decorator(func):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with self.tracer.trace(op_name, tags) as span:
                    # Add function arguments as tags
                    if args:
                        span.tags['args_count'] = len(args)
                    if kwargs:
                        span.tags['kwargs'] = list(kwargs.keys())
                    
                    # Set trace context
                    self.correlation_context.set_trace_context(span.trace_id, span.span_id)
                    
                    try:
                        result = func(*args, **kwargs)
                        span.tags['success'] = True
                        return result
                    except Exception as e:
                        span.tags['success'] = False
                        span.tags['error_type'] = type(e).__name__
                        self.tracer.add_span_log(span.span_id, f"Error: {str(e)}", "error")
                        raise
            
            return wrapper
        return decorator
    
    def profile_operation(self, operation_name: Optional[str] = None,
                         tags: Optional[Dict[str, Any]] = None):
        """Decorator for profiling operations"""
        def decorator(func):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with self.profiler.profile(op_name, tags):
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def observe_operation(self, operation_name: Optional[str] = None,
                         tags: Optional[Dict[str, Any]] = None):
        """Decorator for full observability (tracing + profiling + logging)"""
        def decorator(func):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Generate correlation ID
                correlation_id = str(uuid.uuid4())
                self.correlation_context.set_correlation_id(correlation_id)
                
                # Start tracing and profiling
                with self.tracer.trace(op_name, tags) as span:
                    with self.profiler.profile(op_name, tags) as profile_id:
                        # Set trace context
                        self.correlation_context.set_trace_context(span.trace_id, span.span_id)
                        
                        # Log operation start
                        self.structured_logger.log_with_correlation(
                            'INFO', f"Starting operation: {op_name}",
                            correlation_id, func.__module__,
                            operation=op_name, args_count=len(args), kwargs_keys=list(kwargs.keys())
                        )
                        
                        try:
                            result = func(*args, **kwargs)
                            
                            # Log success
                            self.structured_logger.log_with_correlation(
                                'INFO', f"Operation completed successfully: {op_name}",
                                correlation_id, func.__module__,
                                operation=op_name, success=True
                            )
                            
                            return result
                            
                        except Exception as e:
                            # Log error
                            self.structured_logger.log_with_correlation(
                                'ERROR', f"Operation failed: {op_name} - {str(e)}",
                                correlation_id, func.__module__,
                                operation=op_name, success=False, error_type=type(e).__name__,
                                error_message=str(e), traceback=traceback.format_exc()
                            )
                            raise
            
            return wrapper
        return decorator
    
    def create_correlation_context(self, correlation_id: Optional[str] = None) -> str:
        """Create new correlation context"""
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        self.correlation_context.set_correlation_id(correlation_id)
        return correlation_id
    
    def get_observability_data(self, correlation_id: Optional[str] = None,
                              trace_id: Optional[str] = None,
                              hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive observability data"""
        data = {
            'correlation_id': correlation_id,
            'trace_id': trace_id,
            'period_hours': hours,
            'traces': [],
            'logs': [],
            'performance_profiles': [],
            'summary': {}
        }
        
        # Get trace data
        if trace_id:
            data['traces'] = [asdict(span) for span in self.tracer.get_trace_data(trace_id)]
        
        # Get log data
        data['logs'] = [
            asdict(entry) for entry in self.structured_logger.search_logs(
                correlation_id=correlation_id, trace_id=trace_id, hours=hours
            )
        ]
        
        # Get performance data
        cutoff_time = datetime.now() - timedelta(hours=hours)
        data['performance_profiles'] = [
            asdict(profile) for profile in self.profiler.profiles
            if profile.start_time >= cutoff_time
        ]
        
        # Get summary statistics
        data['summary'] = {
            'traces_count': len(data['traces']),
            'logs_count': len(data['logs']),
            'profiles_count': len(data['performance_profiles']),
            'performance_summary': self.profiler.get_performance_summary(hours)
        }
        
        return data
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health from observability perspective"""
        # Get recent data
        recent_data = self.get_observability_data(hours=1)
        
        # Analyze health indicators
        health_score = 100
        issues = []
        
        # Check error rates in logs
        error_logs = [log for log in recent_data['logs'] if log['level'] in ['ERROR', 'CRITICAL']]
        error_rate = len(error_logs) / max(len(recent_data['logs']), 1) * 100
        
        if error_rate > 10:
            health_score -= 30
            issues.append(f"High error rate: {error_rate:.1f}%")
        elif error_rate > 5:
            health_score -= 15
            issues.append(f"Elevated error rate: {error_rate:.1f}%")
        
        # Check performance issues
        perf_summary = recent_data['summary']['performance_summary']
        if perf_summary:
            avg_duration = perf_summary.get('avg_duration_ms', 0)
            if avg_duration > 2000:
                health_score -= 20
                issues.append(f"Slow average response time: {avg_duration:.0f}ms")
            elif avg_duration > 1000:
                health_score -= 10
                issues.append(f"Elevated response time: {avg_duration:.0f}ms")
            
            # Check bottlenecks
            bottleneck_counts = perf_summary.get('bottleneck_counts', {})
            total_bottlenecks = sum(bottleneck_counts.values())
            if total_bottlenecks > 10:
                health_score -= 15
                issues.append(f"Multiple performance bottlenecks detected: {total_bottlenecks}")
        
        # Check trace errors
        error_traces = [trace for trace in recent_data['traces'] if trace['status'] == 'error']
        trace_error_rate = len(error_traces) / max(len(recent_data['traces']), 1) * 100
        
        if trace_error_rate > 5:
            health_score -= 20
            issues.append(f"High trace error rate: {trace_error_rate:.1f}%")
        
        # Determine health status
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 75:
            status = "good"
        elif health_score >= 60:
            status = "fair"
        elif health_score >= 40:
            status = "poor"
        else:
            status = "critical"
        
        return {
            'status': status,
            'health_score': max(0, health_score),
            'issues': issues,
            'metrics': {
                'error_rate_percent': error_rate,
                'trace_error_rate_percent': trace_error_rate,
                'avg_response_time_ms': perf_summary.get('avg_duration_ms', 0) if perf_summary else 0,
                'total_bottlenecks': sum(perf_summary.get('bottleneck_counts', {}).values()) if perf_summary else 0
            },
            'recommendations': self._generate_health_recommendations(issues)
        }
    
    def _generate_health_recommendations(self, issues: List[str]) -> List[str]:
        """Generate health improvement recommendations"""
        recommendations = []
        
        for issue in issues:
            if "error rate" in issue.lower():
                recommendations.append("Review error logs and implement better error handling")
            elif "response time" in issue.lower():
                recommendations.append("Optimize slow operations and consider caching")
            elif "bottleneck" in issue.lower():
                recommendations.append("Profile slow operations and optimize algorithms")
        
        if not recommendations:
            recommendations.append("System is performing well - continue monitoring")
        
        return recommendations