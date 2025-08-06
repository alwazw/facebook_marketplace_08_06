from flask import Blueprint, request, jsonify
from src.services.task_manager import get_task_manager, TaskPriority, TaskStatus
from datetime import datetime, timedelta

tasks_bp = Blueprint('tasks', __name__)
task_manager = get_task_manager()

@tasks_bp.route('/create', methods=['POST'])
def create_task():
    """
    Create a new task.
    
    Request Body:
        name: Task name
        task_type: Type of task
        priority: Task priority (low, normal, high, urgent, critical)
        scheduled_at: When to execute (ISO format, optional)
        max_retries: Maximum retry attempts (optional)
        timeout: Task timeout in seconds (optional)
        dependencies: List of task IDs this task depends on (optional)
        metadata: Additional task metadata (optional)
        args: Task function arguments (optional)
        kwargs: Task function keyword arguments (optional)
        
    Returns:
        JSON response with task ID
    """
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'task_type' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: name, task_type'
            }), 400
        
        # Parse priority
        priority_str = data.get('priority', 'normal').lower()
        priority_map = {
            'low': TaskPriority.LOW,
            'normal': TaskPriority.NORMAL,
            'high': TaskPriority.HIGH,
            'urgent': TaskPriority.URGENT,
            'critical': TaskPriority.CRITICAL
        }
        priority = priority_map.get(priority_str, TaskPriority.NORMAL)
        
        # Parse scheduled_at
        scheduled_at = None
        if 'scheduled_at' in data:
            try:
                scheduled_at = datetime.fromisoformat(data['scheduled_at'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid scheduled_at format. Use ISO format.'
                }), 400
        
        # Create task
        task_id = task_manager.create_task(
            name=data['name'],
            task_type=data['task_type'],
            args=tuple(data.get('args', [])),
            kwargs=data.get('kwargs', {}),
            priority=priority,
            scheduled_at=scheduled_at,
            max_retries=data.get('max_retries', 3),
            timeout=data.get('timeout', 300),
            dependencies=data.get('dependencies', []),
            metadata=data.get('metadata', {})
        )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Task created successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tasks_bp.route('/<task_id>', methods=['GET'])
