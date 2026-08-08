#!/usr/bin/env python3
"""
ODIN ImportGenius BOL (Bill of Lading) Parser
Extracts supply chain signals from ImportGenius CSV exports

Signals extracted:
- api_shipment_volume: Active Pharmaceutical Ingredient shipment counts
- cmo_relationships: Contract Manufacturing Organization activity  
- manufacturing_scale_up: Recent shipment increases (pre-PDUFA)
- geographic_risk_score: Sourcing from FDA warning-listed regions
- shipment_timing_score: Shipment patterns relative to PDUFA date

Usage:
    python ODIN_IMPORTGENIUS_BOL_PARSER.py -i bol_exports/ -p pdufa_dataset.csv -o enriched_bol_signals.csv
"""

import pandas as pd
import numpy as np
import argparse
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

# FDA Warning-listed regions (high manufacturing risk)
FDA_WARNING_REGIONS = {
    'china': ['china', 'cn', 'prc', 'shanghai', 'beijing', 'guangzhou', 'shenzhen', 'wuhan', 'hangzhou'],
    'india': ['india', 'in', 'mumbai', 'hyderabad', 'ahmedabad', 'pune', 'chennai', 'bangalore'],
    'other_high_risk': ['bangladesh', 'pakistan', 'vietnam']
}

# Common CMO (Contract Manufacturing Organization) keywords
CMO_KEYWORDS = [
    'lonza', 'catalent', 'thermo fisher', 'wuxi', 'samsung biologics', 
    'boehringer ingelheim', 'fujifilm diosynth', 'patheon', 'siegfried',
    'recipharm', 'fareva', 'corden pharma', 'almac', 'pci pharma',
    'ajinomoto bio-pharma', 'cambrex', 'hovione', 'polpharma', 'jubilant',
    'aenova', 'delpharm', 'euroapi', 'sterling pharma'
]

# API (Active Pharmaceutical Ingredient) keywords
API_KEYWORDS = [
    'api', 'active pharmaceutical', 'drug substance', 'bulk drug',
    'intermediate', 'raw material', 'excipient', 'reagent',
    'pharmaceutical grade', 'gmp grade', 'usp grade'
]

# Pharma/Biotech product indicators
PHARMA_KEYWORDS = [
    'pharmaceutical', 'biologic', 'vaccine', 'antibody', 'protein',
    'peptide', 'enzyme', 'hormone', 'medicine', 'drug', 'therapeutic',
    'injectable', 'tablet', 'capsule', 'vial', 'syringe', 'infusion'
]


def clean_company_name(name: str) -> str:
    """Standardize company names for matching"""
    if pd.isna(name):
        return ""
    name = str(name).lower()
    # Remove common suffixes
    for suffix in [' inc', ' inc.', ' corp', ' corp.', ' ltd', ' ltd.', ' llc', 
                   ' plc', ' co.', ' company', ' pharmaceuticals', ' therapeutics',
                   ' biosciences', ' biotech', ' biotechnology']:
        name = name.replace(suffix, '')
    # Remove special characters
    name = re.sub(r'[^\w\s]', '', name)
    return name.strip()


def extract_drug_name(asset: str) -> str:
    """Extract clean drug name from asset field"""
    if pd.isna(asset):
        return ""
    # Remove parenthetical generic names
    drug = re.sub(r'\s*\([^)]*\)', '', str(asset))
    # Remove trial names like "- ALLELE"
    drug = re.sub(r'\s*-\s*\([^)]*\)', '', drug)
    drug = re.sub(r'\s*-\s*[A-Z]{2,}.*$', '', drug)
    return drug.strip().lower()


def is_pharma_shipment(product_desc: str) -> bool:
    """Check if product description indicates pharmaceutical shipment"""
    if pd.isna(product_desc):
        return False
    desc_lower = str(product_desc).lower()
    return any(kw in desc_lower for kw in PHARMA_KEYWORDS)


def is_api_shipment(product_desc: str) -> bool:
    """Check if product description indicates API shipment"""
    if pd.isna(product_desc):
        return False
    desc_lower = str(product_desc).lower()
    return any(kw in desc_lower for kw in API_KEYWORDS)


