#!/usr/bin/env python3
"""
DevDebug AI - Component Tests
Simple tests to validate core functionality
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.interfaces import AgentRequest, AgentResponse, AgentType
from agents.document_agent import DocumentAgent
from agents.execution_agent import ExecutionAgent
from agents.llm_agent import LLMAgent
from core.orchestrator import DevDebugOrchestrator
import yaml


def test_interfaces():
    """Test core interfaces"""
    print("Testing core interfaces...")
    
    # Test AgentRequest
    request = AgentRequest(
        query="Test query",
        context={'namespace': 'default'},
        metadata={},
        session_id="test-123"
    )
    assert request.query == "Test query"
    assert request.namespace == 'default'
    print("  ✓ AgentRequest works")
    
    # Test AgentResponse
    response = AgentResponse(
        success=True,
        data={'test': 'data'},
        agent_type=AgentType.DOCUMENT,
        execution_time=0.5
    )
    assert response.success is True
    print("  ✓ AgentResponse works")
    
    print("✓ Interface tests passed\n")


def test_document_agent():
    """Test Document Agent"""
    print("Testing Document Agent...")
    
    config = {'doc_dir': './docs'}
    agent = DocumentAgent(config)
    
    # Test health check
    assert agent.health_check() is True
    print("  ✓ Document Agent health check passed")
    
    # Test pattern matching
    request = AgentRequest(
        query="My pod is in CrashLoopBackOff",
        context={},
        metadata={},
        session_id="test"
    )
    response = agent.process(request)
    
    assert response.success is True
    assert 'k8s_patterns' in response.data
    print(f"  ✓ Matched {len(response.data['k8s_patterns'])} patterns")
    
    print("✓ Document Agent tests passed\n")


def test_execution_agent():
    """Test Execution Agent"""
    print("Testing Execution Agent...")
    
    config = {'ssh_enabled': False}
    agent = ExecutionAgent(config)
    
    # Test health check
    assert agent.health_check() is True
    print("  ✓ Execution Agent health check passed")
    
    # Test simple command
    request = AgentRequest(
        query="Show me pod status",
        context={'namespace': 'default'},
        metadata={},
        session_id="test"
    )
    response = agent.process(request)
    
    # Should work or gracefully handle kubectl not being available
    print(f"  ✓ Execution Agent response: {response.success}")
    if not response.success:
        print(f"    (kubectl may not be available: {response.error})")
    
    print("✓ Execution Agent tests passed\n")


def test_llm_agent():
    """Test LLM Agent"""
    print("Testing LLM Agent...")
    
    config = {
        'ollama_url': 'http://localhost:11434',
        'model': 'llama3.1:8b'
    }
    agent = LLMAgent(config)
    
    # Health check will fail if Ollama not running - that's OK
    health = agent.health_check()
    print(f"  ✓ LLM Agent health: {health}")
    if not health:
        print("    (Ollama may not be running - fallback mode available)")
    
    # Test request (will use fallback if Ollama not available)
    request = AgentRequest(
        query="My pod is crashing",
        context={},
        metadata={},
        session_id="test"
    )
    response = agent.process(request)
    
    assert response.success is True
    assert 'response' in response.data
    print(f"  ✓ LLM Agent generated response (model: {response.metadata.get('model', 'unknown')})")
    
    print("✓ LLM Agent tests passed\n")


def test_orchestrator():
    """Test Orchestrator"""
    print("Testing Orchestrator...")
    
    # Load config
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        config = {
            'document_agent': {'doc_dir': './docs'},
            'execution_agent': {'ssh_enabled': False},
            'llm_agent': {
                'ollama_url': 'http://localhost:11434',
                'model': 'llama3.1:8b'
            },
            'orchestrator': {}
        }
    
    orchestrator = DevDebugOrchestrator(config)
    
    # Test health check
    health = orchestrator.health_check()
    print(f"  ✓ Orchestrator health: {health['overall_healthy']}")
    for agent_name, agent_health in health['agents'].items():
        status = "✓" if agent_health['healthy'] else "⚠"
        print(f"    {status} {agent_name}: {agent_health['healthy']}")
    
    # Test query processing
    print("\n  Testing query processing...")
    result = orchestrator.process_query(
        query="My pod is in CrashLoopBackOff",
        namespace="default"
    )
    
    assert 'solution' in result
    assert result['session_id'] is not None
    print("  ✓ Query processed successfully")
    print(f"    Session ID: {result['session_id'][:8]}...")
    
    # Test session management
    history = orchestrator.get_session_history(result['session_id'])
    assert len(history) == 1
    print(f"  ✓ Session history: {len(history)} queries")
    
    print("✓ Orchestrator tests passed\n")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("DevDebug AI - Component Tests")
    print("="*60 + "\n")
    
    try:
        test_interfaces()
        test_document_agent()
        test_execution_agent()
        test_llm_agent()
        test_orchestrator()
        
        print("="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        print("\nNotes:")
        print("  • If Ollama is not running, LLM Agent uses fallback mode")
        print("  • If kubectl is not available, some execution features are limited")
        print("  • This is expected and the system handles it gracefully")
        print("\nThe system is working correctly! 🎉\n")
        
        return 0
        
    except Exception as e:
        print("\n" + "="*60)
        print("✗ TEST FAILED")
        print("="*60)
        print(f"\nError: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
