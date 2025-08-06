from flask import Blueprint, request, jsonify
from src.services.query_engine import QueryEngine
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)
query_engine = QueryEngine()

@dashboard_bp.route('/overview', methods=['GET'])
def get_dashboard_overview():
    """
    Main dashboard overview endpoint.
    
    Returns comprehensive system metrics including:
    - Account status and availability
    - Message processing statistics
    - Automation performance metrics
    - System health score
    """
    try:
        overview_data = query_engine.get_system_overview()
        return jsonify({
            'success': True,
            'data': overview_data,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@dashboard_bp.route('/accounts/performance', methods=['GET'])
def get_account_performance():
    """
    Detailed account performance analytics.
    
    Query Parameters:
    - days: Number of days to analyze (default: 7)
    
    Returns:
    - Individual account performance metrics
    - Login success rates
    - Conversation handling statistics
    - Automation run performance
    - Performance rankings
    """
    try:
        days = request.args.get('days', 7, type=int)
        performance_data = query_engine.get_account_performance_detailed(days)
        
        return jsonify({
            'success': True,
            'data': performance_data,
            'analysis_period_days': days,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@dashboard_bp.route('/messages/analytics', methods=['GET'])
def get_message_analytics():
    """
    Comprehensive message classification and processing analytics.
    
    Query Parameters:
    - days: Number of days to analyze (default: 30)
    
    Returns:
    - Message type distribution
    - Classification confidence analysis
    - Processing time metrics
    - Template effectiveness
    - Hourly performance patterns
    """
    try:
        days = request.args.get('days', 30, type=int)
        analytics_data = query_engine.get_message_classification_analytics(days)
        
        return jsonify({
            'success': True,
            'data': analytics_data,
            'analysis_period_days': days,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@dashboard_bp.route('/conversations/analytics', methods=['GET'])
def get_conversation_analytics():
    """
    Detailed conversation analytics and customer behavior patterns.
    
    Query Parameters:
    - days: Number of days to analyze (default: 30)
    
    Returns:
    - Conversation lifecycle analysis
    - Customer engagement patterns
    - Response time distribution
    - Account workload analysis
    - Daily conversation trends
    """
    try:
        days = request.args.get('days', 30, type=int)
        analytics_data = query_engine.get_conversation_analytics(days)
        
        return jsonify({
            'success': True,
            'data': analytics_data,
            'analysis_period_days': days,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@dashboard_bp.route('/automation/performance', methods=['GET'])
def get_automation_performance():
    """
    Comprehensive automation performance analytics.
    
    Query Parameters:
    - days: Number of days to analyze (default: 7)
    
    Returns:
    - Overall automation metrics
    - Performance by account
    - Daily performance trends
    - Error analysis
    - Efficiency metrics
    """
    try:
        days = request.args.get('days', 7, type=int)
        performance_data = query_engine.get_automation_performance_analytics(days)
        
        return jsonify({
            'success': True,
            'data': performance_data,
            'analysis_period_days': days,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@dashboard_bp.route('/real-time', methods=['GET'])
def get_real_time_metrics():
    """
    Real-time system monitoring metrics for live dashboard updates.
    
    Returns:
    - Current system activity
    - Recent message processing
    - Active automation runs
    - System health indicators
    - Alert conditions
    """
    try:
        real_time_data = query_engine.get_real_time_metrics()
        
        return jsonify({
            'success': True,
            'data': real_time_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@dashboard_bp.route('/health-check', methods=['GET'])
def health_check():
    """
    System health check endpoint for monitoring.
    
    Returns:
    - Overall system status
    - Critical metrics
    - Alert summary
    """
    try:
        real_time_data = query_engine.get_real_time_metrics()
        overview_data = query_engine.get_system_overview()
        
        # Extract key health indicators
        health_summary = {
            'overall_status': real_time_data['overall_health'],
            'system_health_score': overview_data['system_health']['overall_score'],
            'account_availability': overview_data['accounts']['availability_rate'],
            'automation_success_rate': overview_data['automation_24h']['success_rate'],
            'message_response_rate': overview_data['messages_24h']['response_rate'],
            'active_alerts': len(real_time_data['alerts']),
            'unprocessed_messages': real_time_data['system_status']['unprocessed_messages'],
            'timestamp': real_time_data['timestamp']
        }
        
        # Determine HTTP status based on health
        status_code = 200
        if real_time_data['overall_health'] == 'critical':
            status_code = 503  # Service Unavailable
        elif real_time_data['overall_health'] == 'warning':
            status_code = 200  # OK but with warnings
        
        return jsonify({
            'success': True,
            'health': health_summary,
            'alerts': real_time_data['alerts']
        }), status_code
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'health': {'overall_status': 'critical', 'error': str(e)},
            'alerts': [{'level': 'critical', 'message': f'Health check failed: {str(e)}', 'metric': 'system_error'}]
        }), 503

@dashboard_bp.route('/summary-stats', methods=['GET'])
def get_summary_stats():
    """
    Quick summary statistics for dashboard widgets.
    
    Returns:
    - Key performance indicators
    - Trend indicators
    - Quick metrics for dashboard cards
    """
    try:
        overview = query_engine.get_system_overview()
        real_time = query_engine.get_real_time_metrics()
        
        # Calculate trend indicators (simplified - in production would compare with previous periods)
        trends = {
            'accounts_trend': 'stable',  # Would calculate based on historical data
            'messages_trend': 'up' if real_time['recent_activity']['messages_last_hour'] > 10 else 'stable',
            'automation_trend': 'up' if overview['automation_24h']['success_rate'] > 90 else 'stable',
            'health_trend': 'up' if overview['system_health']['overall_score'] > 85 else 'down'
        }
        
        summary = {
            'key_metrics': {
                'total_accounts': overview['accounts']['total'],
                'active_accounts': overview['accounts']['active'],
                'total_conversations': overview['conversations']['total'],
                'active_conversations': overview['conversations']['active'],
                'messages_24h': overview['messages_24h']['total'],
                'automation_runs_24h': overview['automation_24h']['total_runs'],
                'system_health_score': overview['system_health']['overall_score'],
                'unprocessed_messages': real_time['system_status']['unprocessed_messages']
            },
            'performance_indicators': {
                'account_availability_rate': overview['accounts']['availability_rate'],
                'message_response_rate': overview['messages_24h']['response_rate'],
                'automation_success_rate': overview['automation_24h']['success_rate'],
                'avg_response_time_minutes': overview['conversations']['avg_response_time_minutes']
            },
            'trends': trends,
            'status': {
                'overall_health': real_time['overall_health'],
                'active_alerts': len(real_time['alerts']),
                'critical_alerts': len([a for a in real_time['alerts'] if a['level'] == 'critical'])
            }
        }
        
        return jsonify({
            'success': True,
            'summary': summary,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@dashboard_bp.route('/export-report', methods=['POST'])
def export_dashboard_report():
    """
    Export comprehensive dashboard report.
    
    Request Body:
    - report_type: Type of report (overview, detailed, performance)
    - date_range: Date range for analysis
    - format: Export format (json, csv - future)
    
    Returns:
    - Comprehensive report data
    """
    try:
        data = request.get_json()
        report_type = data.get('report_type', 'overview')
        days = data.get('days', 7)
        
        report_data = {}
        
        if report_type in ['overview', 'detailed']:
            report_data['overview'] = query_engine.get_system_overview()
            report_data['real_time'] = query_engine.get_real_time_metrics()
        
        if report_type in ['detailed', 'performance']:
            report_data['account_performance'] = query_engine.get_account_performance_detailed(days)
            report_data['message_analytics'] = query_engine.get_message_classification_analytics(days)
            report_data['conversation_analytics'] = query_engine.get_conversation_analytics(days)
            report_data['automation_performance'] = query_engine.get_automation_performance_analytics(days)
        
        # Add report metadata
        report_metadata = {
            'report_type': report_type,
            'generated_at': datetime.utcnow().isoformat(),
            'analysis_period_days': days,
            'data_sources': ['facebook_accounts', 'conversations', 'messages', 'automation_runs', 'system_metrics', 'validation_logs']
        }
        
        return jsonify({
            'success': True,
            'report': {
                'metadata': report_metadata,
                'data': report_data
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

