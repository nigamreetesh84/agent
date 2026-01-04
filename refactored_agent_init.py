"""
Refactored: Direct Agent Initialization Pattern
Similar to the screenshot approach
"""

from anthropic import Anthropic
from typing import List, Dict, Any, Generator
import json

# ============================================
# 1. AGENT DEFINITION (Like Screenshot)
# ============================================

def create_sherlock_agent(model: str = "claude-sonnet-4-20250514"):
    """
    Creates the Sherlock Domestic Account Analysis Agent.
    
    This agent combines:
    1. get_domestic_metadata tool - for quick summaries and metadata
    2. Natural language understanding - guides users to describe data queries
    3. Data Analyzer tool (if available) - for complex filtering and calculations
    """
    
    return {
        "name": "SherlockDomesticAccountAnalysisAssistant",
        
        "description": """An AI Assistant specialized in analyzing domestic account data from Sherlock systems.
        Helps financial business users query and understand account balances, overdraft positions, interest
        calculations, rate spreads, pricing structures, entity hierarchies, and month-to-date metrics across
        cash and security accounts.""",
        
        "model": model,
        
        "tools": [
            {
                "name": "get_domestic_metadata",
                "description": """Analyzes domestic account data and returns intelligent summaries.
                This tool PROCESSES queries and returns ANSWERS, not just metadata.
                
                Examples:
                - "overdraft > 1M" → Returns accounts with overdraft over $1M
                - "total balance by country" → Returns aggregated balances
                - "top 10 accounts" → Returns sorted account list
                """,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query about accounts (e.g., 'show accounts with overdraft > 1M')"
                        }
                    },
                    "required": ["query"]
                }
            }
        ],
        
        "system_message": """You are a Sherlock Domestic Account Data Analysis Assistant designed for financial business users at JPMorgan Chase.

TOOL USAGE - BUSINESS-FOCUSED APPROACH:
The get_domestic_metadata tool is YOUR INTELLIGENT DATA ANALYZER. It doesn't just return metadata - it actually PROCESSES and ANSWERS business questions.

**How to use it effectively**:

1. **For user questions like "Show me accounts with overdraft > $1M"**:
   - Call: get_domestic_metadata("overdraft > 1M")
   - The tool returns the ACTUAL ACCOUNTS matching this criteria
   - Present the results clearly to the user

2. **For aggregation queries like "What's total balance by country?"**:
   - Call: get_domestic_metadata("total balance by country")
   - Tool performs the grouping and calculation
   - Share the aggregated results

3. **For comparative analysis like "Compare overdraft aging"**:
   - Call: get_domestic_metadata("overdraft aging breakdown")
   - Tool analyzes and categorizes the data
   - Present insights with context

RESPONSE STYLE:
- Be conversational and business-focused
- Translate technical results into business insights
- Proactively suggest follow-up analyses
- Use formatting (tables, bullets) for clarity
- Always explain what the numbers mean for the business

EXAMPLE INTERACTIONS:
User: "Show accounts with high overdraft"
You: [Call tool] → "I found 47 accounts with overdraft exceeding $1M. Here are the top 10 by exposure..."

User: "What's our total exposure?"
You: [Call tool] → "Total overdraft exposure is $127.3M across 234 accounts. The largest concentration is in..."

Be helpful, insightful, and action-oriented!"""
    }


# ============================================
# 2. AGENT EXECUTOR (Handles Tool Calling)
# ============================================

