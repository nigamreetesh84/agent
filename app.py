"""
Production-Ready Sherlock Account Analysis API
Main application with streaming, multi-agent system, and conversation memory
"""

from bottle import Bottle, request, response, abort
from gevent import pywsgi, monkey
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
import traceback
from functools import wraps
import asyncio

# Monkey patch for async operations
monkey.patch_all()

# Local imports
from config import Config
from agents.agent_orchestrator import AgentOrchestrator
from services.conversation_service import ConversationService
from middleware.auth import require_auth
from utils.logger import setup_logger

# Initialize app
app = Bottle()
logger = setup_logger(__name__)

# Initialize services
config = Config()
conversation_service = ConversationService(config)
agent_orchestrator = AgentOrchestrator(config)

# CORS middleware
@app.hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = config.CORS_ORIGINS
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, Authorization'
    response.headers['Access-Control-Allow-Credentials'] = 'true'

@app.route('/<:re:.*>', method='OPTIONS')
def handle_options():
    return {}

# Error handling decorator
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
            logger.error(f"Internal error: {str(e)}\n{traceback.format_exc()}")
            response.status = 500
            return {"error": "Internal server error"}
    return wrapper

# Health check
@app.route('/health')
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# WebSocket endpoint for streaming chat
async def _stream_response_handler(agent_orchestrator, user_query, history, conversation_id, user_id):
    """Helper function to handle async streaming"""
    chunks = []
    async for chunk in agent_orchestrator.stream_response(
        user_query,
        history,
        conversation_id,
        user_id
    ):
        chunks.append(chunk)
    return chunks

@app.route('/ws/chat')
def handle_websocket():
    """WebSocket endpoint for real-time streaming chat"""
    wsock = request.environ.get('wsgi.websocket')
    if not wsock:
        abort(400, 'Expected WebSocket request')
    
    conversation_id = None
    user_id = None
    
    try:
        logger.info("WebSocket connection established")
        
        while True:
            message = wsock.receive()
            if message is None:
                logger.info("WebSocket connection closed by client")
                break
            
            try:
                data = json.loads(message)
                user_query = data.get('message', '')
                conversation_id = data.get('conversation_id')
                user_id = data.get('user_id', 'anonymous')
                metadata = data.get('metadata', {})
                
                if not user_query:
                    wsock.send(json.dumps({
                        "type": "error",
                        "message": "Empty message"
                    }))
                    continue
                
                logger.info(f"Processing message from user {user_id}: {user_query[:50]}...")
                
                # Get or create conversation
                conversation = conversation_service.get_or_create_conversation(
                    conversation_id, 
                    user_id
                )
                conversation_id = conversation['id']
                
                # Add user message to history
                conversation_service.add_message(
                    conversation_id,
                    'user',
                    user_query,
                    metadata
                )
                
                # Get conversation history
                history = conversation_service.get_messages(conversation_id)
                
                # Stream response from agent orchestrator
                full_response = ""
                chunks = asyncio.run(_stream_response_handler(
                    agent_orchestrator,
                    user_query,
                    history,
                    conversation_id,
                    user_id
                ))
                
                for chunk in chunks:
                    if chunk['type'] == 'error':
                        logger.error(f"Agent error: {chunk.get('message')}")
                    
                    wsock.send(json.dumps(chunk))
                    
                    if chunk['type'] == 'text':
                        full_response += chunk.get('content', '')
                    elif chunk['type'] == 'visualization':
                        # Store visualization reference
                        conversation_service.add_visualization(
                            conversation_id,
                            chunk.get('viz_id'),
                            chunk.get('viz_data')
                        )
                
                # Save assistant response
                if full_response:
                    conversation_service.add_message(
                        conversation_id,
                        'assistant',
                        full_response,
                        {'agent': chunk.get('agent_used')}
                    )
                
                # Send completion
                wsock.send(json.dumps({
                    "type": "done",
                    "conversation_id": conversation_id
                }))
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                wsock.send(json.dumps({
                    "type": "error",
                    "message": "Invalid message format"
                }))
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}\n{traceback.format_exc()}")
                wsock.send(json.dumps({
                    "type": "error",
                    "message": "Failed to process message"
                }))
    
    except WebSocketError as e:
        logger.error(f"WebSocket error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket handler: {str(e)}\n{traceback.format_exc()}")
    finally:
        if conversation_id:
            # Update conversation last activity
            conversation_service.update_last_activity(conversation_id)
        logger.info("WebSocket connection closed")
    
    return ''

