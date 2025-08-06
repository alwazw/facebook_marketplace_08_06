from flask import Blueprint, request, jsonify
from src.services.validation_service import ValidationService
from src.services.task_manager import get_task_manager, TaskPriority
from datetime import datetime

validation_bp = Blueprint('validation', __name__)
validation_service = ValidationService()
task_manager = get_task_manager()

@validation_bp.route('/run-full-validation', methods=['POST'])
def run_full_validation():
    """
    Run comprehensive system validation.
    
    Returns:
        JSON response with validation results
    """
    try:
        # Run validation as a task for better tracking
        task_id = task_manager.create_task(
            name="Full System Validation",
            task_type="validate_system",
            priority=TaskPriority.HIGH,
            metadata={'requested_by': 'api', 'validation_type': 'full'}
        )
        
        return jsonify({
            'success': True,
            'message': 'Validation task created',
            'task_id': task_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@validation_bp.route('/run-quick-validation', methods=['POST'])
def run_quick_validation():
    """
    Run quick system validation (synchronous).
    
    Returns:
        JSON response with validation results
    """
    try:
        # Run basic validation checks synchronously
        validation_result = validation_service.validate_all_systems()
        
        return jsonify({
            'success': True,
            'validation_result': validation_result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@validation_bp.route('/database-integrity', methods=['GET'])
def check_database_integrity():
    """
    Check database integrity.
    
    Returns:
        JSON response with database validation results
    """
    try:
        integrity_result = validation_service.validate_database_integrity()
        
        return jsonify({
            'success': True,
            'database_integrity': integrity_result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@validation_bp.route('/data-quality', methods=['GET'])
def check_data_quality():
    """
    Check data quality across all tables.
    
    Returns:
        JSON response with data quality results
    """
    try:
        quality_result = validation_service.validate_data_quality()
        
        return jsonify({
            'success': True,
            'data_quality': quality_result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@validation_bp.route('/business-logic', methods=['GET'])
def check_business_logic():
    """
    Check business logic validation.
    
    Returns:
        JSON response with business logic validation results
    """
    try:
        logic_result = validation_service.validate_business_logic()
        
        return jsonify({
            'success': True,
            'business_logic': logic_result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@validation_bp.route('/performance', methods=['GET'])
def check_performance():
    """
    Check system performance metrics.
    
    Returns:
        JSON response with performance validation results
    """
    try:
        performance_result = validation_service.validate_system_performance()
        
        return jsonify({
            'success': True,
            'performance': performance_result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@validation_bp.route('/security', methods=['GET'])
def check_security():
    """
    Check security measures.
    
    Returns:
        JSON response with security validation results
    """
    try:
        security_result = validation_service.validate_security_measures()
        
        return jsonify({
            'success': True,
            'security': security_result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@validation_bp.route('/system-health', methods=['GET'])
def check_system_health():
    """
    Check overall system health.
    
    Returns:
        JSON response with system health validation results
    """
    try:
        health_result = validation_service.validate_system_health()
        
        return jsonify({
            'success': True,
            'system_health': health_result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@validation_bp.route('/validation-history', methods=['GET'])
def get_validation_history():
    """
    Get validation task history.
    
    Query Parameters:
        limit: Number of records to return (default: 20)
        
    Returns:
        JSON response with validation task history
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        
        # Get validation tasks from task manager
        validation_tasks = task_manager.get_tasks_by_type('validate_system')
        
        # Sort by creation time and limit
        validation_tasks.sort(key=lambda t: t.created_at, reverse=True)
        validation_tasks = validation_tasks[:limit]
        
        # Convert to serializable format
        history = []
        for task in validation_tasks:
            task_data = task.to_dict()
            history.append(task_data)
        
        return jsonify({
            'success': True,
            'validation_history': history,
            'total_count': len(validation_tasks),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@validation_bp.route('/validation-report', methods=['POST'])
def generate_validation_report():
    """
    Generate comprehensive validation report.
    
    Request Body:
        report_type: Type of report (summary, detailed, full)
        include_history: Whether to include historical data
        
    Returns:
        JSON response with validation report
    """
    try:
        data = request.get_json() or {}
        report_type = data.get('report_type', 'summary')
        include_history = data.get('include_history', False)
        
        # Run current validation
        current_validation = validation_service.validate_all_systems()
        
        report = {
            'report_type': report_type,
            'generated_at': datetime.utcnow().isoformat(),
            'current_validation': current_validation
        }
        
        if include_history:
            # Get recent validation tasks
            validation_tasks = task_manager.get_tasks_by_type('validate_system')
            validation_tasks.sort(key=lambda t: t.created_at, reverse=True)
            
            history = []
            for task in validation_tasks[:10]:  # Last 10 validations
                if task.result:
                    history.append({
                        'task_id': task.id,
                        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                        'status': task.status.value,
                        'result': task.result
                    })
            
            report['validation_history'] = history
        
        if report_type in ['detailed', 'full']:
            # Add detailed metrics
            report['task_manager_metrics'] = task_manager.get_metrics()
            
            # Add system statistics
            from src.services.query_engine import QueryEngine
            query_engine = QueryEngine()
            report['system_overview'] = query_engine.get_system_overview()
        
        return jsonify({
            'success': True,
            'report': report,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@validation_bp.route('/fix-issues', methods=['POST'])
def fix_validation_issues():
    """
    Attempt to automatically fix validation issues.
    
    Request Body:
        issue_types: List of issue types to fix
        dry_run: Whether to perform a dry run (default: true)
        
    Returns:
        JSON response with fix results
    """
    try:
        data = request.get_json() or {}
        issue_types = data.get('issue_types', [])
        dry_run = data.get('dry_run', True)
        
        fix_results = {
            'dry_run': dry_run,
            'fixes_applied': [],
            'fixes_failed': [],
            'recommendations': []
        }
        
        # Run validation to identify issues
        validation_result = validation_service.validate_all_systems()
        
        # Collect all errors and warnings
        all_issues = []
        for validation_type, results in validation_result['validations'].items():
            all_issues.extend(results.get('errors', []))
            all_issues.extend(results.get('warnings', []))
        
        # Filter by requested issue types if specified
        if issue_types:
            all_issues = [issue for issue in all_issues if issue.get('type') in issue_types]
        
        # Attempt to fix issues
        for issue in all_issues:
            issue_type = issue.get('type')
            
            if issue_type == 'missing_tables':
                if not dry_run:
                    # Recreate missing tables
                    from src.models import db
                    db.create_all()
                    fix_results['fixes_applied'].append({
                        'issue_type': issue_type,
                        'action': 'recreated_missing_tables'
                    })
                else:
                    fix_results['recommendations'].append({
                        'issue_type': issue_type,
                        'recommended_action': 'recreate_missing_tables'
                    })
            
            elif issue_type == 'foreign_key_violations':
                fix_results['recommendations'].append({
                    'issue_type': issue_type,
                    'recommended_action': 'manual_data_cleanup_required'
                })
            
            elif issue_type == 'data_consistency':
                fix_results['recommendations'].append({
                    'issue_type': issue_type,
                    'recommended_action': 'run_data_cleanup_task'
                })
            
            else:
                fix_results['recommendations'].append({
                    'issue_type': issue_type,
                    'recommended_action': 'manual_investigation_required'
                })
        
        return jsonify({
            'success': True,
            'fix_results': fix_results,
            'total_issues_found': len(all_issues),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