def is_cmo_shipper(shipper_name: str) -> bool:
    """Check if shipper is a known CMO"""
    if pd.isna(shipper_name):
        return False
    shipper_lower = str(shipper_name).lower()
    return any(cmo in shipper_lower for cmo in CMO_KEYWORDS)


def get_geographic_risk(origin_country: str) -> Tuple[float, str]:
    """
    Assess geographic manufacturing risk based on origin
    Returns (risk_score, risk_category)
    """
    if pd.isna(origin_country):
        return 0.5, 'unknown'
    
    origin_lower = str(origin_country).lower()
    
    # Check China
    if any(region in origin_lower for region in FDA_WARNING_REGIONS['china']):
        return 0.8, 'china'
    
    # Check India
    if any(region in origin_lower for region in FDA_WARNING_REGIONS['india']):
        return 0.7, 'india'
    
    # Check other high-risk
    if any(region in origin_lower for region in FDA_WARNING_REGIONS['other_high_risk']):
        return 0.6, 'other_high_risk'
    
    # Low risk (US, EU, Japan, etc.)
    low_risk = ['united states', 'usa', 'us', 'germany', 'switzerland', 
                'ireland', 'japan', 'uk', 'united kingdom', 'france', 'belgium']
    if any(region in origin_lower for region in low_risk):
        return 0.2, 'low_risk'
    
    return 0.5, 'medium_risk'


def parse_bol_file(filepath: str) -> pd.DataFrame:
    """
    Parse a single ImportGenius BOL export file
    Handles various CSV formats from ImportGenius
    """
    # Try different encodings
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv(filepath, encoding=encoding)
            break
        except:
            continue
    else:
        print(f"  Warning: Could not read {filepath}")
        return pd.DataFrame()
    
    # Standardize column names (ImportGenius has various formats)
    col_mapping = {
        # Consignee (importer)
        'consignee': 'consignee',
        'consignee_name': 'consignee',
        'consigneename': 'consignee',
        'importer': 'consignee',
        'importer_name': 'consignee',
        
        # Shipper (exporter)
        'shipper': 'shipper',
        'shipper_name': 'shipper',
        'shippername': 'shipper',
        'exporter': 'shipper',
        'exporter_name': 'shipper',
        
        # Product
        'product': 'product',
        'product_description': 'product',
        'productdescription': 'product',
        'description': 'product',
        'goods_description': 'product',
        
        # Origin
        'origin': 'origin_country',
        'origin_country': 'origin_country',
        'origincountry': 'origin_country',
        'country_of_origin': 'origin_country',
        'shipper_country': 'origin_country',
        
        # Date
        'arrival_date': 'arrival_date',
        'arrivaldate': 'arrival_date',
        'date': 'arrival_date',
        'shipment_date': 'arrival_date',
        
        # Quantity/Weight
        'quantity': 'quantity',
        'qty': 'quantity',
        'weight': 'weight',
        'weight_kg': 'weight',
        'gross_weight': 'weight',
        
        # Port
        'port': 'port',
        'port_of_entry': 'port',
        'destination_port': 'port',
        'us_port': 'port'
    }
    
    # Rename columns
    df.columns = df.columns.str.lower().str.strip()
    for old_col, new_col in col_mapping.items():
        if old_col in df.columns and new_col not in df.columns:
            df = df.rename(columns={old_col: new_col})
    
    return df


