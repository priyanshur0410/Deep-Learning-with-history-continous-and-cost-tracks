"""
Admin interface for research models.
"""
from django.contrib import admin
from .models import (
    ResearchSession,
    ResearchSummary,
    ResearchReasoning,
    UploadedDocument,
    ResearchCost,
)


@admin.register(ResearchSession)
class ResearchSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'query', 'status', 'created_at', 'trace_id']
    list_filter = ['status', 'created_at']
    search_fields = ['query', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'completed_at']


@admin.register(ResearchSummary)
class ResearchSummaryAdmin(admin.ModelAdmin):
    list_display = ['session', 'created_at']
    search_fields = ['session__query']


@admin.register(ResearchReasoning)
class ResearchReasoningAdmin(admin.ModelAdmin):
    list_display = ['session', 'step_type', 'created_at']
    list_filter = ['step_type', 'created_at']
    search_fields = ['session__query']


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'file_type', 'session', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['file_name', 'session__query']


@admin.register(ResearchCost)
class ResearchCostAdmin(admin.ModelAdmin):
    list_display = ['session', 'model_name', 'total_tokens', 'estimated_cost_usd', 'created_at']
    list_filter = ['model_name', 'created_at']
    search_fields = ['session__query']

