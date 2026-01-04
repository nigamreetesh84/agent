"""
Visualization Agent (Simplified)
"""

import json
import logging
import uuid
from typing import Dict, List, Generator

logger = logging.getLogger(__name__)


class VisualizationAgent:
    """Creates data visualizations"""
    
    def __init__(self, config, client):
        self.config = config
        self.client = client
        
        # Minimal prompt
        self.system_prompt = """Create chart specs. Output JSON only:
{"chart_type": "bar|pie|table", "title": "...", "description": "...", "data": [...]}

bar: for comparisons, pie: for proportions, table: for details"""
    
    def create_visualization(
        self,
        user_query: str,
        data_result: Dict,
        history: List[Dict]
    ) -> Generator[Dict, None, None]:
        """Generate visualization"""
        
        try:
            yield {"type": "status", "message": "Creating chart...", "agent": "VIZ"}
            
            # Generate viz spec
            viz_spec = self._generate_viz_spec(user_query, data_result)
            
            if viz_spec:
                viz_id = str(uuid.uuid4())
                
                yield {
                    "type": "visualization",
                    "viz_id": viz_id,
                    "viz_data": viz_spec,
                    "agent": "VIZ"
                }
                
                yield {
                    "type": "text",
                    "content": f"\n\n📊 {viz_spec['title']}",
                    "agent": "VIZ"
                }
        
        except Exception as e:
            logger.error(f"Viz error: {e}")
            yield {"type": "text", "content": "\n\nVisualization not available.", "agent": "VIZ"}
    
    def _generate_viz_spec(self, user_query: str, data_result: Dict) -> Dict:
        """Generate chart spec"""
        
        try:
            # Summarize data for GPT
            summary = {
                "type": data_result.get('query_type', 'unknown'),
                "has_accounts": 'accounts' in data_result,
                "has_breakdown": 'breakdown_by_size' in data_result or 'aging_breakdown' in data_result,
                "total_records": len(data_result.get('accounts', []))
            }
            
            response = self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Query: {user_query}\nData: {json.dumps(summary)}\nCreate chart spec."}
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            viz_spec = json.loads(response.choices[0].message.content)
            
            # Transform data
            viz_spec = self._transform_data(viz_spec, data_result)
            
            return viz_spec
        
        except Exception as e:
            logger.error(f"Viz spec error: {e}")
            return None
    
    def _transform_data(self, viz_spec: Dict, data_result: Dict) -> Dict:
        """Transform data for charts"""
        
        chart_type = viz_spec.get('chart_type', 'bar')
        
        try:
            if chart_type == 'bar':
                # Use breakdown if available
                if 'breakdown_by_size' in data_result:
                    breakdown = data_result['breakdown_by_size']
                    viz_spec['data'] = [
                        {"category": k, "value": v['count']}
                        for k, v in breakdown.items()
                    ]
                elif 'aging_breakdown' in data_result:
                    breakdown = data_result['aging_breakdown']
                    viz_spec['data'] = [
                        {"category": k, "value": v}
                        for k, v in breakdown.items()
                    ]
                elif 'top_10_accounts' in data_result:
                    accounts = data_result['top_10_accounts']
                    viz_spec['data'] = [
                        {
                            "category": acc.get('LEGAL_NAME', acc.get('CASID', f"Account {i}")),
                            "value": acc.get('OVERDRAFT_INT_AMT', acc.get('EFF_BALANCE_LCY', 0))
                        }
                        for i, acc in enumerate(accounts[:10])
                    ]
            
            elif chart_type == 'pie':
                if 'breakdown_by_size' in data_result:
                    breakdown = data_result['breakdown_by_size']
                    viz_spec['data'] = [
                        {"name": k, "value": v['count']}
                        for k, v in breakdown.items()
                    ]
            
            elif chart_type == 'table':
                if 'accounts' in data_result:
                    viz_spec['data'] = data_result['accounts'][:20]
        
        except Exception as e:
            logger.error(f"Data transform error: {e}")
            viz_spec['data'] = []
        
        return viz_spec