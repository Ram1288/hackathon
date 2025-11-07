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

**Your Task:**
Analyze the query intent and generate appropriate commands. Think like a K8s expert:
- What information is needed to answer this query?
- Which resources need inspection?
- What's the logical order of investigation?

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

Think step-by-step about what diagnostics are needed, then output JSON:""",
            
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
                return self._create_fallback_response(request, start_time)
            
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
            # Try fallback response
            return self._create_fallback_response(request, start_time, error=str(e))
    
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
        """Determine which prompt template to use"""
        query_lower = request.query.lower()
        
        if 'script' in query_lower or 'generate' in query_lower or 'write code' in query_lower:
            return 'generate_script'
        elif 'log' in query_lower and ('analyze' in query_lower or 'check' in query_lower):
            return 'analyze_logs'
        elif 'explain' in query_lower or 'what is' in query_lower or 'how does' in query_lower:
            return 'explain'
        elif 'optimize' in query_lower or 'improve' in query_lower or 'performance' in query_lower:
            return 'optimize'
        else:
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
    
    def _create_fallback_response(
        self, 
        request: AgentRequest, 
        start_time: float,
        error: Optional[str] = None
    ) -> AgentResponse:
        """Create a fallback response when Ollama is not available"""
        fallback_message = self._generate_rule_based_response(request)
        
        execution_time = time.time() - start_time
        
        return AgentResponse(
            success=True,
            data={
                'response': fallback_message,
                'prompt_type': 'fallback',
                'model': 'rule-based-fallback'
            },
            error=error,
            metadata={
                'ollama_available': False,
                'fallback_mode': True
            },
            agent_type=self.agent_type,
            execution_time=execution_time
        )
    
    def _generate_rule_based_response(self, request: AgentRequest) -> str:
        """Generate a rule-based response when LLM is not available"""
        query_lower = request.query.lower()
        
        # Check for common K8s issues
        if 'crashloop' in query_lower or 'backoff' in query_lower:
            return """**CrashLoopBackOff Troubleshooting:**

1. Check pod logs: `kubectl logs <pod-name> -n <namespace> --previous`
2. Describe the pod: `kubectl describe pod <pod-name> -n <namespace>`
3. Check resource limits: `kubectl get pod <pod-name> -n <namespace> -o yaml | grep -A 5 resources`

**Common Causes:**
- Application crashes on startup
- Missing environment variables or config
- Insufficient resources
- Failed liveness/readiness probes

**Note:** Ollama LLM is not available. Install and start Ollama for more detailed analysis."""
        
        elif 'imagepull' in query_lower:
            return """**ImagePullBackOff Troubleshooting:**

1. Verify image name: `kubectl describe pod <pod-name> -n <namespace>`
2. Check image exists: Verify in your container registry
3. Check credentials: `kubectl get secrets -n <namespace>`

**Common Causes:**
- Incorrect image name or tag
- Private registry without imagePullSecret
- Network connectivity issues
- Registry authentication failure

**Note:** Ollama LLM is not available. Install and start Ollama for more detailed analysis."""
        
        elif 'oom' in query_lower or 'memory' in query_lower:
            return """**OOM (Out of Memory) Troubleshooting:**

1. Check events: `kubectl get events -n <namespace> --sort-by='.lastTimestamp'`
2. Review resource limits: `kubectl describe pod <pod-name> -n <namespace>`
3. Check memory usage: `kubectl top pod <pod-name> -n <namespace>`

**Solutions:**
- Increase memory limits
- Optimize application memory usage
- Check for memory leaks

**Note:** Ollama LLM is not available. Install and start Ollama for more detailed analysis."""
        
        else:
            return f"""**Troubleshooting Guide:**

I've detected your issue: "{request.query}"

**General Kubernetes Troubleshooting Steps:**

1. **Check Pod Status:** `kubectl get pods -n <namespace>`
2. **View Pod Details:** `kubectl describe pod <pod-name> -n <namespace>`
3. **Check Logs:** `kubectl logs <pod-name> -n <namespace>`
4. **Review Events:** `kubectl get events -n <namespace> --sort-by='.lastTimestamp'`
5. **Check Resources:** `kubectl top pods -n <namespace>`

**Note:** Ollama LLM is not available. For more detailed, AI-powered analysis:
1. Install Ollama: `curl -fsSL https://ollama.ai/install.sh | sh`
2. Pull Llama model: `ollama pull llama3.1:8b`
3. Start Ollama service

For now, use the diagnostic commands above to gather more information."""
    
    def generate_diagnostic_commands(self, query: str, namespace: str = "default", pod_name: str = "") -> List[Dict[str, str]]:
        """
        Use LLM to dynamically generate appropriate kubectl commands based on query.
        This is TRUE AI-driven decision making - no hardcoded patterns.
        """
        if not self._check_ollama_available():
            print("[WARN] Ollama unavailable - falling back to minimal diagnostics")
            return []  # Return empty, let execution agent handle minimal fallback
        
        prompt = self.prompt_templates['generate_commands'].format(
            query=query,
            namespace=namespace,
            pod_name=pod_name or "not-specified"
        )
        
        try:
            response_text = self._query_ollama(prompt)
            
            # Try to extract JSON from response
            import json
            import re
            
            # Find JSON in the response (handle both with and without markdown)
            json_match = re.search(r'\{[\s\S]*?"commands"[\s\S]*?\[[\s\S]*?\][\s\S]*?\}', response_text)
            if json_match:
                commands_data = json.loads(json_match.group())
                commands = commands_data.get('commands', [])
                
                # Replace placeholders with actual values
                for cmd_obj in commands:
                    if isinstance(cmd_obj, dict) and 'cmd' in cmd_obj:
                        cmd_obj['cmd'] = cmd_obj['cmd'].replace('<pod-name>', pod_name if pod_name else 'POD_NAME')
                        cmd_obj['cmd'] = cmd_obj['cmd'].replace('{namespace}', namespace)
                
                print(f"[DEBUG] LLM generated {len(commands)} commands dynamically")
                return commands[:5]  # Limit to 5 commands
            else:
                print(f"[WARN] LLM response didn't contain valid JSON: {response_text[:200]}")
                return []  # Let execution agent handle fallback
        except Exception as e:
            print(f"[ERROR] LLM command generation failed: {e}")
            return []  # Let execution agent handle fallback
    
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
