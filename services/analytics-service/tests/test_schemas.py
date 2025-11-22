"""
Unit tests for Analytics Service schemas
"""
import pytest
from datetime import datetime
from app.schemas import EventRequest, EventResponse, MetricsResponse, TimeSeriesPoint


class TestAnalyticsSchemas:
    """Test Analytics Service schemas"""
    
    def test_event_request(self):
        """Test event request schema"""
        event = EventRequest(
            event_type="edit_applied",
            agent_id="agent-01",
            version=5,
            tokens=100,
            timestamp=datetime.utcnow(),
            metadata={"node_id": "node-a"}
        )
        
        assert event.event_type == "edit_applied"
        assert event.agent_id == "agent-01"
        assert event.version == 5
        assert event.tokens == 100
        assert event.metadata["node_id"] == "node-a"
    
    def test_event_request_minimal(self):
        """Test event request with minimal fields"""
        event = EventRequest(
            event_type="budget_exceeded",
            timestamp=datetime.utcnow()
        )
        
        assert event.event_type == "budget_exceeded"
        assert event.agent_id is None
        assert event.version is None
    
    def test_event_response(self):
        """Test event response schema"""
        response = EventResponse(status="ok")
        assert response.status == "ok"
    
    def test_time_series_point(self):
        """Test time series point schema"""
        point = TimeSeriesPoint(
            timestamp="2024-01-01T00:00:00Z",
            value=100
        )
        
        assert point.timestamp == "2024-01-01T00:00:00Z"
        assert point.value == 100
    
    def test_metrics_response(self):
        """Test metrics response schema"""
        metrics = MetricsResponse(
            total_edits=50,
            total_tokens=5000,
            active_agents=10,
            avg_latency_ms=250.5,
            edits_per_minute=5.5,
            token_usage_by_time=[
                TimeSeriesPoint(timestamp="2024-01-01T00:00:00Z", value=1000),
                TimeSeriesPoint(timestamp="2024-01-01T01:00:00Z", value=2000),
            ]
        )
        
        assert metrics.total_edits == 50
        assert metrics.total_tokens == 5000
        assert metrics.active_agents == 10
        assert metrics.avg_latency_ms == 250.5
        assert metrics.edits_per_minute == 5.5
        assert len(metrics.token_usage_by_time) == 2
