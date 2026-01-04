"""
Production-Ready Sherlock Account Analysis API
Simplified synchronous version with gevent
"""

from bottle import Bottle, request, response, abort
from gevent import pywsgi
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler
import json
import os
import logging
from datetime import datetime
import traceback
from functools import wraps

# Local imports
from config import Config
from agents.agent_orchestrator import AgentOrchestrator
from services.conversation_service import ConversationService
from utils.logger import setup_logger

# Initialize
app = Bottle()
logger = setup_logger(__name__)

config = Config()
config.validate()
conversation_service = ConversationService(config)
agent_orchestrator = AgentOrchestrator(config)

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
        "version": "1.0.0"
    }

@app.route('/ws/chat')
def handle_websocket():
    """WebSocket streaming endpoint"""
    wsock = request.environ.get('wsgi.websocket')
    if not wsock:
        abort(400, 'Expected WebSocket request')
    
    conversation_id = None
    
    try:
        logger.info("WebSocket connected")
        
        while True:
            message = wsock.receive()
            if message is None:
                break
            
            try:
                data = json.loads(message)
                user_query = data.get('message', '')
                conversation_id = data.get('conversation_id')
                user_id = data.get('user_id', 'anonymous')
                
                if not user_query:
                    wsock.send(json.dumps({"type": "error", "message": "Empty message"}))
                    continue
                
                logger.info(f"User {user_id}: {user_query[:50]}...")
                
                # Get or create conversation
                conversation = conversation_service.get_or_create_conversation(conversation_id, user_id)
                conversation_id = conversation['id']
                
                # Add user message
                conversation_service.add_message(conversation_id, 'user', user_query, {})
                
                # Get history
                history = conversation_service.get_messages(conversation_id)
                
                # Stream response
                full_response = ""
                for chunk in agent_orchestrator.stream_response(user_query, history, conversation_id, user_id):
                    wsock.send(json.dumps(chunk))
                    
                    if chunk['type'] == 'text':
                        full_response += chunk.get('content', '')
                    elif chunk['type'] == 'visualization':
                        conversation_service.add_visualization(
                            conversation_id,
                            chunk.get('viz_id'),
                            chunk.get('viz_data')
                        )
                
                # Save assistant response
                if full_response:
                    conversation_service.add_message(conversation_id, 'assistant', full_response, {})
                
                wsock.send(json.dumps({"type": "done", "conversation_id": conversation_id}))
                
            except json.JSONDecodeError:
                wsock.send(json.dumps({"type": "error", "message": "Invalid JSON"}))
            except Exception as e:
                logger.error(f"Error: {str(e)}")
                wsock.send(json.dumps({"type": "error", "message": str(e)}))
    
    except WebSocketError as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if conversation_id:
            conversation_service.update_last_activity(conversation_id)
        logger.info("WebSocket closed")
    
    return ''

@app.route('/api/chat', method='POST')
@handle_errors
def chat_api():
    """REST API endpoint"""
    data = request.json
    if not data or 'message' not in data:
        abort(400, 'Missing message')
    
    user_query = data['message']
    conversation_id = data.get('conversation_id')
    user_id = data.get('user_id', 'anonymous')
    
    # Get or create conversation
    conversation = conversation_service.get_or_create_conversation(conversation_id, user_id)
    conversation_id = conversation['id']
    
    conversation_service.add_message(conversation_id, 'user', user_query, {})
    history = conversation_service.get_messages(conversation_id)
    
    # Get response
    result = agent_orchestrator.get_response(user_query, history, conversation_id, user_id)
    
    conversation_service.add_message(conversation_id, 'assistant', result['response'], {})
    
    if result.get('visualizations'):
        for viz in result['visualizations']:
            conversation_service.add_visualization(conversation_id, viz['id'], viz['data'])
    
    return {
        "response": result['response'],
        "conversation_id": conversation_id,
        "visualizations": result.get('visualizations', [])
    }

@app.route('/api/conversations/<conversation_id>')
@handle_errors
def get_conversation(conversation_id):
    conv = conversation_service.get_conversation(conversation_id)
    if not conv:
        abort(404, 'Not found')
    return {
        "conversation": conv,
        "messages": conversation_service.get_messages(conversation_id),
        "visualizations": conversation_service.get_visualizations(conversation_id)
    }

@app.route('/api/conversations')
@handle_errors
def list_conversations():
    user_id = request.query.get('user_id', 'anonymous')
    limit = int(request.query.get('limit', 20))
    offset = int(request.query.get('offset', 0))
    return {"conversations": conversation_service.list_conversations(user_id, limit, offset)}

@app.route('/api/conversations/<conversation_id>', method='DELETE')
@handle_errors
def delete_conversation(conversation_id):
    if not conversation_service.delete_conversation(conversation_id):
        abort(404, 'Not found')
    return {"message": "Deleted"}

def main():
    """Start server"""
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8080))
    
    logger.info(f"Starting on {host}:{port}")
    logger.info(f"Environment: {config.ENVIRONMENT}")
    
    server = pywsgi.WSGIServer((host, port), app, handler_class=WebSocketHandler)
    
    try:
        logger.info("Server ready")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == '__main__':
    main()
