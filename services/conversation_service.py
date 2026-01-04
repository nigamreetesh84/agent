"""
Conversation Service
Manages conversation history and memory
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import redis
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversation history and memory"""
    
    def __init__(self, config):
        self.config = config
        
        # Initialize Redis for persistence (optional)
        if config.REDIS_ENABLED:
            try:
                self.redis_client = redis.Redis(
                    host=config.REDIS_HOST,
                    port=config.REDIS_PORT,
                    db=config.REDIS_DB,
                    password=config.REDIS_PASSWORD,
                    decode_responses=True
                )
                self.redis_client.ping()
                logger.info("Redis connection established")
                self.use_redis = True
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory storage: {e}")
                self.use_redis = False
                self._init_memory_storage()
        else:
            logger.info("Using in-memory storage for conversations")
            self.use_redis = False
            self._init_memory_storage()
    
    def _init_memory_storage(self):
        """Initialize in-memory storage"""
        self.conversations = {}
        self.messages = defaultdict(list)
        self.visualizations = defaultdict(list)
    
    def get_or_create_conversation(
        self,
        conversation_id: Optional[str],
        user_id: str
    ) -> Dict:
        """Get existing conversation or create new one"""
        
        if conversation_id:
            conversation = self.get_conversation(conversation_id)
            if conversation:
                return conversation
        
        # Create new conversation
        conversation_id = str(uuid.uuid4())
        conversation = {
            "id": conversation_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "title": "New Conversation",
            "message_count": 0
        }
        
        self._save_conversation(conversation)
        logger.info(f"Created new conversation: {conversation_id}")
        
        return conversation
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation by ID"""
        
        if self.use_redis:
            key = f"conversation:{conversation_id}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
        else:
            return self.conversations.get(conversation_id)
        
        return None
    
    def _save_conversation(self, conversation: Dict):
        """Save conversation"""
        
        if self.use_redis:
            key = f"conversation:{conversation['id']}"
            self.redis_client.setex(
                key,
                self.config.CONVERSATION_TTL_SECONDS,
                json.dumps(conversation)
            )
            
            # Add to user's conversation list
            user_key = f"user:{conversation['user_id']}:conversations"
            self.redis_client.zadd(
                user_key,
                {conversation['id']: datetime.utcnow().timestamp()}
            )
            self.redis_client.expire(user_key, self.config.CONVERSATION_TTL_SECONDS)
        else:
            self.conversations[conversation['id']] = conversation
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """Add message to conversation"""
        
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self.use_redis:
            key = f"messages:{conversation_id}"
            self.redis_client.rpush(key, json.dumps(message))
            self.redis_client.expire(key, self.config.CONVERSATION_TTL_SECONDS)
        else:
            self.messages[conversation_id].append(message)
        
        # Update conversation
        conversation = self.get_conversation(conversation_id)
        if conversation:
            conversation['message_count'] = conversation.get('message_count', 0) + 1
            conversation['updated_at'] = datetime.utcnow().isoformat()
            
            # Update title based on first user message
            if role == 'user' and conversation['message_count'] == 1:
                conversation['title'] = content[:50] + ('...' if len(content) > 50 else '')
            
            self._save_conversation(conversation)
    
    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Get messages from conversation"""
        
        if self.use_redis:
            key = f"messages:{conversation_id}"
            messages_json = self.redis_client.lrange(key, 0, -1)
            messages = [json.loads(msg) for msg in messages_json]
        else:
            messages = self.messages.get(conversation_id, [])
        
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def add_visualization(
        self,
        conversation_id: str,
        viz_id: str,
        viz_data: Dict
    ):
        """Store visualization data"""
        
        viz = {
            "id": viz_id,
            "conversation_id": conversation_id,
            "data": viz_data,
            "created_at": datetime.utcnow().isoformat()
        }
        
        if self.use_redis:
            key = f"visualization:{viz_id}"
            self.redis_client.setex(
                key,
                self.config.VISUALIZATION_TTL_SECONDS,
                json.dumps(viz)
            )
            
            # Add to conversation's visualization list
            conv_viz_key = f"visualizations:{conversation_id}"
            self.redis_client.rpush(conv_viz_key, viz_id)
            self.redis_client.expire(conv_viz_key, self.config.CONVERSATION_TTL_SECONDS)
        else:
            self.visualizations[conversation_id].append(viz)
    
    def get_visualizations(self, conversation_id: str) -> List[Dict]:
        """Get all visualizations for a conversation"""
        
        if self.use_redis:
            key = f"visualizations:{conversation_id}"
            viz_ids = self.redis_client.lrange(key, 0, -1)
            
            visualizations = []
            for viz_id in viz_ids:
                viz_key = f"visualization:{viz_id}"
                viz_data = self.redis_client.get(viz_key)
                if viz_data:
                    visualizations.append(json.loads(viz_data))
            
            return visualizations
        else:
            return self.visualizations.get(conversation_id, [])
    
    def get_visualization_by_id(self, viz_id: str) -> Optional[Dict]:
        """Get specific visualization"""
        
        if self.use_redis:
            key = f"visualization:{viz_id}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
        else:
            # Search in all conversations
            for vizs in self.visualizations.values():
                for viz in vizs:
                    if viz['id'] == viz_id:
                        return viz
        
        return None
    
    def list_conversations(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """List conversations for a user"""
        
        if self.use_redis:
            key = f"user:{user_id}:conversations"
            # Get conversation IDs sorted by timestamp (newest first)
            conv_ids = self.redis_client.zrevrange(key, offset, offset + limit - 1)
            
            conversations = []
            for conv_id in conv_ids:
                conversation = self.get_conversation(conv_id)
                if conversation:
                    conversations.append(conversation)
            
            return conversations
        else:
            # Filter conversations by user_id
            user_conversations = [
                conv for conv in self.conversations.values()
                if conv['user_id'] == user_id
            ]
            
            # Sort by updated_at
            user_conversations.sort(
                key=lambda x: x['updated_at'],
                reverse=True
            )
            
            return user_conversations[offset:offset + limit]
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        if self.use_redis:
            # Delete conversation
            self.redis_client.delete(f"conversation:{conversation_id}")
            
            # Delete messages
            self.redis_client.delete(f"messages:{conversation_id}")
            
            # Delete visualizations
            viz_ids = self.redis_client.lrange(f"visualizations:{conversation_id}", 0, -1)
            for viz_id in viz_ids:
                self.redis_client.delete(f"visualization:{viz_id}")
            self.redis_client.delete(f"visualizations:{conversation_id}")
            
            # Remove from user's list
            self.redis_client.zrem(
                f"user:{conversation['user_id']}:conversations",
                conversation_id
            )
        else:
            self.conversations.pop(conversation_id, None)
            self.messages.pop(conversation_id, None)
            self.visualizations.pop(conversation_id, None)
        
        logger.info(f"Deleted conversation: {conversation_id}")
        return True
    
    def update_last_activity(self, conversation_id: str):
        """Update conversation's last activity timestamp"""
        
        conversation = self.get_conversation(conversation_id)
        if conversation:
            conversation['updated_at'] = datetime.utcnow().isoformat()
            self._save_conversation(conversation)
    
    def get_analytics(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """Get usage analytics"""
        
        # Simple analytics implementation
        analytics = {
            "total_conversations": 0,
            "total_messages": 0,
            "total_visualizations": 0,
            "period": {
                "start": start_date or "all_time",
                "end": end_date or "now"
            }
        }
        
        if self.use_redis:
            # Count conversations
            if user_id:
                key = f"user:{user_id}:conversations"
                analytics["total_conversations"] = self.redis_client.zcard(key)
            else:
                # Would need additional indexing for global stats
                pass
        else:
            if user_id:
                analytics["total_conversations"] = len([
                    c for c in self.conversations.values()
                    if c['user_id'] == user_id
                ])
                analytics["total_messages"] = sum(
                    len(msgs) for conv_id, msgs in self.messages.items()
                    if self.conversations.get(conv_id, {}).get('user_id') == user_id
                )
            else:
                analytics["total_conversations"] = len(self.conversations)
                analytics["total_messages"] = sum(len(msgs) for msgs in self.messages.values())
        
        return analytics