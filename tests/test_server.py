import pytest
from unittest.mock import MagicMock, patch
import mcp_context_memory

@pytest.fixture
def mock_collections():
    with patch('mcp_context_memory.decisions_collection') as mock_decisions, \
         patch('mcp_context_memory.code_collection') as mock_code:
        yield mock_code, mock_decisions

def test_remember_decision(mock_collections):
    mock_code, mock_decisions = mock_collections
    topic = "Tech Stack"
    context = "We use Symfony 7"
    
    result = mcp_context_memory.remember_decision(topic, context)
    
    assert "Decision successfully stored" in result
    assert topic in result
    mock_decisions.add.assert_called_once()
    args, kwargs = mock_decisions.add.call_args
    assert kwargs['documents'] == [context]
    assert kwargs['metadatas'] == [{"topic": topic}]

def test_search_context_no_results(mock_collections):
    mock_code, mock_decisions = mock_collections
    mock_code.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    mock_decisions.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    
    result = mcp_context_memory.search_context("nothing")
    
    assert "No relevant context found" in result

def test_search_context_with_results(mock_collections):
    mock_code, mock_decisions = mock_collections
    
    # Mock results
    mock_code.query.return_value = {
        "documents": [["class MyClass: pass"]],
        "metadatas": [[{"file_path": "test.py", "node_type": "class_definition", "start_line": 1, "end_line": 2}]],
        "distances": [[0.1]]
    }
    mock_decisions.query.return_value = {
        "documents": [["Use Symfony because it is robust"]],
        "metadatas": [[{"topic": "Tech Stack"}]],
        "distances": [[0.2]]
    }
    
    result = mcp_context_memory.search_context("MyClass")
    
    assert "Code Semantics" in result
    assert "Project Decision" in result
    assert "MyClass" in result
    assert "Symfony" in result
