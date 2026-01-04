"""
Report Generation Agent
Creates formatted reports and documents
"""

import logging
from typing import Dict, List, AsyncGenerator
from datetime import datetime

logger = logging.getLogger(__name__)


class ReportGenerationAgent:
    """Agent specialized in creating reports"""
    
    def __init__(self, config, client):
        self.config = config
        self.client = client
        
        self.system_prompt = """You are a Report Generation Specialist Agent.

Your role is to create professional, well-structured reports from data analysis.

Report Structure:
1. Executive Summary
2. Key Findings
3. Detailed Analysis
4. Recommendations
5. Appendix (if needed)

Formatting Guidelines:
- Use clear headings and sections
- Include relevant metrics and data points
- Use bullet points for clarity
- Add context and explanations
- Professional business tone
- Include date and metadata

Always create comprehensive yet concise reports."""
    
    async def generate_report(
        self,
        user_query: str,
        data_result: Dict,
        history: List[Dict]
    ) -> AsyncGenerator[Dict, None]:
        """Generate a formatted report"""
        
        try:
            yield {
                "type": "status",
                "message": "Generating report...",
                "agent": "REPORT_AGENT"
            }
            
            report_prompt = f"""Generate a comprehensive report based on this analysis:

Query: {user_query}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Data Analysis:
{self._format_report_data(data_result)}

Create a professional report with:
1. Executive Summary
2. Detailed Findings
3. Visual Data Summary
4. Key Recommendations

Use clear formatting with headers and sections."""
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": report_prompt}
            ]
            
            stream = await self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=messages,
                temperature=0.3,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield {
                        "type": "text",
                        "content": chunk.choices[0].delta.content,
                        "agent": "REPORT_AGENT"
                    }
        
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            yield {
                "type": "error",
                "message": f"Failed to generate report: {str(e)}",
                "agent": "REPORT_AGENT"
            }
    
    async def stream_response(
        self,
        user_query: str,
        history: List[Dict]
    ) -> AsyncGenerator[Dict, None]:
        """Stream general report response"""
        
        messages = [{"role": "system", "content": self.system_prompt}]
        
        for msg in history[-5:]:
            if msg['role'] in ['user', 'assistant']:
                messages.append({"role": msg['role'], "content": msg['content']})
        
        messages.append({"role": "user", "content": user_query})
        
        stream = await self.client.chat.completions.create(
            model=self.config.OPENAI_MODEL,
            messages=messages,
            temperature=0.3,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield {
                    "type": "text",
                    "content": chunk.choices[0].delta.content,
                    "agent": "REPORT_AGENT"
                }
    
    def _format_report_data(self, data_result: Dict) -> str:
        """Format data for report"""
        import json
        return json.dumps(data_result, indent=2, default=str)[:1000]  # Limit size
