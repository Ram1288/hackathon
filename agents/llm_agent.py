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
            'generate_commands': """You are a Kubernetes expert. Generate kubectl or helm commands based on the user query.

**User Query:**
{query}

**Context:**
- Namespace: {namespace}
- Pod Name: {pod_name}

{dynamic_knowledge}

**YOUR TASK:**
Analyze the query and generate appropriate kubectl or helm commands. Return ONLY valid JSON - no explanations, no thinking process, no markdown.

**COMMAND GENERATION RULES:**
1. Extract resource/release names from query → use them exactly in commands (NO placeholders)
2. Helm queries (releases, charts, install, upgrade) → helm commands
3. K8s resource queries (pods, deployments, services) → kubectl commands  
4. For bulk/filtered operations → use --field-selector or -l (labels), NOT placeholders
5. Apply namespace: -n {namespace} (or --all-namespaces if query specifies)
6. Maximum 3 commands - each immediately executable

**CRITICAL - "NOT RUNNING" QUERIES:**
- "not running" / "debug" / "troubleshoot" = ANY resource not in healthy operational state
- This means: Check actual pod list first to see STATUS column (shows real state!)
- "Not running" includes: Failed, Pending with errors, CrashLoopBackOff, ImagePullBackOff, CreateContainerConfigError, Completed, etc.
- Don't filter by ONLY Ready==False - that misses pods that never started (Pending with errors)
  
**COMPREHENSIVE APPROACH:**
- First: Get all resources to see their actual STATUS (not just phase)
- Then: Investigate those with problems visible in STATUS column
- Status column shows: CreateContainerConfigError, CrashLoopBackOff, ImagePullBackOff, Error, Completed, etc.
- These are ALL "not running" states - not just Ready==False!
  
**STATUS-FIRST DEBUGGING:**
- Don't filter by phase alone - phase is superficial
- Inspect status object structure - that's where truth lives
- For Pods: status.containerStatuses[].ready + state.waiting.reason
- For Deployments: status.conditions[] + readyReplicas vs replicas
- For any resource: status.conditions[] tells the story

**POD READINESS REALITY:**
Example: Pending phase with CreateContainerConfigError
- phase: Pending (just metadata)
- status.conditions[type=Ready].status: False (not ready!)
- status.conditions[type=Ready].reason: ContainersNotReady (why not ready)
- status.containerStatuses[0].ready: false (which container)
- status.containerStatuses[0].state.waiting.reason: CreateContainerConfigError (root cause!)
- status.containerStatuses[0].state.waiting.message: "runAsNonRoot and image will run as root"

**YOUR KUBECTL EXPERTISE:**
Use your knowledge of kubectl to:
- Retrieve complete resource objects with status fields
- Query and filter specific status information  
- Discover resources with specific conditions
- Correlate status across resource hierarchy
- Access events for chronological context

**OUTPUT FORMAT WISDOM:**
- JSON/YAML output = Complete status object structure (machine-readable)
  → Contains: status.conditions[], containerStatuses[], all status fields
  → Enables: Programmatic filtering, field extraction, automation
  
- Human-formatted output = Summary without structured status object
  → Contains: Overview, events timeline, readable summary
  → Enables: Quick visual inspection, understanding context
  → Limitation: Cannot extract status.conditions[] programmatically

**FORMAT SELECTION THINKING:**
- Query needs status object inspection? → Structured format (JSON/YAML)
- Query needs specific field extraction? → Structured format with field query
- Query needs human-readable overview? → Human format
- Query needs both? → Use appropriate format for each step

Choose the format that matches the data access pattern needed.

**YOUR KUBECTL EXPERTISE:**
Use your knowledge of kubectl to:
- Discover pods and their actual states (not just phases)
- Investigate container readiness and errors
- Access pod events and logs
- Generate commands that reveal the complete picture, not just one filtered view

**OUTPUT FORMAT (return ONLY this, nothing else):**
{{
  "commands": [
    {{"cmd": "<your-generated-command>", "reason": "<brief-reason>"}},
    {{"cmd": "<your-generated-command>", "reason": "<brief-reason>"}}
  ]
}}

**CRITICAL:** Return ONLY the JSON object above. Do NOT include:
- ❌ Explanations before or after JSON
- ❌ Markdown code blocks (```json)
- ❌ Step-by-step thinking process
- ❌ Multiple JSON objects
- ❌ Comments in JSON (no // or /* */)
- ❌ Placeholders like <pod-name>, POD_NAME
- ❌ Unescaped quotes in commands (use single quotes for shell/jq filters)

**JSON FORMATTING:**
- For jq/shell commands: use SINGLE quotes to avoid escaping
- GOOD: "kubectl get pods -o json | jq '.items[]'"
- BAD: "kubectl get pods -o json | jq ".items[]"" (breaks JSON!)

Generate commands now:""",

            'generate_action_commands': """You are a Kubernetes expert. Generate ACTION commands (delete, scale, install, upgrade, etc.).

**User Action Request:**
{query}

**Context:**
- Namespace: {namespace}
- Pod Name: {pod_name}

{dynamic_knowledge}

**YOUR TASK:**
Generate kubectl or helm commands to execute the requested action.

**KEY PRINCIPLES:**
- For bulk operations → use --field-selector or -l (labels), NOT placeholders
- For specific resources → use exact names from query
- Discovery before destructive actions when helpful
- Namespace: -n {namespace} (or --all-namespaces if specified)

**SEMANTIC UNDERSTANDING (CRITICAL):**
- "not running" / "debug not running" = ANY pod not in healthy operational state
  → Includes: Pending with errors, Failed, CrashLoopBackOff, CreateContainerConfigError, ImagePullBackOff, Completed, Error, etc.
  → NOT just Ready==False - must check STATUS column which shows actual state
  → First get pod list to see STATUS, then investigate those with problems
  
- "failed" = Pods in Failed phase specifically (narrow)

- "completed" = Pods in Succeeded phase specifically (narrow)
  
- "errors" / "container errors" = Container-level issues (check container status, events, logs)

**COMPREHENSIVE "NOT RUNNING" APPROACH:**
- "Not running" is broad - means pod isn't in healthy Running state
- STATUS column reveals truth: CreateContainerConfigError, CrashLoopBackOff, ImagePullBackOff, Error, Completed, etc.
- Don't assume only one phase or condition - get pod list first to see real STATUS
- Then drill down into specific pods showing problems in STATUS column

**CRITICAL KUBERNETES INSIGHT:**
- Pod Phase (Pending, Running, Failed, Succeeded, Unknown) ≠ Pod Operational State
- TRUE source of truth: **status object** (conditions + containerStatuses)
  
**STATUS STRUCTURE WISDOM:**
For ANY K8s resource (Pod, Deployment, StatefulSet, DaemonSet, Job, CronJob):
- status.conditions[] = Array of condition types (Ready, ContainersReady, PodScheduled, etc.)
  → condition.type = what aspect (Ready, Available, Progressing)
  → condition.status = True/False/Unknown
  → condition.reason = WHY (ContainersNotReady, ImagePullBackOff, etc.)
  → condition.message = detailed explanation
  
- status.containerStatuses[] = Array of container states
  → ready = true/false (container operational state)
  → state.waiting.reason = why not started (CreateContainerConfigError, ImagePullBackOff, etc.)
  → state.running = container running
  → state.terminated.reason = why stopped (Error, Completed, OOMKilled, etc.)

**THE TRUTH HIERARCHY:**
1. STATUS column (what you see in pod list) = Actual operational state
2. status.containerStatuses[].ready = Is container actually working?
3. status.containerStatuses[].state.waiting.reason = Why not? (root cause)
4. status.conditions[].reason = Higher-level reason
5. status.phase = High-level state (Pending/Running/Failed) - least specific

**CRITICAL REALIZATION:**
- "Not running" query → First get pod list to see STATUS column (shows real problems!)
- Root cause → Drill into status.containerStatuses[].state.waiting.reason
- Don't filter by only one condition - "not running" is broad, encompasses many states

**APPLIES TO ALL RESOURCES:**
- Deployment: status.conditions[type=Available], status.replicas vs status.readyReplicas
- StatefulSet: status.currentReplicas vs status.readyReplicas, status.conditions[]
- DaemonSet: status.numberReady vs status.desiredNumberScheduled
- Job: status.conditions[type=Complete/Failed], status.succeeded/failed
- CronJob: status.lastScheduleTime, status.active[]

**YOUR KUBECTL EXPERTISE:**
You know how to:
- Get resource status in JSON/YAML format to inspect status object
- Query specific fields using jsonpath or custom-columns
- Filter resources by condition status
- Correlate status across resource types (Pod → ReplicaSet → Deployment)

Generate commands that reveal the status object truth, not just surface-level phase.

**YOUR KUBECTL EXPERTISE:**
You know kubectl commands to:
- List pods with their actual operational states
- Filter by phases, labels, field selectors
- Describe pods to see events and container states  
- Extract specific information using output formats (json, jsonpath, wide)
- Chain commands to discover and act on resources

Use this knowledge to generate appropriate commands based on the query intent.

**AVOID ASSUMPTIONS:**
- ❌ "not running" does NOT mean only phase=Failed
- ❌ Don't filter to single phase when query asks for comprehensive check
- ❌ Ready column matters more than phase for operational status

**OUTPUT FORMAT (return ONLY this JSON, nothing else):**
{{
  "commands": [
    {{"cmd": "<your-command>", "reason": "<why>"}},
    {{"cmd": "<your-command>", "reason": "<why>"}}
  ]
}}

**JSON FORMATTING RULES:**
- Escape quotes inside command strings: use single quotes for shell commands or escape with \\
- Example GOOD: {{"cmd": "kubectl get pods -o json | jq '.items[]'"}}
- Example BAD: {{"cmd": "kubectl get pods -o json | jq ".items[]""}} (unescaped quotes)
- Use single quotes for jq/shell filters to avoid JSON escaping issues

Generate executable commands for: {query}""",
            
            'troubleshoot': """You are a Kubernetes and RHEL systems expert. A user has a query about their Kubernetes cluster.

**User Query:**
{query}

**Investigation Root Cause (AI-determined):**
{root_cause}

**Diagnostic Results from kubectl:**
{diagnostics}

**Relevant Documentation:**
{documentation}

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

Provide ONLY the Python code, well-commented.""",
            
            'explain': """You are a Kubernetes expert. Explain the following concept or command clearly and concisely.

**Query:**
{query}

**Context:**
{context}

Provide:
1. A clear explanation
2. When and why you would use this
3. Common pitfalls to avoid

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
        logs = request.context.get('logs', 'No logs provided')
        context = request.context.get('additional_context', '')
        root_cause = request.context.get('root_cause', 'Investigation in progress...')
        
        # Fill in template
        prompt = template.format(
            query=request.query,
            diagnostics=diagnostics,
            documentation=documentation,
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
        # Remove invalid control characters (except \n, \r, \t)
        json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', json_str)
        
        # Remove single-line comments (// ...)
        json_str = re.sub(r'//[^\n]*', '', json_str)
        
        # Remove multi-line comments (/* ... */)
        json_str = re.sub(r'/\*[\s\S]*?\*/', '', json_str)
        
        # Fix trailing commas before } or ]
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
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
            
            # AI-First Approach: Detect placeholders and ask LLM to fix them
            commands_with_placeholders = self._detect_placeholders(commands)
            
            if commands_with_placeholders:
                # LLM generated placeholders - ask it to refine
                print(f"[AI] Detected placeholders in commands, requesting refinement...")
                commands = self._refine_commands_with_llm(query, commands, namespace, pod_name)
            
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
            
            # AI-First Approach: Detect placeholders and ask LLM to fix them
            commands_with_placeholders = self._detect_placeholders(commands)
            
            if commands_with_placeholders:
                # LLM generated placeholders - ask it to refine
                print(f"[AI] Detected placeholders in commands, requesting refinement...")
                commands = self._refine_commands_with_llm(query, commands, namespace, pod_name)
            
            print(f"[AI] LLM generated {len(commands)} action commands (discovery + execution)")
            return commands[:5]  # Limit to 5 commands
            
        except AgentProcessingError:
            raise
        except Exception as e:
            raise AgentProcessingError(f"LLM action command generation failed: {e}")
    
    def _detect_placeholders(self, commands: List[Dict]) -> List[Dict]:
        """
        AI-First: Detect if LLM generated placeholders instead of actual commands.
        Returns list of commands containing placeholders.
        
        CRITICAL: Only detect ACTUAL placeholders, not valid kubectl arguments.
        Valid: --field-selector status.phase=Failed (kubectl enum value)
        Invalid: <pod-name>, POD_NAME, {release} (placeholder variables)
        """
        import re
        
        # Whitelist: Valid kubectl/helm enum values and common command words
        # These are NOT placeholders - they're legitimate K8s API values
        valid_k8s_terms = r'\b(Failed|Unknown|Succeeded|Running|Pending|Error|CrashLoopBackOff|ImagePullBackOff|Completed|Terminating|READY|STATUS|AGE|NAME|NAMESPACE)\b'
        
        placeholder_patterns = [
            r'<[^>]+>',                    # <pod-name>, <pod-names>, <release-name>
            r'\{[^}]+\}',                  # {pod_name}, {release} (not JSON output format)
            r'\$[A-Z_][A-Z_0-9]*',         # $POD_NAME, $RELEASE (shell variables)
            r'\bPOD[_-]?NAMES?\b',         # POD_NAME, POD-NAME, POD_NAMES (obvious placeholders)
            r'\bRELEASE[_-]?NAMES?\b',     # RELEASE_NAME, RELEASE-NAME
            r'\bNAMESPACE_NAME\b',         # NAMESPACE_NAME
            r'\bDEPLOYMENT[_-]?NAME\b',    # DEPLOYMENT_NAME
        ]
        
        commands_with_placeholders = []
        for cmd_obj in commands:
            cmd = cmd_obj.get('cmd', '')
            
            # First check if it's a valid K8s term
            if re.search(valid_k8s_terms, cmd, re.IGNORECASE):
                # Command contains valid K8s enum values - check more carefully
                # Only flag if it has OBVIOUS placeholders
                for pattern in placeholder_patterns[:3]:  # Only check <>, {}, $ patterns
                    if re.search(pattern, cmd):
                        print(f"[DEBUG] Placeholder detected in: {cmd}")
                        commands_with_placeholders.append(cmd_obj)
                        break
            else:
                # No K8s terms - apply all patterns
                for pattern in placeholder_patterns:
                    if re.search(pattern, cmd, re.IGNORECASE):
                        print(f"[DEBUG] Placeholder detected in: {cmd}")
                        commands_with_placeholders.append(cmd_obj)
                        break
        
        return commands_with_placeholders
    
    def _refine_commands_with_llm(self, original_query: str, commands: List[Dict], namespace: str, pod_name: str) -> List[Dict]:
        """
        AI-First: Ask LLM to refine commands that contain placeholders.
        Let LLM reason about the correct approach using its training knowledge.
        """
        refinement_prompt = f"""You generated commands with PLACEHOLDERS. Fix them.

