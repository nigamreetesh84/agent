"""
Data Tools
Implements data querying and analysis functions
"""

import pandas as pd
import numpy as np
import json
import logging
import re
from datetime import datetime
from typing import Dict, Optional
from functools import lru_cache
from tenacity import retry, stop_after_attempt

logger = logging.getLogger(__name__)


class DataTools:
    """Tools for querying and analyzing account data"""
    
    def __init__(self, config):
        self.config = config
        self.data_file_path = config.DATA_FILE_PATH
        self._cache_timestamp = None
        self._cached_df = None
    
    @lru_cache(maxsize=1)
    def _load_dataframe(self) -> pd.DataFrame:
        """Load dataframe with caching"""
        try:
            # Support multiple file formats
            if self.data_file_path.endswith('.csv'):
                df = pd.read_csv(self.data_file_path)
            elif self.data_file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(self.data_file_path)
            elif self.data_file_path.endswith('.parquet'):
                df = pd.read_parquet(self.data_file_path)
            else:
                raise ValueError(f"Unsupported file format: {self.data_file_path}")
            
            logger.info(f"Loaded dataframe: {len(df)} rows, {len(df.columns)} columns")
            
            # Convert date columns
            date_columns = [col for col in df.columns if 'DATE' in col.upper() or 'DT' in col.upper()]
            for col in date_columns:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except:
                    pass
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            return df
        
        except Exception as e:
            logger.error(f"Error loading dataframe: {e}")
            raise
    
    def get_domestic_metadata(self, query: str = "summary") -> Dict:
        """
        Main tool function - analyzes domestic account data
        """
        try:
            df = self._load_dataframe()
            query_lower = query.lower().strip()
            
            # METADATA QUERIES
            if query_lower == "summary":
                return self._generate_summary(df)
            
            if query_lower in ["columns", "fields"]:
                return self._get_columns(df)
            
            if query_lower == "sample":
                return self._get_sample(df)
            
            # OVERDRAFT ANALYSIS
            if "overdraft" in query_lower:
                return self._analyze_overdraft(df, query_lower)
            
            # TENURE ANALYSIS
            if any(word in query_lower for word in ["tenure", "aging", "days"]):
                return self._analyze_tenure(df, query_lower)
            
            # BALANCE ANALYSIS
            if "balance" in query_lower:
                return self._analyze_balance(df, query_lower)
            
            # AGGREGATION QUERIES
            if any(word in query_lower for word in ["by country", "by region", "group by"]):
                return self._aggregate_data(df, query_lower)
            
            # TOP N QUERIES
            if "top" in query_lower or "highest" in query_lower or "largest" in query_lower:
                return self._get_top_accounts(df, query_lower)
            
            # COUNT QUERIES
            if any(word in query_lower for word in ["how many", "count", "number of"]):
                return self._count_query(df, query_lower)
            
            # Default: return suggestions
            return {
                "error": "Query not understood",
                "query_received": query,
                "suggestions": [
                    "overdraft > 1M",
                    "tenure > 90 days",
                    "total balance by country",
                    "top 10 by balance",
                    "summary"
                ]
            }
        
        except Exception as e:
            logger.error(f"Error in get_domestic_metadata: {e}")
            return {
                "error": str(e),
                "query": query
            }
    
    def _generate_summary(self, df: pd.DataFrame) -> Dict:
        """Generate dataset summary"""
        
        summary = {
            "dataset_name": "Sherlock Domestic Account Data",
            "loaded_at": datetime.now().isoformat(),
            "total_records": len(df),
            "total_columns": len(df.columns),
            "business_date": str(df['BUSINESS_DT'].max()) if 'BUSINESS_DT' in df.columns else None,
            "key_columns": {
                "identifiers": [c for c in df.columns if c in ['CASID', 'ECI', 'UCN', 'LEGAL_NAME']],
                "balances": [c for c in df.columns if 'BALANCE' in c],
                "overdraft": [c for c in df.columns if 'OVERDRAFT' in c],
                "geographic": [c for c in df.columns if 'COUNTRY' in c],
                "flags": [c for c in df.columns if 'FLAG' in c or 'IND' in c]
            }
        }
        
        # Quick stats
        if 'OVERDRAFT_INT_AMT' in df.columns:
            overdraft_df = df[df['OVERDRAFT_INT_AMT'] > 0]
            summary['quick_stats'] = {
                "total_accounts": len(df),
                "accounts_with_overdraft": len(overdraft_df),
                "total_overdraft_amount": float(overdraft_df['OVERDRAFT_INT_AMT'].sum()) if len(overdraft_df) > 0 else 0,
                "total_effective_balance": float(df['EFF_BALANCE_LCY'].sum()) if 'EFF_BALANCE_LCY' in df.columns else 0
            }
        
        return summary
    
    def _get_columns(self, df: pd.DataFrame) -> Dict:
        """Return available columns"""
        return {
            "total_columns": len(df.columns),
            "columns": df.columns.tolist()
        }
    
    def _get_sample(self, df: pd.DataFrame) -> Dict:
        """Return sample records"""
        return {
            "sample_size": min(3, len(df)),
            "sample_data": df.head(3).to_dict(orient='records')
        }
    
    def _analyze_overdraft(self, df: pd.DataFrame, query: str) -> Dict:
        """Analyze overdraft data"""
        
        if 'OVERDRAFT_INT_AMT' not in df.columns:
            return {"error": "OVERDRAFT_INT_AMT column not found"}
        
        overdraft_df = df[df['OVERDRAFT_INT_AMT'] > 0].copy()
        
        if len(overdraft_df) == 0:
            return {
                "message": "No overdraft accounts found",
                "total_accounts": 0
            }
        
        # Extract threshold if present
        threshold = self._extract_amount(query)
        
        if threshold:
            overdraft_df = overdraft_df[overdraft_df['OVERDRAFT_INT_AMT'] > threshold]
        
        # Prepare result columns
        result_cols = ['CASID', 'OVERDRAFT_INT_AMT']
        if 'LEGAL_NAME' in df.columns:
            result_cols.insert(1, 'LEGAL_NAME')
        if 'EFF_BALANCE_LCY' in df.columns:
            result_cols.append('EFF_BALANCE_LCY')
        if 'COUNTRY_CD' in df.columns:
            result_cols.append('COUNTRY_CD')
        if 'OD_Tenure' in df.columns:
            result_cols.append('OD_Tenure')
        
        # Filter to existing columns
        result_cols = [c for c in result_cols if c in overdraft_df.columns]
        
        # Calculate aggregates
        result = {
            "query": f"Accounts with overdraft > ${threshold:,.0f}" if threshold else "Overdraft analysis",
            "total_accounts": len(overdraft_df),
            "total_overdraft_amount": float(overdraft_df['OVERDRAFT_INT_AMT'].sum()),
            "average_overdraft": float(overdraft_df['OVERDRAFT_INT_AMT'].mean()),
            "max_overdraft": float(overdraft_df['OVERDRAFT_INT_AMT'].max()),
            "accounts": overdraft_df[result_cols].head(20).to_dict(orient='records')
        }
        
        # Add breakdown by size
        result['breakdown_by_size'] = {
            "over_1M": {
                "count": int((overdraft_df['OVERDRAFT_INT_AMT'] > 1_000_000).sum()),
                "sum": float(overdraft_df[overdraft_df['OVERDRAFT_INT_AMT'] > 1_000_000]['OVERDRAFT_INT_AMT'].sum())
            },
            "500K_1M": {
                "count": int(((overdraft_df['OVERDRAFT_INT_AMT'] >= 500_000) & 
                             (overdraft_df['OVERDRAFT_INT_AMT'] <= 1_000_000)).sum()),
                "sum": float(overdraft_df[(overdraft_df['OVERDRAFT_INT_AMT'] >= 500_000) & 
                            (overdraft_df['OVERDRAFT_INT_AMT'] <= 1_000_000)]['OVERDRAFT_INT_AMT'].sum())
            },
            "under_500K": {
                "count": int((overdraft_df['OVERDRAFT_INT_AMT'] < 500_000).sum()),
                "sum": float(overdraft_df[overdraft_df['OVERDRAFT_INT_AMT'] < 500_000]['OVERDRAFT_INT_AMT'].sum())
            }
        }
        
        # Top 10 accounts
        result['top_10_accounts'] = overdraft_df.nlargest(10, 'OVERDRAFT_INT_AMT')[result_cols].to_dict(orient='records')
        
        return result
    
    def _analyze_tenure(self, df: pd.DataFrame, query: str) -> Dict:
        """Analyze tenure/aging data"""
        
        if 'OD_Tenure' not in df.columns:
            return {"error": "OD_Tenure column not found"}
        
        tenure_df = df[df['OD_Tenure'].notna() & (df['OD_Tenure'] > 0)].copy()
        
        if len(tenure_df) == 0:
            return {
                "message": "No tenure data found",
                "total_accounts": 0
            }
        
        # Extract threshold
        threshold = self._extract_days(query)
        
        if threshold:
            tenure_df = tenure_df[tenure_df['OD_Tenure'] > threshold]
        
        # Prepare result columns
        result_cols = ['CASID', 'OD_Tenure']
        if 'LEGAL_NAME' in df.columns:
            result_cols.insert(1, 'LEGAL_NAME')
        if 'OVERDRAFT_INT_AMT' in df.columns:
            result_cols.append('OVERDRAFT_INT_AMT')
        if 'EFF_BALANCE_LCY' in df.columns:
            result_cols.append('EFF_BALANCE_LCY')
        
        result_cols = [c for c in result_cols if c in tenure_df.columns]
        
        result = {
            "query": f"Accounts with tenure > {threshold} days" if threshold else "Tenure analysis",
            "total_accounts": len(tenure_df),
            "average_tenure": float(tenure_df['OD_Tenure'].mean()),
            "max_tenure": float(tenure_df['OD_Tenure'].max()),
            "accounts": tenure_df[result_cols].head(20).to_dict(orient='records')
        }
        
        # Aging breakdown
        result['aging_breakdown'] = {
            "0_30_days": int((tenure_df['OD_Tenure'] <= 30).sum()),
            "31_60_days": int(((tenure_df['OD_Tenure'] > 30) & (tenure_df['OD_Tenure'] <= 60)).sum()),
            "61_90_days": int(((tenure_df['OD_Tenure'] > 60) & (tenure_df['OD_Tenure'] <= 90)).sum()),
            "91_180_days": int(((tenure_df['OD_Tenure'] > 90) & (tenure_df['OD_Tenure'] <= 180)).sum()),
            "over_180_days": int((tenure_df['OD_Tenure'] > 180).sum())
        }
        
        return result
    
    def _analyze_balance(self, df: pd.DataFrame, query: str) -> Dict:
        """Analyze balance data"""
        
        balance_col = 'EFF_BALANCE_LCY' if 'EFF_BALANCE_LCY' in df.columns else None
        
        if not balance_col:
            return {"error": "Balance column not found"}
        
        result = {
            "total_balance": float(df[balance_col].sum()),
            "average_balance": float(df[balance_col].mean()),
            "median_balance": float(df[balance_col].median()),
            "accounts_with_positive_balance": int((df[balance_col] > 0).sum()),
            "accounts_with_negative_balance": int((df[balance_col] < 0).sum())
        }
        
        return result
    
    def _aggregate_data(self, df: pd.DataFrame, query: str) -> Dict:
        """Aggregate data by specified dimension"""
        
        # Determine grouping column
        if "country" in query:
            group_col = 'COUNTRY_CD'
        elif "region" in query:
            group_col = 'REGION'  # if exists
        else:
            return {"error": "Aggregation dimension not understood"}
        
        if group_col not in df.columns:
            return {"error": f"{group_col} column not found"}
        
        # Determine aggregation column
        if "balance" in query:
            agg_col = 'EFF_BALANCE_LCY'
        elif "overdraft" in query:
            agg_col = 'OVERDRAFT_INT_AMT'
        else:
            agg_col = 'EFF_BALANCE_LCY'  # default
        
        if agg_col not in df.columns:
            return {"error": f"{agg_col} column not found"}
        
        # Aggregate
        grouped = df.groupby(group_col)[agg_col].agg(['sum', 'count', 'mean']).reset_index()
        grouped.columns = [group_col, 'total', 'count', 'average']
        
        # Sort by total descending
        grouped = grouped.sort_values('total', ascending=False)
        
        return {
            "aggregation": f"By {group_col}",
            "metric": agg_col,
            "results": grouped.to_dict(orient='records')
        }
    
    def _get_top_accounts(self, df: pd.DataFrame, query: str) -> Dict:
        """Get top N accounts"""
        
        # Extract N
        n = self._extract_number(query, default=10)
        
        # Determine sort column
        if "balance" in query:
            sort_col = 'EFF_BALANCE_LCY'
        elif "overdraft" in query:
            sort_col = 'OVERDRAFT_INT_AMT'
        else:
            sort_col = 'EFF_BALANCE_LCY'
        
        if sort_col not in df.columns:
            return {"error": f"{sort_col} column not found"}
        
        top_df = df.nlargest(n, sort_col)
        
        result_cols = ['CASID', sort_col]
        if 'LEGAL_NAME' in df.columns:
            result_cols.insert(1, 'LEGAL_NAME')
        
        result_cols = [c for c in result_cols if c in top_df.columns]
        
        return {
            "query": f"Top {n} accounts by {sort_col}",
            "count": len(top_df),
            "accounts": top_df[result_cols].to_dict(orient='records')
        }
    
    def _count_query(self, df: pd.DataFrame, query: str) -> Dict:
        """Handle count queries"""
        
        if "overdraft" in query:
            count = int((df['OVERDRAFT_INT_AMT'] > 0).sum()) if 'OVERDRAFT_INT_AMT' in df.columns else 0
            return {
                "count": count,
                "description": "Accounts with overdraft"
            }
        
        return {
            "count": len(df),
            "description": "Total accounts"
        }
    
    def _extract_amount(self, query: str) -> Optional[float]:
        """Extract dollar amount from query"""
        # Match patterns like $1M, 1m, 1000000, $1,000,000
        patterns = [
            r'\$?([\d,]+(?:\.\d+)?)\s*([kmb])',  # $1M, 1m, 1k
            r'\$?([\d,]+)'  # $1000000, 1,000,000
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                amount = float(match.group(1).replace(',', ''))
                if len(match.groups()) > 1:
                    unit = match.group(2).lower()
                    if unit == 'k':
                        amount *= 1_000
                    elif unit == 'm':
                        amount *= 1_000_000
                    elif unit == 'b':
                        amount *= 1_000_000_000
                return amount
        
        return None
    
    def _extract_days(self, query: str) -> Optional[int]:
        """Extract day count from query"""
        match = re.search(r'(\d+)\s*day', query, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    
    def _extract_number(self, query: str, default: int = 10) -> int:
        """Extract number from query"""
        match = re.search(r'top\s+(\d+)|(\d+)\s+top', query, re.IGNORECASE)
        if match:
            return int(match.group(1) or match.group(2))
        return default