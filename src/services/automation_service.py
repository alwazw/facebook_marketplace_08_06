from datetime import datetime, timedelta
import random
import time
from src.models import db, FacebookAccount, Conversation, Message, MessageTemplate, AutomationRun, SystemMetric, ValidationLog

class AutomationService:
    def __init__(self):
        self.current_run = None
    
    def run_automation_cycle(self, account_id):
        """Run a complete automation cycle for an account"""
        account = FacebookAccount.query.get(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        if account.is_locked:
            raise ValueError(f"Account {account_id} is locked: {account.lock_reason}")
        
        # Create automation run record
        self.current_run = AutomationRun(
            facebook_account_id=account_id,
            run_type='manual',
            status='running'
        )
        self.current_run.start_run()
        db.session.add(self.current_run)
        db.session.commit()
        
        try:
            # Simulate automation steps with real data logging
            self._log_automation_start(account)
            
            # Step 1: Check conversations
            conversations = self._check_conversations(account)
            
            # Step 2: Find new messages
            new_messages = self._find_new_messages(conversations)
            
            # Step 3: Process messages
            processed_messages = self._process_messages(new_messages)
            
            # Step 4: Send responses
            responses_sent = self._send_responses(processed_messages)
            
            # Complete the run
            self.current_run.conversations_checked = len(conversations)
            self.current_run.new_messages_found = len(new_messages)
            self.current_run.messages_processed = len(processed_messages)
            self.current_run.responses_sent = responses_sent
            self.current_run.complete_run()
            
            # Update account usage
            account.record_login_attempt(success=True)
            
            # Log system metrics
            self._log_system_metrics()
            
            db.session.commit()
            
            return {
                'success': True,
                'run_id': self.current_run.id,
                'summary': {
                    'conversations_checked': self.current_run.conversations_checked,
                    'new_messages_found': self.current_run.new_messages_found,
                    'messages_processed': self.current_run.messages_processed,
                    'responses_sent': self.current_run.responses_sent,
                    'duration_seconds': self.current_run.duration_seconds
                }
            }
            
        except Exception as e:
            self.current_run.fail_run(str(e))
            account.record_login_attempt(success=False)
            db.session.commit()
            raise
    
    def _log_automation_start(self, account):
        """Log automation start"""
        print(f"Starting automation for account: {account.display_name}")
        
        # Create validation log
        validation = ValidationLog(
            validation_type='automation_start',
            entity_type='account',
            entity_id=account.id,
            validation_status='passed',
            validation_message=f'Automation started for account {account.display_name}'
        )
        validation.set_validation_data({
            'account_active': account.is_active,
            'account_locked': account.is_locked,
            'last_used': account.last_used.isoformat() if account.last_used else None
        })
        db.session.add(validation)
    
    def _check_conversations(self, account):
        """Check conversations for the account"""
        print(f"Checking conversations for account {account.id}")
        
        # Get active conversations for this account
        conversations = Conversation.query.filter_by(
            facebook_account_id=account.id,
            status='active'
        ).all()
        
        # Simulate checking each conversation
        for conversation in conversations:
            time.sleep(0.1)  # Simulate processing time
            
            # Log conversation check
            validation = ValidationLog(
                validation_type='conversation_check',
                entity_type='conversation',
                entity_id=conversation.id,
                validation_status='passed',
                validation_message=f'Checked conversation with {conversation.customer_name}'
            )
            validation.set_validation_data({
                'message_count': conversation.message_count,
                'unread_count': conversation.unread_count,
                'last_message_time': conversation.last_message_time.isoformat() if conversation.last_message_time else None
            })
            db.session.add(validation)
        
        return conversations
    
    def _find_new_messages(self, conversations):
        """Find new messages in conversations"""
        print(f"Finding new messages in {len(conversations)} conversations")
        
        new_messages = []
        
        for conversation in conversations:
            # Simulate finding new messages (randomly add 0-2 new messages)
            if random.random() < 0.3:  # 30% chance of new messages
                num_new = random.randint(1, 2)
                
                for _ in range(num_new):
                    # Create a new customer message
                    message_types = ['price_inquiry', 'availability_check', 'location_inquiry', 'condition_inquiry']
                    message_type = random.choice(message_types)
                    
                    sample_messages = {
                        'price_inquiry': ["What's your best price?", "Can you do $X?", "Is the price negotiable?"],
                        'availability_check': ["Is this still available?", "Can I buy this today?", "Do you still have this?"],
                        'location_inquiry': ["Where can I pick this up?", "What's your location?", "Can we meet somewhere?"],
                        'condition_inquiry': ["What condition is this in?", "Does it work properly?", "Any damage?"]
                    }
                    
                    message_text = random.choice(sample_messages[message_type])
                    
                    message = Message(
                        conversation_id=conversation.id,
                        message_text=message_text,
                        is_from_customer=True,
                        is_processed=False,
                        message_type=message_type,
                        classification_confidence=random.uniform(0.7, 0.95),
                        timestamp=datetime.utcnow()
                    )
                    
                    db.session.add(message)
                    new_messages.append(message)
                    
                    # Update conversation stats
                    conversation.message_count += 1
                    conversation.customer_message_count += 1
                    conversation.unread_count += 1
                    conversation.last_message_time = message.timestamp
                    conversation.last_customer_message_time = message.timestamp
                    conversation.updated_at = datetime.utcnow()
        
        db.session.flush()  # Flush to get message IDs
        return new_messages
    
    def _process_messages(self, messages):
        """Process new messages"""
        print(f"Processing {len(messages)} new messages")
        
        processed_messages = []
        
        for message in messages:
            start_time = time.time()
            
            # Classify message if not already classified
            if not message.message_type:
                message.classify_message()
            
            # Find appropriate template
            template = MessageTemplate.query.filter_by(
                message_type=message.message_type,
                is_active=True
            ).first()
            
            if template:
                # Generate response
                conversation = Conversation.query.get(message.conversation_id)
                response_text = template.render(
                    customer_name=conversation.customer_name,
                    item_name=conversation.marketplace_item_title,
                    price=conversation.marketplace_item_price
                )
                
                processing_time = time.time() - start_time
                
                # Mark message as processed
                message.mark_processed(
                    template_used=template.name,
                    response_generated=response_text,
                    processing_time=processing_time
                )
                
                # Update template usage
                template.increment_usage()
                
                processed_messages.append(message)
                
                # Log processing
                validation = ValidationLog(
                    validation_type='message_processing',
                    entity_type='message',
                    entity_id=message.id,
                    validation_status='passed',
                    validation_message=f'Processed {message.message_type} message'
                )
                validation.set_validation_data({
                    'template_used': template.name,
                    'processing_time': processing_time,
                    'confidence': message.classification_confidence
                })
                db.session.add(validation)
            
            else:
                # No template found
                self.current_run.add_warning(f"No template found for message type: {message.message_type}")
        
        return processed_messages
    
    def _send_responses(self, processed_messages):
        """Send responses for processed messages"""
        print(f"Sending responses for {len(processed_messages)} messages")
        
        responses_sent = 0
        
        for message in processed_messages:
            # Simulate sending response (95% success rate)
            if random.random() < 0.95:
                # Create bot response message
                bot_message = Message(
                    conversation_id=message.conversation_id,
                    message_text=message.response_generated,
                    is_from_customer=False,
                    is_processed=True,
                    is_automated_response=True,
                    template_used=message.template_used,
                    response_sent=True,
                    response_sent_at=datetime.utcnow(),
                    timestamp=datetime.utcnow()
                )
                
                db.session.add(bot_message)
                
                # Mark original message response as sent
                message.mark_response_sent()
                
                # Update conversation stats
                conversation = Conversation.query.get(message.conversation_id)
                conversation.message_count += 1
                conversation.bot_response_count += 1
                conversation.unread_count = max(0, conversation.unread_count - 1)
                conversation.last_message_time = bot_message.timestamp
                conversation.last_bot_response_time = bot_message.timestamp
                conversation.updated_at = datetime.utcnow()
                
                responses_sent += 1
                
                # Log response sent
                validation = ValidationLog(
                    validation_type='response_sent',
                    entity_type='message',
                    entity_id=message.id,
                    validation_status='passed',
                    validation_message=f'Response sent for {message.message_type} message'
                )
                validation.set_validation_data({
                    'response_length': len(bot_message.message_text),
                    'template_used': message.template_used
                })
                db.session.add(validation)
            
            else:
                # Failed to send response
                error_msg = "Failed to send response - network error"
                message.error_message = error_msg
                self.current_run.add_error(error_msg, 'response_sending')
        
        return responses_sent
    
    def _log_system_metrics(self):
        """Log system metrics after automation run"""
        timestamp = datetime.utcnow()
        
        # Calculate current metrics
        total_conversations = Conversation.query.count()
        active_conversations = Conversation.query.filter_by(status='active').count()
        total_messages = Message.query.count()
        unprocessed_messages = Message.query.filter_by(is_from_customer=True, is_processed=False).count()
        
        # Response rate calculation
        customer_messages = Message.query.filter_by(is_from_customer=True).count()
        processed_customer_messages = Message.query.filter_by(is_from_customer=True, is_processed=True).count()
        response_rate = (processed_customer_messages / customer_messages * 100) if customer_messages > 0 else 0
        
        # Active accounts
        active_accounts = FacebookAccount.query.filter_by(is_active=True, is_locked=False).count()
        
        # Recent automation runs success rate
        recent_runs = AutomationRun.query.filter(
            AutomationRun.start_time >= datetime.utcnow() - timedelta(hours=24)
        ).all()
        
        successful_runs = len([r for r in recent_runs if r.status == 'completed'])
        automation_success_rate = (successful_runs / len(recent_runs) * 100) if recent_runs else 100
        
        # Create metrics
        metrics = [
            ('total_conversations', total_conversations, 'gauge'),
            ('active_conversations', active_conversations, 'gauge'),
            ('total_messages', total_messages, 'gauge'),
            ('unprocessed_messages', unprocessed_messages, 'gauge'),
            ('response_rate_percent', response_rate, 'gauge'),
            ('active_accounts', active_accounts, 'gauge'),
            ('automation_success_rate', automation_success_rate, 'gauge'),
            ('automation_runs_24h', len(recent_runs), 'gauge')
        ]
        
        for metric_name, value, metric_type in metrics:
            metric = SystemMetric(
                metric_name=metric_name,
                metric_value=value,
                metric_type=metric_type,
                timestamp=timestamp
            )
            metric.set_tags({'automation_run_id': self.current_run.id})
            db.session.add(metric)
    
    def get_automation_stats(self, account_id=None):
        """Get automation statistics"""
        query = AutomationRun.query
        if account_id:
            query = query.filter_by(facebook_account_id=account_id)
        
        runs = query.order_by(AutomationRun.start_time.desc()).limit(50).all()
        
        if not runs:
            return {
                'total_runs': 0,
                'successful_runs': 0,
                'failed_runs': 0,
                'success_rate': 0,
                'avg_duration': 0,
                'total_messages_processed': 0,
                'total_responses_sent': 0
            }
        
        successful_runs = [r for r in runs if r.status == 'completed']
        failed_runs = [r for r in runs if r.status == 'failed']
        
        total_messages = sum(r.messages_processed for r in runs)
        total_responses = sum(r.responses_sent for r in runs)
        avg_duration = sum(r.duration_seconds or 0 for r in runs) / len(runs)
        
        return {
            'total_runs': len(runs),
            'successful_runs': len(successful_runs),
            'failed_runs': len(failed_runs),
            'success_rate': len(successful_runs) / len(runs) * 100,
            'avg_duration': avg_duration,
            'total_messages_processed': total_messages,
            'total_responses_sent': total_responses,
            'response_rate': (total_responses / total_messages * 100) if total_messages > 0 else 0
        }
    
    def run_all_accounts(self):
        """Run automation for all active accounts"""
        accounts = FacebookAccount.query.filter_by(is_active=True, is_locked=False).all()
        
        results = []
        for account in accounts:
            try:
                result = self.run_automation_cycle(account.id)
                results.append({
                    'account_id': account.id,
                    'account_name': account.display_name,
                    'success': True,
                    'summary': result['summary']
                })
            except Exception as e:
                results.append({
                    'account_id': account.id,
                    'account_name': account.display_name,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'accounts_processed': len(accounts),
            'successful_accounts': len([r for r in results if r['success']]),
            'failed_accounts': len([r for r in results if not r['success']]),
            'results': results
        }

