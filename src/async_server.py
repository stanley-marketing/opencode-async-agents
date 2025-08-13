# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""
Asynchronous OpenCode-Slack Server with high-performance optimizations:
- Async request handling with FastAPI
- Connection pooling and rate limiting
- Concurrent task processing
- Advanced error handling and recovery
- Horizontal scaling preparation
"""

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import asyncio
import json
import logging
import os
import signal
import sys
import time
import uvicorn

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.optimized_file_ownership import OptimizedFileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.config.logging_config import setup_logging
from src.utils.async_opencode_wrapper import AsyncOpencodeSessionManager
from src.chat.communication_manager import CommunicationManager
from src.agents.agent_manager import AgentManager
from src.bridge.agent_bridge import AgentBridge
from src.integrations.websocket_server_integration import create_websocket_integration

# Optional imports for monitoring system
try:
    from src.monitoring.agent_health_monitor import AgentHealthMonitor
    from src.monitoring.agent_recovery_manager import AgentRecoveryManager
    from src.monitoring.monitoring_dashboard import MonitoringDashboard
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

logger = logging.getLogger(__name__)

# Pydantic models for request/response validation
class EmployeeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=50)
    smartness: str = Field(default="normal", pattern="^(smart|normal)$")

class EmployeeBatchCreate(BaseModel):
    employees: List[EmployeeCreate] = Field(..., min_items=1, max_items=100)

class TaskAssignment(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    task: str = Field(..., min_length=1, max_length=10000)
    model: Optional[str] = Field(default=None, max_length=100)
    mode: str = Field(default="build", pattern="^(build|chat|analyze)$")
    priority: int = Field(default=0, ge=0, le=10)

class TaskBatchAssignment(BaseModel):
    tasks: List[TaskAssignment] = Field(..., min_items=1, max_items=50)

class FileLockRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    files: List[str] = Field(..., min_items=1, max_items=100)
    description: str = Field(default="", max_length=1000)

class ProjectRootUpdate(BaseModel):
    project_root: str = Field(..., min_length=1, max_length=500)

class RateLimiter:
    """Simple rate limiter for API endpoints"""

    def __init__(self, max_requests: int = 100, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for client"""
        async with self._lock:
            now = time.time()

            # Clean old requests
            if client_id in self.requests:
                self.requests[client_id] = [
                    req_time for req_time in self.requests[client_id]
                    if now - req_time < self.time_window
                ]
            else:
                self.requests[client_id] = []

            # Check rate limit
            if len(self.requests[client_id]) < self.max_requests:
                self.requests[client_id].append(now)
                return True

            return False