Query: "{original_query}"
Namespace: {namespace}

Your output has placeholders (like <pod-names>, POD_NAME, etc):
{json.dumps(commands, indent=2)}

ISSUE: Placeholders cannot be executed. Commands must be immediately runnable.

TASK: Regenerate as executable commands. Use your kubectl expertise to:
- For bulk operations → use --field-selector or -l (label selectors)
- For specific resources → extract actual names from the query
- Ensure all commands can run without manual replacement

Return ONLY JSON:
{{
  "commands": [
    {{"cmd": "executable-command", "reason": "why"}},
    {{"cmd": "executable-command", "reason": "why"}}
  ]
}}"""
        
        try:
            response_text = self._query_ollama(refinement_prompt, max_tokens=1000)
            refined_data = self._extract_and_validate_json(response_text)
            
            if refined_data and 'commands' in refined_data:
                # Verify no placeholders in refined commands
                still_has_placeholders = self._detect_placeholders(refined_data['commands'])
                if still_has_placeholders:
                    print(f"[AI] ⚠️  Refinement still has placeholders! Filtering them out...")
                    return self._fallback_placeholder_removal(commands, namespace, original_query)
                
                print(f"[AI] ✓ Successfully refined {len(refined_data['commands'])} commands")
                return refined_data['commands']
            else:
                print(f"[AI] Refinement returned invalid JSON, filtering placeholders...")
                return self._fallback_placeholder_removal(commands, namespace, original_query)
                
        except Exception as e:
            print(f"[AI] Refinement error: {e}, filtering placeholders...")
            return self._fallback_placeholder_removal(commands, namespace, original_query)
    
    def _fallback_placeholder_removal(self, commands: List[Dict], namespace: str, query: str) -> List[Dict]:
        """
        TRUE AI-FIRST: If LLM refinement fails, we don't fall back to hardcoded patterns.
        Instead, we filter out placeholder commands and return only safe, executable ones.
        If nothing is executable, return empty list - forcing user to rephrase.
        
        Uses SAME logic as _detect_placeholders to avoid false positives.
        """
        import re
        
        print(f"[AI] ⚠️  LLM refinement failed. Filtering placeholder commands...")
        
        # Whitelist: Valid kubectl/helm values (not placeholders)
        valid_k8s_terms = r'\b(Failed|Unknown|Succeeded|Running|Pending|Error|CrashLoopBackOff|ImagePullBackOff|Completed|Terminating|READY|STATUS|AGE|NAME|NAMESPACE)\b'
        
        # Actual placeholder patterns
        obvious_placeholders = [
            r'<[^>]+>',                    # <pod-name>, <release-name>
            r'\{[^}]+\}',                  # {pod_name}, {release}
            r'\$[A-Z_][A-Z_0-9]*',         # $POD_NAME, $RELEASE
            r'\bPOD[_-]?NAMES?\b',         # POD_NAME, POD-NAME
            r'\bRELEASE[_-]?NAMES?\b',     # RELEASE_NAME
            r'\bNAMESPACE_NAME\b',
            r'\bDEPLOYMENT[_-]?NAME\b',
        ]
        
        safe_commands = []
        for cmd_obj in commands:
            cmd = cmd_obj.get('cmd', '')
            
            # Check for OBVIOUS placeholders only
            has_placeholder = False
            for pattern in obvious_placeholders:
                if re.search(pattern, cmd, re.IGNORECASE):
                    # But exclude valid K8s enum values
                    if not (pattern == obvious_placeholders[1] and '-o jsonpath=' in cmd):  # Allow JSONPath
                        has_placeholder = True
                        break
            
            if not has_placeholder:
                # Command is safe and executable
                safe_commands.append(cmd_obj)
                print(f"[AI] ✓ Keeping executable command: {cmd}")
            else:
                # Command has placeholders - skip it
                print(f"[AI] ✗ Skipping command with placeholder: {cmd}")
        
        if not safe_commands:
            print(f"[AI] ⚠️  No executable commands available. LLM needs better guidance.")
            print(f"[AI] Suggestion: User should rephrase query with more specific details.")
        
        return safe_commands
    
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
