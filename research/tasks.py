"""
Celery tasks for async research execution.
"""
import os
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import ResearchSession, ResearchSummary, ResearchReasoning, ResearchCost
from core.research_adapter import DeepResearchAdapter
from core.document_processor import DocumentProcessor


@shared_task(bind=True, max_retries=3)
def execute_research(self, session_id: int):
    """
    Execute research asynchronously using the deep research agent.
    
    Args:
        session_id: ID of the ResearchSession to execute
    """
    try:
        session = ResearchSession.objects.get(id=session_id)
        session.status = 'running'
        session.save()
        
        # Get document summaries if any (only non-empty summaries)
        document_summaries = [
            summary for summary in 
            session.uploaded_documents.values_list('summary', flat=True)
            if summary and summary.strip()
        ]
        
        # Initialize adapter
        adapter = DeepResearchAdapter(
            model_name=settings.DEFAULT_MODEL,
            api_key=settings.OPENAI_API_KEY
        )
        
        # Run research
        result = adapter.run_research(
            query=session.query,
            parent_summary=session.parent_summary,
            document_summaries=document_summaries,
        )
        
        # Update session with results
        session.final_report = result.get('report', '')
        session.summary = result.get('summary', '')
        session.sources = result.get('sources', [])
        session.trace_id = result.get('trace_id', '')
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save()
        
        # Create or update summary
        ResearchSummary.objects.update_or_create(
            session=session,
            defaults={
                'content': result.get('summary', ''),
                'key_findings': result.get('sources', [])[:10],  # Top 10 as key findings
            }
        )
        
        # Store reasoning steps (high-level only)
        reasoning_steps = result.get('reasoning', [])
        for step in reasoning_steps:
            ResearchReasoning.objects.create(
                session=session,
                step_type=step.get('type', 'general'),
                description=step.get('description', ''),
                metadata=step.get('metadata', {}),
            )
        
        # Calculate and store cost
        token_usage = result.get('token_usage', {})
        model_name = token_usage.get('model_name', settings.DEFAULT_MODEL)
        input_tokens = token_usage.get('input_tokens', 0)
        output_tokens = token_usage.get('output_tokens', 0)
        total_tokens = token_usage.get('total_tokens', input_tokens + output_tokens)
        
        # Calculate cost
        pricing = settings.MODEL_PRICING.get(model_name, {'input': 0, 'output': 0})
        cost = (
            (input_tokens / 1_000_000) * pricing['input'] +
            (output_tokens / 1_000_000) * pricing['output']
        )
        
        ResearchCost.objects.update_or_create(
            session=session,
            defaults={
                'model_name': model_name,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
                'estimated_cost_usd': cost,
            }
        )
        
        return {
            'session_id': session_id,
            'status': 'completed',
            'trace_id': session.trace_id,
        }
        
    except ResearchSession.DoesNotExist:
        return {'error': f'ResearchSession {session_id} not found'}
    except Exception as exc:
        # Update session status to failed
        try:
            session = ResearchSession.objects.get(id=session_id)
            session.status = 'failed'
            session.error_message = str(exc)
            session.save()
        except:
            pass
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def process_document(session_id: int, document_id: int):
    """
    Process uploaded document: extract text and generate summary.
    
    Args:
        session_id: ID of the ResearchSession
        document_id: ID of the UploadedDocument
    """
    from .models import UploadedDocument
    
    try:
        document = UploadedDocument.objects.get(id=document_id, session_id=session_id)
        processor = DocumentProcessor()
        
        # Extract text
        extracted_text = processor.extract_text(document.file_path.path, document.file_type)
        document.extracted_text = extracted_text
        
        # Generate summary
        summary = processor.summarize_text(extracted_text)
        document.summary = summary
        
        document.save()
        
        return {'document_id': document_id, 'status': 'processed'}
    except UploadedDocument.DoesNotExist:
        return {'error': f'UploadedDocument {document_id} not found'}
    except Exception as exc:
        return {'error': str(exc)}

