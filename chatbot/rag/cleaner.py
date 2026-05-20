"""
Content Cleaner - Boilerplate Removal and Main Content Extraction
Uses Trafilatura + Custom Cleaning Rules for Vet Manual Content

This module:
1. Uses Trafilatura to extract main content from crawled HTML/markdown
2. Applies custom rules for veterinary manual-specific boilerplate
3. Removes author metadata, navigation, TOC, footers, copyright
4. Preserves only educational/veterinary knowledge
"""

import re
import json
from pathlib import Path
from typing import Optional, Tuple
import trafilatura
from trafilatura import extract


# Get project root
BASE_DIR = Path(__file__).resolve().parent.parent
RAG_OUTPUT_DIR = BASE_DIR / "rag_output"
CLEANED_OUTPUT_DIR = BASE_DIR / "rag_output_cleaned"
MANIFEST_FILE = RAG_OUTPUT_DIR / "manifest.jsonl"

CLEANED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────
# Cleaning Patterns & Rules
# ─────────────────────────────────────────────────────────────────

# Lines/sections that should be removed entirely
JUNK_PATTERNS = [
    # Navigation and breadcrumbs
    r"^\s*\d+\.\s*<\[.*?\]\(.*?\)",  # "1. <[Text](url)"
    r"^\s*\*\s+\[.*?\]\(.*?\)\s*(\|)?",  # "* [Text](url)" navigation with optional pipe
    
    # Section headers for navigation
    r"^\s*(Find In Topic|IN THIS TOPIC|OTHER TOPICS IN THIS CHAPTER|PET OWNER VERSION|PROFESSIONAL VERSION)\s*$",
    r"^\s*(Expand all|Collapse all)\s*$",
    
    # Cookie notices
    r"^\s*\*?\s*(Cookie Preferences|This Site Uses Cookies|Customize my Settings|Accept Cookies)\s*$",
    r"^\s*We suggest you.*?choose",
    
    # Copyright and footer
    r"^\s*Copyright©?\s*\d{4}",
    r"^\s*©\s*\d{4}",
    r"^Modified\s+[A-Za-z]+\s+\d{4}\s*$",
    r"^v\d+\s*$",  # Version numbers like "v108069242"
    
    # Author metadata - more flexible patterns
    r"By\s+\[?[A-Z][a-z\s]+\]?\s*,?\s*(DVM|PhD|DABVP|ACVS|MPH)",
    r"Reviewed\s+(By|by)\s+\[?[A-Z][a-z\s]+\]?\s*,?\s*(DVM|PhD|DABVP|ACVS)",
    r"Reviewed/Revised.*",
    r"College Station|MSD Veterinary",  # Author affiliations
    
    # Quiz and interactive elements
    r"^\s*\[.*?quiz.*?\]",
    r"^\s*\*+\s*(Take the quiz|Quiz:|Answer the question|Question)",
    
    # Social/external links
    r"^\s*(Follow us|Share|Print|Email|View our|Available resources).*$",
    
    # TOC links with pipes - more aggressive pattern
    r"\[.*?\]\(.*?#.*?\)\s*\|",
    
    # Empty or nearly empty lines with only punctuation/pipes
    r"^\s*[\|\-\*_|]+\s*$",
    
    # Language selectors
    r"^\s*English\s*$",
]

# Compile patterns for efficiency
COMPILED_JUNK_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in JUNK_PATTERNS]


def remove_junk_lines(text: str) -> str:
    """Remove lines matching junk patterns."""
    lines = text.splitlines()
    cleaned_lines = []
    
    for line in lines:
        is_junk = any(pattern.search(line) for pattern in COMPILED_JUNK_PATTERNS)
        if not is_junk:
            cleaned_lines.append(line)
    
    return "\n".join(cleaned_lines)