def get_task(task_id):
    """
    Get task details by ID.
    
    Returns:
        JSON response with task details
    """
    try:
        task = task_manager.get_task(task_id)
        
        if not task:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        return jsonify({
            'success': True,
            'task': task.to_dict(),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tasks_bp.route('/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """
    Cancel a task.
    
    Returns:
        JSON response with cancellation result
    """
    try:
        success = task_manager.cancel_task(task_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Task cancelled successfully',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Task could not be cancelled (not found or already completed)'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tasks_bp.route('/<task_id>/retry', methods=['POST'])
def retry_task(task_id):
    """
    Retry a failed task.
    
    Returns:
        JSON response with retry result
    """
    try:
        success = task_manager.retry_task(task_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Task retry initiated',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Task could not be retried (not found, not failed, or max retries exceeded)'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tasks_bp.route('/list', methods=['GET'])
def list_tasks():
    """
    List tasks with optional filtering.
    
    Query Parameters:
        status: Filter by task status
        task_type: Filter by task type
        limit: Number of tasks to return (default: 50)
        offset: Number of tasks to skip (default: 0)
        
    Returns:
        JSON response with task list
    """
    try:
        status_filter = request.args.get('status')
        task_type_filter = request.args.get('task_type')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get all tasks
        all_tasks = list(task_manager.tasks.values())
        
        # Apply filters
        if status_filter:
            try:
                status_enum = TaskStatus(status_filter.lower())
                all_tasks = [task for task in all_tasks if task.status == status_enum]
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Invalid status: {status_filter}'
                }), 400
        
        if task_type_filter:
            all_tasks = [task for task in all_tasks if task.task_type == task_type_filter]
        
        # Sort by creation time (newest first)
        all_tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        # Apply pagination
        total_count = len(all_tasks)
        paginated_tasks = all_tasks[offset:offset + limit]
        
        # Convert to serializable format
        tasks_data = [task.to_dict() for task in paginated_tasks]
        
        return jsonify({
            'success': True,
            'tasks': tasks_data,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tasks_bp.route('/status-summary', methods=['GET'])
def get_status_summary():
    """
    Get task status summary.
    
    Returns:
        JSON response with task counts by status
    """
    try:
        status_counts = {}
        
        for status in TaskStatus:
            count = len(task_manager.get_tasks_by_status(status))
            status_counts[status.value] = count
        
        return jsonify({
            'success': True,
            'status_summary': status_counts,
            'total_tasks': len(task_manager.tasks),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tasks_bp.route('/metrics', methods=['GET'])
def get_task_metrics():
    """
    Get task manager performance metrics.
    
    Returns:
        JSON response with performance metrics
    """
    try:
        metrics = task_manager.get_metrics()
        
        return jsonify({
            'success': True,
            'metrics': metrics,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tasks_bp.route('/schedule-automation', methods=['POST'])
def schedule_automation():
    """
    Schedule automation tasks.
    
    Request Body:
        task_type: Type of automation (cycle, process_messages, etc.)
        account_id: Specific account ID (optional)
        priority: Task priority (optional)
        scheduled_at: When to execute (optional)
        
    Returns:
        JSON response with scheduled task ID
    """
    try:
        data = request.get_json() or {}
        
        task_type = data.get('task_type', 'automation_cycle')
        account_id = data.get('account_id')
        
        # Parse priority
        priority_str = data.get('priority', 'normal').lower()
        priority_map = {
            'low': TaskPriority.LOW,
            'normal': TaskPriority.NORMAL,
            'high': TaskPriority.HIGH,
            'urgent': TaskPriority.URGENT,
            'critical': TaskPriority.CRITICAL
        }
        priority = priority_map.get(priority_str, TaskPriority.NORMAL)
        
        # Parse scheduled_at
        scheduled_at = None
        if 'scheduled_at' in data:
            try:
                scheduled_at = datetime.fromisoformat(data['scheduled_at'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid scheduled_at format. Use ISO format.'
                }), 400
        
        # Create appropriate task based on type
        if task_type == 'automation_cycle':
            task_name = f"Automation Cycle - Account {account_id}" if account_id else "Automation Cycle - All Accounts"
            kwargs = {'account_id': account_id} if account_id else {}
        elif task_type == 'process_messages':
            task_name = "Process Unprocessed Messages"
            kwargs = {'limit': data.get('limit', 50)}
        elif task_type == 'account_rotation':
            task_name = "Account Rotation"
            kwargs = {}
        elif task_type == 'health_check':
            task_name = "System Health Check"
            kwargs = {}
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown automation task type: {task_type}'
            }), 400
        
        task_id = task_manager.create_task(
            name=task_name,
            task_type=task_type,
            kwargs=kwargs,
            priority=priority,
            scheduled_at=scheduled_at,
            metadata={'automation_type': task_type, 'requested_by': 'api'}
        )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'Automation task scheduled: {task_name}',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tasks_bp.route('/bulk-operations', methods=['POST'])
def bulk_operations():
    """
    Perform bulk operations on tasks.
    
    Request Body:
        operation: Operation to perform (cancel, retry, delete)
        task_ids: List of task IDs
        filters: Alternative to task_ids - filter criteria
        
    Returns:
        JSON response with operation results
    """
    try:
        data = request.get_json()
        
        if not data or 'operation' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: operation'
            }), 400
        
        operation = data['operation'].lower()
        task_ids = data.get('task_ids', [])
        filters = data.get('filters', {})
        
        # Get tasks to operate on
        if task_ids:
            tasks_to_process = [task_manager.get_task(tid) for tid in task_ids]
            tasks_to_process = [t for t in tasks_to_process if t is not None]
        elif filters:
            # Apply filters to get tasks
            all_tasks = list(task_manager.tasks.values())
            
            if 'status' in filters:
                try:
                    status_enum = TaskStatus(filters['status'].lower())
                    all_tasks = [task for task in all_tasks if task.status == status_enum]
                except ValueError:
                    return jsonify({
                        'success': False,
                        'error': f'Invalid status filter: {filters["status"]}'
                    }), 400
            
            if 'task_type' in filters:
                all_tasks = [task for task in all_tasks if task.task_type == filters['task_type']]
            
            if 'older_than_hours' in filters:
                cutoff_time = datetime.utcnow() - timedelta(hours=filters['older_than_hours'])
                all_tasks = [task for task in all_tasks if task.created_at < cutoff_time]
            
            tasks_to_process = all_tasks
        else:
            return jsonify({
                'success': False,
                'error': 'Either task_ids or filters must be provided'
            }), 400
        
        # Perform operation
        results = {
            'operation': operation,
            'total_tasks': len(tasks_to_process),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for task in tasks_to_process:
            try:
                if operation == 'cancel':
                    success = task_manager.cancel_task(task.id)
                elif operation == 'retry':
                    success = task_manager.retry_task(task.id)
                elif operation == 'delete':
                    # Remove task from manager (only if not running)
                    if task.status not in [TaskStatus.RUNNING, TaskStatus.QUEUED]:
                        task_manager.tasks.pop(task.id, None)
                        success = True
                    else:
                        success = False
                        results['errors'].append(f"Cannot delete running/queued task: {task.id}")
                else:
                    results['errors'].append(f"Unknown operation: {operation}")
                    continue
                
                if success:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Operation failed for task: {task.id}")
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Error processing task {task.id}: {str(e)}")
        
        return jsonify({
            'success': True,
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tasks_bp.route('/start-manager', methods=['POST'])
def start_task_manager():
    """
    Start the task manager.
    
    Returns:
        JSON response with start result
    """
    try:
        if task_manager.is_running:
            return jsonify({
                'success': True,
                'message': 'Task manager is already running',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        task_manager.start()
        
        return jsonify({
            'success': True,
            'message': 'Task manager started successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tasks_bp.route('/stop-manager', methods=['POST'])
def stop_task_manager():
    """
    Stop the task manager.
    
    Returns:
        JSON response with stop result
    """
    try:
        if not task_manager.is_running:
            return jsonify({
                'success': True,
                'message': 'Task manager is already stopped',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        task_manager.stop()
        
        return jsonify({
            'success': True,
            'message': 'Task manager stopped successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tasks_bp.route('/manager-status', methods=['GET'])
def get_manager_status():
    """
    Get task manager status.
    
    Returns:
        JSON response with manager status
    """
    try:
        status = {
            'is_running': task_manager.is_running,
            'max_workers': task_manager.max_workers,
            'active_tasks': len(task_manager.running_tasks),
            'queued_tasks': task_manager.task_queue.qsize(),
            'total_tasks': len(task_manager.tasks),
            'metrics': task_manager.get_metrics()
        }
        
        return jsonify({
            'success': True,
            'manager_status': status,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

