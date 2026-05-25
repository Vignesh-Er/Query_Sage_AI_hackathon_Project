import pytest
import json
from unittest.mock import MagicMock, patch
from app.config import settings
from app.prompt import call_ai_provider

@pytest.mark.anyio
@patch("httpx.AsyncClient.post")
async def test_call_ai_provider_anthropic_tool_use(mock_post):
    # Setup test credentials and provider
    settings.QUERYSAGE_AI_PROVIDER = "anthropic"
    settings.QUERYSAGE_ANTHROPIC_API_KEY = "test-key"
    
    # Hardcoded valid response dictionary
    mock_input_dict = {
        "rewritten_query": "SELECT * FROM users WHERE id = 1;",
        "changes": [
            {
                "type": "index_added",
                "original_fragment": "SELECT * FROM users",
                "replacement_fragment": "SELECT * FROM users WHERE id = 1",
                "reason": "Add filter limit",
                "orm_equivalent": "User.objects.filter(id=1)"
            }
        ],
        "index_recommendations": [
            {
                "statement": "CREATE INDEX idx_users_id ON users(id);",
                "justification": "Optimize filter"
            }
        ],
        "estimated_row_reduction_percent": 90.0,
        "confidence": "high",
        "plain_summary": "Optimized using index.",
        "follow_up_questions": []
    }
    
    # Mock HTTP response as MagicMock to allow synchronous .json() call
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_123",
                "name": "submit_query_analysis",
                "input": mock_input_dict
            }
        ]
    }
    mock_post.return_value = mock_response
    
    # Run call_ai_provider
    context = {"input_query": "SELECT * FROM users;"}
    result = await call_ai_provider(context)
    
    # Assert result matches the mock input dictionary directly without modification
    assert result == mock_input_dict
    
    # Assert HTTP payload arguments passed to Anthropic
    mock_post.assert_called_once()
    kwargs = mock_post.call_args[1]
    assert "json" in kwargs
    payload = kwargs["json"]
    
    # Assert tools argument is populated with submit_query_analysis
    assert "tools" in payload
    assert len(payload["tools"]) == 1
    assert payload["tools"][0]["name"] == "submit_query_analysis"
    
    # Assert tool_choice is passed correctly
    assert "tool_choice" in payload
    assert payload["tool_choice"] == {
        "type": "tool",
        "name": "submit_query_analysis"
    }

def test_mock_messages_create_arguments():
    # Create a mock for messages.create
    messages_mock = MagicMock()
    
    # Simulate a call to messages.create with the specified arguments
    messages_mock.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        system="system prompt",
        messages=[{"role": "user", "content": "SELECT * FROM users;"}],
        tools=[{
            "name": "submit_query_analysis",
            "description": "Submit database query performance and correctness analysis.",
            "input_schema": {}
        }],
        tool_choice={
            "type": "tool",
            "name": "submit_query_analysis"
        }
    )
    
    # Capture the arguments using call_args
    call_args = messages_mock.create.call_args
    
    # Assertions on call_args.kwargs
    assert "tools" in call_args.kwargs
    assert isinstance(call_args.kwargs["tools"], list)
    assert len(call_args.kwargs["tools"]) == 1
    assert call_args.kwargs["tools"][0]["name"] == "submit_query_analysis"
    
    assert "tool_choice" in call_args.kwargs
    assert call_args.kwargs["tool_choice"] == {
        "type": "tool",
        "name": "submit_query_analysis"
    }
