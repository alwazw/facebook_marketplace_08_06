from flask import Blueprint, request, jsonify
from src.models import db, FacebookAccount, Conversation, Message, AutomationRun
from src.services.automation_service import AutomationService
from datetime import datetime, timedelta

automation_bp = Blueprint('automation', __name__)
automation_service = AutomationService()

@automation_bp.route('/accounts', methods=['GET'])
def get_accounts():
    """Get all Facebook accounts"""
    try:
        accounts = FacebookAccount.query.all()
        return jsonify({
            'success': True,
            'accounts': [account.to_dict() for account in accounts],
            'total_count': len(accounts)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/accounts/<int:account_id>', methods=['GET'])
def get_account(account_id):
    """Get specific account details"""
    try:
        account = FacebookAccount.query.get(account_id)
        if not account:
            return jsonify({'success': False, 'error': 'Account not found'}), 404
        
        return jsonify({
            'success': True,
            'account': account.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/run-cycle', methods=['POST'])
def run_automation_cycle():
    """Run automation cycle for a specific account"""
    try:
        data = request.get_json()
        account_id = data.get('account_id')
        
        if not account_id:
            return jsonify({'success': False, 'error': 'account_id is required'}), 400
        
        result = automation_service.run_automation_cycle(account_id)
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/run-all-accounts', methods=['POST'])
def run_all_accounts():
    """Run automation for all active accounts"""
    try:
        result = automation_service.run_all_accounts()
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/stats', methods=['GET'])
def get_automation_stats():
    """Get automation statistics"""
    try:
        account_id = request.args.get('account_id', type=int)
        stats = automation_service.get_automation_stats(account_id)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/conversations', methods=['GET'])
def get_conversations():
    """Get conversations with filtering"""
    try:
        account_id = request.args.get('account_id', type=int)
        status = request.args.get('status', 'active')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = Conversation.query
        
        if account_id:
            query = query.filter_by(facebook_account_id=account_id)
        
        if status:
            query = query.filter_by(status=status)
        
        total_count = query.count()
        conversations = query.order_by(Conversation.last_message_time.desc()).offset(offset).limit(limit).all()
        
        return jsonify({
            'success': True,
            'conversations': [conv.to_dict() for conv in conversations],
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/conversations/<int:conversation_id>/messages', methods=['GET'])
def get_conversation_messages(conversation_id):
    """Get messages for a specific conversation"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({'success': False, 'error': 'Conversation not found'}), 404
        
        query = Message.query.filter_by(conversation_id=conversation_id)
        total_count = query.count()
        messages = query.order_by(Message.timestamp.asc()).offset(offset).limit(limit).all()
        
        return jsonify({
            'success': True,
            'messages': [msg.to_dict() for msg in messages],
            'conversation_id': conversation_id,
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/unprocessed-messages', methods=['GET'])
def get_unprocessed_messages():
    """Get unprocessed messages"""
    try:
        account_id = request.args.get('account_id', type=int)
        limit = request.args.get('limit', 20, type=int)
        
        query = Message.query.filter_by(is_from_customer=True, is_processed=False)
        
        if account_id:
            # Join with conversations to filter by account
            query = query.join(Conversation).filter(Conversation.facebook_account_id == account_id)
        
        messages = query.order_by(Message.timestamp.desc()).limit(limit).all()
        
        # Include conversation details
        result_messages = []
        for message in messages:
            msg_dict = message.to_dict()
            msg_dict['conversation'] = {
                'customer_name': message.conversation.customer_name,
                'marketplace_item_title': message.conversation.marketplace_item_title,
                'account_id': message.conversation.facebook_account_id
            }
            result_messages.append(msg_dict)
        
        return jsonify({
            'success': True,
            'unprocessed_messages': result_messages,
            'total_count': len(result_messages),
            'limit': limit
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/recent-runs', methods=['GET'])
def get_recent_runs():
    """Get recent automation runs"""
    try:
        account_id = request.args.get('account_id', type=int)
        limit = request.args.get('limit', 20, type=int)
        
        query = AutomationRun.query
        
        if account_id:
            query = query.filter_by(facebook_account_id=account_id)
        
        runs = query.order_by(AutomationRun.start_time.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'automation_runs': [run.to_dict() for run in runs],
            'total_count': len(runs),
            'limit': limit
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    """Get comprehensive dashboard statistics"""
    try:
        # Account statistics
        total_accounts = FacebookAccount.query.count()
        active_accounts = FacebookAccount.query.filter_by(is_active=True, is_locked=False).count()
        locked_accounts = FacebookAccount.query.filter_by(is_locked=True).count()
        
        # Conversation statistics
        total_conversations = Conversation.query.count()
        active_conversations = Conversation.query.filter_by(status='active').count()
        
        # Message statistics
        total_messages = Message.query.count()
        customer_messages = Message.query.filter_by(is_from_customer=True).count()
        bot_responses = Message.query.filter_by(is_from_customer=False).count()
        unprocessed_messages = Message.query.filter_by(is_from_customer=True, is_processed=False).count()
        
        # Response rate
        processed_customer_messages = Message.query.filter_by(is_from_customer=True, is_processed=True).count()
        response_rate = (processed_customer_messages / customer_messages * 100) if customer_messages > 0 else 0
        
        # Recent automation runs (last 24 hours)
        recent_runs = AutomationRun.query.filter(
            AutomationRun.start_time >= datetime.utcnow() - timedelta(hours=24)
        ).all()
        
        successful_runs = len([r for r in recent_runs if r.status == 'completed'])
        failed_runs = len([r for r in recent_runs if r.status == 'failed'])
        automation_success_rate = (successful_runs / len(recent_runs) * 100) if recent_runs else 100
        
        # Average response time (last 24 hours)
        recent_conversations = Conversation.query.filter(
            Conversation.updated_at >= datetime.utcnow() - timedelta(hours=24)
        ).all()
        
        response_times = [c.response_time_avg_minutes for c in recent_conversations if c.response_time_avg_minutes]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Messages processed in last 24 hours
        recent_messages = Message.query.filter(
            Message.timestamp >= datetime.utcnow() - timedelta(hours=24),
            Message.is_from_customer == True
        ).count()
        
        return jsonify({
            'success': True,
            'dashboard_stats': {
                'accounts': {
                    'total': total_accounts,
                    'active': active_accounts,
                    'locked': locked_accounts,
                    'availability_rate': (active_accounts / total_accounts * 100) if total_accounts > 0 else 0
                },
                'conversations': {
                    'total': total_conversations,
                    'active': active_conversations,
                    'closed': total_conversations - active_conversations
                },
                'messages': {
                    'total': total_messages,
                    'customer_messages': customer_messages,
                    'bot_responses': bot_responses,
                    'unprocessed': unprocessed_messages,
                    'response_rate': response_rate,
                    'recent_24h': recent_messages
                },
                'automation': {
                    'recent_runs': len(recent_runs),
                    'successful_runs': successful_runs,
                    'failed_runs': failed_runs,
                    'success_rate': automation_success_rate,
                    'avg_response_time_minutes': avg_response_time
                },
                'system_health': {
                    'overall_score': min(100, (response_rate + automation_success_rate + (active_accounts/total_accounts*100)) / 3) if total_accounts > 0 else 100,
                    'status': 'healthy' if automation_success_rate > 80 and response_rate > 70 else 'warning' if automation_success_rate > 60 else 'critical'
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

