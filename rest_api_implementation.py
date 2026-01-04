"""
REST API Implementation - No WebSocket Required
Simpler architecture with streaming via Server-Sent Events (SSE)
"""

from bottle import Bottle, request, response, abort
import json
import os
import logging
from datetime import datetime
import traceback
from functools import wraps

# Local imports
from config import Config
from services.conversation_service import ConversationService
from utils.logger import setup_logger

# Import your new agent executor
from agent_definition import initialize_agent

# Initialize
app = Bottle()
logger = setup_logger(__name__)

config = Config()
config.validate()
conversation_service = ConversationService(config)
agent_executor = initialize_agent(config)  # New initialization

# CORS
@app.hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = config.CORS_ORIGINS
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, Authorization'

@app.route('/<:re:.*>', method='OPTIONS')
def handle_options():
    return {}

def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            response.status = 400
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Error: {str(e)}\n{traceback.format_exc()}")
            response.status = 500
            return {"error": "Internal server error"}
    return wrapper

@app.route('/health')
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }

# ============================================
# OPTION 1: Simple Synchronous REST API
# ============================================

@app.route('/api/chat', method='POST')
@handle_errors
def chat_simple():
    """
    Simple synchronous REST endpoint
    Returns complete response at once
    """
    data = request.json
    if not data or 'message' not in data:
        abort(400, 'Missing message')
    
    user_query = data['message']
    conversation_id = data.get('conversation_id')
    user_id = data.get('user_id', 'anonymous')
    
    logger.info(f"User {user_id}: {user_query[:50]}...")
    
    # Get or create conversation
    conversation = conversation_service.get_or_create_conversation(conversation_id, user_id)
    conversation_id = conversation['id']
    
    # Save user message
    conversation_service.add_message(conversation_id, 'user', user_query, {})
    
    # Get conversation history
    history = conversation_service.get_messages(conversation_id)
    formatted_history = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history[:-1]  # Exclude the message we just added
    ]
    
    # Get response from agent
    assistant_response = agent_executor.run(user_query, formatted_history)
    
    # Save assistant response
    conversation_service.add_message(conversation_id, 'assistant', assistant_response, {})
    
    return {
        "response": assistant_response,
        "conversation_id": conversation_id,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# OPTION 2: Server-Sent Events (SSE) for Streaming
# ============================================

@app.route('/api/chat/stream', method='POST')
@handle_errors
def chat_stream():
    """
    Streaming endpoint using Server-Sent Events (SSE)
    Alternative to WebSocket, works with standard HTTP
    """
    data = request.json
    if not data or 'message' not in data:
        abort(400, 'Missing message')
    
    user_query = data['message']
    conversation_id = data.get('conversation_id')
    user_id = data.get('user_id', 'anonymous')
    
    # Get or create conversation
    conversation = conversation_service.get_or_create_conversation(conversation_id, user_id)
    conversation_id = conversation['id']
    
    # Save user message
    conversation_service.add_message(conversation_id, 'user', user_query, {})
    
    # Get history
    history = conversation_service.get_messages(conversation_id)
    formatted_history = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history[:-1]
    ]
    
    # Set SSE headers
    response.content_type = 'text/event-stream'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    
    def generate():
        """Generator for SSE streaming"""
        full_response = ""
        
        try:
            for chunk in agent_executor.stream(user_query, formatted_history):
                # Format as SSE
                event_data = json.dumps(chunk)
                yield f"data: {event_data}\n\n"
                
                # Collect full response
                if chunk['type'] == 'text':
                    full_response += chunk.get('content', '')
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
            
            # Save complete response
            if full_response:
                conversation_service.add_message(conversation_id, 'assistant', full_response, {})
        
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return generate()


# ============================================
# OPTION 3: Chunked Transfer Encoding
# ============================================

@app.route('/api/chat/chunked', method='POST')
@handle_errors
def chat_chunked():
    """
    Chunked streaming without SSE
    Simpler client-side parsing
    """
    data = request.json
    if not data or 'message' not in data:
        abort(400, 'Missing message')
    
    user_query = data['message']
    conversation_id = data.get('conversation_id')
    user_id = data.get('user_id', 'anonymous')
    
    # Get or create conversation
    conversation = conversation_service.get_or_create_conversation(conversation_id, user_id)
    conversation_id = conversation['id']
    
    # Save user message
    conversation_service.add_message(conversation_id, 'user', user_query, {})
    
    # Get history
    history = conversation_service.get_messages(conversation_id)
    formatted_history = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history[:-1]
    ]
    
    # Set chunked headers
    response.content_type = 'application/json'
    response.headers['Transfer-Encoding'] = 'chunked'
    
    def generate():
        """Generator for chunked streaming"""
        full_response = ""
        
        try:
            for chunk in agent_executor.stream(user_query, formatted_history):
                # Send each chunk as separate JSON
                yield json.dumps(chunk) + "\n"
                
                if chunk['type'] == 'text':
                    full_response += chunk.get('content', '')
            
            # Send completion
            yield json.dumps({'type': 'done', 'conversation_id': conversation_id}) + "\n"
            
            # Save response
            if full_response:
                conversation_service.add_message(conversation_id, 'assistant', full_response, {})
        
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            yield json.dumps({'type': 'error', 'message': str(e)}) + "\n"
    
    return generate()


# ============================================
# Conversation Management Endpoints
# ============================================

@app.route('/api/conversations/<conversation_id>')
@handle_errors
def get_conversation(conversation_id):
    """Get conversation details"""
    conv = conversation_service.get_conversation(conversation_id)
    if not conv:
        abort(404, 'Conversation not found')
    
    return {
        "conversation": conv,
        "messages": conversation_service.get_messages(conversation_id),
        "visualizations": conversation_service.get_visualizations(conversation_id)
    }

@app.route('/api/conversations')
@handle_errors
def list_conversations():
    """List all conversations for a user"""
    user_id = request.query.get('user_id', 'anonymous')
    limit = int(request.query.get('limit', 20))
    offset = int(request.query.get('offset', 0))
    
    return {
        "conversations": conversation_service.list_conversations(user_id, limit, offset)
    }

@app.route('/api/conversations/<conversation_id>', method='DELETE')
@handle_errors
def delete_conversation(conversation_id):
    """Delete a conversation"""
    if not conversation_service.delete_conversation(conversation_id):
        abort(404, 'Conversation not found')
    
    return {"message": "Conversation deleted successfully"}


# ============================================
# Server Startup
# ============================================

def main():
    """Start server"""
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8080))
    
    logger.info(f"Starting REST API server on {host}:{port}")
    logger.info(f"Environment: {config.ENVIRONMENT}")
    logger.info("Available endpoints:")
    logger.info("  POST   /api/chat          - Simple sync chat")
    logger.info("  POST   /api/chat/stream   - SSE streaming")
    logger.info("  POST   /api/chat/chunked  - Chunked streaming")
    logger.info("  GET    /api/conversations - List conversations")
    logger.info("  GET    /api/conversations/<id> - Get conversation")
    logger.info("  DELETE /api/conversations/<id> - Delete conversation")
    
    # Use standard WSGI server (no WebSocket handler needed)
    from gevent import pywsgi
    server = pywsgi.WSGIServer((host, port), app)
    
    try:
        logger.info("Server ready ✓")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == '__main__':
    main()
