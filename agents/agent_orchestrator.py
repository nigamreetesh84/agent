"""
Multi-Agent Orchestrator
Routes queries to specialized agents based on intent and manages agent collaboration
"""

import json
import logging
from typing import Dict, List, AsyncGenerator, Optional
from openai import AsyncOpenAI
import asyncio

from agents.data_agent import DataAnalysisAgent
from agents.visualization_agent import VisualizationAgent
from agents.insight_agent import InsightAgent
from agents.report_agent import ReportGenerationAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates multiple specialized agents to handle complex queries
    """
    
    def __init__(self, config):
        self.config = config
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        
        # Initialize specialized agents
        self.data_agent = DataAnalysisAgent(config, self.client)
        self.visualization_agent = VisualizationAgent(config, self.client)
        self.insight_agent = InsightAgent(config, self.client)
        self.report_agent = ReportGenerationAgent(config, self.client)
        
        # Agent router prompt
        self.router_prompt = """You are an intelligent agent router. Analyze the user's query and determine which specialized agent(s) should handle it.

Available Agents:
1. DATA_AGENT: For querying, filtering, and analyzing account data (balances, overdrafts, tenure, etc.)
2. VISUALIZATION_AGENT: For creating charts, graphs, and visual representations of data
3. INSIGHT_AGENT: For generating business insights, trends, anomalies, and predictions
4. REPORT_AGENT: For creating formatted reports, summaries, and documents

Query Analysis:
- If user asks for specific data or filters: Use DATA_AGENT
- If user wants to see charts/graphs: Use VISUALIZATION_AGENT (usually after DATA_AGENT)
- If user wants insights, trends, or recommendations: Use INSIGHT_AGENT
- If user wants a report or summary: Use REPORT_AGENT
- Complex queries may require multiple agents in sequence

Respond with JSON only:
{
    "primary_agent": "AGENT_NAME",
    "secondary_agents": ["AGENT_NAME"],
    "reasoning": "Brief explanation",
    "requires_data": true/false
}"""
    
    async def route_query(self, user_query: str, history: List[Dict]) -> Dict:
        """Determine which agent(s) should handle the query"""
        try:
            messages = [
                {"role": "system", "content": self.router_prompt},
                {"role": "user", "content": f"User query: {user_query}"}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            routing = json.loads(response.choices[0].message.content)
            logger.info(f"Query routed to: {routing['primary_agent']}")
            return routing
            
        except Exception as e:
            logger.error(f"Error routing query: {e}")
            # Default to data agent if routing fails
            return {
                "primary_agent": "DATA_AGENT",
                "secondary_agents": [],
                "reasoning": "Default routing due to error",
                "requires_data": True
            }
    
    async def stream_response(
        self,
        user_query: str,
        history: List[Dict],
        conversation_id: str,
        user_id: str
    ) -> AsyncGenerator[Dict, None]:
        """
        Stream response from appropriate agent(s)
        Yields chunks of data as they become available
        """
        try:
            # Route the query
            routing = await self.route_query(user_query, history)
            
            yield {
                "type": "routing",
                "agent": routing['primary_agent'],
                "reasoning": routing['reasoning']
            }
            
            # Execute primary agent
            primary_agent = self._get_agent(routing['primary_agent'])
            data_result = None
            
            if routing['requires_data'] or routing['primary_agent'] == 'DATA_AGENT':
                yield {
                    "type": "status",
                    "message": "Analyzing data...",
                    "agent": routing['primary_agent']
                }
                
                # Get data from data agent
                async for chunk in primary_agent.stream_analysis(user_query, history):
                    if chunk['type'] == 'data':
                        data_result = chunk['data']
                    yield chunk
            else:
                # Non-data agents
                async for chunk in primary_agent.stream_response(user_query, history):
                    yield chunk
            
            # Execute secondary agents if needed
            for secondary_agent_name in routing.get('secondary_agents', []):
                secondary_agent = self._get_agent(secondary_agent_name)
                
                yield {
                    "type": "status",
                    "message": f"Generating {secondary_agent_name.lower().replace('_', ' ')}...",
                    "agent": secondary_agent_name
                }
                
                # Pass data to secondary agents
                if secondary_agent_name == 'VISUALIZATION_AGENT' and data_result:
                    async for chunk in secondary_agent.create_visualization(
                        user_query, data_result, history
                    ):
                        yield chunk
                
                elif secondary_agent_name == 'INSIGHT_AGENT':
                    async for chunk in secondary_agent.generate_insights(
                        user_query, data_result or {}, history
                    ):
                        yield chunk
                
                elif secondary_agent_name == 'REPORT_AGENT':
                    async for chunk in secondary_agent.generate_report(
                        user_query, data_result or {}, history
                    ):
                        yield chunk
            
            # Final completion
            yield {
                "type": "complete",
                "agent_used": routing['primary_agent']
            }
            
        except Exception as e:
            logger.error(f"Error in stream_response: {e}")
            yield {
                "type": "error",
                "message": f"An error occurred: {str(e)}"
            }
    
    def get_response(
        self,
        user_query: str,
        history: List[Dict],
        conversation_id: str,
        user_id: str
    ) -> Dict:
        """
        Non-streaming version - get complete response
        """
        try:
            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                self._get_complete_response(user_query, history, conversation_id, user_id)
            )
            
            loop.close()
            return result
            
        except Exception as e:
            logger.error(f"Error in get_response: {e}")
            return {
                "response": "I apologize, but I encountered an error processing your request.",
                "error": str(e)
            }
    
    async def _get_complete_response(
        self,
        user_query: str,
        history: List[Dict],
        conversation_id: str,
        user_id: str
    ) -> Dict:
        """Internal method to get complete response"""
        response_text = ""
        visualizations = []
        metadata = {}
        agent_used = None
        
        async for chunk in self.stream_response(user_query, history, conversation_id, user_id):
            if chunk['type'] == 'text':
                response_text += chunk.get('content', '')
            elif chunk['type'] == 'visualization':
                visualizations.append({
                    'id': chunk.get('viz_id'),
                    'data': chunk.get('viz_data')
                })
            elif chunk['type'] == 'complete':
                agent_used = chunk.get('agent_used')
            elif chunk['type'] == 'metadata':
                metadata.update(chunk.get('data', {}))
        
        return {
            "response": response_text,
            "visualizations": visualizations,
            "agent_used": agent_used,
            "metadata": metadata
        }
    
    def _get_agent(self, agent_name: str):
        """Get agent instance by name"""
        agents = {
            'DATA_AGENT': self.data_agent,
            'VISUALIZATION_AGENT': self.visualization_agent,
            'INSIGHT_AGENT': self.insight_agent,
            'REPORT_AGENT': self.report_agent
        }
        
        agent = agents.get(agent_name)
        if not agent:
            logger.warning(f"Unknown agent: {agent_name}, defaulting to DATA_AGENT")
            return self.data_agent
        
        return agent
