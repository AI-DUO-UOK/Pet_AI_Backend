"""
Content Cleaning Statistics Analyzer
Shows detailed before/after metrics for cleaned RAG files
"""

import json
from pathlib import Path
from collections import defaultdict

# Paths
BASE_DIR = Path(__file__).resolve().parent
RAG_ORIGINAL = BASE_DIR / "chatbot" / "rag_output"
RAG_CLEANED = BASE_DIR / "chatbot" / "rag_output_cleaned"
REPORT_FILE = RAG_CLEANED / "cleaning_report.json"

def analyze_statistics():
    """Generate detailed statistics from cleaning report."""
    
    if not REPORT_FILE.exists():
        print(f"Report file not found: {REPORT_FILE}")
        return
    
    with open(REPORT_FILE) as f:
        data = json.load(f)
    
    print("\n" + "="*100)
    print("  CONTENT CLEANING STATISTICS - DETAILED ANALYSIS")
    print("="*100 + "\n")
    
    # Overall summary
    print("OVERALL SUMMARY")
    print("-" * 100)
    total_files = data['total_files']
    successful = data['successfully_cleaned']
    input_total = data['total_input_chars']
    output_total = data['total_output_chars']
    compression = ((input_total - output_total) / input_total * 100) if input_total > 0 else 0
    
    print(f"Total Files:              {total_files}")
    print(f"Successfully Cleaned:     {successful} ({successful/total_files*100:.1f}%)")
    print(f"Input Characters:         {input_total:,}")
    print(f"Output Characters:        {output_total:,}")
    print(f"Characters Removed:       {input_total - output_total:,}")
    print(f"Overall Compression:      {compression:.1f}%")
    print()
    
    # Categorize by removal rate
    files_list = data['files'].items()
    removal_rates = [(name, info['compression_ratio']) for name, info in files_list]
    removal_rates.sort(key=lambda x: x[1], reverse=True)
    
    # Top removed (boilerplate-heavy files)
    print("TOP 10 FILES BY BOILERPLATE REMOVAL")
    print("-" * 100)
    print(f"{'Rank':<5} {'File':<60} {'Removed':<10} {'In':<10} {'Out':<10}")
    print("-" * 100)
    
    for i, (filename, ratio) in enumerate(removal_rates[:10], 1):
        info = data['files'][filename]
        in_chars = info['input_chars']
        out_chars = info['output_chars']
        print(f"{i:<5} {filename[:59]:<60} {ratio:>8.1f}% {in_chars:>9,} {out_chars:>9,}")
    
    print()
    
    # Content-heavy files (minimal removal)
    print("TOP 10 CONTENT-HEAVY FILES (Minimal Removal)")
    print("-" * 100)
    print(f"{'Rank':<5} {'File':<60} {'Removed':<10} {'In':<10} {'Out':<10}")
    print("-" * 100)
    
    for i, (filename, ratio) in enumerate(reversed(removal_rates[-10:]), 1):
        info = data['files'][filename]
        in_chars = info['input_chars']
        out_chars = info['output_chars']
        print(f"{i:<5} {filename[:59]:<60} {ratio:>8.1f}% {in_chars:>9,} {out_chars:>9,}")
    
    print()
    
    # Distribution analysis
    print("DISTRIBUTION ANALYSIS")
    print("-" * 100)
    
    # Group by removal percentage ranges
    ranges = {
        '0-5%': [r for _, r in removal_rates if 0 <= r < 5],
        '5-10%': [r for _, r in removal_rates if 5 <= r < 10],
        '10-15%': [r for _, r in removal_rates if 10 <= r < 15],
        '15-20%': [r for _, r in removal_rates if 15 <= r < 20],
        '20-30%': [r for _, r in removal_rates if 20 <= r < 30],
        '30-50%': [r for _, r in removal_rates if 30 <= r < 50],
        '50%+': [r for _, r in removal_rates if r >= 50],
    }
    
    print(f"{'Removal Range':<20} {'Files':<10} {'Percentage':<15}")
    print("-" * 100)
    
    for range_name, items in ranges.items():
        if items:
            percentage = len(items) / total_files * 100
            print(f"{range_name:<20} {len(items):<10} {percentage:>6.1f}%")
    
    print()
    
    # Average stats by category
    print("CONTENT CATEGORY ANALYSIS")
    print("-" * 100)
    
    # Categorize by file type/content
    categories = defaultdict(list)
    for filename, ratio in removal_rates:
        if '__' not in filename:
            category = "Index Pages"
        elif 'behavior' in filename:
            category = "Behavior"
        elif 'blood-disorders' in filename:
            category = "Blood Disorders"
        elif 'skin-disorders' in filename:
            category = "Skin Disorders"
        elif 'eye' in filename:
            category = "Eye Disorders"
        else:
            category = "Other"
        
        info = data['files'][filename]
        categories[category].append({
            'ratio': ratio,
            'input': info['input_chars'],
            'output': info['output_chars']
        })
    
    print(f"{'Category':<25} {'Files':<10} {'Avg Removal':<15} {'Avg Size':<15}")
    print("-" * 100)
    
    for category in sorted(categories.keys()):
        items = categories[category]
        avg_removal = sum(item['ratio'] for item in items) / len(items)
        avg_size = sum(item['output'] for item in items) / len(items)
        print(f"{category:<25} {len(items):<10} {avg_removal:>6.1f}% {avg_size:>13,.0f} chars")
    
    print()
    print("="*100)
    print()
    
    # Show specific examples
    print("EXAMPLE: ANEMIA ARTICLE CLEANING")
    print("-" * 100)
    
    anemia_file = "www.msdvetmanual.com__cat-owners__blood-disorders-of-cats__anemia-in-cats.txt"
    if anemia_file in data['files']:
        info = data['files'][anemia_file]
        print(f"File: {anemia_file}")
        print(f"Input:  {info['input_chars']:,} characters")
        print(f"Output: {info['output_chars']:,} characters")
        print(f"Removed: {info['compression_ratio']:.1f}%")
        print()
        
        # Show actual content
        original_file = RAG_ORIGINAL / anemia_file
        cleaned_file = RAG_CLEANED / anemia_file
        
        if original_file.exists() and cleaned_file.exists():
            original_text = original_file.read_text()[:200]
            cleaned_text = cleaned_file.read_text()[:200]
            
            print("BEFORE (first 200 chars):")
            print(original_text)
            print("\nAFTER (first 200 chars):")
            print(cleaned_text)
    
    print()
    print("="*100)
    print("Analysis complete!")
    print()

if __name__ == "__main__":
    analyze_statistics()