def calculate_bol_signals(bol_df: pd.DataFrame, company: str, drug: str, 
                          pdufa_date: datetime, lookback_months: int = 18) -> Dict:
    """
    Calculate BOL-derived signals for a single PDUFA event
    
    Returns dict with:
    - bol_total_shipments: Total relevant shipments found
    - bol_api_shipments: API-specific shipment count
    - bol_cmo_shipments: Shipments from known CMOs
    - bol_geographic_risk: Weighted average geographic risk
    - bol_scale_up_ratio: Recent vs historical shipment ratio
    - bol_china_pct: Percentage of shipments from China
    - bol_india_pct: Percentage of shipments from India
    """
    signals = {
        'bol_total_shipments': 0,
        'bol_api_shipments': 0,
        'bol_cmo_shipments': 0,
        'bol_geographic_risk': None,
        'bol_scale_up_ratio': None,
        'bol_china_pct': None,
        'bol_india_pct': None,
        'bol_data_found': False
    }
    
    if bol_df.empty:
        return signals
    
    company_clean = clean_company_name(company)
    drug_clean = extract_drug_name(drug)
    
    # Filter to relevant shipments (by consignee matching company)
    if 'consignee' not in bol_df.columns:
        return signals
    
    bol_df['consignee_clean'] = bol_df['consignee'].apply(clean_company_name)
    
    # Match by company name
    mask = bol_df['consignee_clean'].str.contains(company_clean, na=False)
    
    # Also try to match by drug name in product description
    if 'product' in bol_df.columns and drug_clean:
        drug_mask = bol_df['product'].str.lower().str.contains(drug_clean, na=False)
        mask = mask | drug_mask
    
    relevant_df = bol_df[mask].copy()
    
    if relevant_df.empty:
        return signals
    
    signals['bol_data_found'] = True
    
    # Parse dates and filter to lookback period
    if 'arrival_date' in relevant_df.columns:
        relevant_df['arrival_date'] = pd.to_datetime(relevant_df['arrival_date'], errors='coerce')
        cutoff_date = pdufa_date - timedelta(days=lookback_months * 30)
        relevant_df = relevant_df[
            (relevant_df['arrival_date'] >= cutoff_date) & 
            (relevant_df['arrival_date'] < pdufa_date)
        ]
    
    if relevant_df.empty:
        return signals
    
    # Count total shipments
    signals['bol_total_shipments'] = len(relevant_df)
    
    # Count API shipments
    if 'product' in relevant_df.columns:
        signals['bol_api_shipments'] = relevant_df['product'].apply(is_api_shipment).sum()
    
    # Count CMO shipments
    if 'shipper' in relevant_df.columns:
        signals['bol_cmo_shipments'] = relevant_df['shipper'].apply(is_cmo_shipper).sum()
    
    # Calculate geographic risk
    if 'origin_country' in relevant_df.columns:
        geo_risks = relevant_df['origin_country'].apply(lambda x: get_geographic_risk(x)[0])
        signals['bol_geographic_risk'] = round(geo_risks.mean(), 3) if len(geo_risks) > 0 else None
        
        # Calculate China/India percentages
        geo_categories = relevant_df['origin_country'].apply(lambda x: get_geographic_risk(x)[1])
        total = len(geo_categories)
        if total > 0:
            signals['bol_china_pct'] = round((geo_categories == 'china').sum() / total * 100, 1)
            signals['bol_india_pct'] = round((geo_categories == 'india').sum() / total * 100, 1)
    
    # Calculate scale-up ratio (last 6 months vs prior 12 months)
    if 'arrival_date' in relevant_df.columns:
        six_months_ago = pdufa_date - timedelta(days=180)
        eighteen_months_ago = pdufa_date - timedelta(days=540)
        
        recent = relevant_df[relevant_df['arrival_date'] >= six_months_ago]
        historical = relevant_df[
            (relevant_df['arrival_date'] >= eighteen_months_ago) & 
            (relevant_df['arrival_date'] < six_months_ago)
        ]
        
        recent_count = len(recent)
        historical_count = len(historical)
        
        if historical_count > 0:
            # Normalize to same time period (6 months)
            historical_normalized = historical_count / 2  # 12 months -> 6 months equivalent
            if historical_normalized > 0:
                signals['bol_scale_up_ratio'] = round(recent_count / historical_normalized, 2)
    
    return signals


def load_all_bol_exports(bol_dir: str) -> pd.DataFrame:
    """Load and combine all BOL export files from a directory"""
    all_dfs = []
    
    bol_path = Path(bol_dir)
    if not bol_path.exists():
        print(f"Warning: BOL directory not found: {bol_dir}")
        return pd.DataFrame()
    
    # Find all CSV files
    csv_files = list(bol_path.glob('*.csv')) + list(bol_path.glob('*.CSV'))
    
    print(f"Found {len(csv_files)} BOL export files")
    
    for csv_file in csv_files:
        print(f"  Loading: {csv_file.name}")
        df = parse_bol_file(str(csv_file))
        if not df.empty:
            df['source_file'] = csv_file.name
            all_dfs.append(df)
    
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        print(f"Total BOL records loaded: {len(combined)}")
        return combined
    
    return pd.DataFrame()


