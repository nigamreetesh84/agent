"""
Generate sample data for testing
Run this if you don't have real data yet
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_sample_data(n_records=100):
    """Generate sample domestic account data"""
    
    np.random.seed(42)
    
    data = {
        'CASID': [f'CASID{i:06d}' for i in range(n_records)],
        'LEGAL_NAME': [f'Company {i}' for i in range(n_records)],
        'ECI': [f'ECI{i:04d}' for i in range(n_records)],
        'UCN': [f'UCN{i:05d}' for i in range(n_records)],
        'COUNTRY_CD': np.random.choice(['US', 'UK', 'FR', 'DE', 'JP'], n_records),
        'EFF_BALANCE_LCY': np.random.uniform(-1000000, 5000000, n_records),
        'EFF_BALANCE_DBT': np.random.uniform(0, 100000, n_records),
        'EFF_BALANCE_CRDT': np.random.uniform(0, 100000, n_records),
        'MTD_BALANCE_LCY': np.random.uniform(-500000, 3000000, n_records),
        'OVERDRAFT_INT_AMT': np.random.choice([0] * 60 + list(np.random.uniform(10000, 2000000, 40))),
        'OD_Tenure': np.random.choice([0] * 60 + list(np.random.randint(1, 365, 40))),
        'OD_RATE': np.random.uniform(0, 8, n_records),
        'OVERDRAFT_LIMIT_AMT': np.random.uniform(0, 3000000, n_records),
        'BUSINESS_DT': [datetime.now() - timedelta(days=np.random.randint(0, 30)) for _ in range(n_records)],
        'ERISA_IND': np.random.choice(['Y', 'N'], n_records, p=[0.1, 0.9]),
        'CHAD_LAD_FLAG': np.random.choice(['Y', 'N'], n_records, p=[0.05, 0.95])
    }
    
    df = pd.DataFrame(data)
    
    # Save to Excel
    output_path = 'data/domestic_accounts.xlsx'
    df.to_excel(output_path, index=False)
    print(f"✅ Sample data generated: {output_path}")
    print(f"📊 Generated {n_records} records")
    print(f"💰 Accounts with overdraft: {(df['OVERDRAFT_INT_AMT'] > 0).sum()}")
    print(f"📈 Total overdraft amount: ${df['OVERDRAFT_INT_AMT'].sum():,.2f}")

if __name__ == '__main__':
    generate_sample_data(100)