class AsyncOpencodeSlackServer:
    """High-performance async OpenCode-Slack server"""

    def __init__(self, host: str = "localhost", port: int = 8080, websocket_port: int = 8765,
                 db_path: str = "employees.db", sessions_dir: str = "sessions",
                 max_concurrent_tasks: int = 50, max_connections: int = 20, transport_type: str = None):
        self.host = host
        self.port = port
        self.websocket_port = websocket_port
        self.db_path = db_path
        self.sessions_dir = sessions_dir
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_connections = max_connections
        self.transport_type = transport_type

        # Server state
        self.running = False
        self.chat_enabled = False
        self.startup_time = None

        # Rate limiter
        self.rate_limiter = RateLimiter(max_requests=1000, time_window=60)

        # Performance metrics
        self.metrics = {
            'requests_total': 0,
            'requests_success': 0,
            'requests_error': 0,
            'response_times': [],
            'active_tasks': 0
        }

        # Initialize components (will be done in startup)
        self.file_manager = None
        self.task_tracker = None
        self.session_manager = None
        self.communication_manager = None
        self.agent_manager = None
        self.agent_bridge = None
        self.health_monitor = None
        self.recovery_manager = None
        self.monitoring_dashboard = None
        self.websocket_integration = None

        # Create FastAPI app
        self.app = self._create_app()

    def _create_app(self) -> FastAPI:
        """Create FastAPI application with all configurations"""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await self._startup()
            yield
            # Shutdown
            await self._shutdown()

        app = FastAPI(
            title="OpenCode-Slack Agent Orchestration System",
            description="High-performance async agent orchestration with LLM integration",
            version="2.0.0",
            lifespan=lifespan
        )

        # Add middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        app.add_middleware(GZipMiddleware, minimum_size=1000)

        # Add custom middleware for metrics and rate limiting
        @app.middleware("http")
        async def metrics_and_rate_limit_middleware(request: Request, call_next):
            start_time = time.time()

            # Rate limiting
            client_ip = request.client.host
            if not await self.rate_limiter.is_allowed(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded", "retry_after": 60}
                )

            # Process request
            self.metrics['requests_total'] += 1

            try:
                response = await call_next(request)
                self.metrics['requests_success'] += 1

                # Record response time
                response_time = time.time() - start_time
                self.metrics['response_times'].append(response_time)

                # Keep only last 1000 response times
                if len(self.metrics['response_times']) > 1000:
                    self.metrics['response_times'] = self.metrics['response_times'][-1000:]

                return response

            except Exception as e:
                self.metrics['requests_error'] += 1
                logger.error(f"Request failed: {e}")
                return JSONResponse(
                    status_code=500,
                    content={"error": "Internal server error", "message": str(e)}
                )

        # Add routes
        self._add_routes(app)

        return app

    async def _startup(self):
        """Initialize all components on startup"""
        logger.info("Starting AsyncOpencodeSlackServer...")
        self.startup_time = datetime.now()

        try:
            # Load environment variables
            self._load_environment()

            # Initialize core components
            await self._initialize_components()

            # Auto-start chat system if configured
            await self._auto_start_chat_if_configured()

            self.running = True
            logger.info(f"AsyncOpencodeSlackServer started successfully on {self.host}:{self.port}")

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise

    async def _shutdown(self):
        """Clean shutdown of all components"""
        logger.info("Shutting down AsyncOpencodeSlackServer...")

        try:
            # Stop communication system
            self.chat_enabled = False
            if self.websocket_integration:
                self.websocket_integration.stop_communication()

            # Clean up all active sessions
            if self.session_manager:
                await self.session_manager.cleanup_all_sessions()

            # Close file manager
            if self.file_manager:
                self.file_manager.close()

            self.running = False
            logger.info("AsyncOpencodeSlackServer shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    def _load_environment(self):
        """Load environment variables"""
        try:
            from dotenv import load_dotenv
            env_path = Path(__file__).parent.parent / '.env'
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"Loaded .env from {env_path}")
            else:
                load_dotenv()
        except ImportError:
            logger.warning("python-dotenv not installed")
        except Exception as e:
            logger.warning(f"Could not load .env: {e}")

    async def _initialize_components(self):
        """Initialize all system components"""
        # Initialize optimized file manager
        self.file_manager = OptimizedFileOwnershipManager(
            db_path=self.db_path,
            max_connections=self.max_connections
        )

        # Initialize task tracker
        self.task_tracker = TaskProgressTracker(self.sessions_dir)

        # Initialize async session manager
        self.session_manager = AsyncOpencodeSessionManager(
            file_manager=self.file_manager,
            sessions_dir=self.sessions_dir,
            max_concurrent_sessions=self.max_concurrent_tasks
        )

        # Initialize WebSocket integration
        self.websocket_integration = create_websocket_integration(
            host=self.host,
            websocket_port=self.websocket_port,
            transport_type=self.transport_type
        )
        
        # Initialize communication system
        self.communication_manager = self.websocket_integration.communication_manager
        self.agent_manager = AgentManager(self.file_manager, self.communication_manager)

        # Set up monitoring system
        self.agent_manager.setup_monitoring_system(self.task_tracker, self.session_manager)

        # Sync agents with employees
        self.agent_manager.sync_agents_with_employees()

        self.agent_bridge = AgentBridge(self.session_manager, self.agent_manager)
        
        # Integrate WebSocket functionality
        self.websocket_integration.integrate_with_server(
            self, self.agent_manager, self.session_manager
        )

        # Initialize advanced monitoring if available
        if MONITORING_AVAILABLE:
            await self._setup_advanced_monitoring()

        logger.info("All components initialized successfully")

    async def _setup_advanced_monitoring(self):
        """Set up advanced monitoring system"""
        try:
            self.health_monitor = AgentHealthMonitor(self.agent_manager, self.task_tracker)
            self.recovery_manager = AgentRecoveryManager(self.agent_manager, self.session_manager)
            self.monitoring_dashboard = MonitoringDashboard(self.health_monitor, self.recovery_manager)

            def anomaly_callback(agent_name, anomalies, status_record):
                if self.recovery_manager:
                    asyncio.create_task(
                        self._handle_agent_anomaly(agent_name, anomalies, status_record)
                    )

            self.health_monitor.start_monitoring(anomaly_callback)
            logger.info("Advanced monitoring system initialized")

        except Exception as e:
            logger.error(f"Failed to initialize monitoring system: {e}")

    async def _handle_agent_anomaly(self, agent_name: str, anomalies: List, status_record: Dict):
        """Handle agent anomaly asynchronously"""
        try:
            if self.recovery_manager:
                # Run recovery in background
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.recovery_manager.handle_agent_anomaly,
                    agent_name, anomalies, status_record
                )
        except Exception as e:
            logger.error(f"Error handling agent anomaly: {e}")

    async def _auto_start_chat_if_configured(self):
        """Auto-start communication system if configured"""
        try:
            safe_mode = os.environ.get('OPENCODE_SAFE_MODE', '').lower() in ['true', '1', 'yes']

            if safe_mode:
                logger.info("Safe mode enabled - Communication system disabled")
                return

            success = self.websocket_integration.start_communication()
            if success:
                self.agent_bridge.start_monitoring()
                self.chat_enabled = True
                transport_type = self.communication_manager.get_transport_type()
                logger.info(f"{transport_type} communication system auto-started")
            else:
                logger.info("Communication system failed to start")

        except Exception as e:
            logger.error(f"Failed to auto-start communication system: {e}")

    def _add_routes(self, app: FastAPI):
        """Add all API routes"""

        @app.get("/health")
        async def health_check():
            """Enhanced health check endpoint"""
            uptime = (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0

            # Calculate average response time
            avg_response_time = 0
            if self.metrics['response_times']:
                avg_response_time = sum(self.metrics['response_times']) / len(self.metrics['response_times'])

            return {
                "status": "healthy",
                "uptime_seconds": uptime,
                "chat_enabled": self.chat_enabled,
                "active_sessions": len(self.session_manager.get_active_sessions()) if self.session_manager else 0,
                "total_agents": len(self.agent_manager.agents) if self.agent_manager else 0,
                "performance_metrics": {
                    "requests_total": self.metrics['requests_total'],
                    "requests_success": self.metrics['requests_success'],
                    "requests_error": self.metrics['requests_error'],
                    "error_rate": self.metrics['requests_error'] / max(self.metrics['requests_total'], 1) * 100,
                    "avg_response_time_ms": avg_response_time * 1000,
                    "active_tasks": self.metrics['active_tasks']
                }
            }

        @app.get("/employees")
        async def list_employees():
            """List all employees"""
            if not self.file_manager:
                raise HTTPException(status_code=503, detail="File manager not available")

            # Run in thread pool to avoid blocking
            employees = await asyncio.get_event_loop().run_in_executor(
                None, self.file_manager.list_employees
            )
            return {"employees": employees}

        @app.post("/employees")
        async def hire_employee(employee: EmployeeCreate, background_tasks: BackgroundTasks):
            """Hire a new employee"""
            if not self.file_manager:
                raise HTTPException(status_code=503, detail="File manager not available")

            # Run in thread pool
            success = await asyncio.get_event_loop().run_in_executor(
                None, self.file_manager.hire_employee,
                employee.name, employee.role, employee.smartness
            )

            if success:
                # Create agent in background
                if self.agent_manager:
                    background_tasks.add_task(
                        self._create_agent_background,
                        employee.name, employee.role
                    )

                return {
                    "message": f"Successfully hired {employee.name} as {employee.role}",
                    "employee": employee.dict()
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to hire {employee.name}. Employee may already exist."
                )

        @app.post("/employees/batch")
        async def hire_employees_batch(batch: EmployeeBatchCreate, background_tasks: BackgroundTasks):
            """Hire multiple employees in batch"""
            if not self.file_manager:
                raise HTTPException(status_code=503, detail="File manager not available")

            # Prepare batch data
            employees_data = [
                (emp.name, emp.role, emp.smartness)
                for emp in batch.employees
            ]

            # Run batch hire in thread pool
            results = await asyncio.get_event_loop().run_in_executor(
                None, self.file_manager.hire_employees_batch, employees_data
            )

            # Create agents for successful hires in background
            if self.agent_manager:
                for emp in batch.employees:
                    if results.get(emp.name, False):
                        background_tasks.add_task(
                            self._create_agent_background,
                            emp.name, emp.role
                        )

            successful = sum(results.values())
            return {
                "message": f"Successfully hired {successful}/{len(batch.employees)} employees",
                "results": results
            }

        @app.delete("/employees/{name}")
        async def fire_employee(name: str):
            """Fire an employee"""
            if not self.file_manager:
                raise HTTPException(status_code=503, detail="File manager not available")

            # Stop any active sessions first
            if self.session_manager and name in self.session_manager.active_sessions:
                await self.session_manager.stop_employee_task(name)

            # Remove agent
            if self.agent_manager:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.agent_manager.remove_agent, name
                )

            # Fire employee
            success = await asyncio.get_event_loop().run_in_executor(
                None, self.file_manager.fire_employee, name, self.task_tracker
            )

            if success:
                return {"message": f"Successfully fired {name}"}
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to fire {name}. Employee may not exist."
                )

        @app.post("/tasks")
        async def assign_task(task: TaskAssignment):
            """Assign a task to an employee"""
            if not self.session_manager:
                raise HTTPException(status_code=503, detail="Session manager not available")

            # Check if employee exists
            employees = await asyncio.get_event_loop().run_in_executor(
                None, self.file_manager.list_employees
            )
            employee_names = [emp['name'] for emp in employees]

            if task.name not in employee_names:
                # Auto-hire as developer
                success = await asyncio.get_event_loop().run_in_executor(
                    None, self.file_manager.hire_employee, task.name, "developer"
                )
                if not success:
                    raise HTTPException(status_code=400, detail=f"Failed to hire {task.name}")

                if self.agent_manager:
                    await self._create_agent_background(task.name, "developer")

            # Start task
            self.metrics['active_tasks'] += 1
            try:
                session_id = await self.session_manager.start_employee_task(
                    task.name, task.task, task.model, task.mode, task.priority
                )

                if session_id:
                    return {
                        "message": f"Started task for {task.name}",
                        "session_id": session_id,
                        "task": task.task,
                        "model": task.model,
                        "mode": task.mode,
                        "priority": task.priority
                    }
                else:
                    raise HTTPException(status_code=500, detail=f"Failed to start task for {task.name}")
            finally:
                self.metrics['active_tasks'] = max(0, self.metrics['active_tasks'] - 1)

        @app.post("/tasks/batch")
        async def assign_tasks_batch(batch: TaskBatchAssignment):
            """Assign multiple tasks in batch"""
            if not self.session_manager:
                raise HTTPException(status_code=503, detail="Session manager not available")

            results = []
            self.metrics['active_tasks'] += len(batch.tasks)

            try:
                # Process tasks concurrently
                tasks = []
                for task in batch.tasks:
                    tasks.append(self._assign_single_task(task))

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                successful = 0
                response_results = []

                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        response_results.append({
                            "employee": batch.tasks[i].name,
                            "success": False,
                            "error": str(result)
                        })
                    else:
                        response_results.append({
                            "employee": batch.tasks[i].name,
                            "success": True,
                            "session_id": result
                        })
                        successful += 1

                return {
                    "message": f"Assigned {successful}/{len(batch.tasks)} tasks successfully",
                    "results": response_results
                }

            finally:
                self.metrics['active_tasks'] = max(0, self.metrics['active_tasks'] - len(batch.tasks))

        @app.delete("/tasks/{name}")
        async def stop_task(name: str):
            """Stop an employee's task"""
            if not self.session_manager:
                raise HTTPException(status_code=503, detail="Session manager not available")

            await self.session_manager.stop_employee_task(name)
            return {"message": f"Stopped task for {name}"}

        @app.get("/status")
        async def get_status():
            """Get comprehensive system status"""
            status = {}

            if self.session_manager:
                status['active_sessions'] = self.session_manager.get_active_sessions()
            else:
                status['active_sessions'] = {}

            if self.file_manager:
                locked_files = await asyncio.get_event_loop().run_in_executor(
                    None, self.file_manager.get_all_locked_files
                )
                employees = await asyncio.get_event_loop().run_in_executor(
                    None, self.file_manager.list_employees
                )
                status['locked_files'] = locked_files
                status['employees'] = employees
            else:
                status['locked_files'] = []
                status['employees'] = []

            status['chat_enabled'] = self.chat_enabled

            if self.agent_manager:
                status['chat_statistics'] = self.agent_manager.get_chat_statistics()
            else:
                status['chat_statistics'] = None

            # Add performance metrics
            if self.file_manager and hasattr(self.file_manager, 'get_performance_metrics'):
                status['performance_metrics'] = await asyncio.get_event_loop().run_in_executor(
                    None, self.file_manager.get_performance_metrics
                )

            if self.session_manager and hasattr(self.session_manager, 'get_performance_metrics'):
                status['session_metrics'] = self.session_manager.get_performance_metrics()

            return status

        @app.get("/performance")
        async def get_performance_metrics():
            """Get detailed performance metrics"""
            metrics = {
                "server_metrics": self.metrics.copy(),
                "uptime_seconds": (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0
            }

            if self.file_manager and hasattr(self.file_manager, 'get_performance_metrics'):
                metrics["database_metrics"] = await asyncio.get_event_loop().run_in_executor(
                    None, self.file_manager.get_performance_metrics
                )

            if self.session_manager and hasattr(self.session_manager, 'get_performance_metrics'):
                metrics["session_metrics"] = self.session_manager.get_performance_metrics()

            return metrics

        # Add other routes (files, progress, chat, etc.)
        self._add_additional_routes(app)

    def _add_additional_routes(self, app: FastAPI):
        """Add additional routes for completeness"""

        @app.post("/files/lock")
        async def lock_files(request: FileLockRequest):
            """Lock files for an employee"""
            if not self.file_manager:
                raise HTTPException(status_code=503, detail="File manager not available")

            result = await asyncio.get_event_loop().run_in_executor(
                None, self.file_manager.lock_files,
                request.name, request.files, request.description
            )

            if self.task_tracker:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.task_tracker.create_task_file,
                    request.name, request.description, request.files
                )

            return {"result": result}

        @app.post("/files/release")
        async def release_files(name: str, files: Optional[List[str]] = None):
            """Release files for an employee"""
            if not self.file_manager:
                raise HTTPException(status_code=503, detail="File manager not available")

            released = await asyncio.get_event_loop().run_in_executor(
                None, self.file_manager.release_files, name, files
            )
            return {"released": released}

        @app.get("/project-root")
        async def get_project_root():
            """Get the current project root directory"""
            if not self.file_manager:
                raise HTTPException(status_code=503, detail="File manager not available")

            project_root = await asyncio.get_event_loop().run_in_executor(
                None, self.file_manager.get_project_root
            )
            return {"project_root": project_root}

        @app.post("/project-root")
        async def set_project_root(request: ProjectRootUpdate):
            """Set the project root directory"""
            if not self.file_manager:
                raise HTTPException(status_code=503, detail="File manager not available")

            success = await asyncio.get_event_loop().run_in_executor(
                None, self.file_manager.set_project_root, request.project_root
            )

            if success:
                return {"message": f"Project root set to {request.project_root}"}
            else:
                raise HTTPException(status_code=500, detail="Failed to set project root")

    async def _assign_single_task(self, task: TaskAssignment) -> str:
        """Assign a single task (helper for batch operations)"""
        # Check if employee exists
        employees = await asyncio.get_event_loop().run_in_executor(
            None, self.file_manager.list_employees
        )
        employee_names = [emp['name'] for emp in employees]

        if task.name not in employee_names:
            # Auto-hire as developer
            success = await asyncio.get_event_loop().run_in_executor(
                None, self.file_manager.hire_employee, task.name, "developer"
            )
            if not success:
                raise Exception(f"Failed to hire {task.name}")

            if self.agent_manager:
                await self._create_agent_background(task.name, "developer")

        # Start task
        session_id = await self.session_manager.start_employee_task(
            task.name, task.task, task.model, task.mode, task.priority
        )

        if not session_id:
            raise Exception(f"Failed to start task for {task.name}")

        return session_id

    async def _create_agent_background(self, name: str, role: str):
        """Create agent in background"""
        try:
            if self.agent_manager:
                expertise = self.agent_manager._get_expertise_for_role(role)
                await asyncio.get_event_loop().run_in_executor(
                    None, self.agent_manager.create_agent, name, role, expertise
                )
        except Exception as e:
            logger.error(f"Failed to create agent for {name}: {e}")

    async def start(self):
        """Start the async server"""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=True,
            loop="asyncio",
            workers=1  # Single worker for now, can be increased for horizontal scaling
        )

        server = uvicorn.Server(config)
        await server.serve()

