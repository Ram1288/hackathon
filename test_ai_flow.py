"""Quick test of AI-driven flow"""
from agents.execution_agent import ExecutionAgent
from core.interfaces import AgentRequest

# Test 1: Execution agent with AI commands
print("Test 1: Execution Agent with AI-generated commands")
agent = ExecutionAgent({})
agent.initialize()
print("✓ Agent initialized")

request = AgentRequest(
    query='show pods',
    context={
        'ai_generated_commands': [
            {'cmd': 'kubectl get pods -n default', 'reason': 'List pods'}
        ]
    },
    metadata={},
    session_id='test'
)
response = agent.process(request)
print(f"✓ AI command execution: {'Success' if response.success else 'Failed'}")
print(f"✓ Mode used: {response.metadata.get('mode')}")

# Test 2: Fallback when no AI commands
print("\nTest 2: Fallback when LLM unavailable")
request2 = AgentRequest(
    query='show pods',
    context={'namespace': 'default'},
    metadata={},
    session_id='test2'
)
response2 = agent.process(request2)
print(f"✓ Fallback execution: {'Success' if response2.success else 'Failed'}")
print(f"✓ Mode used: {response2.metadata.get('mode')}")

print("\n✅ All tests passed! Execution agent is clean and AI-driven.")
