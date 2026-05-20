"""
Advanced Semantic Serialization

Converts raw chunks into embedding-friendly serialized text
while preserving semantic structure and relationships
"""

import logging
from typing import List, Dict, Any
import re


logger = logging.getLogger(__name__)


class AdvancedSerializer:
    """
    Semantically-aware serialization for chunks
    
    Transforms:
    - Text chunks with contextual headings
    - Table rows into semantic key-value pairs
    - Lists into structured text
    - Code blocks and examples
    - Markdown formatting
    """
    
    @staticmethod
    def serialize_text_chunk(
        text: str,
        headings: List[str] = None,
        heading_hierarchy: str = "",
        section: str = "",
    ) -> str:
        """
        Serialize text chunk with contextual information
        
        Adds heading context to make embeddings more meaningful
        
        Args:
            text: Raw chunk text
            headings: List of heading lines from hierarchy
            heading_hierarchy: Formatted hierarchy string
            section: Section name/context
            
        Returns:
            Contextual text ready for embedding
        """
        contextual_text = ""
        
        # Add section context if available
        if section:
            contextual_text += f"Section: {section}\n\n"
        
        # Add heading hierarchy for semantic context
        if heading_hierarchy:
            contextual_text += f"Context: {heading_hierarchy}\n\n"
        
        # Add the actual text content
        contextual_text += text
        
        return contextual_text.strip()
    
    @staticmethod
    def serialize_table(
        headers: List[str],
        rows: List[List[str]],
        group_size: int = 5,
    ) -> List[str]:
        """
        Serialize table into semantic text chunks
        
        Creates row-by-row semantic representations:
        "Drug: ACE inhibitors, Usage: Heart failure, Dosage: 10mg"
        
        Args:
            headers: Table header names
            rows: List of row data (each row is list of values)
            group_size: Number of rows to group in one chunk
            
        Returns:
            List of semantically serialized rows
        """
        serialized_rows = []
        
        for row in rows:
            if len(row) != len(headers):
                logger.warning(f"Row length {len(row)} != header length {len(headers)}")
                continue
            
            # Create semantic representation of row
            row_parts = []
            for header, value in zip(headers, row):
                if value and value.strip():  # Skip empty cells
                    # Format as "Header: Value"
                    row_parts.append(f"{header.strip()}: {value.strip()}")
            
            # Join with commas for readability
            serialized_row = ", ".join(row_parts)
            if serialized_row:
                serialized_rows.append(serialized_row)
        
        return serialized_rows
    
    @staticmethod
    def serialize_grouped_table(
        headers: List[str],
        rows: List[List[str]],
        group_size: int = 5,
    ) -> str:
        """
        Serialize table with grouped representation
        
        Keeps table structure visible with headers and grouped rows
        
        Args:
            headers: Table header names
            rows: List of row data
            group_size: Rows per group
            
        Returns:
            Formatted table string
        """
        # Create header representation
        header_text = " | ".join(f"{h.strip()}" for h in headers)
        
        # Create row representations
        row_texts = []
        for row in rows:
            if len(row) == len(headers):
                row_text = " | ".join(f"{v.strip()}" for v in row)
                row_texts.append(row_text)
        
        # Group rows
        grouped_rows = []
        for i in range(0, len(row_texts), group_size):
            group = row_texts[i:i + group_size]
            grouped_rows.append("\n".join(group))
        
        # Combine all parts
        result = f"""Table Headers:
{header_text}

Rows:
{chr(10).join(grouped_rows)}"""
        
        return result.strip()
    
    @staticmethod
    def serialize_list(
        items: List[str],
        context: str = "",
    ) -> str:
        """
        Serialize list items with context
        
        Args:
            items: List items
            context: List context/purpose
            
        Returns:
            Serialized list text
        """
        text = ""
        
        if context:
            text += f"{context}:\n"
        
        for item in items:
            text += f"- {item.strip()}\n"
        
        return text.strip()
    
    @staticmethod
    def serialize_code_block(
        code: str,
        language: str = "",
        context: str = "",
    ) -> str:
        """
        Serialize code block with context
        
        Args:
            code: Code content
            language: Programming language
            context: Code purpose/context
            
        Returns:
            Serialized code
        """
        text = ""
        
        if context:
            text += f"Code Example: {context}\n"
        
        if language:
            text += f"Language: {language}\n"
        
        text += code
        
        return text.strip()
    
    @staticmethod
    def extract_and_serialize_markdown_table(text: str) -> tuple[str, List[str]]:
        """
        Extract markdown tables and serialize them semantically
        
        Identifies markdown pipes (|) and converts to semantic format
        
        Args:
            text: Markdown text possibly containing tables
            
        Returns:
            Tuple of (remaining_text, serialized_table_chunks)
        """
        serialized_chunks = []
        remaining_lines = []
        in_table = False
        table_lines = []
        
        for line in text.split("\n"):
            # Detect markdown table (contains |)
            if "|" in line and not line.strip().startswith("#"):
                if not in_table:
                    in_table = True
                    table_lines = [line]
                else:
                    table_lines.append(line)
            else:
                # Process accumulated table
                if in_table and table_lines:
                    chunks = AdvancedSerializer._process_markdown_table(table_lines)
                    serialized_chunks.extend(chunks)
                    in_table = False
                    table_lines = []
                
                remaining_lines.append(line)
        
        # Handle trailing table
        if in_table and table_lines:
            chunks = AdvancedSerializer._process_markdown_table(table_lines)
            serialized_chunks.extend(chunks)
        
        remaining_text = "\n".join(remaining_lines)
        
        return remaining_text, serialized_chunks
    
    @staticmethod
    def _process_markdown_table(table_lines: List[str]) -> List[str]:
        """
        Process markdown table lines and serialize
        
        Args:
            table_lines: Lines containing table markdown
            
        Returns:
            List of serialized rows
        """
        if len(table_lines) < 2:
            return []
        
        # Extract headers from first line
        headers = [
            h.strip() for h in table_lines[0].split("|")
            if h.strip()
        ]
        
        serialized_rows = []
        
        # Process data rows (skip separator row at index 1)
        for line in table_lines[2:]:
            cells = [
                c.strip() for c in line.split("|")
                if c.strip()
            ]
            
            if len(cells) == len(headers):
                row_parts = []
                for h, v in zip(headers, cells):
                    if v:
                        row_parts.append(f"{h}: {v}")
                
                serialized = ", ".join(row_parts)
                if serialized:
                    serialized_rows.append(serialized)
        
        return serialized_rows
    
    @staticmethod
    def clean_markdown_formatting(text: str) -> str:
        """
        Clean markdown formatting while preserving semantic structure
        
        Args:
            text: Markdown text
            
        Returns:
            Cleaned text
        """
        # Preserve headings structure
        lines = text.split("\n")
        cleaned_lines = []
        
        for line in lines:
            # Keep headings but could add processing here
            if line.strip().startswith("#"):
                cleaned_lines.append(line)
            else:
                # Remove excessive markdown syntax
                cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", line)  # **bold**
                cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned)    # *italic*
                cleaned = re.sub(r"`(.*?)`", r"\1", cleaned)      # `code`
                cleaned_lines.append(cleaned)
        
        return "\n".join(cleaned_lines)
