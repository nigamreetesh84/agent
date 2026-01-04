"""
Insight Generation Agent
Generates business insights, trends, and recommendations
"""

import logging
from typing import Dict, List, AsyncGenerator

logger = logging.getLogger(__name__)


class InsightAgent:
    """Agent specialized in generating business insights"""
    
    def __init__(self, config, client):
        self.config = config
        self.client = client
        
        self.system_prompt = """You are a Business Insight Specialist Agent for financial analysis.

Your role is to:
1. Analyze data patterns and trends
2. Identify risks and opportunities
3. Generate actionable business recommendations
4. Provide context and implications

Focus areas:
- Credit risk assessment
- Trend analysis
- Anomaly detection
- Predictive insights
- Strategic recommendations

Guidelines:
- Be specific and data-driven
- Explain implications clearly
- Prioritize by business impact
- Provide actionable next steps
- Use professional financial language"""
    
    async def generate_insights(
        self,
        user_query: str,
        data_result: Dict,
        history: List[Dict]
    ) -> AsyncGenerator[Dict, None]:
        """Generate insights from data"""
        
        try:
            yield {
                "type": "status",
                "message": "Generating insights...",
                "agent": "INSIGHT_AGENT"
            }
            
            # Build prompt for insight generation
            insight_prompt = f"""Analyze this data and provide business insights:

Data Summary:
{self._format_data_summary(data_result)}

Generate:
1. Key findings and patterns
2. Risk assessment
3. Business implications
4. Recommended actions

Be specific and actionable."""
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": insight_prompt}
            ]
            
            # Stream insights
            stream = await self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=messages,
                temperature=0.4,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield {
                        "type": "text",
                        "content": chunk.choices[0].delta.content,
                        "agent": "INSIGHT_AGENT"
                    }
        
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            yield {
                "type": "error",
                "message": f"Failed to generate insights: {str(e)}",
                "agent": "INSIGHT_AGENT"
            }
    
    async def stream_response(
        self,
        user_query: str,
        history: List[Dict]
    ) -> AsyncGenerator[Dict, None]:
        """Stream general insight response"""
        
        messages = [{"role": "system", "content": self.system_prompt}]
        
        for msg in history[-5:]:
            if msg['role'] in ['user', 'assistant']:
                messages.append({"role": msg['role'], "content": msg['content']})
        
        messages.append({"role": "user", "content": user_query})
        
        stream = await self.client.chat.completions.create(
            model=self.config.OPENAI_MODEL,
            messages=messages,
            temperature=0.4,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield {
                    "type": "text",
                    "content": chunk.choices[0].delta.content,
                    "agent": "INSIGHT_AGENT"
                }
    
    def _format_data_summary(self, data_result: Dict) -> str:
        """Format data for insight generation"""
        
        summary_parts = []
        
        if 'total_accounts' in data_result:
            summary_parts.append(f"Total Accounts: {data_result['total_accounts']}")
        
        if 'total_overdraft_amount' in data_result:
            summary_parts.append(f"Total Overdraft: ${data_result['total_overdraft_amount']:,.0f}")
        
        if 'average_overdraft' in data_result:
            summary_parts.append(f"Average Overdraft: ${data_result['average_overdraft']:,.0f}")
        
        if 'breakdown_by_size' in data_result:
            summary_parts.append("\nBreakdown by Size:")
            for size, data in data_result['breakdown_by_size'].items():
                summary_parts.append(f"  {size}: {data['count']} accounts, ${data.get('sum', 0):,.0f}")
        
        if 'aging_breakdown' in data_result:
            summary_parts.append("\nAging Breakdown:")
            for period, count in data_result['aging_breakdown'].items():
                summary_parts.append(f"  {period}: {count} accounts")
        
        return "\n".join(summary_parts)