def enrich_pdufa_with_bol(pdufa_df: pd.DataFrame, bol_df: pd.DataFrame, 
                          verbose: bool = False) -> pd.DataFrame:
    """
    Enrich PDUFA dataset with BOL-derived signals
    """
    # Initialize new columns
    bol_columns = [
        'bol_total_shipments', 'bol_api_shipments', 'bol_cmo_shipments',
        'bol_geographic_risk', 'bol_scale_up_ratio', 'bol_china_pct', 
        'bol_india_pct', 'bol_data_found'
    ]
    
    for col in bol_columns:
        pdufa_df[col] = None
    
    if bol_df.empty:
        print("No BOL data available - returning PDUFA with empty BOL columns")
        return pdufa_df
    
    # Process each PDUFA event
    total = len(pdufa_df)
    for idx, row in pdufa_df.iterrows():
        if verbose and idx % 50 == 0:
            print(f"Processing {idx}/{total}...")
        
        # Parse PDUFA date
        try:
            pdufa_date = pd.to_datetime(row['catalyst_date'])
        except:
            continue
        
        # Calculate signals
        signals = calculate_bol_signals(
            bol_df=bol_df,
            company=row.get('company', ''),
            drug=row.get('asset', ''),
            pdufa_date=pdufa_date
        )
        
        # Update row
        for col, val in signals.items():
            pdufa_df.at[idx, col] = val
    
    return pdufa_df


def generate_search_queries(pdufa_df: pd.DataFrame, days_ahead: int = 60,
                           prioritize_risk: bool = True) -> List[Dict]:
    """
    Generate prioritized ImportGenius search queries for upcoming catalysts
    
    Priority order:
    1. Upcoming PDUFAs with manufacturing_risk flag
    2. Upcoming PDUFAs with inexperienced sponsors
    3. Upcoming PDUFAs (general)
    4. High-value/interesting catalysts
    """
    # Convert dates
    pdufa_df['catalyst_date'] = pd.to_datetime(pdufa_df['catalyst_date'], errors='coerce')
    
    today = datetime.now()
    cutoff = today + timedelta(days=days_ahead)
    
    # Filter to upcoming catalysts
    upcoming = pdufa_df[
        (pdufa_df['catalyst_date'] >= today) & 
        (pdufa_df['catalyst_date'] <= cutoff)
    ].copy()
    
    # Sort by priority
    upcoming['priority_score'] = 0
    
    # Manufacturing risk = highest priority
    if 'manufacturing_risk' in upcoming.columns:
        upcoming.loc[upcoming['manufacturing_risk'] == True, 'priority_score'] += 100
    
    # Inexperienced sponsor = high priority
    if 'experienced_sponsor' in upcoming.columns:
        upcoming.loc[upcoming['experienced_sponsor'] == False, 'priority_score'] += 50
    
    # First cycle (no prior approval for this drug) = medium priority
    if 'first_cycle' in upcoming.columns:
        upcoming.loc[upcoming['first_cycle'] == True, 'priority_score'] += 25
    
    # Small molecule = slightly higher (more supply chain complexity)
    if 'modality' in upcoming.columns:
        upcoming.loc[upcoming['modality'] == 'Small Molecule', 'priority_score'] += 10
    
    # Sort by priority then date
    upcoming = upcoming.sort_values(['priority_score', 'catalyst_date'], 
                                     ascending=[False, True])
    
    # Generate search queries
    queries = []
    for idx, row in upcoming.iterrows():
        company = str(row.get('company', '')).strip()
        asset = str(row.get('asset', '')).strip()
        drug_clean = re.sub(r'\s*\([^)]*\)', '', asset).strip()  # Remove (generic)
        ticker = str(row.get('ticker', '')).strip()
        pdufa_date = row['catalyst_date'].strftime('%Y-%m-%d') if pd.notna(row['catalyst_date']) else 'TBD'
        
        # Clean company name for search
        company_search = re.sub(r'\s+(Inc\.|Corp\.|Ltd\.|LLC|PLC|Co\.).*$', '', company, flags=re.I).strip()
        
        # Determine why this is prioritized
        priority_reasons = []
        if row.get('manufacturing_risk') == True:
            priority_reasons.append('MFG_RISK')
        if row.get('experienced_sponsor') == False:
            priority_reasons.append('NEW_SPONSOR')
        if row.get('first_cycle') == True:
            priority_reasons.append('FIRST_CYCLE')
        
        queries.append({
            'priority': len(queries) + 1,
            'ticker': ticker,
            'company': company,
            'company_search': company_search,
            'drug': drug_clean,
            'pdufa_date': pdufa_date,
            'priority_reasons': ', '.join(priority_reasons) if priority_reasons else 'UPCOMING',
            'search_query_company': f'consname contains {company_search}',
            'search_query_product': f'product contains {drug_clean}' if drug_clean else '',
            'therapeutic_area': row.get('therapeutic_area', ''),
            'modality': row.get('modality', '')
        })
    
    return queries


