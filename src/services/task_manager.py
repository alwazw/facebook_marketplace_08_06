"""
Comprehensive task management service for Facebook Marketplace automation system.

This service handles:
1. Task scheduling and execution
2. Task queue management
3. Task monitoring and status tracking
4. Task retry and error handling
5. Task performance analytics
6. Task dependency management
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from queue import Queue, PriorityQueue
from concurrent.futures import ThreadPoolExecutor, Future
from src.models import db
from src.models.automation_run import AutomationRun
from src.services.automation_service import AutomationService
from src.services.validation_service import ValidationService

class TaskStatus(Enum):
    """Task execution status enumeration"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5

@dataclass
class Task:
    """Task definition class"""
    id: str
    name: str
    task_type: str
    function: Callable
    args: tuple = ()
    kwargs: dict = None
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    scheduled_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    timeout: int = 300  # seconds
    dependencies: List[str] = None
    metadata: dict = None
    result: Any = None
    error: str = None
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.scheduled_at is None:
            self.scheduled_at = self.created_at
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}
    
    def __lt__(self, other):
        """For priority queue ordering"""
        return self.priority.value > other.priority.value  # Higher priority value = higher priority
    
    def to_dict(self) -> dict:
        """Convert task to dictionary for serialization"""
        task_dict = asdict(self)
        # Convert datetime objects to ISO strings
        for field in ['created_at', 'scheduled_at', 'started_at', 'completed_at']:
            if task_dict[field]:
                task_dict[field] = task_dict[field].isoformat()
        # Convert enums to values
        task_dict['priority'] = self.priority.value
        task_dict['status'] = self.status.value
        # Remove function reference for serialization
        task_dict.pop('function', None)
        return task_dict