def main():
    """Main function to run the async server"""
    import argparse

    # Get default values from environment
    default_port = int(os.environ.get('PORT', 8080))
    default_host = os.environ.get('HOST', 'localhost')
    default_websocket_port = int(os.environ.get('WEBSOCKET_PORT', 8765))
    default_transport = os.environ.get('OPENCODE_TRANSPORT', 'websocket')

    parser = argparse.ArgumentParser(description='Async OpenCode-Slack Server with WebSocket Support')
    parser.add_argument('--host', default=default_host, help=f'Host to bind to (default: {default_host})')
    parser.add_argument('--port', type=int, default=default_port, help=f'HTTP port to bind to (default: {default_port})')
    parser.add_argument('--websocket-port', type=int, default=default_websocket_port, help=f'WebSocket port to bind to (default: {default_websocket_port})')
    parser.add_argument('--transport', choices=['telegram', 'websocket'], default=default_transport, help=f'Communication transport (default: {default_transport})')
    parser.add_argument('--db-path', default='employees.db', help='Database path (default: employees.db)')
    parser.add_argument('--sessions-dir', default='sessions', help='Sessions directory (default: sessions)')
    parser.add_argument('--max-concurrent-tasks', type=int, default=50, help='Max concurrent tasks (default: 50)')
    parser.add_argument('--max-connections', type=int, default=20, help='Max DB connections (default: 20)')

    args = parser.parse_args()

    # Set up logging
    setup_logging(cli_mode=False)

    # Create and start server
    server = AsyncOpencodeSlackServer(
        host=args.host,
        port=args.port,
        websocket_port=args.websocket_port,
        db_path=args.db_path,
        sessions_dir=args.sessions_dir,
        max_concurrent_tasks=args.max_concurrent_tasks,
        max_connections=args.max_connections,
        transport_type=args.transport
    )

    print(f"🚀 Starting Async OpenCode-Slack Server on http://{args.host}:{args.port}")
    print(f"🔌 WebSocket support on port {args.websocket_port}")
    print(f"📡 Using {args.transport} transport")
    print(f"📊 Max concurrent tasks: {args.max_concurrent_tasks}")
    print(f"🔗 Max DB connections: {args.max_connections}")
    print("Press Ctrl+C to stop")

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        logger.error(f"Server startup failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()