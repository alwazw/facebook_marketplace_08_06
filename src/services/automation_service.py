import asyncio
import os
from datetime import datetime
from src.models import db, FacebookAccount, Conversation, Message, MessageTemplate, AutomationRun
from src.services.browser_service import BrowserService

class AutomationService:
    def __init__(self):
        self.current_run = None

    def run_automation_cycle(self, account_id):
        """Run a complete automation cycle for an account using browser automation."""
        account = FacebookAccount.query.get(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")

        if account.is_locked:
            raise ValueError(f"Account {account_id} is locked: {account.lock_reason}")

        self.current_run = AutomationRun(
            facebook_account_id=account_id,
            run_type='manual',
            status='running'
        )
        self.current_run.start_run()
        db.session.add(self.current_run)
        db.session.commit()

        try:
            # Run the entire browser automation within a single event loop
            asyncio.run(self.async_automation_wrapper(account))

            self.current_run.complete_run()
            account.record_login_attempt(success=True)
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

    async def async_automation_wrapper(self, account: FacebookAccount):
        """
        A wrapper to run the entire browser automation lifecycle in a single async context.
        """
        user_data_dir = os.path.join('browser_data', f'account_{account.id}')
        os.makedirs(user_data_dir, exist_ok=True)
        
        browser_service = BrowserService(user_data_dir, persistent=False)

        try:
            await browser_service.start()
            
            await browser_service.login(account)

            print("Checking for unanswered messages...")
            unanswered_conversations = await browser_service.get_unanswered_messages()

            if not unanswered_conversations:
                print("No unanswered messages found.")
            else:
                print(f"Found {len(unanswered_conversations)} unanswered conversations. Processing...")
                
                for conversation in unanswered_conversations:
                    message_text = conversation.get("last_message_text")
                    if not message_text:
                        print(f"Skipping conversation {conversation.get('conversation_id')} due to empty message text.")
                        continue

                    # Create a temporary message object to use the classification logic
                    temp_message = Message(message_text=message_text)
                    temp_message.classify_message()
                    
                    message_type = temp_message.message_type
                    print(f"Message classified as: {message_type}")
                    
                    # Find a template for this message type
                    template = MessageTemplate.query.filter_by(message_type=message_type, is_active=True).first()
                    
                    if template:
                        # For now, we don't have the variables to render the template fully.
                        # We will just use the raw template text.
                        # In a real scenario, we would get customer_name, item_name, etc.
                        reply_text = template.template_text

                        # A simple substitution for now
                        if '{customer_name}' in reply_text:
                            reply_text = reply_text.replace('{customer_name}', 'there')

                        await browser_service.send_reply(conversation, reply_text)

                        # Update run stats
                        if self.current_run:
                            self.current_run.messages_processed += 1
                            self.current_run.responses_sent += 1
                    else:
                        print(f"No active template found for message type: {message_type}")

            await browser_service.logout()
        finally:
            await browser_service.close()

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
