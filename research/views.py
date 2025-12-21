"""
API views for research endpoints.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from .models import ResearchSession, UploadedDocument
from .serializers import (
    ResearchSessionListSerializer,
    ResearchSessionDetailSerializer,
    StartResearchSerializer,
    ContinueResearchSerializer,
    UploadDocumentSerializer,
)
from .tasks import execute_research, process_document


class ResearchViewSet(viewsets.ViewSet):
    """
    ViewSet for research operations.
    """
    permission_classes = [AllowAny]  # Adjust based on your auth requirements
    
    @action(detail=False, methods=['post'])
    def start(self, request):
        """
        POST /api/research/start
        Start a new research session.
        """
        serializer = StartResearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        query = serializer.validated_data['query']
        user_id = serializer.validated_data.get('user_id')
        
        # Get or create user
        if user_id:
            user = get_object_or_404(User, id=user_id)
        elif request.user.is_authenticated:
            user = request.user
        else:
            # Create anonymous user or use default
            user, _ = User.objects.get_or_create(
                username='anonymous',
                defaults={'email': 'anonymous@example.com'}
            )
        
        # Create research session
        session = ResearchSession.objects.create(
            user=user,
            query=query,
            status='pending',
        )
        
        # Trigger async research execution
        execute_research.delay(session.id)
        
        return Response(
            {
                'session_id': session.id,
                'status': session.status,
                'message': 'Research session started',
            },
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'], url_path='continue')
    def continue_research(self, request, pk=None):
        """
        POST /api/research/{id}/continue
        Continue a research session with a new query.
        """
        parent_session = get_object_or_404(ResearchSession, id=pk)
        
        serializer = ContinueResearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        query = serializer.validated_data['query']
        user_id = serializer.validated_data.get('user_id')
        
        # Get user
        if user_id:
            user = get_object_or_404(User, id=user_id)
        elif request.user.is_authenticated:
            user = request.user
        else:
            user = parent_session.user
        
        # Get parent summary
        parent_summary = parent_session.summary
        if not parent_summary and parent_session.research_summary:
            parent_summary = parent_session.research_summary.content
        
        # Create new research session linked to parent
        new_session = ResearchSession.objects.create(
            user=user,
            parent=parent_session,
            query=query,
            parent_summary=parent_summary,
            status='pending',
        )
        
        # Trigger async research execution
        execute_research.delay(new_session.id)
        
        return Response(
            {
                'session_id': new_session.id,
                'parent_id': parent_session.id,
                'status': new_session.status,
                'message': 'Research continuation started',
            },
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def upload(self, request, pk=None):
        """
        POST /api/research/{id}/upload
        Upload a document (PDF or TXT) for context injection.
        """
        session = get_object_or_404(ResearchSession, id=pk)
        
        serializer = UploadDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uploaded_file = serializer.validated_data['file']
        file_name = uploaded_file.name
        file_type = 'pdf' if file_name.lower().endswith('.pdf') else 'txt'
        
        # Create document record
        document = UploadedDocument.objects.create(
            session=session,
            file_name=file_name,
            file_type=file_type,
            file_path=uploaded_file,
        )
        
        # Trigger async document processing
        process_document.delay(session.id, document.id)
        
        return Response(
            {
                'document_id': document.id,
                'file_name': file_name,
                'file_type': file_type,
                'message': 'Document uploaded and processing started',
            },
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """
        GET /api/research/history
        Get research history for a user.
        """
        user_id = request.query_params.get('user_id')
        
        if user_id:
            user = get_object_or_404(User, id=user_id)
        elif request.user.is_authenticated:
            user = request.user
        else:
            return Response(
                {'error': 'User ID required or user must be authenticated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sessions = ResearchSession.objects.filter(user=user)
        serializer = ResearchSessionListSerializer(sessions, many=True)
        
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """
        GET /api/research/{id}
        Get detailed information about a research session.
        """
        session = get_object_or_404(ResearchSession, id=pk)
        serializer = ResearchSessionDetailSerializer(session)
        return Response(serializer.data)