class SherlockAgentExecutor:
    """Executes the Sherlock agent with tool calling support"""
    
    def __init__(self, agent_config: Dict[str, Any], anthropic_api_key: str):
        self.config = agent_config
        self.client = Anthropic(api_key=anthropic_api_key)
        self.model = agent_config["model"]
        self.tools = self._format_tools_for_anthropic(agent_config["tools"])
        self.system_message = agent_config["system_message"]
        
        # Tool implementations
        self.tool_implementations = {
            "get_domestic_metadata": self._execute_get_domestic_metadata
        }
    
    def _format_tools_for_anthropic(self, tools: List[Dict]) -> List[Dict]:
        """Convert tool definitions to Anthropic format"""
        return tools
    
    def _execute_get_domestic_metadata(self, query: str) -> Dict[str, Any]:
        """
        Mock implementation - replace with your actual data query logic
        """
        # TODO: Replace with actual database/API call
        return {
            "success": True,
            "query": query,
            "results": [
                {"account_id": "ACC001", "balance": 1500000, "overdraft": 1200000},
                {"account_id": "ACC002", "balance": 2300000, "overdraft": 1800000}
            ],
            "summary": f"Found 2 accounts matching: {query}",
            "total_count": 2
        }
    
    def run(self, user_query: str, conversation_history: List[Dict] = None) -> str:
        """Execute agent with tool calling loop"""
        
        messages = conversation_history or []
        messages.append({
            "role": "user",
            "content": user_query
        })
        
        max_iterations = 5
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_message,
                tools=self.tools,
                messages=messages
            )
            
            # Check if we're done
            if response.stop_reason == "end_turn":
                # Extract text response
                text_content = ""
                for block in response.content:
                    if block.type == "text":
                        text_content += block.text
                return text_content
            
            # Handle tool calls
            if response.stop_reason == "tool_use":
                # Add assistant response to history
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # Execute tools and collect results
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        
                        # Execute tool
                        if tool_name in self.tool_implementations:
                            result = self.tool_implementations[tool_name](**tool_input)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(result)
                            })
                
                # Add tool results to history
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
                
                # Continue loop to get final response
                continue
        
        return "Maximum iterations reached. Please try rephrasing your question."
    
    def stream(self, user_query: str, conversation_history: List[Dict] = None) -> Generator:
        """Stream agent responses with tool calling"""
        
        messages = conversation_history or []
        messages.append({
            "role": "user",
            "content": user_query
        })
        
        max_iterations = 5
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=self.system_message,
                tools=self.tools,
                messages=messages
            ) as stream:
                
                current_tool_use = None
                
                for event in stream:
                    # Text streaming
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            yield {
                                "type": "text",
                                "content": event.delta.text
                            }
                    
                    # Tool use started
                    elif event.type == "content_block_start":
                        if hasattr(event.content_block, "type") and event.content_block.type == "tool_use":
                            current_tool_use = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input": ""
                            }
                            yield {
                                "type": "tool_call",
                                "tool": event.content_block.name,
                                "status": "started"
                            }
                
                # Get final message
                message = stream.get_final_message()
                
                if message.stop_reason == "end_turn":
                    yield {"type": "done"}
                    return
                
                # Handle tool execution
                if message.stop_reason == "tool_use":
                    messages.append({
                        "role": "assistant",
                        "content": message.content
                    })
                    
                    tool_results = []
                    for block in message.content:
                        if block.type == "tool_use":
                            yield {
                                "type": "tool_call",
                                "tool": block.name,
                                "status": "executing",
                                "input": block.input
                            }
                            
                            result = self.tool_implementations[block.name](**block.input)
                            
                            yield {
                                "type": "tool_call",
                                "tool": block.name,
                                "status": "completed"
                            }
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(result)
                            })
                    
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                    
                    continue


# ============================================
# 3. USAGE IN YOUR BACKEND
# ============================================

def initialize_agent(config):
    """Initialize agent using the new pattern"""
    
    # Create agent configuration
    agent_config = create_sherlock_agent(
        model=config.MODEL_NAME  # Make it configurable
    )
    
    # Create executor
    agent_executor = SherlockAgentExecutor(
        agent_config=agent_config,
        anthropic_api_key=config.ANTHROPIC_API_KEY
    )
    
    return agent_executor


# Example usage in your Flask/Bottle app:
"""
# In prod_backend_main.py:

from agent_definition import initialize_agent

# Replace this:
# agent_orchestrator = AgentOrchestrator(config)

# With this:
agent_executor = initialize_agent(config)

# Then in your endpoints:
response = agent_executor.run(user_query, history)
# or
for chunk in agent_executor.stream(user_query, history):
    wsock.send(json.dumps(chunk))
"""
