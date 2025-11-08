"""LLM Agent using Ollama with Llama 3.1"""
import requests
import json
import time
from typing import Dict, Any, List, Optional

from core.interfaces import BaseAgent, AgentRequest, AgentResponse, AgentType, AgentProcessingError


class LLMAgent(BaseAgent):
    """
    LLM Agent using Ollama with Llama 3.1 8B
    Provides intelligent analysis and troubleshooting advice
    """
    
    def initialize(self):
        """Initialize LLM agent"""
        self.agent_type = AgentType.LLM
        self.ollama_url = self.config.get('ollama_url', 'http://localhost:11434')
        self.model = self.config.get('model', 'llama3.1:8b')
        self.temperature = self.config.get('temperature', 0.7)
        self.max_tokens = self.config.get('max_tokens', 1000)
        
        self.api_endpoints = {
            'generate': f'{self.ollama_url}/api/generate',
            'chat': f'{self.ollama_url}/api/chat',
            'embeddings': f'{self.ollama_url}/api/embeddings',
            'tags': f'{self.ollama_url}/api/tags'
        }
        
        # Initialize knowledge agent for dynamic learning
        from agents.knowledge_agent import KnowledgeAgent
        self.knowledge_agent = KnowledgeAgent(self.config)
        self.knowledge_agent.initialize()
        
        # AI-driven prompts with ZERO hardcoded commands/patterns
        self.prompt_templates = {
            'generate_commands': """You are a Kubernetes expert with deep understanding of cloud-native troubleshooting.

**User Query:**
{query}

**Context:**
- Namespace: {namespace}
- Pod Name: {pod_name}

{dynamic_knowledge}

**CRITICAL DIAGNOSTIC STRATEGY:**
When debugging issues (like "pods not running"), you MUST use a TWO-PHASE approach:

**PHASE 1 - DISCOVERY (always first):**
- List/find the problematic resources with specific selectors
- Use --field-selector, -l (labels), or -o (output format) to filter
- Examples:
  * Find non-running pods: `kubectl get pods -n {namespace} --field-selector=status.phase!=Running -o wide`
  * Find failed pods: `kubectl get pods -n {namespace} --field-selector=status.phase=Failed`
  * List all events: `kubectl get events -n {namespace} --sort-by=.lastTimestamp`

**PHASE 2 - DETAILED DIAGNOSTICS (after discovery):**
- Use the discovered resource names in detailed commands
- If you don't know specific names yet, use `-o jsonpath` to extract them
- Examples (these commands will be generated LATER with actual names):
  * `kubectl describe pod <specific-pod-name> -n {namespace}`
  * `kubectl logs <specific-pod-name> -n {namespace} --tail=50`

**For THIS request, generate ONLY Phase 1 (discovery) commands!**
The system will parse results and generate Phase 2 commands automatically.

**CRITICAL RULES:**
1. ❌ NEVER use placeholders in Phase 1 commands
2. ✅ Use field-selectors, labels, output formats to find resources
3. ✅ Commands must be immediately executable without substitution
4. ✅ Maximum 3 discovery commands per request
5. ✅ Use ONLY resources discovered in this environment (see above)

**CRITICAL OUTPUT REQUIREMENTS:**
1. Return ONLY valid JSON - no markdown, no code blocks, no explanations
2. Use double quotes for all strings (not single quotes)
3. NO COMMENTS in JSON (no //, no /* */) - JSON does not support comments!
4. Escape special characters properly (\\n, \\", \\\\)
5. Each command must be executable as-is (no placeholders)

**EXACT OUTPUT FORMAT:**
{{
  "commands": [
    {{
      "cmd": "kubectl get pods -n {namespace} --field-selector=status.phase!=Running -o wide",
      "reason": "Find all non-running pods with detailed status information"
    }},
    {{
      "cmd": "kubectl get events -n {namespace} --sort-by=.lastTimestamp --field-selector=type=Warning",
      "reason": "Get recent warning events that might explain pod failures"
    }}
  ]
}}

**GOOD Examples (Phase 1 discovery):**
{{
  "commands": [
    {{"cmd": "kubectl get pods -n production --field-selector=status.phase!=Running -o jsonpath='{{.items[*].metadata.name}}'", "reason": "List non-running pod names"}},
    {{"cmd": "kubectl get events -n production --sort-by=.lastTimestamp", "reason": "Check recent events"}}
  ]
}}

**BAD Examples (DO NOT DO THIS):**
❌ {{"cmd": "kubectl describe pod <pod-name> -n default"}} - has placeholder!
❌ {{"cmd": "kubectl logs POD_NAME"}} - has placeholder!
❌ // {{"cmd": "kubectl get pods"}} - has comment!

Now generate Phase 1 (discovery) commands in VALID JSON format:""",

            'generate_action_commands': """You are a Kubernetes expert executing ACTION commands.

**User Action Request:**
{query}

**Context:**
- Namespace: {namespace}
- Pod Name: {pod_name}

{dynamic_knowledge}

**ACTION EXECUTION STRATEGY:**
The user wants to EXECUTE an action (delete, create, scale, etc.), not just investigate.
Generate commands to discover resources, then execute the action.

**STEP 1 - DISCOVERY (use simple -o wide, not jsonpath):**
  * Find non-running pods: kubectl get pods -n {namespace} --field-selector=status.phase!=Running -o wide
  * Find all pods: kubectl get pods -n {namespace} -o wide

**STEP 2 - ACTION (use field-selectors when possible):**
  * Delete non-running pods: kubectl delete pods -n {namespace} --field-selector=status.phase!=Running
  * Scale deployment: kubectl scale deployment NAME -n {namespace} --replicas=3
  * Restart deployment: kubectl rollout restart deployment NAME -n {namespace}

**CRITICAL JSON RULES:**
1. Use ONLY double quotes in JSON
2. DO NOT use jsonpath output format (causes quote issues)
3. Use -o wide or -o name instead
4. NO special characters in cmd field that need escaping
5. Keep commands simple and executable

**CORRECT OUTPUT (copy this structure exactly):**
{{
  "commands": [
    {{
      "cmd": "kubectl get pods -n {namespace} --field-selector=status.phase!=Running -o wide",
      "reason": "Step 1: List non-running pods"
    }},
    {{
      "cmd": "kubectl delete pods -n {namespace} --field-selector=status.phase!=Running",
      "reason": "Step 2: Delete non-running pods"
    }}
  ]
}}

**BAD - DO NOT DO THIS:**
{{"cmd": "kubectl get pods -o jsonpath=\"{{.items[*].name}}\""}}  ← Nested quotes break JSON!

Generate 2 commands in VALID JSON format (discovery + action):

Now generate action commands in VALID JSON format:""",
            
            'troubleshoot': """You are a Kubernetes and RHEL systems expert. A user has a query about their Kubernetes cluster.

**User Query:**
{query}

**Investigation Root Cause (AI-determined):**
{root_cause}

**Diagnostic Results from kubectl:**
{diagnostics}

**Relevant Documentation:**
{documentation}

**Code Examples Available:**
{code_examples}

CRITICAL: The investigation agent has already identified the root cause above. Your job is to provide a detailed solution based on that root cause. DO NOT contradict or ignore the investigation findings!

If this is an informational query (list, show, get resources):
- Summarize what was found in the diagnostic results
- Provide a brief explanation of the resources
- Suggest useful follow-up queries or commands

If this is a troubleshooting query:
1. **Acknowledge the Root Cause**: Start with the identified root cause from the investigation
2. **Immediate Solution**: Provide specific commands or steps to fix the issue based on the root cause
3. **Verification**: How to verify the fix worked
4. **Prevention**: Steps to prevent this issue in the future

Be concise, technical, and actionable. Base your analysis on the investigation findings and diagnostic results provided.""",
            
            'analyze_logs': """You are a Kubernetes expert analyzing pod logs to identify issues.

**Pod Logs:**
{logs}

**Context:**
{context}

Analyze these logs and provide:

1. **Issue Identification**: What error or issue do you see?
2. **Severity Assessment**: How critical is this issue?
3. **Root Cause**: What is likely causing this problem?
4. **Recommended Actions**: Specific steps to resolve the issue

Be specific and reference actual log lines where relevant.""",
            
            'generate_script': """You are a Python expert specializing in Kubernetes automation.

**Requirement:**
{requirement}

**Context:**
{context}

Generate a Python script using the official kubernetes-client library that accomplishes this requirement.

Requirements:
- Use the kubernetes library (from kubernetes import client, config)
- Include proper error handling
- Add helpful comments
- Make it production-ready
- Include example usage

Provide ONLY the Python code, well-commented.""",
            
            'explain': """You are a Kubernetes expert. Explain the following concept or command clearly and concisely.

**Query:**
{query}

**Context:**
{context}

Provide:
1. A clear explanation
2. When and why you would use this
3. Example usage
4. Common pitfalls to avoid

Keep the explanation practical and focused.""",
            
            'optimize': """You are a Kubernetes performance optimization expert.

**Current Situation:**
{query}

**Diagnostic Data:**
{diagnostics}

Analyze the current configuration and provide optimization recommendations:

1. **Performance Issues Identified**: What problems do you see?
2. **Optimization Recommendations**: Specific changes to make
3. **Expected Impact**: What improvements to expect
4. **Implementation Steps**: How to implement the changes

Focus on practical, measurable improvements."""
        }
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """Process LLM request"""
        start_time = time.time()
        
        try:
            # Check if Ollama is available
            if not self._check_ollama_available():
                raise AgentProcessingError(
                    "Ollama LLM service is not available. This is a 100% AI-driven system. "
                    "Please start Ollama: 'ollama serve' and ensure model is available: 'ollama pull llama3.1:8b'"
                )
            
            # Determine prompt type
            prompt_type = self._determine_prompt_type(request)
            
            # Build prompt
            prompt = self._build_prompt(prompt_type, request)
            
            # Query Ollama
            response_text = self._query_ollama(prompt)
            
            execution_time = time.time() - start_time
            
            return AgentResponse(
                success=True,
                data={
                    'response': response_text,
                    'prompt_type': prompt_type,
                    'model': self.model
                },
                error=None,
                metadata={
                    'model': self.model,
                    'prompt_type': prompt_type,
                    'ollama_available': True
                },
                agent_type=self.agent_type,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return AgentResponse(
                success=False,
                data={},
                error=str(e),
                metadata={
                    'ollama_available': False,
                    'error_type': type(e).__name__
                },
                agent_type=self.agent_type,
                execution_time=execution_time
            )
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            response = requests.get(f'{self.ollama_url}/api/tags', timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(self.model in m.get('name', '') for m in models)
            return False
        except:
            return False
    
    def _determine_prompt_type(self, request: AgentRequest) -> str:
        """
        Determine which prompt template to use.
        
        For AI-driven approach, we primarily use 'troubleshoot' which handles everything.
        Only use specialized templates when explicitly clear from context.
        """
        # Always use troubleshoot template - it's comprehensive and AI-driven
        # The LLM will adapt its response based on the query intent automatically
        return 'troubleshoot'
    
    def _build_prompt(self, prompt_type: str, request: AgentRequest) -> str:
        """Build prompt from template and context"""
        template = self.prompt_templates[prompt_type]
        
        # Extract context data
        diagnostics = self._format_diagnostics(request.context.get('diagnostics', {}))
        documentation = self._format_documentation(request.context.get('documentation', []))
        code_examples = self._format_code_examples(request.context.get('code_examples', {}))
        logs = request.context.get('logs', 'No logs provided')
        context = request.context.get('additional_context', '')
        root_cause = request.context.get('root_cause', 'Investigation in progress...')
        
        # Fill in template
        prompt = template.format(
            query=request.query,
            diagnostics=diagnostics,
            documentation=documentation,
            code_examples=code_examples,
            logs=logs,
            context=context,
            requirement=request.query,
            root_cause=root_cause
        )
        
        return prompt
    
    def _format_diagnostics(self, diagnostics: Dict) -> str:
        """Format diagnostics data for the prompt"""
        if not diagnostics:
            return "No diagnostic data available."
        
        formatted = []
        for key, value in diagnostics.items():
            if isinstance(value, dict):
                if 'stdout' in value:
                    # Include full output for better context (up to 2000 chars)
                    output = value['stdout'][:2000]
                    formatted.append(f"**{key}:**\n```\n{output}\n```")
                elif 'error' in value:
                    formatted.append(f"**{key}:** Error - {value['error']}")
            else:
                formatted.append(f"**{key}:** {str(value)[:200]}")
        
        return '\n\n'.join(formatted) if formatted else "Diagnostics available but empty."
    
    def _format_documentation(self, docs: List[Dict]) -> str:
        """Format documentation for the prompt"""
        if not docs:
            return "No relevant documentation found."
        
        formatted = []
        for doc in docs[:3]:  # Limit to top 3 docs
            formatted.append(
                f"**{doc.get('filename', 'Unknown')}** (Score: {doc.get('score', 0)}):\n"
                f"{doc.get('snippet', '')[:300]}"
            )
        
        return '\n\n'.join(formatted)
    
    def _format_code_examples(self, examples: Dict) -> str:
        """Format code examples for the prompt"""
        if not examples or (not examples.get('python') and not examples.get('kubectl')):
            return "No code examples available."
        
        formatted = []
        
        if examples.get('python'):
            formatted.append("**Python Examples:**")
            for i, example in enumerate(examples['python'][:2], 1):
                formatted.append(f"```python\n{example[:300]}\n```")
        
        if examples.get('kubectl'):
            formatted.append("\n**Kubectl Examples:**")
            for i, example in enumerate(examples['kubectl'][:2], 1):
                formatted.append(f"```bash\n{example[:200]}\n```")
        
        return '\n\n'.join(formatted)
    
    def _query_ollama(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Query Ollama API"""
        payload = {
            'model': self.model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': self.temperature,
                'num_predict': max_tokens or self.max_tokens
            }
        }
        
        try:
            response = requests.post(
                self.api_endpoints['generate'],
                json=payload,
                timeout=60  # Longer timeout for LLM
            )
            response.raise_for_status()
            return response.json().get('response', 'No response generated')
        except requests.exceptions.Timeout:
            raise AgentProcessingError("Ollama request timed out")
        except requests.exceptions.RequestException as e:
            raise AgentProcessingError(f"Ollama query failed: {str(e)}")
    

    
    def _extract_and_validate_json(self, llm_response: str) -> Optional[Dict]:
        """
        Extract and validate JSON from LLM response.
        Works with multiple LLM formats (Ollama, OpenAI, Claude, etc.)
        Handles common LLM mistakes like comments, single quotes, etc.
        """
        import json
        import re
        
        # Step 1: Remove markdown code blocks if present
        # Handle: ```json {...}``` or ```{...}```
        cleaned = re.sub(r'```(?:json)?\s*', '', llm_response)
        cleaned = re.sub(r'```\s*$', '', cleaned)
        
        # Step 2: Find JSON object
        # Match from first { to last } - but handle truncated responses
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if not json_match:
            print(f"[DEBUG] No JSON found in response: {llm_response[:200]}")
            return None
        
        json_str = json_match.group()
        
        # Step 2.5: Check if JSON looks truncated (incomplete)
        # Count opening and closing braces/brackets
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        
        if open_braces > close_braces or open_brackets > close_brackets:
            print(f"[DEBUG] JSON appears truncated (LLM hit token limit)")
            # Try to salvage what we have by closing structures
            while json_str.count('{') > json_str.count('}'):
                json_str += '}'
            while json_str.count('[') > json_str.count(']'):
                json_str += ']'
            print(f"[DEBUG] Attempting to fix truncated JSON...")
        
        # Step 3: Clean up common LLM JSON issues
        # Remove single-line comments (// ...)
        json_str = re.sub(r'//[^\n]*', '', json_str)
        
        # Remove multi-line comments (/* ... */)
        json_str = re.sub(r'/\*[\s\S]*?\*/', '', json_str)
        
        # Fix trailing commas before } or ]
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Fix single quotes to double quotes (some LLMs do this)
        json_str = re.sub(r"(?<!\\)'", '"', json_str)
        
        # Fix unescaped newlines in strings
        json_str = re.sub(r'(?<!\\)\n(?=[^"]*"[^"]*:)', '\\n', json_str)
        
        # Step 4: Try to parse
        try:
            data = json.loads(json_str)
            
            # Step 5: Validate schema
            if not isinstance(data, dict):
                print(f"[DEBUG] JSON is not a dict: {type(data)}")
                return None
            
            if 'commands' not in data:
                print(f"[DEBUG] Missing 'commands' key in JSON")
                return None
            
            if not isinstance(data['commands'], list):
                print(f"[DEBUG] 'commands' is not a list")
                return None
            
            # Validate each command
            valid_commands = []
            for cmd_obj in data['commands']:
                if isinstance(cmd_obj, dict) and 'cmd' in cmd_obj and 'reason' in cmd_obj:
                    valid_commands.append(cmd_obj)
                else:
                    print(f"[DEBUG] Invalid command object: {cmd_obj}")
            
            if not valid_commands:
                print(f"[DEBUG] No valid commands found")
                return None
            
            data['commands'] = valid_commands
            return data
            
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON decode error: {e}")
            print(f"[DEBUG] Attempted to parse: {json_str[:500]}")
            return None
        except Exception as e:
            print(f"[DEBUG] Unexpected error in JSON extraction: {e}")
            return None
    
    def generate_diagnostic_commands(self, query: str, namespace: str = "default", pod_name: str = "") -> List[Dict[str, str]]:
        """
        Use LLM to dynamically generate appropriate kubectl commands based on query.
        Now uses DISCOVERED knowledge instead of hardcoded patterns.
        100% AI - no fallback. If Ollama unavailable, system fails gracefully.
        """
        if not self._check_ollama_available():
            raise AgentProcessingError("Ollama LLM required for command generation. Start with: ollama serve")
        
        # Get dynamic knowledge from knowledge agent
        dynamic_context = self.knowledge_agent.generate_dynamic_prompt_context()
        
        prompt = self.prompt_templates['generate_commands'].format(
            query=query,
            namespace=namespace,
            pod_name=pod_name or "not-specified",
            dynamic_knowledge=dynamic_context
        )
        
        try:
            # Use 1500 tokens for command generation (prevents JSON truncation)
            response_text = self._query_ollama(prompt, max_tokens=1500)
            
            # Use robust JSON extraction that works with multiple LLMs
            commands_data = self._extract_and_validate_json(response_text)
            
            if not commands_data:
                raise AgentProcessingError(
                    f"LLM did not return valid JSON. Check debug output above. Response: {response_text[:300]}"
                )
            
            commands = commands_data.get('commands', [])
            
            # Replace placeholders with actual values
            for cmd_obj in commands:
                if isinstance(cmd_obj, dict) and 'cmd' in cmd_obj:
                    cmd_obj['cmd'] = cmd_obj['cmd'].replace('<pod-name>', pod_name if pod_name else 'POD_NAME')
                    cmd_obj['cmd'] = cmd_obj['cmd'].replace('{namespace}', namespace)
                    cmd_obj['cmd'] = cmd_obj['cmd'].replace('<namespace>', namespace)
            
            print(f"[AI] LLM generated {len(commands)} commands dynamically")
            return commands[:5]  # Limit to 5 commands
            
        except AgentProcessingError:
            raise
        except Exception as e:
            raise AgentProcessingError(f"LLM command generation failed: {e}")
    
    def generate_action_commands(self, query: str, namespace: str = "default", pod_name: str = "") -> List[Dict[str, str]]:
        """
        Generate kubectl commands for ACTION requests (delete, create, scale, etc.).
        Unlike diagnostic commands, this generates BOTH discovery AND execution commands.
        """
        if not self._check_ollama_available():
            raise AgentProcessingError("Ollama LLM required for command generation. Start with: ollama serve")
        
        # Get dynamic knowledge from knowledge agent
        dynamic_context = self.knowledge_agent.generate_dynamic_prompt_context()
        
        prompt = self.prompt_templates['generate_action_commands'].format(
            query=query,
            namespace=namespace,
            pod_name=pod_name or "not-specified",
            dynamic_knowledge=dynamic_context
        )
        
        try:
            # Use 1500 tokens for action commands (need space for discovery + action)
            response_text = self._query_ollama(prompt, max_tokens=1500)
            
            # Use robust JSON extraction
            commands_data = self._extract_and_validate_json(response_text)
            
            if not commands_data:
                raise AgentProcessingError(
                    f"LLM did not return valid JSON for action commands. Check debug output above."
                )
            
            commands = commands_data.get('commands', [])
            
            # Replace placeholders with actual values
            for cmd_obj in commands:
                if isinstance(cmd_obj, dict) and 'cmd' in cmd_obj:
                    cmd_obj['cmd'] = cmd_obj['cmd'].replace('<pod-name>', pod_name if pod_name else 'POD_NAME')
                    cmd_obj['cmd'] = cmd_obj['cmd'].replace('{namespace}', namespace)
                    cmd_obj['cmd'] = cmd_obj['cmd'].replace('<namespace>', namespace)
            
            print(f"[AI] LLM generated {len(commands)} action commands (discovery + execution)")
            return commands[:5]  # Limit to 5 commands
            
        except AgentProcessingError:
            raise
        except Exception as e:
            raise AgentProcessingError(f"LLM action command generation failed: {e}")
    
    def learn_from_resolution(self, query: str, commands_executed: List[str], outcome: str):
        """
        Learn from successful troubleshooting session.
        This builds knowledge over time instead of hardcoding patterns.
        """
        self.knowledge_agent.learn_from_successful_resolution(query, commands_executed, outcome)
    
    def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text"""
        if not self._check_ollama_available():
            return []
        
        payload = {
            'model': self.model,
            'prompt': text
        }
        
        try:
            response = requests.post(
                self.api_endpoints['embeddings'],
                json=payload,
                timeout=10
            )
            return response.json().get('embedding', [])
        except:
            return []
    
    def health_check(self) -> bool:
        """Check if Ollama is running"""
        return self._check_ollama_available()
