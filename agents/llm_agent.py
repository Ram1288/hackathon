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
        
        # Specialized prompts for K8s troubleshooting
        self.prompt_templates = {
            'generate_commands': """You are a Kubernetes expert. Analyze the user's query and dynamically determine the EXACT kubectl commands needed.

**User Query:**
{query}

**Available Context:**
- Namespace: {namespace}
- Pod Name: {pod_name}

**Available kubectl Commands (READ-ONLY):**
- kubectl get [pods|nodes|services|deployments|namespaces|events|configmaps|secrets|pvc|pv|ingress|networkpolicies|endpoints|serviceaccounts|rolebindings]
- kubectl describe [resource-type] [resource-name] -n [namespace]
- kubectl logs [pod-name] -n [namespace] [--previous] [--tail=N] [--since=TIME]
- kubectl top [nodes|pods] -n [namespace]
- kubectl get events -n [namespace] [--sort-by=.lastTimestamp] [--field-selector=...]
- kubectl get pods --show-labels -n [namespace] (useful for network policy debugging)

**Available kubectl Commands (WRITE - use when explicitly requested):**
- kubectl delete pods -n [namespace] --field-selector=status.phase!=Running (delete non-running pods)
- kubectl delete pod [specific-pod-name] -n [namespace] (delete specific pod)
- kubectl delete [resource-type] [resource-name] -n [namespace] (delete specific resource)

**Your Task:**
Analyze the query intent and generate EXECUTABLE commands (no placeholders!).

**CRITICAL RULES:**
1. ❌ NEVER use placeholders like POD_NAME, <pod-name>, {pod_name}
2. ✅ Use field-selectors for bulk operations: --field-selector=status.phase!=Running
3. ✅ If query mentions specific pod name, use it directly
4. ✅ Generate commands that execute WITHOUT manual substitution

**DELETE Operations - Correct Patterns:**
❌ WRONG: kubectl delete pod POD_NAME -n {namespace}
❌ WRONG: kubectl delete pod <pod-name> -n {namespace}
✅ CORRECT: kubectl delete pods -n {namespace} --field-selector=status.phase!=Running
✅ CORRECT: kubectl delete pod grafana-operator-xyz -n {namespace} (if specific name in query)

**DESCRIBE Operations - Correct Patterns:**
❌ WRONG: kubectl describe pod POD_NAME -n {namespace}
✅ CORRECT: Skip describe in bulk operations (not needed for delete)
✅ CORRECT: kubectl describe pod grafana-operator-xyz -n {namespace} (if specific name given)

**Think:**
- User says "delete pods not running" → Use field-selector to delete directly
- User says "delete pod grafana-xyz" → Use actual name grafana-xyz
- User says "check pod status" → kubectl get pods (no placeholders)

**Common Troubleshooting Patterns:**
- Pod crashes/restarts → describe pod + logs --previous + events
- Resource issues (CPU/Memory) → top pods/nodes + describe pod + events
- Config issues → get configmaps/secrets + describe pod + logs
- Network connectivity issues → get services + describe service + get endpoints + get networkpolicies
- Network policy blocking → get networkpolicies + describe networkpolicy + get pods --show-labels
- Certificate/TLS issues → describe pod + logs + get secrets + describe ingress
- Storage/PVC issues → get pvc + describe pvc + get pv + describe pod (check volume mounts)
- Slow performance → top pods/nodes + logs + describe pod
- Permission/RBAC errors → describe pod + logs + get serviceaccounts + get rolebindings
- ImagePullBackOff → describe pod + events + get secrets (check image pull secrets)
- DNS resolution issues → describe pod + logs + get services + get endpoints

**Output Format (JSON only, no markdown, no explanation):**
{{
  "commands": [
    {{"cmd": "actual kubectl command here", "reason": "why this command"}},
    ...max 5 commands
  ]
}}

Now analyze the user query and generate the appropriate kubectl commands in JSON format:""",
            
            'troubleshoot': """You are a Kubernetes and RHEL systems expert. A user has a query about their Kubernetes cluster.

**User Query:**
{query}

**Diagnostic Results from kubectl:**
{diagnostics}

**Relevant Documentation:**
{documentation}

**Code Examples Available:**
{code_examples}

IMPORTANT: First, analyze the diagnostic results carefully. If the kubectl commands executed successfully and returned results (pods, services, etc.), acknowledge this in your response. The user may be asking to list/view resources rather than troubleshoot a problem.

If this is an informational query (list, show, get resources):
- Summarize what was found in the diagnostic results
- Provide a brief explanation of the resources
- Suggest useful follow-up queries or commands

If this is a troubleshooting query:
1. **Root Cause Analysis**: Identify the likely cause of the issue based on the diagnostic data
2. **Immediate Solution**: Provide specific commands or steps to fix the issue
3. **Verification**: How to verify the fix worked
4. **Prevention**: Steps to prevent this issue in the future

Be concise, technical, and actionable. Base your analysis on the actual diagnostic results provided.""",
            
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
        
        # Fill in template
        prompt = template.format(
            query=request.query,
            diagnostics=diagnostics,
            documentation=documentation,
            code_examples=code_examples,
            logs=logs,
            context=context,
            requirement=request.query
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
    
    def _query_ollama(self, prompt: str) -> str:
        """Query Ollama API"""
        payload = {
            'model': self.model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': self.temperature,
                'num_predict': self.max_tokens
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
    

    
    def generate_diagnostic_commands(self, query: str, namespace: str = "default", pod_name: str = "") -> List[Dict[str, str]]:
        """
        Use LLM to dynamically generate appropriate kubectl commands based on query.
        This is TRUE AI-driven decision making - no hardcoded patterns.
        100% AI - no fallback. If Ollama unavailable, system fails gracefully.
        """
        if not self._check_ollama_available():
            raise AgentProcessingError("Ollama LLM required for command generation. Start with: ollama serve")
        
        prompt = self.prompt_templates['generate_commands'].format(
            query=query,
            namespace=namespace,
            pod_name=pod_name or "not-specified"
        )
        
        try:
            response_text = self._query_ollama(prompt)
            
            # Extract JSON from response
            import json
            import re
            
            json_match = re.search(r'\{[\s\S]*?"commands"[\s\S]*?\[[\s\S]*?\][\s\S]*?\}', response_text)
            if json_match:
                commands_data = json.loads(json_match.group())
                commands = commands_data.get('commands', [])
                
                # Replace placeholders with actual values
                for cmd_obj in commands:
                    if isinstance(cmd_obj, dict) and 'cmd' in cmd_obj:
                        cmd_obj['cmd'] = cmd_obj['cmd'].replace('<pod-name>', pod_name if pod_name else 'POD_NAME')
                        cmd_obj['cmd'] = cmd_obj['cmd'].replace('{namespace}', namespace)
                
                print(f"[AI] LLM generated {len(commands)} commands dynamically")
                return commands[:5]  # Limit to 5 commands
            else:
                raise AgentProcessingError(f"LLM response didn't contain valid JSON: {response_text[:200]}")
        except Exception as e:
            raise AgentProcessingError(f"LLM command generation failed: {e}")
    
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
