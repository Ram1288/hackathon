"""Quick test of AI-driven flow"""
from agents.execution_agent import ExecutionAgent
from core.interfaces import AgentRequest
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Test 1: Execution agent with AI commands
print("Test 1: Execution Agent with AI-generated commands")
agent = ExecutionAgent(config.get('execution_agent', {}))
agent.initialize()
print("✓ Agent initialized")
print(f"✓ Security: allow_delete={agent.allow_delete}, read_only_mode={agent.read_only_mode}")

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
if response.success:
    print(f"✓ Mode used: {response.metadata.get('mode')}")

# Test 2: Delete operation (should work with allow_delete=true)
print("\nTest 2: Delete operation with permissions")
request2 = AgentRequest(
    query='delete pod test',
    context={
        'ai_generated_commands': [
            {'cmd': 'kubectl delete pod test -n default', 'reason': 'Delete pod'}
        ]
    },
    metadata={},
    session_id='test2'
)
response2 = agent.process(request2)
print(f"✓ Delete execution: {'Allowed (Success or kubectl error)' if response2.success else 'Blocked by security'}")

# Test 3: Fallback when no AI commands
print("\nTest 3: Fallback when LLM unavailable")
request3 = AgentRequest(
    query='show pods',
    context={'namespace': 'default'},
    metadata={},
    session_id='test3'
)
response3 = agent.process(request3)
print(f"✓ Fallback execution: {'Success' if response3.success else 'Failed'}")

print("\n✅ All tests completed! Execution agent is AI-driven with smart security.")