# REST API endpoint (non-streaming alternative)
@app.route('/api/chat', method='POST')
@handle_errors
def chat_api():
    """REST API endpoint for non-streaming chat"""
    data = request.json
    
    if not data or 'message' not in data:
        abort(400, 'Missing required field: message')
    
    user_query = data['message']
    conversation_id = data.get('conversation_id')
    user_id = data.get('user_id', 'anonymous')
    metadata = data.get('metadata', {})
    
    logger.info(f"REST API request from user {user_id}: {user_query[:50]}...")
    
    # Get or create conversation
    conversation = conversation_service.get_or_create_conversation(
        conversation_id,
        user_id
    )
    conversation_id = conversation['id']
    
    # Add user message
    conversation_service.add_message(conversation_id, 'user', user_query, metadata)
    
    # Get conversation history
    history = conversation_service.get_messages(conversation_id)
    
    # Get response from orchestrator (non-streaming)
    result = agent_orchestrator.get_response(
        user_query,
        history,
        conversation_id,
        user_id
    )
    
    # Save assistant response
    conversation_service.add_message(
        conversation_id,
        'assistant',
        result['response'],
        {'agent': result.get('agent_used')}
    )
    
    # Save visualizations if any
    if result.get('visualizations'):
        for viz in result['visualizations']:
            conversation_service.add_visualization(
                conversation_id,
                viz['id'],
                viz['data']
            )
    
    return {
        "response": result['response'],
        "conversation_id": conversation_id,
        "agent_used": result.get('agent_used'),
        "visualizations": result.get('visualizations', []),
        "metadata": result.get('metadata', {})
    }

# Get conversation history
@app.route('/api/conversations/<conversation_id>')
@handle_errors
def get_conversation(conversation_id):
    """Get conversation history"""
    conversation = conversation_service.get_conversation(conversation_id)
    
    if not conversation:
        abort(404, 'Conversation not found')
    
    return {
        "conversation": conversation,
        "messages": conversation_service.get_messages(conversation_id),
        "visualizations": conversation_service.get_visualizations(conversation_id)
    }

# List conversations for user
@app.route('/api/conversations')
@handle_errors
def list_conversations():
    """List all conversations for a user"""
    user_id = request.query.get('user_id', 'anonymous')
    limit = int(request.query.get('limit', 20))
    offset = int(request.query.get('offset', 0))
    
    conversations = conversation_service.list_conversations(user_id, limit, offset)
    
    return {
        "conversations": conversations,
        "limit": limit,
        "offset": offset
    }

# Delete conversation
@app.route('/api/conversations/<conversation_id>', method='DELETE')
@handle_errors
def delete_conversation(conversation_id):
    """Delete a conversation"""
    success = conversation_service.delete_conversation(conversation_id)
    
    if not success:
        abort(404, 'Conversation not found')
    
    return {"message": "Conversation deleted successfully"}

# Get visualization data
@app.route('/api/visualizations/<viz_id>')
@handle_errors
def get_visualization(viz_id):
    """Get visualization data by ID"""
    viz_data = conversation_service.get_visualization_by_id(viz_id)
    
    if not viz_data:
        abort(404, 'Visualization not found')
    
    return viz_data

# Analytics endpoint
@app.route('/api/analytics')
@handle_errors
def get_analytics():
    """Get usage analytics"""
    user_id = request.query.get('user_id')
    start_date = request.query.get('start_date')
    end_date = request.query.get('end_date')
    
    analytics = conversation_service.get_analytics(user_id, start_date, end_date)
    
    return analytics

# Main entry point
def main():
    """Start the server"""
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8080))
    
    logger.info(f"Starting Sherlock API server on {host}:{port}")
    logger.info(f"Environment: {config.ENVIRONMENT}")
    logger.info(f"Log level: {config.LOG_LEVEL}")
    
    server = pywsgi.WSGIServer(
        (host, port),
        app,
        handler_class=WebSocketHandler,
        log=logger
    )
    
    try:
        logger.info("Server is ready to accept connections")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise

if __name__ == '__main__':
    main()