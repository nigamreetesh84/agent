from bottle import Bottle, request, response
from gevent import pywsgi
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler
import json
import anthropic
import os

app = Bottle()

# Initialize Claude client
claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def get_domestic_metadata(query: str) -> dict:
    """Your existing tool implementation"""
    df = load_dataframe()
    # ... your existing logic ...
    return result_dict

# Define tools for Claude
tools = [{
    "name": "get_domestic_metadata",
    "description": """Analyzes domestic account data and answers business queries.
    
    This tool intelligently processes business questions about accounts, overdrafts,
    balances, and other metrics. It performs server-side filtering, aggregation,
    and calculations to provide direct answers.
    
    Examples:
    - "overdraft > 1M": Accounts with overdraft over $1M
    - "tenure > 90 days": Accounts with overdraft tenure over 90 days
    - "total balance by country": Aggregate balances by country
    - "tenure aging breakdown": Overdraft aging analysis by buckets""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Business query or request type (e.g., 'overdraft > 1M', 'tenure > 90 days')"
            }
        },
        "required": ["query"]
    }
}]

system_prompt = """You are a Sherlock Domestic Account Data Analysis Assistant for JPMorgan Chase Security Services.

Your role is to help financial business users query and understand account data including balances, 
overdraft positions, interest calculations, rate spreads, pricing structures, entity hierarchies, 
and month-to-date metrics.

TOOL USAGE APPROACH:
The get_domestic_metadata tool is YOUR INTELLIGENT DATA ANALYZER. It doesn't just return metadata - 
it actually PROCESSES and ANSWERS business questions!

When users ask questions:
1. Translate their question into a concise query parameter for the tool
2. Call the tool with queries like: "overdraft > 1M", "tenure > 90 days", "total balance by country"
3. The tool will filter, calculate, and return the actual business answer
4. You present the results in a business-friendly format with insights

PRESENTATION STYLE:
- Start with an executive summary of key findings
- For large datasets: Highlight top items and provide context
- For financial data: Format numbers with $ and commas
- For risk analysis: Explain what the numbers mean for business decisions
- Use tables sparingly - prefer conversational insights
- If showing sample results, mention how many total exist

BUSINESS CONTEXT:
- Overdraft positions represent credit exposure and risk
- Tenure (aging) indicates how long overdrafts have existed - longer is riskier
- ERISA flags indicate special regulatory requirements
- Balance aggregations help understand regional or entity-level exposure

Always maintain a professional, insightful tone. You're not just returning data - 
you're providing financial intelligence."""

@app.route('/ws/chat')
def handle_websocket():
    """WebSocket endpoint for streaming chat"""
    wsock = request.environ.get('wsgi.websocket')
    if not wsock:
        return 'Expected WebSocket request'
    
    try:
        while True:
            # Receive user message
            message = wsock.receive()
            if message is None:
                break
                
            data = json.loads(message)
            user_query = data.get('message', '')
            conversation_history = data.get('history', [])
            
            # Build messages for Claude
            messages = conversation_history + [
                {"role": "user", "content": user_query}
            ]
            
            # Stream response from Claude
            with claude_client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                temperature=0.1,
                system=system_prompt,
                tools=tools,
                messages=messages
            ) as stream:
                current_text = ""
                tool_use_block = None
                
                for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            tool_use_block = event.content_block
                            # Send tool call notification
                            wsock.send(json.dumps({
                                "type": "tool_call",
                                "tool": tool_use_block.name,
                                "status": "started"
                            }))
                    
                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            # Stream text chunks to client
                            text_chunk = event.delta.text
                            current_text += text_chunk
                            wsock.send(json.dumps({
                                "type": "text",
                                "content": text_chunk
                            }))
                        elif event.delta.type == "input_json_delta":
                            # Tool input being built
                            pass
                    
                    elif event.type == "content_block_stop":
                        if tool_use_block:
                            # Execute tool
                            tool_input = tool_use_block.input
                            wsock.send(json.dumps({
                                "type": "tool_call",
                                "tool": tool_use_block.name,
                                "status": "executing",
                                "input": tool_input
                            }))
                            
                            try:
                                # Call your tool
                                tool_result = get_domestic_metadata(tool_input['query'])
                                
                                wsock.send(json.dumps({
                                    "type": "tool_call",
                                    "tool": tool_use_block.name,
                                    "status": "completed"
                                }))
                                
                                # Continue conversation with tool result
                                messages.append({
                                    "role": "assistant",
                                    "content": [tool_use_block]
                                })
                                messages.append({
                                    "role": "user",
                                    "content": [{
                                        "type": "tool_result",
                                        "tool_use_id": tool_use_block.id,
                                        "content": json.dumps(tool_result)
                                    }]
                                })
                                
                                # Get final response with tool result
                                with claude_client.messages.stream(
                                    model="claude-sonnet-4-20250514",
                                    max_tokens=4096,
                                    temperature=0.1,
                                    system=system_prompt,
                                    tools=tools,
                                    messages=messages
                                ) as followup_stream:
                                    for followup_event in followup_stream:
                                        if (followup_event.type == "content_block_delta" and 
                                            followup_event.delta.type == "text_delta"):
                                            wsock.send(json.dumps({
                                                "type": "text",
                                                "content": followup_event.delta.text
                                            }))
                                
                            except Exception as e:
                                wsock.send(json.dumps({
                                    "type": "error",
                                    "message": f"Tool execution failed: {str(e)}"
                                }))
                            
                            tool_use_block = None
                
                # Send completion signal
                wsock.send(json.dumps({"type": "done"}))
                
    except WebSocketError:
        pass
    
    return ''

@app.route('/api/chat', method='POST')
def chat_api():
    """REST API endpoint (non-streaming alternative)"""
    data = request.json
    user_query = data.get('message', '')
    conversation_history = data.get('history', [])
    
    messages = conversation_history + [
        {"role": "user", "content": user_query}
    ]
    
    # Non-streaming response
    response_obj = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0.1,
        system=system_prompt,
        tools=tools,
        messages=messages
    )
    
    # Handle tool calls
    while response_obj.stop_reason == "tool_use":
        tool_use = next(block for block in response_obj.content if block.type == "tool_use")
        
        # Execute tool
        tool_result = get_domestic_metadata(tool_use.input['query'])
        
        # Add to conversation
        messages.append({"role": "assistant", "content": response_obj.content})
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": json.dumps(tool_result)
            }]
        })
        
        # Get next response
        response_obj = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.1,
            system=system_prompt,
            tools=tools,
            messages=messages
        )
    
    # Extract final text response
    assistant_message = next(
        (block.text for block in response_obj.content if hasattr(block, 'text')),
        ""
    )
    
    return {
        "response": assistant_message,
        "conversation_id": data.get('conversation_id'),
        "model": "claude-sonnet-4-20250514"
    }

if __name__ == '__main__':
    server = pywsgi.WSGIServer(
        ('0.0.0.0', 8080),
        app,
        handler_class=WebSocketHandler
    )
    print("Server running on http://0.0.0.0:8080")
    server.serve_forever()