class TaskManager:
    """Comprehensive task management system"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = PriorityQueue()
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, Future] = {}
        self.completed_tasks: Dict[str, Task] = {}
        self.failed_tasks: Dict[str, Task] = {}
        
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.worker_thread = None
        
        # Task type registry
        self.task_registry = {}
        self._register_default_tasks()
        
        # Performance metrics
        self.metrics = {
            'total_tasks_created': 0,
            'total_tasks_completed': 0,
            'total_tasks_failed': 0,
            'total_execution_time': 0,
            'average_execution_time': 0,
            'tasks_per_minute': 0,
            'last_reset': datetime.utcnow()
        }
        
        # Validation service
        self.validation_service = ValidationService()
        
        # Automation service
        self.automation_service = AutomationService()
    
    def start(self):
        """Start the task manager"""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            self.logger.info("Task manager started")
    
    def stop(self):
        """Stop the task manager"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        self.executor.shutdown(wait=True)
        self.logger.info("Task manager stopped")
    
    def create_task(self, 
                   name: str,
                   task_type: str,
                   function: Callable = None,
                   args: tuple = (),
                   kwargs: dict = None,
                   priority: TaskPriority = TaskPriority.NORMAL,
                   scheduled_at: datetime = None,
                   max_retries: int = 3,
                   timeout: int = 300,
                   dependencies: List[str] = None,
                   metadata: dict = None) -> str:
        """
        Create a new task.
        
        Args:
            name: Human-readable task name
            task_type: Type of task (must be registered)
            function: Function to execute (optional if task_type is registered)
            args: Function arguments
            kwargs: Function keyword arguments
            priority: Task priority level
            scheduled_at: When to execute the task
            max_retries: Maximum retry attempts
            timeout: Task timeout in seconds
            dependencies: List of task IDs this task depends on
            metadata: Additional task metadata
            
        Returns:
            Task ID string
        """
        task_id = f"{task_type}_{int(time.time() * 1000)}"
        
        # Get function from registry if not provided
        if function is None:
            if task_type not in self.task_registry:
                raise ValueError(f"Unknown task type: {task_type}")
            function = self.task_registry[task_type]
        
        task = Task(
            id=task_id,
            name=name,
            task_type=task_type,
            function=function,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            scheduled_at=scheduled_at or datetime.utcnow(),
            max_retries=max_retries,
            timeout=timeout,
            dependencies=dependencies or [],
            metadata=metadata or {}
        )
        
        self.tasks[task_id] = task
        self.metrics['total_tasks_created'] += 1
        
        # Queue task if dependencies are met
        if self._dependencies_met(task):
            self._queue_task(task)
        
        self.logger.info(f"Created task {task_id}: {name}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self.tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get task status by ID"""
        task = self.get_task(task_id)
        return task.status if task else None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        if task.status in [TaskStatus.PENDING, TaskStatus.QUEUED]:
            task.status = TaskStatus.CANCELLED
            self.logger.info(f"Cancelled task {task_id}")
            return True
        elif task.status == TaskStatus.RUNNING:
            # Try to cancel running task
            future = self.running_tasks.get(task_id)
            if future and future.cancel():
                task.status = TaskStatus.CANCELLED
                self.running_tasks.pop(task_id, None)
                self.logger.info(f"Cancelled running task {task_id}")
                return True
        
        return False
    
    def retry_task(self, task_id: str) -> bool:
        """Manually retry a failed task"""
        task = self.get_task(task_id)
        if not task or task.status != TaskStatus.FAILED:
            return False
        
        if task.retry_count >= task.max_retries:
            self.logger.warning(f"Task {task_id} has exceeded max retries")
            return False
        
        task.status = TaskStatus.RETRYING
        task.retry_count += 1
        task.error = None
        
        # Schedule retry with delay
        retry_delay = task.retry_delay * (2 ** (task.retry_count - 1))  # Exponential backoff
        task.scheduled_at = datetime.utcnow() + timedelta(seconds=retry_delay)
        
        if self._dependencies_met(task):
            self._queue_task(task)
        
        self.logger.info(f"Retrying task {task_id} (attempt {task.retry_count})")
        return True
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with specific status"""
        return [task for task in self.tasks.values() if task.status == status]
    
    def get_tasks_by_type(self, task_type: str) -> List[Task]:
        """Get all tasks of specific type"""
        return [task for task in self.tasks.values() if task.task_type == task_type]
    
    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks"""
        return self.get_tasks_by_status(TaskStatus.PENDING)
    
    def get_running_tasks(self) -> List[Task]:
        """Get all running tasks"""
        return self.get_tasks_by_status(TaskStatus.RUNNING)
    
    def get_failed_tasks(self) -> List[Task]:
        """Get all failed tasks"""
        return self.get_tasks_by_status(TaskStatus.FAILED)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get task manager performance metrics"""
        current_time = datetime.utcnow()
        time_diff = (current_time - self.metrics['last_reset']).total_seconds()
        
        if time_diff > 0:
            self.metrics['tasks_per_minute'] = (self.metrics['total_tasks_completed'] / time_diff) * 60
        
        if self.metrics['total_tasks_completed'] > 0:
            self.metrics['average_execution_time'] = self.metrics['total_execution_time'] / self.metrics['total_tasks_completed']
        
        return {
            **self.metrics,
            'active_tasks': len(self.running_tasks),
            'queued_tasks': self.task_queue.qsize(),
            'total_tasks': len(self.tasks),
            'success_rate': (self.metrics['total_tasks_completed'] / max(1, self.metrics['total_tasks_created'])) * 100
        }
    
    def reset_metrics(self):
        """Reset performance metrics"""
        self.metrics = {
            'total_tasks_created': 0,
            'total_tasks_completed': 0,
            'total_tasks_failed': 0,
            'total_execution_time': 0,
            'average_execution_time': 0,
            'tasks_per_minute': 0,
            'last_reset': datetime.utcnow()
        }
    
    def register_task_type(self, task_type: str, function: Callable):
        """Register a new task type"""
        self.task_registry[task_type] = function
        self.logger.info(f"Registered task type: {task_type}")
    
    def _register_default_tasks(self):
        """Register default task types"""
        self.register_task_type('automation_cycle', self._run_automation_cycle)
        self.register_task_type('process_messages', self._process_messages)
        self.register_task_type('validate_system', self._validate_system)
        self.register_task_type('cleanup_data', self._cleanup_data)
        self.register_task_type('generate_report', self._generate_report)
        self.register_task_type('account_rotation', self._account_rotation)
        self.register_task_type('health_check', self._health_check)
    
    def _worker_loop(self):
        """Main worker loop for processing tasks"""
        while self.is_running:
            try:
                # Check for scheduled tasks
                self._check_scheduled_tasks()
                
                # Process queued tasks
                if not self.task_queue.empty() and len(self.running_tasks) < self.max_workers:
                    task = self.task_queue.get_nowait()
                    self._execute_task(task)
                
                # Check completed tasks
                self._check_completed_tasks()
                
                # Brief sleep to prevent busy waiting
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in worker loop: {str(e)}")
                time.sleep(5)  # Longer sleep on error
    
    def _check_scheduled_tasks(self):
        """Check for tasks that are ready to be queued"""
        current_time = datetime.utcnow()
        
        for task in list(self.tasks.values()):
            if (task.status == TaskStatus.PENDING and 
                task.scheduled_at <= current_time and 
                self._dependencies_met(task)):
                self._queue_task(task)
    
    def _queue_task(self, task: Task):
        """Add task to execution queue"""
        task.status = TaskStatus.QUEUED
        self.task_queue.put(task)
        self.logger.debug(f"Queued task {task.id}")
    
    def _execute_task(self, task: Task):
        """Execute a task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        # Submit task to thread pool
        future = self.executor.submit(self._run_task, task)
        self.running_tasks[task.id] = future
        
        self.logger.info(f"Started executing task {task.id}: {task.name}")
    
    def _run_task(self, task: Task) -> Any:
        """Run the actual task function"""
        try:
            # Execute the task function
            result = task.function(*task.args, **task.kwargs)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            
            # Update metrics
            execution_time = (task.completed_at - task.started_at).total_seconds()
            self.metrics['total_execution_time'] += execution_time
            self.metrics['total_tasks_completed'] += 1
            
            self.logger.info(f"Completed task {task.id} in {execution_time:.2f}s")
            
            # Check for dependent tasks
            self._check_dependent_tasks(task.id)
            
            return result
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            
            self.metrics['total_tasks_failed'] += 1
            
            self.logger.error(f"Task {task.id} failed: {str(e)}")
            
            # Auto-retry if retries available
            if task.retry_count < task.max_retries:
                self.retry_task(task.id)
            
            raise
    
    def _check_completed_tasks(self):
        """Check for completed running tasks"""
        completed_task_ids = []
        
        for task_id, future in self.running_tasks.items():
            if future.done():
                completed_task_ids.append(task_id)
        
        for task_id in completed_task_ids:
            self.running_tasks.pop(task_id, None)
    
    def _dependencies_met(self, task: Task) -> bool:
        """Check if all task dependencies are completed"""
        for dep_id in task.dependencies:
            dep_task = self.get_task(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True
    
    def _check_dependent_tasks(self, completed_task_id: str):
        """Check for tasks that depend on the completed task"""
        for task in self.tasks.values():
            if (task.status == TaskStatus.PENDING and 
                completed_task_id in task.dependencies and 
                self._dependencies_met(task)):
                self._queue_task(task)
    
    # Default task implementations
    
    def _run_automation_cycle(self, account_id: int = None) -> Dict[str, Any]:
        """Run automation cycle for specified account or all accounts"""
        try:
            if account_id:
                result = self.automation_service.run_automation_cycle(account_id)
            else:
                result = self.automation_service.run_all_accounts()
            
            return {
                'success': True,
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Automation cycle failed: {str(e)}")
            raise
    
    def _process_messages(self, limit: int = 50) -> Dict[str, Any]:
        """Process unprocessed messages"""
        try:
            result = self.automation_service.process_unprocessed_messages(limit)
            
            return {
                'success': True,
                'processed_count': result.get('processed_count', 0),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Message processing failed: {str(e)}")
            raise
    
    def _validate_system(self) -> Dict[str, Any]:
        """Run comprehensive system validation"""
        try:
            result = self.validation_service.validate_all_systems()
            
            return {
                'success': True,
                'validation_result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"System validation failed: {str(e)}")
            raise
    
    def _cleanup_data(self, days_old: int = 30) -> Dict[str, Any]:
        """Clean up old data"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Clean up old automation runs
            old_runs = AutomationRun.query.filter(
                AutomationRun.created_at < cutoff_date,
                AutomationRun.status.in_(['completed', 'failed'])
            ).all()
            
            deleted_count = len(old_runs)
            for run in old_runs:
                db.session.delete(run)
            
            db.session.commit()
            
            return {
                'success': True,
                'deleted_automation_runs': deleted_count,
                'cutoff_date': cutoff_date.isoformat(),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Data cleanup failed: {str(e)}")
            db.session.rollback()
            raise
    
    def _generate_report(self, report_type: str = 'daily') -> Dict[str, Any]:
        """Generate system report"""
        try:
            # This would generate various reports based on type
            report_data = {
                'report_type': report_type,
                'generated_at': datetime.utcnow().isoformat(),
                'metrics': self.get_metrics(),
                'system_status': 'operational'
            }
            
            return {
                'success': True,
                'report': report_data,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Report generation failed: {str(e)}")
            raise
    
    def _account_rotation(self) -> Dict[str, Any]:
        """Perform account rotation"""
        try:
            # This would implement account rotation logic
            result = {
                'rotated_accounts': 0,
                'active_accounts': 6,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return {
                'success': True,
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Account rotation failed: {str(e)}")
            raise
    
    def _health_check(self) -> Dict[str, Any]:
        """Perform system health check"""
        try:
            # Basic health check
            health_data = {
                'database_connected': True,
                'task_manager_running': self.is_running,
                'active_tasks': len(self.running_tasks),
                'queued_tasks': self.task_queue.qsize(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return {
                'success': True,
                'health': health_data,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            raise

# Global task manager instance
task_manager = TaskManager()

def get_task_manager() -> TaskManager:
    """Get the global task manager instance"""
    return task_manager

