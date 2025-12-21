"""
Adapter/wrapper for open_deep_research agent.
This module provides a clean interface to the deep research agent without modifying its core logic.
"""
import os
import sys
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langsmith import traceable
import uuid
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


class TokenTrackingCallback(BaseCallbackHandler):
    """Callback handler to track token usage."""
    
    def __init__(self):
        super().__init__()
        self.input_tokens = 0
        self.output_tokens = 0
        self.model_name = None
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Called when LLM starts."""
        pass
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM ends - track tokens."""
        if response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})
            self.input_tokens += token_usage.get('prompt_tokens', 0)
            self.output_tokens += token_usage.get('completion_tokens', 0)
            if not self.model_name and 'model_name' in response.llm_output:
                self.model_name = response.llm_output['model_name']
    
    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when LLM errors."""
        pass


class DeepResearchAdapter:
    """
    Adapter for open_deep_research agent.
    Wraps the agent to provide:
    - Context injection (parent research, uploaded documents)
    - Token tracking
    - LangSmith tracing
    - Reasoning extraction (high-level only)
    """
    
    def __init__(self, model_name: str = None, api_key: str = None):
        """
        Initialize the adapter.
        
        Args:
            model_name: Name of the model to use
            api_key: OpenAI API key
        """
        self.model_name = model_name or os.getenv('DEFAULT_MODEL', 'gpt-4-turbo-preview')
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=0,
            openai_api_key=self.api_key,
        )
        self.token_callback = TokenTrackingCallback()
    
    def _build_context(self, query: str, parent_summary: str = None, document_summaries: List[str] = None) -> str:
        """
        Build the research context from query, parent summary, and document summaries.
        
        Args:
            query: The research query
            parent_summary: Summary from parent research (for continuation)
            document_summaries: List of document summaries
            
        Returns:
            Enhanced query with context
        """
        context_parts = [query]
        
        if parent_summary:
            context_parts.append(
                f"\n\nPrevious Research Summary:\n{parent_summary}\n\n"
                "IMPORTANT: Do not repeat information already covered in the previous research. "
                "Focus on new aspects, deeper analysis, or different angles of the topic."
            )
        
        if document_summaries:
            context_parts.append("\n\nAdditional Context from Uploaded Documents:")
            for i, doc_summary in enumerate(document_summaries, 1):
                context_parts.append(f"\nDocument {i}:\n{doc_summary}")
        
        return "\n".join(context_parts)
    
    def _extract_reasoning(self, research_output: Any) -> List[Dict[str, Any]]:
        """
        Extract high-level reasoning from research output.
        This should be adjusted based on the actual open_deep_research output structure.
        
        Args:
            research_output: Output from the research agent
            
        Returns:
            List of reasoning steps (high-level only, no chain-of-thought)
        """
        reasoning = []
        
        # Try to extract reasoning from the output
        # This is a placeholder - adjust based on actual structure
        if hasattr(research_output, 'reasoning'):
            for step in research_output.reasoning:
                reasoning.append({
                    'type': step.get('type', 'general'),
                    'description': step.get('description', ''),
                    'metadata': step.get('metadata', {}),
                })
        elif isinstance(research_output, dict):
            # If output is a dict, try to extract reasoning
            if 'reasoning' in research_output:
                reasoning = research_output['reasoning']
            elif 'steps' in research_output:
                # Convert steps to reasoning format
                for step in research_output['steps']:
                    if isinstance(step, dict) and 'type' in step:
                        reasoning.append({
                            'type': step.get('type', 'general'),
                            'description': step.get('description', ''),
                            'metadata': step.get('metadata', {}),
                        })
        
        return reasoning
    
    @traceable(name="deep_research")
    def run_research(
        self,
        query: str,
        parent_summary: str = None,
        document_summaries: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run deep research using the open_deep_research agent.
        
        This method attempts to import and use the open_deep_research package.
        If not available, it provides a fallback that can be adjusted.
        
        Args:
            query: The research query
            parent_summary: Summary from parent research (for continuation)
            document_summaries: List of document summaries to inject
            **kwargs: Additional arguments to pass to the research agent
            
        Returns:
            Dictionary containing:
            - report: Final structured report
            - summary: High-level summary
            - sources: List of sources
            - reasoning: List of high-level reasoning steps
            - token_usage: Token usage information
            - trace_id: LangSmith trace ID (if available)
        """
        # Build enhanced query with context
        enhanced_query = self._build_context(query, parent_summary, document_summaries)
        
        # Initialize token tracking
        self.token_callback = TokenTrackingCallback()
        
        # Try to import and use open_deep_research
        # The actual import path may need to be adjusted based on the package structure
        try:
            # Option 1: Try direct import (if installed as package)
            from open_deep_research import run_research as run_deep_research
            use_package = True
        except ImportError:
            try:
                # Option 2: Try importing from a local clone
                # Adjust path as needed
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'open_deep_research'))
                from open_deep_research import run_research as run_deep_research
                use_package = True
            except ImportError:
                use_package = False
        
        if use_package:
            try:
                # Call the actual research function
                # Adjust parameters based on actual open_deep_research API
                result = run_deep_research(
                    query=enhanced_query,
                    llm=self.llm,
                    callbacks=[self.token_callback],
                    **kwargs
                )
                
                # Extract results (adjust based on actual return structure)
                # The actual structure may vary - this is a template
                if isinstance(result, dict):
                    report = result.get('report', result.get('final_report', ''))
                    summary = result.get('summary', '')
                    sources = result.get('sources', result.get('citations', []))
                    reasoning = self._extract_reasoning(result)
                else:
                    # If result is not a dict, try to extract attributes
                    report = getattr(result, 'report', getattr(result, 'final_report', ''))
                    summary = getattr(result, 'summary', '')
                    sources = getattr(result, 'sources', getattr(result, 'citations', []))
                    reasoning = self._extract_reasoning(result)
                
                # Get trace ID from LangSmith if available
                # LangSmith automatically sets this in the environment during tracing
                trace_id = os.getenv('LANGCHAIN_TRACE_ID', '')
                # If not available, generate a unique ID for tracking
                if not trace_id:
                    trace_id = str(uuid.uuid4())
                
                return {
                    'report': report or '',
                    'summary': summary or '',
                    'sources': sources if isinstance(sources, list) else [],
                    'reasoning': reasoning,
                    'token_usage': {
                        'input_tokens': self.token_callback.input_tokens,
                        'output_tokens': self.token_callback.output_tokens,
                        'total_tokens': self.token_callback.input_tokens + self.token_callback.output_tokens,
                        'model_name': self.token_callback.model_name or self.model_name,
                    },
                    'trace_id': trace_id,
                }
            except Exception as e:
                raise RuntimeError(f"Error running deep research: {str(e)}")
        else:
            # Fallback: Provide a basic implementation for development/testing
            # This should be replaced with actual open_deep_research integration
            raise NotImplementedError(
                "open_deep_research package not found. "
                "Please install it using: pip install git+https://github.com/langchain-ai/open_deep_research.git "
                "or clone the repository and adjust the import path in core/research_adapter.py"
            )

