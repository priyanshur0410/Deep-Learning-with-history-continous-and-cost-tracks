"""
Serializers for research API endpoints.
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    ResearchSession,
    ResearchSummary,
    ResearchReasoning,
    UploadedDocument,
    ResearchCost,
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class ResearchReasoningSerializer(serializers.ModelSerializer):
    """Serializer for ResearchReasoning model."""
    
    class Meta:
        model = ResearchReasoning
        fields = ['id', 'step_type', 'description', 'metadata', 'created_at']


class ResearchCostSerializer(serializers.ModelSerializer):
    """Serializer for ResearchCost model."""
    
    class Meta:
        model = ResearchCost
        fields = [
            'model_name',
            'input_tokens',
            'output_tokens',
            'total_tokens',
            'estimated_cost_usd',
        ]


class UploadedDocumentSerializer(serializers.ModelSerializer):
    """Serializer for UploadedDocument model."""
    
    class Meta:
        model = UploadedDocument
        fields = [
            'id',
            'file_name',
            'file_type',
            'uploaded_at',
            'summary',
        ]
        read_only_fields = ['summary', 'uploaded_at']


class ResearchSessionListSerializer(serializers.ModelSerializer):
    """Serializer for listing research sessions."""
    
    user = UserSerializer(read_only=True)
    parent_id = serializers.IntegerField(source='parent.id', read_only=True, allow_null=True)
    
    class Meta:
        model = ResearchSession
        fields = [
            'id',
            'user',
            'parent_id',
            'query',
            'status',
            'summary',
            'trace_id',
            'created_at',
            'updated_at',
            'completed_at',
        ]


class ResearchSessionDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed research session view."""
    
    user = UserSerializer(read_only=True)
    parent_id = serializers.IntegerField(source='parent.id', read_only=True, allow_null=True)
    reasoning_steps = ResearchReasoningSerializer(many=True, read_only=True)
    cost = ResearchCostSerializer(read_only=True)
    uploaded_documents = UploadedDocumentSerializer(many=True, read_only=True)
    
    class Meta:
        model = ResearchSession
        fields = [
            'id',
            'user',
            'parent_id',
            'query',
            'status',
            'trace_id',
            'parent_summary',
            'final_report',
            'summary',
            'sources',
            'reasoning_steps',
            'cost',
            'uploaded_documents',
            'created_at',
            'updated_at',
            'completed_at',
            'error_message',
        ]


class StartResearchSerializer(serializers.Serializer):
    """Serializer for starting a new research session."""
    
    query = serializers.CharField(
        required=True,
        help_text="The research query/question"
    )
    user_id = serializers.IntegerField(
        required=False,
        help_text="User ID (defaults to request user if authenticated)"
    )


class ContinueResearchSerializer(serializers.Serializer):
    """Serializer for continuing a research session."""
    
    query = serializers.CharField(
        required=True,
        help_text="The new research query/question"
    )
    user_id = serializers.IntegerField(
        required=False,
        help_text="User ID (defaults to request user if authenticated)"
    )


class UploadDocumentSerializer(serializers.Serializer):
    """Serializer for uploading a document."""
    
    file = serializers.FileField(
        required=True,
        help_text="PDF or TXT file to upload"
    )
    
    def validate_file(self, value):
        """Validate file type."""
        file_name = value.name.lower()
        if not (file_name.endswith('.pdf') or file_name.endswith('.txt')):
            raise serializers.ValidationError("Only PDF and TXT files are supported.")
        return value