def remove_author_metadata(text: str) -> str:
    """Remove author and reviewer metadata while preserving content."""
    # Remove lines with author bylines
    text = re.sub(
        r"^By\s+\[?[A-Z][a-z\s,\.]+\]?\s*(?:DVM|PhD|DABVP|ACVS|MPH)[^\n]*\n",
        "",
        text,
        flags=re.MULTILINE | re.IGNORECASE
    )
    
    # Remove lines with reviewer information
    text = re.sub(
        r"^Reviewed\s+(?:by|By)\s+\[?[A-Z][a-z\s,\.]+\]?\s*(?:DVM|PhD|DABVP|ACVS)[^\n]*\n",
        "",
        text,
        flags=re.MULTILINE | re.IGNORECASE
    )
    
    # Remove revision metadata
    text = re.sub(r"^Reviewed/Revised.*\n", "", text, flags=re.MULTILINE | re.IGNORECASE)
    
    # Remove version identifiers
    text = re.sub(r"^v\d+\s*\n", "", text, flags=re.MULTILINE)
    
    return text


def remove_table_of_contents(text: str) -> str:
    """Remove table of contents and navigation links."""
    lines = text.splitlines()
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Skip "Find In Topic" and similar headers
        if any(marker in stripped for marker in ["Find In Topic", "IN THIS TOPIC", "OTHER TOPICS"]):
            continue
        
        # Skip TOC links (lines with [text](url#anchor)|)
        if re.match(r"^\*?\s*\[.*?\]\(.*?#.*?\)\s*\|", stripped):
            continue
        
        # Skip pure pipe separators
        if re.match(r"^\s*\|+\s*$", stripped):
            continue
        
        # Skip section navigation headers
        if stripped in ["Expand all", "Collapse all", "PET OWNER VERSION", "PROFESSIONAL VERSION"]:
            continue
        
        cleaned_lines.append(line)
    
    return "\n".join(cleaned_lines)


def normalize_whitespace(text: str) -> str:
    """Collapse multiple blank lines into single blanks, clean up spacing."""
    # Replace multiple consecutive blank lines with single blank
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Clean up spaces around punctuation
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    
    # Clean leading/trailing whitespace from lines
    lines = text.splitlines()
    lines = [line.rstrip() for line in lines]
    text = "\n".join(lines)
    
    return text.strip()


def extract_semantic_content(text: str) -> str:
    """
    Use multiple heuristics to identify and keep only semantic content.
    Remove repeated boilerplate, navigation sections, and low-value text.
    """
    lines = text.splitlines()
    semantic_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Skip very short lines (likely navigation or artifacts)
        if len(stripped) < 10:
            continue
        
        # Skip lines that are mostly links or formatting
        if stripped.startswith("[") and stripped.count("]") > 2:
            continue
        
        # Skip common footer patterns
        if any(keyword in stripped.lower() for keyword in 
               ["©", "copyright", "all rights reserved", "privacy policy", 
                "terms of use", "contact us", "about us"]):
            continue
        
        semantic_lines.append(line)
    
    return "\n".join(semantic_lines)


def remove_urls(text: str) -> str:
    """Remove URLs while preserving link text."""
    # Pattern 1: Remove markdown links [text](url) - keep the text
    text = re.sub(r'\[([^\]]+)\]\(https?://[^\)]+\)', r'\1', text)
    
    # Pattern 2: Remove markdown links with other protocols [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Pattern 3: Remove bare URLs (http, https, ftp, etc.)
    text = re.sub(r'https?://[^\s)]+', '', text)
    text = re.sub(r'ftps?://[^\s)]+', '', text)
    text = re.sub(r'www\.[^\s)]+', '', text)
    
    # Pattern 4: Clean up leftover brackets and pipes
    text = re.sub(r'\[\s*\]', '', text)  # Empty brackets
    text = re.sub(r'\|\s*\|', '|', text)  # Double pipes
    
    return text


def clean_text_content(text: str) -> str:
    """
    Main cleaning pipeline:
    1. Remove author/reviewer metadata
    2. Remove junk lines
    3. Remove table of contents
    4. Remove URLs
    5. Extract semantic content
    6. Normalize whitespace
    """
    # Step 1: Remove author metadata
    text = remove_author_metadata(text)
    
    # Step 2: Remove junk lines matching patterns
    text = remove_junk_lines(text)
    
    # Step 3: Remove TOC and navigation links
    text = remove_table_of_contents(text)
    
    # Step 4: Remove URLs entirely
    text = remove_urls(text)
    
    # Step 5: Extract semantic content
    text = extract_semantic_content(text)
    
    # Step 6: Normalize whitespace
    text = normalize_whitespace(text)
    
    return text


