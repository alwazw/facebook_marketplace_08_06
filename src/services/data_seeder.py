from datetime import datetime, timedelta
import random
from src.models import db, FacebookAccount, Conversation, Message, MessageTemplate, AutomationRun, SystemMetric, ValidationLog

class DataSeeder:
    def __init__(self):
        self.customer_names = [
            "John Smith", "Sarah Johnson", "Mike Davis", "Emily Brown", "David Wilson",
            "Lisa Anderson", "Chris Taylor", "Amanda Martinez", "Ryan Garcia", "Jessica Rodriguez",
            "Kevin Lee", "Michelle White", "Daniel Thompson", "Ashley Harris", "James Clark",
            "Nicole Lewis", "Brandon Walker", "Stephanie Hall", "Tyler Allen", "Megan Young"
        ]
        
        self.marketplace_items = [
            {"title": "iPhone 13 Pro Max 256GB", "price": 899.99},
            {"title": "MacBook Air M2 2022", "price": 1199.99},
            {"title": "Samsung 65\" 4K Smart TV", "price": 649.99},
            {"title": "PlayStation 5 Console", "price": 499.99},
            {"title": "Nike Air Jordan 1 Size 10", "price": 179.99},
            {"title": "Dining Table Set (6 chairs)", "price": 299.99},
            {"title": "Canon EOS R5 Camera", "price": 2499.99},
            {"title": "Gaming PC RTX 4080", "price": 1899.99},
            {"title": "Sectional Sofa - Gray", "price": 799.99},
            {"title": "Road Bike - Trek 2023", "price": 1299.99}
        ]
        
        self.message_examples = {
            'price_inquiry': [
                "What's your lowest price?",
                "Is the price negotiable?",
                "How much are you asking for this?",
                "Can you do $X for this?",
                "What's the best price you can offer?"
            ],
            'availability_check': [
                "Is this still available?",
                "Do you still have this item?",
                "Can I buy this today?",
                "Is this sold yet?",
                "When can I pick this up?"
            ],
            'location_inquiry': [
                "Where are you located?",
                "Can I pick this up?",
                "What's your address?",
                "How far are you from downtown?",
                "Can you meet somewhere?"
            ],
            'condition_inquiry': [
                "What condition is this in?",
                "Does everything work properly?",
                "Are there any scratches or damage?",
                "How old is this item?",
                "Why are you selling this?"
            ],
            'initial_contact': [
                "Hi, I'm interested in this item",
                "Hello, is this available?",
                "Hey, I saw your listing",
                "Hi there, I'd like to know more",
                "Hello, I'm interested in buying this"
            ]
        }
    
    def seed_all_data(self):
        """Seed all data for the system"""
        print("Starting data seeding...")
        
        # Clear existing data
        self.clear_existing_data()
        
        # Seed in order due to foreign key relationships
        self.seed_facebook_accounts()
        self.seed_message_templates()
        self.seed_conversations()
        self.seed_messages()
        self.seed_automation_runs()
        self.seed_system_metrics()
        self.seed_validation_logs()
        
        db.session.commit()
        print("Data seeding completed successfully!")
    
    def clear_existing_data(self):
        """Clear existing data from all tables"""
        print("Clearing existing data...")
        ValidationLog.query.delete()
        SystemMetric.query.delete()
        AutomationRun.query.delete()
        Message.query.delete()
        MessageTemplate.query.delete()
        Conversation.query.delete()
        FacebookAccount.query.delete()
        db.session.commit()
    
    def seed_facebook_accounts(self):
        """Create Facebook accounts"""
        print("Seeding Facebook accounts...")
        
        accounts_data = [
            {"email": "amy@amycomputers.com", "display_name": "Amy Computers - Main"},
            {"email": "amy.sales@amycomputers.com", "display_name": "Amy Computers - Sales"},
            {"email": "amy.support@amycomputers.com", "display_name": "Amy Computers - Support"},
            {"email": "amy.marketplace@amycomputers.com", "display_name": "Amy Computers - Marketplace"},
            {"email": "amy.business@amycomputers.com", "display_name": "Amy Computers - Business"},
            {"email": "amy.backup@amycomputers.com", "display_name": "Amy Computers - Backup"}
        ]
        
        for i, account_data in enumerate(accounts_data):
            account = FacebookAccount(
                email=account_data["email"],
                display_name=account_data["display_name"],
                is_active=True,
                is_locked=i == 5,  # Lock the last account for testing
                lock_reason="Rate limit exceeded" if i == 5 else None,
                last_used=datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
                login_attempts=random.randint(5, 50),
                successful_logins=random.randint(4, 45),
                failed_logins=random.randint(0, 5)
            )
            db.session.add(account)
        
        db.session.flush()  # Flush to get IDs
    
    def seed_message_templates(self):
        """Create message templates"""
        print("Seeding message templates...")
        
        templates_data = [
            {
                "name": "price_inquiry_response",
                "message_type": "price_inquiry",
                "template_text": "Hi {customer_name}! The price for the {item_name} is ${price}. This is a fair price considering the condition and market value. Let me know if you're interested!",
                "variables": ["customer_name", "item_name", "price"]
            },
            {
                "name": "availability_response",
                "message_type": "availability_check",
                "template_text": "Hello {customer_name}! Yes, the {item_name} is still available. Would you like to schedule a time to pick it up or see it in person?",
                "variables": ["customer_name", "item_name"]
            },
            {
                "name": "location_response",
                "message_type": "location_inquiry",
                "template_text": "Hi {customer_name}! I'm located in downtown area. We can arrange pickup at a convenient location or I can provide my address for pickup. What works best for you?",
                "variables": ["customer_name"]
            },
            {
                "name": "condition_response",
                "message_type": "condition_inquiry",
                "template_text": "Hello {customer_name}! The {item_name} is in excellent condition. It's been well-maintained and everything works perfectly. I can send you more photos if you'd like to see specific details.",
                "variables": ["customer_name", "item_name"]
            },
            {
                "name": "initial_contact_response",
                "message_type": "initial_contact",
                "template_text": "Hi {customer_name}! Thanks for your interest in the {item_name}. It's a great item and I'm happy to answer any questions you might have. What would you like to know?",
                "variables": ["customer_name", "item_name"]
            },
            {
                "name": "general_response",
                "message_type": "general_inquiry",
                "template_text": "Hello {customer_name}! Thanks for reaching out. I'm happy to help with any questions about the {item_name}. Please let me know what specific information you need!",
                "variables": ["customer_name", "item_name"]
            }
        ]
        
        for template_data in templates_data:
            template = MessageTemplate(
                name=template_data["name"],
                message_type=template_data["message_type"],
                template_text=template_data["template_text"],
                usage_count=random.randint(10, 100),
                success_rate=random.uniform(75.0, 95.0)
            )
            template.set_variables(template_data["variables"])
            db.session.add(template)
        
        db.session.flush()
    
    def seed_conversations(self):
        """Create conversations"""
        print("Seeding conversations...")
        
        accounts = FacebookAccount.query.all()
        
        for _ in range(50):  # Create 50 conversations
            account = random.choice(accounts)
            item = random.choice(self.marketplace_items)
            customer = random.choice(self.customer_names)
            
            created_time = datetime.utcnow() - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            conversation = Conversation(
                facebook_account_id=account.id,
                customer_name=customer,
                customer_profile_url=f"https://facebook.com/{customer.lower().replace(' ', '.')}",
                marketplace_item_id=f"item_{random.randint(100000, 999999)}",
                marketplace_item_title=item["title"],
                marketplace_item_price=item["price"],
                status=random.choice(['active', 'active', 'active', 'closed']),  # More active conversations
                priority=random.choice(['normal', 'normal', 'high', 'low']),
                created_at=created_time,
                updated_at=created_time
            )
            
            db.session.add(conversation)
        
        db.session.flush()
    
    def seed_messages(self):
        """Create messages for conversations"""
        print("Seeding messages...")
        
        conversations = Conversation.query.all()
        
        for conversation in conversations:
            # Create 2-8 messages per conversation
            num_messages = random.randint(2, 8)
            
            for i in range(num_messages):
                # Alternate between customer and bot messages
                is_from_customer = i % 2 == 0
                
                if is_from_customer:
                    # Customer message
                    message_type = random.choice(list(self.message_examples.keys()))
                    message_text = random.choice(self.message_examples[message_type])
                else:
                    # Bot response
                    message_type = 'bot_response'
                    message_text = f"Thank you for your message! I'll get back to you shortly about the {conversation.marketplace_item_title}."
                
                message_time = conversation.created_at + timedelta(
                    hours=i * random.randint(1, 6),
                    minutes=random.randint(0, 59)
                )
                
                message = Message(
                    conversation_id=conversation.id,
                    message_text=message_text,
                    is_from_customer=is_from_customer,
                    is_processed=not is_from_customer or random.choice([True, True, False]),  # Most processed
                    is_automated_response=not is_from_customer,
                    message_type=message_type if is_from_customer else None,
                    classification_confidence=random.uniform(0.7, 0.95) if is_from_customer else None,
                    template_used=f"{message_type}_response" if not is_from_customer else None,
                    response_generated=message_text if not is_from_customer else None,
                    response_sent=not is_from_customer,
                    response_sent_at=message_time if not is_from_customer else None,
                    processing_time_seconds=random.uniform(0.5, 3.0) if not is_from_customer else None,
                    timestamp=message_time,
                    processed_at=message_time + timedelta(seconds=random.randint(1, 30)) if not is_from_customer else None
                )
                
                # Classify customer messages
                if is_from_customer:
                    message.classify_message()
                
                db.session.add(message)
            
            # Update conversation stats
            conversation.update_message_stats()
        
        db.session.flush()
    
    def seed_automation_runs(self):
        """Create automation run records"""
        print("Seeding automation runs...")
        
        accounts = FacebookAccount.query.all()
        
        for _ in range(100):  # Create 100 automation runs
            account = random.choice(accounts)
            
            start_time = datetime.utcnow() - timedelta(
                days=random.randint(0, 7),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            duration = random.randint(30, 300)  # 30 seconds to 5 minutes
            end_time = start_time + timedelta(seconds=duration)
            
            conversations_checked = random.randint(5, 20)
            new_messages = random.randint(0, 10)
            processed = random.randint(0, new_messages)
            responses_sent = random.randint(0, processed)
            errors = random.randint(0, 2)
            
            run = AutomationRun(
                facebook_account_id=account.id,
                run_type=random.choice(['manual', 'scheduled', 'auto']),
                status=random.choice(['completed', 'completed', 'completed', 'failed']),  # Most successful
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                conversations_checked=conversations_checked,
                new_messages_found=new_messages,
                messages_processed=processed,
                responses_sent=responses_sent,
                errors_encountered=errors,
                avg_processing_time_per_message=random.uniform(1.0, 5.0),
                success_rate=random.uniform(80.0, 100.0)
            )
            
            if errors > 0:
                run.set_error_details([
                    {
                        "timestamp": start_time.isoformat(),
                        "type": "network_error",
                        "message": "Temporary connection timeout"
                    }
                ])
            
            db.session.add(run)
        
        db.session.flush()
    
    def seed_system_metrics(self):
        """Create system metrics"""
        print("Seeding system metrics...")
        
        # Create metrics for the last 7 days
        for days_ago in range(7):
            date = datetime.utcnow() - timedelta(days=days_ago)
            
            # Daily metrics
            metrics = [
                ("messages_processed", random.randint(50, 200), "counter"),
                ("response_time_avg", random.uniform(2.0, 8.0), "gauge"),
                ("success_rate", random.uniform(85.0, 98.0), "gauge"),
                ("active_conversations", random.randint(20, 80), "gauge"),
                ("system_uptime", random.uniform(95.0, 100.0), "gauge"),
                ("error_rate", random.uniform(0.0, 5.0), "gauge"),
                ("accounts_active", random.randint(4, 6), "gauge"),
                ("automation_runs", random.randint(10, 30), "counter")
            ]
            
            for metric_name, value, metric_type in metrics:
                metric = SystemMetric(
                    metric_name=metric_name,
                    metric_value=value,
                    metric_type=metric_type,
                    timestamp=date
                )
                metric.set_tags({"date": date.strftime("%Y-%m-%d")})
                db.session.add(metric)
        
        db.session.flush()
    
    def seed_validation_logs(self):
        """Create validation logs"""
        print("Seeding validation logs...")
        
        validation_types = [
            "account_health_check",
            "message_processing_validation",
            "conversation_integrity_check",
            "template_validation",
            "system_health_check"
        ]
        
        for _ in range(50):
            validation_type = random.choice(validation_types)
            status = random.choice(['passed', 'passed', 'passed', 'warning', 'failed'])
            
            log = ValidationLog(
                validation_type=validation_type,
                entity_type=random.choice(['account', 'conversation', 'message', 'system']),
                entity_id=random.randint(1, 50),
                validation_status=status,
                validation_message=f"Validation {status} for {validation_type}",
                timestamp=datetime.utcnow() - timedelta(
                    hours=random.randint(0, 168)  # Last week
                )
            )
            
            log.set_validation_data({
                "checks_performed": random.randint(1, 10),
                "issues_found": random.randint(0, 3) if status != 'passed' else 0
            })
            
            db.session.add(log)
        
        db.session.flush()

def seed_database():
    """Main function to seed the database"""
    seeder = DataSeeder()
    seeder.seed_all_data()
    return True

