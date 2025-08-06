from flask import Blueprint, request, jsonify
from src.models import db, FacebookAccount, Conversation, Message, MessageTemplate, AutomationRun, SystemMetric, ValidationLog
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/query-builder', methods=['POST'])
def execute_custom_query():
    """Execute custom analytics queries"""
    try:
        data = request.get_json()
        query_type = data.get('query_type')
        filters = data.get('filters', {})
        
        if query_type == 'conversation_performance':
            return get_conversation_performance(filters)
        elif query_type == 'message_classification_stats':
            return get_message_classification_stats(filters)
        elif query_type == 'account_performance':
            return get_account_performance(filters)
        elif query_type == 'template_effectiveness':
            return get_template_effectiveness(filters)
        elif query_type == 'system_health_trends':
            return get_system_health_trends(filters)
        else:
            return jsonify({'success': False, 'error': 'Invalid query type'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def get_conversation_performance(filters):
    """Get conversation performance analytics"""
    # Base query
    query = db.session.query(
        Conversation.id,
        Conversation.customer_name,
        Conversation.marketplace_item_title,
        Conversation.status,
        Conversation.message_count,
        Conversation.customer_message_count,
        Conversation.bot_response_count,
        Conversation.response_time_avg_minutes,
        Conversation.created_at,
        FacebookAccount.display_name.label('account_name')
    ).join(FacebookAccount)
    
    # Apply filters
    if filters.get('account_id'):
        query = query.filter(Conversation.facebook_account_id == filters['account_id'])
    
    if filters.get('status'):
        query = query.filter(Conversation.status == filters['status'])
    
    if filters.get('date_from'):
        date_from = datetime.fromisoformat(filters['date_from'])
        query = query.filter(Conversation.created_at >= date_from)
    
    if filters.get('date_to'):
        date_to = datetime.fromisoformat(filters['date_to'])
        query = query.filter(Conversation.created_at <= date_to)
    
    conversations = query.order_by(Conversation.created_at.desc()).limit(100).all()
    
    # Calculate aggregated metrics
    total_conversations = len(conversations)
    avg_response_time = sum(c.response_time_avg_minutes or 0 for c in conversations) / total_conversations if total_conversations > 0 else 0
    avg_messages_per_conversation = sum(c.message_count for c in conversations) / total_conversations if total_conversations > 0 else 0
    
    # Response rate calculation
    total_customer_messages = sum(c.customer_message_count for c in conversations)
    total_bot_responses = sum(c.bot_response_count for c in conversations)
    response_rate = (total_bot_responses / total_customer_messages * 100) if total_customer_messages > 0 else 0
    
    return jsonify({
        'success': True,
        'data': {
            'conversations': [
                {
                    'id': c.id,
                    'customer_name': c.customer_name,
                    'item_title': c.marketplace_item_title,
                    'status': c.status,
                    'message_count': c.message_count,
                    'customer_messages': c.customer_message_count,
                    'bot_responses': c.bot_response_count,
                    'response_time_minutes': c.response_time_avg_minutes,
                    'created_at': c.created_at.isoformat(),
                    'account_name': c.account_name
                } for c in conversations
            ],
            'aggregated_metrics': {
                'total_conversations': total_conversations,
                'avg_response_time_minutes': avg_response_time,
                'avg_messages_per_conversation': avg_messages_per_conversation,
                'response_rate_percent': response_rate
            }
        }
    })

def get_message_classification_stats(filters):
    """Get message classification statistics"""
    # Query message types and their counts
    query = db.session.query(
        Message.message_type,
        func.count(Message.id).label('count'),
        func.avg(Message.classification_confidence).label('avg_confidence'),
        func.avg(Message.processing_time_seconds).label('avg_processing_time')
    ).filter(Message.is_from_customer == True)
    
    # Apply filters
    if filters.get('date_from'):
        date_from = datetime.fromisoformat(filters['date_from'])
        query = query.filter(Message.timestamp >= date_from)
    
    if filters.get('date_to'):
        date_to = datetime.fromisoformat(filters['date_to'])
        query = query.filter(Message.timestamp <= date_to)
    
    if filters.get('account_id'):
        query = query.join(Conversation).filter(Conversation.facebook_account_id == filters['account_id'])
    
    message_stats = query.group_by(Message.message_type).all()
    
    # Get template usage stats
    template_query = db.session.query(
        MessageTemplate.name,
        MessageTemplate.message_type,
        MessageTemplate.usage_count,
        MessageTemplate.success_rate
    ).filter(MessageTemplate.is_active == True)
    
    templates = template_query.all()
    
    # Calculate processing accuracy
    processed_messages = db.session.query(Message).filter(
        Message.is_from_customer == True,
        Message.is_processed == True
    )
    
    if filters.get('date_from'):
        processed_messages = processed_messages.filter(Message.timestamp >= datetime.fromisoformat(filters['date_from']))
    
    if filters.get('date_to'):
        processed_messages = processed_messages.filter(Message.timestamp <= datetime.fromisoformat(filters['date_to']))
    
    total_processed = processed_messages.count()
    successfully_responded = processed_messages.filter(Message.response_sent == True).count()
    processing_accuracy = (successfully_responded / total_processed * 100) if total_processed > 0 else 0
    
    return jsonify({
        'success': True,
        'data': {
            'message_type_distribution': [
                {
                    'message_type': stat.message_type,
                    'count': stat.count,
                    'avg_confidence': float(stat.avg_confidence or 0),
                    'avg_processing_time': float(stat.avg_processing_time or 0)
                } for stat in message_stats
            ],
            'template_performance': [
                {
                    'template_name': t.name,
                    'message_type': t.message_type,
                    'usage_count': t.usage_count,
                    'success_rate': float(t.success_rate)
                } for t in templates
            ],
            'processing_metrics': {
                'total_processed_messages': total_processed,
                'successfully_responded': successfully_responded,
                'processing_accuracy_percent': processing_accuracy
            }
        }
    })

def get_account_performance(filters):
    """Get account performance analytics"""
    # Query account performance metrics
    query = db.session.query(
        FacebookAccount.id,
        FacebookAccount.display_name,
        FacebookAccount.email,
        FacebookAccount.is_active,
        FacebookAccount.is_locked,
        FacebookAccount.successful_logins,
        FacebookAccount.failed_logins,
        FacebookAccount.last_used,
        func.count(Conversation.id).label('total_conversations'),
        func.count(AutomationRun.id).label('total_runs')
    ).outerjoin(Conversation).outerjoin(AutomationRun)
    
    # Apply date filters to related tables
    if filters.get('date_from'):
        date_from = datetime.fromisoformat(filters['date_from'])
        query = query.filter(
            or_(
                Conversation.created_at >= date_from,
                AutomationRun.start_time >= date_from,
                Conversation.created_at.is_(None)
            )
        )
    
    accounts = query.group_by(FacebookAccount.id).all()
    
    # Get detailed automation stats for each account
    account_details = []
    for account in accounts:
        # Get recent automation runs
        recent_runs = AutomationRun.query.filter_by(facebook_account_id=account.id)
        
        if filters.get('date_from'):
            recent_runs = recent_runs.filter(AutomationRun.start_time >= datetime.fromisoformat(filters['date_from']))
        
        runs = recent_runs.order_by(AutomationRun.start_time.desc()).limit(50).all()
        
        successful_runs = len([r for r in runs if r.status == 'completed'])
        total_messages_processed = sum(r.messages_processed for r in runs)
        total_responses_sent = sum(r.responses_sent for r in runs)
        avg_duration = sum(r.duration_seconds or 0 for r in runs) / len(runs) if runs else 0
        
        account_details.append({
            'id': account.id,
            'display_name': account.display_name,
            'email': account.email,
            'is_active': account.is_active,
            'is_locked': account.is_locked,
            'successful_logins': account.successful_logins,
            'failed_logins': account.failed_logins,
            'last_used': account.last_used.isoformat() if account.last_used else None,
            'total_conversations': account.total_conversations,
            'automation_stats': {
                'total_runs': len(runs),
                'successful_runs': successful_runs,
                'success_rate': (successful_runs / len(runs) * 100) if runs else 0,
                'total_messages_processed': total_messages_processed,
                'total_responses_sent': total_responses_sent,
                'avg_duration_seconds': avg_duration,
                'response_rate': (total_responses_sent / total_messages_processed * 100) if total_messages_processed > 0 else 0
            }
        })
    
    return jsonify({
        'success': True,
        'data': {
            'accounts': account_details,
            'summary': {
                'total_accounts': len(accounts),
                'active_accounts': len([a for a in accounts if a.is_active]),
                'locked_accounts': len([a for a in accounts if a.is_locked]),
                'total_conversations': sum(a.total_conversations for a in accounts),
                'avg_conversations_per_account': sum(a.total_conversations for a in accounts) / len(accounts) if accounts else 0
            }
        }
    })

def get_template_effectiveness(filters):
    """Get template effectiveness analytics"""
    # Query template usage and success rates
    templates = MessageTemplate.query.filter_by(is_active=True).all()
    
    template_details = []
    for template in templates:
        # Get messages that used this template
        messages_query = Message.query.filter_by(template_used=template.name)
        
        if filters.get('date_from'):
            messages_query = messages_query.filter(Message.timestamp >= datetime.fromisoformat(filters['date_from']))
        
        if filters.get('date_to'):
            messages_query = messages_query.filter(Message.timestamp <= datetime.fromisoformat(filters['date_to']))
        
        messages = messages_query.all()
        
        # Calculate effectiveness metrics
        total_usage = len(messages)
        successful_responses = len([m for m in messages if m.response_sent])
        avg_processing_time = sum(m.processing_time_seconds or 0 for m in messages) / total_usage if total_usage > 0 else 0
        
        # Get conversations where this template was used
        conversation_ids = list(set(m.conversation_id for m in messages))
        conversations = Conversation.query.filter(Conversation.id.in_(conversation_ids)).all() if conversation_ids else []
        
        # Calculate conversation outcomes
        closed_conversations = len([c for c in conversations if c.status == 'closed'])
        avg_conversation_rating = sum(c.conversation_rating or 0 for c in conversations) / len(conversations) if conversations else 0
        
        template_details.append({
            'template_name': template.name,
            'message_type': template.message_type,
            'template_text': template.template_text,
            'variables': template.get_variables(),
            'usage_metrics': {
                'total_usage': total_usage,
                'successful_responses': successful_responses,
                'success_rate': (successful_responses / total_usage * 100) if total_usage > 0 else 0,
                'avg_processing_time': avg_processing_time
            },
            'conversation_impact': {
                'conversations_affected': len(conversations),
                'closed_conversations': closed_conversations,
                'closure_rate': (closed_conversations / len(conversations) * 100) if conversations else 0,
                'avg_rating': avg_conversation_rating
            }
        })
    
    return jsonify({
        'success': True,
        'data': {
            'templates': template_details,
            'summary': {
                'total_templates': len(templates),
                'avg_success_rate': sum(t['usage_metrics']['success_rate'] for t in template_details) / len(template_details) if template_details else 0,
                'most_used_template': max(template_details, key=lambda x: x['usage_metrics']['total_usage'])['template_name'] if template_details else None,
                'best_performing_template': max(template_details, key=lambda x: x['usage_metrics']['success_rate'])['template_name'] if template_details else None
            }
        }
    })

def get_system_health_trends(filters):
    """Get system health trends over time"""
    # Get system metrics over time
    days = filters.get('days', 7)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    metrics = SystemMetric.query.filter(SystemMetric.timestamp >= start_date).order_by(SystemMetric.timestamp.asc()).all()
    
    # Group metrics by date and type
    daily_metrics = {}
    for metric in metrics:
        date_key = metric.timestamp.strftime('%Y-%m-%d')
        if date_key not in daily_metrics:
            daily_metrics[date_key] = {}
        daily_metrics[date_key][metric.metric_name] = metric.metric_value
    
    # Get validation logs for error trends
    validation_logs = ValidationLog.query.filter(
        ValidationLog.timestamp >= start_date
    ).order_by(ValidationLog.timestamp.asc()).all()
    
    # Group validation logs by date and status
    daily_validations = {}
    for log in validation_logs:
        date_key = log.timestamp.strftime('%Y-%m-%d')
        if date_key not in daily_validations:
            daily_validations[date_key] = {'passed': 0, 'warning': 0, 'failed': 0}
        daily_validations[date_key][log.validation_status] += 1
    
    # Get automation run trends
    automation_runs = AutomationRun.query.filter(
        AutomationRun.start_time >= start_date
    ).order_by(AutomationRun.start_time.asc()).all()
    
    daily_automation = {}
    for run in automation_runs:
        date_key = run.start_time.strftime('%Y-%m-%d')
        if date_key not in daily_automation:
            daily_automation[date_key] = {'total': 0, 'successful': 0, 'failed': 0}
        daily_automation[date_key]['total'] += 1
        if run.status == 'completed':
            daily_automation[date_key]['successful'] += 1
        elif run.status == 'failed':
            daily_automation[date_key]['failed'] += 1
    
    # Calculate overall health score trends
    health_trends = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        date_key = date.strftime('%Y-%m-%d')
        
        # Get metrics for this date
        day_metrics = daily_metrics.get(date_key, {})
        day_validations = daily_validations.get(date_key, {'passed': 0, 'warning': 0, 'failed': 0})
        day_automation = daily_automation.get(date_key, {'total': 0, 'successful': 0, 'failed': 0})
        
        # Calculate health score
        response_rate = day_metrics.get('response_rate_percent', 0)
        automation_success = (day_automation['successful'] / day_automation['total'] * 100) if day_automation['total'] > 0 else 100
        validation_success = (day_validations['passed'] / sum(day_validations.values()) * 100) if sum(day_validations.values()) > 0 else 100
        
        health_score = (response_rate + automation_success + validation_success) / 3
        
        health_trends.append({
            'date': date_key,
            'health_score': health_score,
            'metrics': day_metrics,
            'validations': day_validations,
            'automation': day_automation
        })
    
    return jsonify({
        'success': True,
        'data': {
            'health_trends': health_trends,
            'summary': {
                'avg_health_score': sum(h['health_score'] for h in health_trends) / len(health_trends) if health_trends else 0,
                'trend_direction': 'improving' if len(health_trends) >= 2 and health_trends[-1]['health_score'] > health_trends[0]['health_score'] else 'declining',
                'total_validations': sum(sum(h['validations'].values()) for h in health_trends),
                'total_automation_runs': sum(h['automation']['total'] for h in health_trends)
            }
        }
    })

@analytics_bp.route('/export-data', methods=['POST'])
def export_data():
    """Export analytics data in various formats"""
    try:
        data = request.get_json()
        export_type = data.get('export_type', 'json')
        query_type = data.get('query_type')
        filters = data.get('filters', {})
        
        # Execute the query based on type
        if query_type == 'conversation_performance':
            result = get_conversation_performance(filters)
        elif query_type == 'message_classification_stats':
            result = get_message_classification_stats(filters)
        elif query_type == 'account_performance':
            result = get_account_performance(filters)
        elif query_type == 'template_effectiveness':
            result = get_template_effectiveness(filters)
        elif query_type == 'system_health_trends':
            result = get_system_health_trends(filters)
        else:
            return jsonify({'success': False, 'error': 'Invalid query type'}), 400
        
        # For now, return JSON format
        # In a real implementation, you could add CSV, Excel export functionality
        return result
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