def process_single_file(input_path: Path, output_path: Path) -> Tuple[bool, str, int, int]:
    """
    Process a single text file:
    - Read raw content
    - Try Trafilatura extraction first (if input looks like HTML/markdown)
    - Apply custom cleaning
    - Save cleaned output
    
    Returns: (success, cleaned_text, input_chars, output_chars)
    """
    try:
        # Read raw content
        raw_text = input_path.read_text(encoding="utf-8")
        input_chars = len(raw_text)
        
        # Try Trafilatura extraction if content looks like it has markdown/HTML artifacts
        if "[" in raw_text and "](" in raw_text:
            # Content still has markdown links - try to extract with Trafilatura
            try:
                # Trafilatura expects HTML, so we'll use it as a content extractor
                extracted = extract(raw_text, include_comments=False)
                if extracted and len(extracted) > 200:
                    raw_text = extracted
            except Exception:
                # Trafilatura failed or not applicable, continue with raw text
                pass
        
        # Apply custom cleaning pipeline
        cleaned_text = clean_text_content(raw_text)
        output_chars = len(cleaned_text)
        
        # Only save if we have meaningful content left
        if output_chars > 100:
            output_path.write_text(cleaned_text, encoding="utf-8")
            return True, cleaned_text, input_chars, output_chars
        else:
            return False, cleaned_text, input_chars, output_chars
            
    except Exception as e:
        print(f"  Error processing {input_path.name}: {e}")
        return False, "", 0, 0


def process_all_files() -> dict:
    """Process all text files in rag_output directory."""
    txt_files = sorted(RAG_OUTPUT_DIR.glob("*.txt"))
    
    if not txt_files:
        print(f"No .txt files found in {RAG_OUTPUT_DIR}")
        return {}
    
    print(f"Found {len(txt_files)} files to clean\n")
    print("=" * 80)
    print(f"  Content Cleaning Pipeline")
    print("=" * 80)
    
    results = {
        "total_files": len(txt_files),
        "successfully_cleaned": 0,
        "failed": 0,
        "total_input_chars": 0,
        "total_output_chars": 0,
        "files": {}
    }
    
    for idx, input_path in enumerate(txt_files, 1):
        output_path = CLEANED_OUTPUT_DIR / input_path.name
        
        success, cleaned_text, input_chars, output_chars = process_single_file(
            input_path, output_path
        )
        
        compression_ratio = (1 - output_chars / input_chars) * 100 if input_chars > 0 else 0
        
        status = "✓ CLEANED" if success else "✗ FAILED"
        print(f"\n[{idx:3d}] {status}")
        print(f"      File: {input_path.name}")
        print(f"      Input:  {input_chars:,} chars | Output: {output_chars:,} chars | Removed: {compression_ratio:.1f}%")
        
        if success:
            print(f"      → {output_path.name}")
            results["successfully_cleaned"] += 1
            results["total_input_chars"] += input_chars
            results["total_output_chars"] += output_chars
            results["files"][input_path.name] = {
                "input_chars": input_chars,
                "output_chars": output_chars,
                "compression_ratio": compression_ratio
            }
        else:
            results["failed"] += 1
    
    print(f"\n{'='*80}")
    print(f"  Cleaning Complete")
    print(f"{'='*80}")
    print(f"Successfully cleaned: {results['successfully_cleaned']} / {len(txt_files)}")
    print(f"Failed:               {results['failed']} / {len(txt_files)}")
    print(f"Total input chars:    {results['total_input_chars']:,}")
    print(f"Total output chars:   {results['total_output_chars']:,}")
    if results['total_input_chars'] > 0:
        overall_ratio = (1 - results['total_output_chars'] / results['total_input_chars']) * 100
        print(f"Overall compression:  {overall_ratio:.1f}% boilerplate removed")
    print(f"Output directory:     {CLEANED_OUTPUT_DIR}")
    print(f"{'='*80}\n")
    
    return results


def main():
    """Run the cleaning pipeline."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  WEB CONTENT CLEANER - Boilerplate Removal & Main Content Extraction  ".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    results = process_all_files()
    
    # Save results summary
    results_file = CLEANED_OUTPUT_DIR / "cleaning_report.json"
    results_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Results saved to: {results_file}\n")


if __name__ == "__main__":
    main()
