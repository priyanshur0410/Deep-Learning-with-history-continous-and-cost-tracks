"""
Data models for research sessions and related entities.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class ResearchSession(models.Model):
    """Represents a research session with query, status, and results."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='research_sessions')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='continuations')
    query = models.TextField(help_text="The research query/question")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    trace_id = models.CharField(max_length=255, blank=True, help_text="LangSmith trace ID")
    
    # Context from parent research
    parent_summary = models.TextField(blank=True, help_text="Summary from parent research for continuation")
    
    # Results
    final_report = models.TextField(blank=True, help_text="Structured final report")
    summary = models.TextField(blank=True, help_text="High-level summary")
    sources = models.JSONField(default=list, help_text="List of sources used")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, help_text="Error message if status is failed")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Research {self.id}: {self.query[:50]}... ({self.status})"


class ResearchSummary(models.Model):
    """Stores summaries of research findings."""
    
    session = models.OneToOneField(ResearchSession, on_delete=models.CASCADE, related_name='research_summary')
    content = models.TextField(help_text="Summary content")
    key_findings = models.JSONField(default=list, help_text="List of key findings")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Summary for Research {self.session.id}"


class ResearchReasoning(models.Model):
    """Stores high-level reasoning (query planning, source selection) without chain-of-thought."""
    
    session = models.ForeignKey(ResearchSession, on_delete=models.CASCADE, related_name='reasoning_steps')
    step_type = models.CharField(max_length=50, help_text="Type of reasoning step (e.g., 'query_planning', 'source_selection')")
    description = models.TextField(help_text="High-level description of the reasoning step")
    metadata = models.JSONField(default=dict, help_text="Additional metadata")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.step_type} for Research {self.session.id}"


class UploadedDocument(models.Model):
    """Manages documents uploaded for context injection."""
    
    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('txt', 'Text'),
    ]
    
    session = models.ForeignKey(ResearchSession, on_delete=models.CASCADE, related_name='uploaded_documents')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    file_path = models.FileField(upload_to='documents/%Y/%m/%d/')
    extracted_text = models.TextField(blank=True, help_text="Raw extracted text")
    summary = models.TextField(blank=True, help_text="Summarized content for context injection")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.file_name} for Research {self.session.id}"


class ResearchCost(models.Model):
    """Tracks token usage and costs for research sessions."""
    
    session = models.OneToOneField(ResearchSession, on_delete=models.CASCADE, related_name='cost')
    model_name = models.CharField(max_length=100, help_text="Model used for this research")
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Cost for Research {self.session.id}: ${self.estimated_cost_usd}"