def export_search_list(queries: List[Dict], output_path: str):
    """Export search queries to CSV for manual ImportGenius lookup"""
    df = pd.DataFrame(queries)
    df.to_csv(output_path, index=False)
    print(f"Exported {len(queries)} search queries to {output_path}")
    return df


def main():
    parser = argparse.ArgumentParser(description='ODIN ImportGenius BOL Parser')
    parser.add_argument('-i', '--input', help='Directory containing BOL CSV exports')
    parser.add_argument('-p', '--pdufa', required=True, help='PDUFA dataset CSV')
    parser.add_argument('-o', '--output', help='Output enriched CSV')
    parser.add_argument('-s', '--searches', help='Output search queries CSV')
    parser.add_argument('--days', type=int, default=60, help='Days ahead for search queries')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--generate-searches', action='store_true', 
                        help='Only generate search queries, no BOL parsing')
    
    args = parser.parse_args()
    
    # Load PDUFA dataset
    print(f"Loading PDUFA dataset: {args.pdufa}")
    pdufa_df = pd.read_csv(args.pdufa)
    print(f"Loaded {len(pdufa_df)} PDUFA events")
    
    # Generate search queries if requested
    if args.generate_searches or args.searches:
        searches_output = args.searches or 'ODIN_IMPORTGENIUS_SEARCHES.csv'
        print(f"\nGenerating ImportGenius search queries ({args.days} days ahead)...")
        queries = generate_search_queries(pdufa_df, days_ahead=args.days)
        export_search_list(queries, searches_output)
        
        # Print top priorities
        print(f"\n{'='*80}")
        print("TOP PRIORITY SEARCHES (next {args.days} days):")
        print(f"{'='*80}")
        for q in queries[:20]:
            print(f"{q['priority']:3d}. [{q['ticker']:6s}] {q['drug'][:30]:<30s} | PDUFA: {q['pdufa_date']} | {q['priority_reasons']}")
            print(f"      Company search: {q['search_query_company']}")
            if q['search_query_product']:
                print(f"      Product search: {q['search_query_product']}")
            print()
    
    # Parse BOL data if provided
    if args.input and not args.generate_searches:
        print(f"\nLoading BOL exports from: {args.input}")
        bol_df = load_all_bol_exports(args.input)
        
        if not bol_df.empty:
            print(f"\nEnriching PDUFA data with BOL signals...")
            enriched_df = enrich_pdufa_with_bol(pdufa_df, bol_df, verbose=args.verbose)
            
            # Save output
            output_path = args.output or 'ODIN_PDUFA_BOL_ENRICHED.csv'
            enriched_df.to_csv(output_path, index=False)
            print(f"\nSaved enriched dataset to: {output_path}")
            
            # Summary stats
            bol_found = enriched_df['bol_data_found'].sum()
            print(f"\nBOL Signal Summary:")
            print(f"  Events with BOL data: {bol_found}/{len(enriched_df)}")
            if bol_found > 0:
                print(f"  Avg shipments: {enriched_df['bol_total_shipments'].mean():.1f}")
                print(f"  Avg API shipments: {enriched_df['bol_api_shipments'].mean():.1f}")
                print(f"  Avg CMO shipments: {enriched_df['bol_cmo_shipments'].mean():.1f}")
    
    print("\nDone!")


if __name__ == '__main__':
    main()
