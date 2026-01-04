"""
Data Analysis Agent (Synchronous, Token-Optimized)
"""

import json
import logging
from typing import Dict, List, Generator

from tools.data_tools import DataTools

logger = logging.getLogger(__name__)


class DataAnalysisAgent:
    """Data analysis specialist"""
    
    def __init__(self, config, client):
        self.config = config
        self.client = client
        self.data_tools = DataTools(config)
        
        # Minimal system prompt to save tokens
        self.system_prompt = """You're a financial data analyst. Use get_domestic_metadata tool to query account data.
Present findings clearly with key numbers. Explain business implications concisely."""
        
        # Tool definition
        self.tools = [{
            "type": "function",
            "function": {
                "name": "get_domestic_metadata",
                "description": "Query account data: overdrafts, balances, tenure. Examples: 'overdraft > 1M', 'tenure > 90 days', 'top 10 by balance', 'summary'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Query string"}
                    },
                    "required": ["query"]
                }
            }
        }]
    
    def _call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Execute tool"""
        if tool_name == "get_domestic_metadata":
            return self.data_tools.get_domestic_metadata(arguments.get('query', ''))
        return {"error": f"Unknown tool: {tool_name}"}
    
    def stream_analysis(self, user_query: str, history: List[Dict]) -> Generator[Dict, None, None]:
        """Stream data analysis"""
        
        try:
            # Build messages (keep history minimal)
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Only last 5 messages for context
            for msg in history[-5:]:
                if msg['role'] in ['user', 'assistant']:
                    messages.append({"role": msg['role'], "content": msg['content']})
            
            messages.append({"role": "user", "content": user_query})
            
            yield {"type": "status", "message": "Querying data...", "agent": "DATA"}
            
            # First call to get tool use
            response = self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=1000  # Limit tokens
            )
            
            message = response.choices[0].message
            
            # Handle tool calls
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    
                    yield {
                        "type": "tool_call",
                        "tool": func_name,
                        "status": "executing",
                        "query": func_args.get('query', '')
                    }
                    
                    # Execute
                    tool_result = self._call_tool(func_name, func_args)
                    
                    yield {"type": "tool_call", "tool": func_name, "status": "completed"}
                    yield {"type": "data", "data": tool_result}
                    
                    # Add to messages
                    messages.append({
                        "role": "assistant",
                        "tool_calls": [{
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": func_name,
                                "arguments": tool_call.function.arguments
                            }
                        }]
                    })
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })
                
                # Get formatted response with streaming
                yield {"type": "status", "message": "Formatting...", "agent": "DATA"}
                
                stream = self.client.chat.completions.create(
                    model=self.config.OPENAI_MODEL,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=800,  # Limit output
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield {
                            "type": "text",
                            "content": chunk.choices[0].delta.content,
                            "agent": "DATA"
                        }
            
            else:
                # No tool needed, direct response
                yield {"type": "text", "content": message.content or "No data found.", "agent": "DATA"}
        
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            yield {"type": "error", "message": str(e), "agent": "DATA"}
