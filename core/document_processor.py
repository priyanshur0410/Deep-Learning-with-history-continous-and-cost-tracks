"""
Document processing utilities for PDF and TXT files.
"""
import os
from typing import Optional
from PyPDF2 import PdfReader
from langchain_openai import ChatOpenAI
from django.conf import settings


class DocumentProcessor:
    """Processes uploaded documents (PDF, TXT) and generates summaries."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.DEFAULT_MODEL,
            temperature=0,
            openai_api_key=settings.OPENAI_API_KEY,
        )
    
    def extract_text(self, file_path: str, file_type: str) -> str:
        """
        Extract text from a document file.
        
        Args:
            file_path: Path to the file
            file_type: Type of file ('pdf' or 'txt')
            
        Returns:
            Extracted text content
        """
        if file_type == 'pdf':
            return self._extract_pdf_text(file_path)
        elif file_type == 'txt':
            return self._extract_txt_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file."""
        try:
            reader = PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text())
            return "\n".join(text_parts)
        except Exception as e:
            raise RuntimeError(f"Error extracting PDF text: {str(e)}")
    
    def _extract_txt_text(self, file_path: str) -> str:
        """Extract text from TXT file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Error extracting TXT text: {str(e)}")
    
    def summarize_text(self, text: str, max_length: int = 1000) -> str:
        """
        Generate a concise summary of the extracted text.
        
        Args:
            text: The text to summarize
            max_length: Maximum length of summary in characters
            
        Returns:
            Summarized text
        """
        if not text or len(text.strip()) == 0:
            return ""
        
        # Truncate if too long (to avoid token limits)
        if len(text) > 10000:
            text = text[:10000] + "..."
        
        prompt = f"""Please provide a concise summary of the following text. 
Focus on key points and main ideas. Keep the summary under {max_length} characters.

Text:
{text}

Summary:"""
        
        try:
            response = self.llm.invoke(prompt)
            summary = response.content.strip()
            
            # Ensure summary doesn't exceed max_length
            if len(summary) > max_length:
                summary = summary[:max_length] + "..."
            
            return summary
        except Exception as e:
            # Fallback: return truncated text if LLM fails
            return text[:max_length] + "..." if len(text) > max_length else text

