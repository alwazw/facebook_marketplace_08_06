from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, case, text
from src.models import db, FacebookAccount, Conversation, Message, MessageTemplate, AutomationRun, SystemMetric, ValidationLog

class QueryEngine:
    """
    Comprehensive query engine for generating dashboard statistics and analytics.
    This class contains all the complex SQL queries and aggregation logic used throughout the system.
    """
    
    def __init__(self):
        self.db = db
    
    # ==================== DASHBOARD OVERVIEW QUERIES ====================
    
    def get_system_overview(self):
        """
        Main dashboard overview query - combines multiple metrics into a single response.
        
        Query Objective: Provide high-level system health and performance metrics
        Tables Joined: facebook_accounts, conversations, messages, automation_runs
        Calculations: 
        - Account availability rate
        - Message processing rate  
        - Response rate percentage
        - System health score (weighted average)
        """
        
        # Account metrics
        account_stats = self.db.session.query(
            func.count(FacebookAccount.id).label('total_accounts'),
            func.sum(case((FacebookAccount.is_active == True, 1), else_=0)).label('active_accounts'),
            func.sum(case((FacebookAccount.is_locked == True, 1), else_=0)).label('locked_accounts'),
            func.sum(case((and_(FacebookAccount.is_active == True, FacebookAccount.is_locked == False), 1), else_=0)).label('available_accounts')
        ).first()
        
        # Conversation metrics
        conversation_stats = self.db.session.query(
            func.count(Conversation.id).label('total_conversations'),
            func.sum(case((Conversation.status == 'active', 1), else_=0)).label('active_conversations'),
            func.avg(Conversation.response_time_avg_minutes).label('avg_response_time')
        ).first()
        
        # Message metrics (last 24 hours)
        last_24h = datetime.utcnow() - timedelta(hours=24)
        message_stats = self.db.session.query(
            func.count(Message.id).label('total_messages_24h'),
            func.sum(case((Message.is_from_customer == True, 1), else_=0)).label('customer_messages_24h'),
            func.sum(case((and_(Message.is_from_customer == False, Message.is_automated_response == True), 1), else_=0)).label('bot_responses_24h'),
            func.sum(case((and_(Message.is_from_customer == True, Message.is_processed == False), 1), else_=0)).label('unprocessed_messages')
        ).filter(Message.timestamp >= last_24h).first()
        
        # Automation run metrics (last 24 hours)
        automation_stats = self.db.session.query(
            func.count(AutomationRun.id).label('total_runs_24h'),
            func.sum(case((AutomationRun.status == 'completed', 1), else_=0)).label('successful_runs_24h'),
            func.sum(case((AutomationRun.status == 'failed', 1), else_=0)).label('failed_runs_24h'),
            func.avg(AutomationRun.duration_seconds).label('avg_run_duration'),
            func.sum(AutomationRun.messages_processed).label('total_messages_processed_24h'),
            func.sum(AutomationRun.responses_sent).label('total_responses_sent_24h')
        ).filter(AutomationRun.start_time >= last_24h).first()
        
        # Calculate derived metrics
        account_availability_rate = (account_stats.available_accounts / account_stats.total_accounts * 100) if account_stats.total_accounts > 0 else 0
        
        message_response_rate = (message_stats.bot_responses_24h / message_stats.customer_messages_24h * 100) if message_stats.customer_messages_24h > 0 else 0
        
        automation_success_rate = (automation_stats.successful_runs_24h / automation_stats.total_runs_24h * 100) if automation_stats.total_runs_24h > 0 else 100
        
        processing_efficiency = (automation_stats.total_responses_sent_24h / automation_stats.total_messages_processed_24h * 100) if automation_stats.total_messages_processed_24h > 0 else 0
        
        # Calculate overall system health score (weighted average)
        health_score = (
            account_availability_rate * 0.25 +  # 25% weight
            message_response_rate * 0.35 +      # 35% weight  
            automation_success_rate * 0.25 +    # 25% weight
            processing_efficiency * 0.15        # 15% weight
        )
        
        return {
            'accounts': {
                'total': account_stats.total_accounts,
                'active': account_stats.active_accounts,
                'locked': account_stats.locked_accounts,
                'available': account_stats.available_accounts,
                'availability_rate': round(account_availability_rate, 2)
            },
            'conversations': {
                'total': conversation_stats.total_conversations,
                'active': conversation_stats.active_conversations,
                'avg_response_time_minutes': round(float(conversation_stats.avg_response_time or 0), 2)
            },
            'messages_24h': {
                'total': message_stats.total_messages_24h,
                'customer_messages': message_stats.customer_messages_24h,
                'bot_responses': message_stats.bot_responses_24h,
                'unprocessed': message_stats.unprocessed_messages,
                'response_rate': round(message_response_rate, 2)
            },
            'automation_24h': {
                'total_runs': automation_stats.total_runs_24h,
                'successful_runs': automation_stats.successful_runs_24h,
                'failed_runs': automation_stats.failed_runs_24h,
                'success_rate': round(automation_success_rate, 2),
                'avg_duration_seconds': round(float(automation_stats.avg_run_duration or 0), 2),
                'messages_processed': automation_stats.total_messages_processed_24h,
                'responses_sent': automation_stats.total_responses_sent_24h,
                'processing_efficiency': round(processing_efficiency, 2)
            },
            'system_health': {
                'overall_score': round(health_score, 2),
                'status': 'healthy' if health_score >= 80 else 'warning' if health_score >= 60 else 'critical'
            }
        }
    
    # ==================== ACCOUNT PERFORMANCE QUERIES ====================
    
    def get_account_performance_detailed(self, days=7):
        """
        Detailed account performance analysis with conversation and automation metrics.
        
        Query Objective: Analyze individual account performance and usage patterns
        Tables Joined: facebook_accounts, conversations, automation_runs, messages
        Calculations:
        - Conversations per account
        - Success rates per account
        - Usage distribution
        - Performance rankings
        """
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Main account performance query with subqueries for related metrics
        account_performance = self.db.session.query(
            FacebookAccount.id,
            FacebookAccount.display_name,
            FacebookAccount.email,
            FacebookAccount.is_active,
            FacebookAccount.is_locked,
            FacebookAccount.successful_logins,
            FacebookAccount.failed_logins,
            FacebookAccount.last_used,
            
            # Conversation metrics subquery
            func.count(Conversation.id).label('total_conversations'),
            func.sum(case((Conversation.status == 'active', 1), else_=0)).label('active_conversations'),
            func.avg(Conversation.response_time_avg_minutes).label('avg_response_time'),
            
            # Message metrics subquery  
            func.sum(Conversation.message_count).label('total_messages'),
            func.sum(Conversation.customer_message_count).label('customer_messages'),
            func.sum(Conversation.bot_response_count).label('bot_responses')
            
        ).outerjoin(Conversation).filter(
            or_(Conversation.created_at >= start_date, Conversation.created_at.is_(None))
        ).group_by(FacebookAccount.id).all()
        
        # Get automation run metrics for each account
        automation_metrics = {}
        for account in account_performance:
            runs = self.db.session.query(
                func.count(AutomationRun.id).label('total_runs'),
                func.sum(case((AutomationRun.status == 'completed', 1), else_=0)).label('successful_runs'),
                func.sum(AutomationRun.messages_processed).label('messages_processed'),
                func.sum(AutomationRun.responses_sent).label('responses_sent'),
                func.avg(AutomationRun.duration_seconds).label('avg_duration')
            ).filter(
                AutomationRun.facebook_account_id == account.id,
                AutomationRun.start_time >= start_date
            ).first()
            
            automation_metrics[account.id] = {
                'total_runs': runs.total_runs or 0,
                'successful_runs': runs.successful_runs or 0,
                'success_rate': (runs.successful_runs / runs.total_runs * 100) if runs.total_runs > 0 else 0,
                'messages_processed': runs.messages_processed or 0,
                'responses_sent': runs.responses_sent or 0,
                'response_rate': (runs.responses_sent / runs.messages_processed * 100) if runs.messages_processed > 0 else 0,
                'avg_duration': float(runs.avg_duration or 0)
            }
        
        # Format results with calculated performance scores
        results = []
        for account in account_performance:
            auto_metrics = automation_metrics.get(account.id, {})
            
            # Calculate performance score (0-100)
            login_success_rate = (account.successful_logins / (account.successful_logins + account.failed_logins) * 100) if (account.successful_logins + account.failed_logins) > 0 else 100
            conversation_response_rate = (account.bot_responses / account.customer_messages * 100) if account.customer_messages > 0 else 0
            automation_success_rate = auto_metrics.get('success_rate', 0)
            
            performance_score = (login_success_rate * 0.3 + conversation_response_rate * 0.4 + automation_success_rate * 0.3)
            
            results.append({
                'id': account.id,
                'display_name': account.display_name,
                'email': account.email,
                'is_active': account.is_active,
                'is_locked': account.is_locked,
                'last_used': account.last_used.isoformat() if account.last_used else None,
                'login_metrics': {
                    'successful_logins': account.successful_logins,
                    'failed_logins': account.failed_logins,
                    'success_rate': round(login_success_rate, 2)
                },
                'conversation_metrics': {
                    'total_conversations': account.total_conversations,
                    'active_conversations': account.active_conversations,
                    'total_messages': account.total_messages or 0,
                    'customer_messages': account.customer_messages or 0,
                    'bot_responses': account.bot_responses or 0,
                    'response_rate': round(conversation_response_rate, 2),
                    'avg_response_time_minutes': round(float(account.avg_response_time or 0), 2)
                },
                'automation_metrics': auto_metrics,
                'performance_score': round(performance_score, 2)
            })
        
        # Sort by performance score
        results.sort(key=lambda x: x['performance_score'], reverse=True)
        
        return results
    
    # ==================== MESSAGE ANALYTICS QUERIES ====================
    
    def get_message_classification_analytics(self, days=30):
        """
        Comprehensive message classification and processing analytics.
        
        Query Objective: Analyze message types, classification accuracy, and processing performance
        Tables Joined: messages, conversations, message_templates
        Calculations:
        - Message type distribution
        - Classification confidence analysis
        - Processing time analysis
        - Template effectiveness metrics
        """
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Message type distribution with confidence metrics
        message_type_stats = self.db.session.query(
            Message.message_type,
            func.count(Message.id).label('count'),
            func.avg(Message.classification_confidence).label('avg_confidence'),
            func.min(Message.classification_confidence).label('min_confidence'),
            func.max(Message.classification_confidence).label('max_confidence'),
            func.avg(Message.processing_time_seconds).label('avg_processing_time'),
            func.sum(case((Message.is_processed == True, 1), else_=0)).label('processed_count'),
            func.sum(case((Message.response_sent == True, 1), else_=0)).label('responded_count')
        ).filter(
            Message.is_from_customer == True,
            Message.timestamp >= start_date
        ).group_by(Message.message_type).all()
        
        # Template usage and effectiveness
        template_stats = self.db.session.query(
            MessageTemplate.name,
            MessageTemplate.message_type,
            MessageTemplate.usage_count,
            MessageTemplate.success_rate,
            func.count(Message.id).label('recent_usage')
        ).outerjoin(
            Message, Message.template_used == MessageTemplate.name
        ).filter(
            or_(Message.timestamp >= start_date, Message.timestamp.is_(None))
        ).group_by(MessageTemplate.id).all()
        
        # Processing performance by time of day
        hourly_performance = self.db.session.query(
            func.extract('hour', Message.timestamp).label('hour'),
            func.count(Message.id).label('message_count'),
            func.avg(Message.processing_time_seconds).label('avg_processing_time'),
            func.sum(case((Message.response_sent == True, 1), else_=0)).label('responses_sent')
        ).filter(
            Message.is_from_customer == True,
            Message.timestamp >= start_date
        ).group_by(func.extract('hour', Message.timestamp)).all()
        
        # Confidence distribution analysis
        confidence_distribution = self.db.session.query(
            case(
                (Message.classification_confidence >= 0.9, 'high'),
                (Message.classification_confidence >= 0.7, 'medium'),
                (Message.classification_confidence >= 0.5, 'low'),
                else_='very_low'
            ).label('confidence_level'),
            func.count(Message.id).label('count'),
            func.sum(case((Message.response_sent == True, 1), else_=0)).label('successful_responses')
        ).filter(
            Message.is_from_customer == True,
            Message.timestamp >= start_date,
            Message.classification_confidence.isnot(None)
        ).group_by('confidence_level').all()
        
        return {
            'message_types': [
                {
                    'message_type': stat.message_type,
                    'count': stat.count,
                    'avg_confidence': round(float(stat.avg_confidence or 0), 3),
                    'confidence_range': {
                        'min': round(float(stat.min_confidence or 0), 3),
                        'max': round(float(stat.max_confidence or 0), 3)
                    },
                    'avg_processing_time_seconds': round(float(stat.avg_processing_time or 0), 3),
                    'processing_rate': round((stat.processed_count / stat.count * 100), 2),
                    'response_rate': round((stat.responded_count / stat.count * 100), 2)
                } for stat in message_type_stats
            ],
            'templates': [
                {
                    'name': template.name,
                    'message_type': template.message_type,
                    'total_usage': template.usage_count,
                    'recent_usage': template.recent_usage,
                    'success_rate': round(float(template.success_rate), 2)
                } for template in template_stats
            ],
            'hourly_performance': [
                {
                    'hour': int(hour.hour),
                    'message_count': hour.message_count,
                    'avg_processing_time': round(float(hour.avg_processing_time or 0), 3),
                    'response_rate': round((hour.responses_sent / hour.message_count * 100), 2)
                } for hour in hourly_performance
            ],
            'confidence_distribution': [
                {
                    'confidence_level': conf.confidence_level,
                    'count': conf.count,
                    'success_rate': round((conf.successful_responses / conf.count * 100), 2)
                } for conf in confidence_distribution
            ]
        }
    
    # ==================== CONVERSATION ANALYTICS QUERIES ====================
    
    def get_conversation_analytics(self, days=30):
        """
        Detailed conversation analytics including customer behavior and response patterns.
        
        Query Objective: Analyze conversation patterns, customer engagement, and resolution rates
        Tables Joined: conversations, messages, facebook_accounts
        Calculations:
        - Conversation lifecycle metrics
        - Customer engagement patterns
        - Resolution rates and times
        - Account workload distribution
        """
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Conversation status and lifecycle analysis
        conversation_lifecycle = self.db.session.query(
            Conversation.status,
            func.count(Conversation.id).label('count'),
            func.avg(Conversation.message_count).label('avg_messages'),
            func.avg(Conversation.response_time_avg_minutes).label('avg_response_time'),
            func.avg(
                func.extract('epoch', Conversation.updated_at - Conversation.created_at) / 3600
            ).label('avg_duration_hours')
        ).filter(
            Conversation.created_at >= start_date
        ).group_by(Conversation.status).all()
        
        # Customer engagement patterns
        engagement_patterns = self.db.session.query(
            case(
                (Conversation.message_count >= 10, 'high_engagement'),
                (Conversation.message_count >= 5, 'medium_engagement'),
                (Conversation.message_count >= 2, 'low_engagement'),
                else_='single_message'
            ).label('engagement_level'),
            func.count(Conversation.id).label('conversation_count'),
            func.avg(Conversation.response_time_avg_minutes).label('avg_response_time'),
            func.sum(case((Conversation.status == 'closed', 1), else_=0)).label('closed_count')
        ).filter(
            Conversation.created_at >= start_date
        ).group_by('engagement_level').all()
        
        # Account workload distribution
        account_workload = self.db.session.query(
            FacebookAccount.display_name,
            func.count(Conversation.id).label('conversation_count'),
            func.sum(Conversation.message_count).label('total_messages'),
            func.avg(Conversation.response_time_avg_minutes).label('avg_response_time'),
            func.sum(case((Conversation.status == 'active', 1), else_=0)).label('active_conversations')
        ).join(Conversation).filter(
            Conversation.created_at >= start_date
        ).group_by(FacebookAccount.id).all()
        
        # Response time distribution
        response_time_distribution = self.db.session.query(
            case(
                (Conversation.response_time_avg_minutes <= 5, 'very_fast'),
                (Conversation.response_time_avg_minutes <= 15, 'fast'),
                (Conversation.response_time_avg_minutes <= 60, 'moderate'),
                (Conversation.response_time_avg_minutes <= 240, 'slow'),
                else_='very_slow'
            ).label('response_speed'),
            func.count(Conversation.id).label('count'),
            func.sum(case((Conversation.status == 'closed', 1), else_=0)).label('closed_count')
        ).filter(
            Conversation.created_at >= start_date,
            Conversation.response_time_avg_minutes.isnot(None)
        ).group_by('response_speed').all()
        
        # Daily conversation trends
        daily_trends = self.db.session.query(
            func.date(Conversation.created_at).label('date'),
            func.count(Conversation.id).label('new_conversations'),
            func.sum(case((Conversation.status == 'closed', 1), else_=0)).label('closed_conversations'),
            func.avg(Conversation.message_count).label('avg_messages_per_conversation')
        ).filter(
            Conversation.created_at >= start_date
        ).group_by(func.date(Conversation.created_at)).order_by('date').all()
        
        return {
            'lifecycle_analysis': [
                {
                    'status': lifecycle.status,
                    'count': lifecycle.count,
                    'avg_messages': round(float(lifecycle.avg_messages or 0), 2),
                    'avg_response_time_minutes': round(float(lifecycle.avg_response_time or 0), 2),
                    'avg_duration_hours': round(float(lifecycle.avg_duration_hours or 0), 2)
                } for lifecycle in conversation_lifecycle
            ],
            'engagement_patterns': [
                {
                    'engagement_level': pattern.engagement_level,
                    'conversation_count': pattern.conversation_count,
                    'avg_response_time_minutes': round(float(pattern.avg_response_time or 0), 2),
                    'closure_rate': round((pattern.closed_count / pattern.conversation_count * 100), 2)
                } for pattern in engagement_patterns
            ],
            'account_workload': [
                {
                    'account_name': workload.display_name,
                    'conversation_count': workload.conversation_count,
                    'total_messages': workload.total_messages,
                    'avg_response_time_minutes': round(float(workload.avg_response_time or 0), 2),
                    'active_conversations': workload.active_conversations,
                    'workload_score': round((workload.conversation_count * 0.6 + workload.active_conversations * 0.4), 2)
                } for workload in account_workload
            ],
            'response_time_distribution': [
                {
                    'response_speed': dist.response_speed,
                    'count': dist.count,
                    'closure_rate': round((dist.closed_count / dist.count * 100), 2)
                } for dist in response_time_distribution
            ],
            'daily_trends': [
                {
                    'date': trend.date.isoformat(),
                    'new_conversations': trend.new_conversations,
                    'closed_conversations': trend.closed_conversations,
                    'closure_rate': round((trend.closed_conversations / trend.new_conversations * 100), 2) if trend.new_conversations > 0 else 0,
                    'avg_messages_per_conversation': round(float(trend.avg_messages_per_conversation or 0), 2)
                } for trend in daily_trends
            ]
        }
    
    # ==================== AUTOMATION PERFORMANCE QUERIES ====================
    
    def get_automation_performance_analytics(self, days=7):
        """
        Comprehensive automation performance analysis.
        
        Query Objective: Analyze automation efficiency, success patterns, and performance trends
        Tables Joined: automation_runs, facebook_accounts, validation_logs
        Calculations:
        - Success rate trends
        - Performance by account
        - Error pattern analysis
        - Efficiency metrics
        """
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Overall automation performance metrics
        overall_performance = self.db.session.query(
            func.count(AutomationRun.id).label('total_runs'),
            func.sum(case((AutomationRun.status == 'completed', 1), else_=0)).label('successful_runs'),
            func.sum(case((AutomationRun.status == 'failed', 1), else_=0)).label('failed_runs'),
            func.avg(AutomationRun.duration_seconds).label('avg_duration'),
            func.sum(AutomationRun.conversations_checked).label('total_conversations_checked'),
            func.sum(AutomationRun.new_messages_found).label('total_new_messages'),
            func.sum(AutomationRun.messages_processed).label('total_messages_processed'),
            func.sum(AutomationRun.responses_sent).label('total_responses_sent'),
            func.sum(AutomationRun.errors_encountered).label('total_errors')
        ).filter(AutomationRun.start_time >= start_date).first()
        
        # Performance by account
        account_performance = self.db.session.query(
            FacebookAccount.display_name,
            func.count(AutomationRun.id).label('total_runs'),
            func.sum(case((AutomationRun.status == 'completed', 1), else_=0)).label('successful_runs'),
            func.avg(AutomationRun.duration_seconds).label('avg_duration'),
            func.sum(AutomationRun.messages_processed).label('messages_processed'),
            func.sum(AutomationRun.responses_sent).label('responses_sent'),
            func.avg(AutomationRun.success_rate).label('avg_success_rate')
        ).join(AutomationRun).filter(
            AutomationRun.start_time >= start_date
        ).group_by(FacebookAccount.id).all()
        
        # Daily performance trends
        daily_performance = self.db.session.query(
            func.date(AutomationRun.start_time).label('date'),
            func.count(AutomationRun.id).label('total_runs'),
            func.sum(case((AutomationRun.status == 'completed', 1), else_=0)).label('successful_runs'),
            func.avg(AutomationRun.duration_seconds).label('avg_duration'),
            func.sum(AutomationRun.messages_processed).label('messages_processed'),
            func.sum(AutomationRun.responses_sent).label('responses_sent')
        ).filter(
            AutomationRun.start_time >= start_date
        ).group_by(func.date(AutomationRun.start_time)).order_by('date').all()
        
        # Error analysis from validation logs
        error_analysis = self.db.session.query(
            ValidationLog.validation_type,
            func.count(ValidationLog.id).label('total_validations'),
            func.sum(case((ValidationLog.validation_status == 'failed', 1), else_=0)).label('failed_validations'),
            func.sum(case((ValidationLog.validation_status == 'warning', 1), else_=0)).label('warning_validations')
        ).filter(
            ValidationLog.timestamp >= start_date
        ).group_by(ValidationLog.validation_type).all()
        
        # Calculate derived metrics
        success_rate = (overall_performance.successful_runs / overall_performance.total_runs * 100) if overall_performance.total_runs > 0 else 0
        processing_efficiency = (overall_performance.total_responses_sent / overall_performance.total_messages_processed * 100) if overall_performance.total_messages_processed > 0 else 0
        error_rate = (overall_performance.total_errors / overall_performance.total_runs) if overall_performance.total_runs > 0 else 0
        
        return {
            'overall_metrics': {
                'total_runs': overall_performance.total_runs,
                'successful_runs': overall_performance.successful_runs,
                'failed_runs': overall_performance.failed_runs,
                'success_rate': round(success_rate, 2),
                'avg_duration_seconds': round(float(overall_performance.avg_duration or 0), 2),
                'conversations_checked': overall_performance.total_conversations_checked,
                'new_messages_found': overall_performance.total_new_messages,
                'messages_processed': overall_performance.total_messages_processed,
                'responses_sent': overall_performance.total_responses_sent,
                'processing_efficiency': round(processing_efficiency, 2),
                'error_rate': round(error_rate, 3),
                'total_errors': overall_performance.total_errors
            },
            'account_performance': [
                {
                    'account_name': perf.display_name,
                    'total_runs': perf.total_runs,
                    'successful_runs': perf.successful_runs,
                    'success_rate': round((perf.successful_runs / perf.total_runs * 100), 2) if perf.total_runs > 0 else 0,
                    'avg_duration_seconds': round(float(perf.avg_duration or 0), 2),
                    'messages_processed': perf.messages_processed,
                    'responses_sent': perf.responses_sent,
                    'response_rate': round((perf.responses_sent / perf.messages_processed * 100), 2) if perf.messages_processed > 0 else 0,
                    'avg_success_rate': round(float(perf.avg_success_rate or 0), 2)
                } for perf in account_performance
            ],
            'daily_trends': [
                {
                    'date': trend.date.isoformat(),
                    'total_runs': trend.total_runs,
                    'successful_runs': trend.successful_runs,
                    'success_rate': round((trend.successful_runs / trend.total_runs * 100), 2) if trend.total_runs > 0 else 0,
                    'avg_duration_seconds': round(float(trend.avg_duration or 0), 2),
                    'messages_processed': trend.messages_processed,
                    'responses_sent': trend.responses_sent,
                    'processing_efficiency': round((trend.responses_sent / trend.messages_processed * 100), 2) if trend.messages_processed > 0 else 0
                } for trend in daily_performance
            ],
            'error_analysis': [
                {
                    'validation_type': error.validation_type,
                    'total_validations': error.total_validations,
                    'failed_validations': error.failed_validations,
                    'warning_validations': error.warning_validations,
                    'failure_rate': round((error.failed_validations / error.total_validations * 100), 2) if error.total_validations > 0 else 0,
                    'warning_rate': round((error.warning_validations / error.total_validations * 100), 2) if error.total_validations > 0 else 0
                } for error in error_analysis
            ]
        }
    
    # ==================== REAL-TIME MONITORING QUERIES ====================
    
    def get_real_time_metrics(self):
        """
        Real-time system monitoring metrics for live dashboard updates.
        
        Query Objective: Provide current system status and recent activity
        Tables Joined: All tables for comprehensive status
        Calculations:
        - Current system load
        - Recent activity metrics
        - Active processes
        - Alert conditions
        """
        
        # Current time windows
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        last_5_minutes = now - timedelta(minutes=5)
        
        # Recent activity metrics
        recent_activity = self.db.session.query(
            func.count(Message.id).label('messages_last_hour'),
            func.sum(case((Message.timestamp >= last_5_minutes, 1), else_=0)).label('messages_last_5min'),
            func.sum(case((and_(Message.is_from_customer == True, Message.timestamp >= last_hour), 1), else_=0)).label('customer_messages_last_hour'),
            func.sum(case((and_(Message.is_automated_response == True, Message.timestamp >= last_hour), 1), else_=0)).label('bot_responses_last_hour')
        ).filter(Message.timestamp >= last_hour).first()
        
        # Active automation runs
        active_runs = self.db.session.query(
            func.count(AutomationRun.id).label('active_runs')
        ).filter(AutomationRun.status == 'running').first()
        
        # System health indicators
        health_indicators = self.db.session.query(
            func.count(FacebookAccount.id).label('total_accounts'),
            func.sum(case((and_(FacebookAccount.is_active == True, FacebookAccount.is_locked == False), 1), else_=0)).label('healthy_accounts'),
            func.sum(case((Message.is_processed == False, 1), else_=0)).label('unprocessed_messages'),
            func.count(Conversation.id).label('active_conversations')
        ).outerjoin(Message, and_(Message.is_from_customer == True, Message.is_processed == False)).outerjoin(Conversation, Conversation.status == 'active').first()
        
        # Recent errors and warnings
        recent_issues = self.db.session.query(
            func.count(ValidationLog.id).label('total_validations'),
            func.sum(case((ValidationLog.validation_status == 'failed', 1), else_=0)).label('failed_validations'),
            func.sum(case((ValidationLog.validation_status == 'warning', 1), else_=0)).label('warning_validations')
        ).filter(ValidationLog.timestamp >= last_hour).first()
        
        # Calculate alert conditions
        account_health_rate = (health_indicators.healthy_accounts / health_indicators.total_accounts * 100) if health_indicators.total_accounts > 0 else 0
        processing_backlog = health_indicators.unprocessed_messages or 0
        error_rate = (recent_issues.failed_validations / recent_issues.total_validations * 100) if recent_issues.total_validations > 0 else 0
        
        # Determine alert levels
        alerts = []
        if account_health_rate < 80:
            alerts.append({
                'level': 'critical' if account_health_rate < 50 else 'warning',
                'message': f'Account availability low: {account_health_rate:.1f}%',
                'metric': 'account_health'
            })
        
        if processing_backlog > 10:
            alerts.append({
                'level': 'warning',
                'message': f'Processing backlog: {processing_backlog} unprocessed messages',
                'metric': 'processing_backlog'
            })
        
        if error_rate > 10:
            alerts.append({
                'level': 'warning' if error_rate < 25 else 'critical',
                'message': f'High error rate: {error_rate:.1f}%',
                'metric': 'error_rate'
            })
        
        return {
            'timestamp': now.isoformat(),
            'recent_activity': {
                'messages_last_hour': recent_activity.messages_last_hour,
                'messages_last_5min': recent_activity.messages_last_5min,
                'customer_messages_last_hour': recent_activity.customer_messages_last_hour,
                'bot_responses_last_hour': recent_activity.bot_responses_last_hour,
                'response_rate_last_hour': round((recent_activity.bot_responses_last_hour / recent_activity.customer_messages_last_hour * 100), 2) if recent_activity.customer_messages_last_hour > 0 else 0
            },
            'system_status': {
                'active_automation_runs': active_runs.active_runs,
                'total_accounts': health_indicators.total_accounts,
                'healthy_accounts': health_indicators.healthy_accounts,
                'account_health_rate': round(account_health_rate, 2),
                'unprocessed_messages': processing_backlog,
                'active_conversations': health_indicators.active_conversations
            },
            'recent_issues': {
                'total_validations': recent_issues.total_validations,
                'failed_validations': recent_issues.failed_validations,
                'warning_validations': recent_issues.warning_validations,
                'error_rate': round(error_rate, 2)
            },
            'alerts': alerts,
            'overall_health': 'healthy' if len(alerts) == 0 else 'warning' if all(a['level'] == 'warning' for a in alerts) else 'critical'
        }

