"""
AI-Driven Security Policy Agent
Instead of hardcoded forbidden commands list, uses LLM to evaluate command safety
"""
import time
from typing import Dict, List, Tuple
import requests

from core.interfaces import BaseAgent, AgentRequest, AgentResponse, AgentType, AgentProcessingError


class SecurityPolicyAgent(BaseAgent):
    """
    AI-driven security evaluation - NO hardcoded forbidden commands
    Uses LLM to reason about command safety based on context
    """
    
    def initialize(self):
        """Initialize security policy agent"""
        self.agent_type = AgentType.EXECUTION
        self.ollama_url = self.config.get('ollama_url', 'http://localhost:11434')
        self.model = self.config.get('model', 'llama3.1:8b')
        
        # Permission context (configured, not hardcoded commands)
        self.allow_delete = self.config.get('allow_delete', False)
        self.allow_create = self.config.get('allow_create', False)
        self.allow_update = self.config.get('allow_update', False)
        self.read_only_mode = self.config.get('read_only_mode', True)
        
        # Security policy prompt
        self.security_prompt = """You are a security expert evaluating Kubernetes command safety.

**Command to evaluate:**
{command}

**User's original query:**
{user_query}

**Permission context:**
- Delete operations allowed: {allow_delete}
- Create operations allowed: {allow_create}
- Update operations allowed: {allow_update}
- Read-only mode: {read_only_mode}

**IMPORTANT RULES:**
1. kubectl get/describe/logs/top commands are ALWAYS SAFE (read-only)
2. If user wants to delete and delete is allowed, kubectl delete is SAFE
3. Multi-step operations are normal: first get resources, then delete them
4. Only block if command contains actual dangerous operations like: rm, dd, mkfs, format

**Your task:**
Evaluate if this specific kubectl command is safe to execute.

**Output JSON only:**
{{
  "safe": true/false,
  "reason": "brief explanation",
  "risk_level": "low|medium|high",
  "suggestion": "alternative if unsafe, null otherwise"
}}

Examples:
- kubectl get pods → {{"safe": true, "reason": "read-only operation"}}
- kubectl delete pod xyz (when allow_delete=true) → {{"safe": true, "reason": "delete allowed"}}
- kubectl delete pod xyz (when allow_delete=false) → {{"safe": false, "reason": "delete not permitted"}}
- rm -rf / → {{"safe": false, "reason": "dangerous shell command"}}"""
    
    def evaluate_command_safety(self, command: str, user_query: str) -> Tuple[bool, str, str]:
        """
        Use LLM to evaluate command safety instead of hardcoded checks.
        Returns: (is_safe, reason, suggestion)
        """
        # Check if Ollama is available
        if not self._check_ollama_available():
            # Fallback to basic permission check if LLM unavailable
            return self._basic_permission_check(command)
        
        # Build prompt
        prompt = self.security_prompt.format(
            command=command,
            user_query=user_query,
            allow_delete=self.allow_delete,
            allow_create=self.allow_create,
            allow_update=self.allow_update,
            read_only_mode=self.read_only_mode
        )
        
        try:
            # Query LLM for safety evaluation
            response_text = self._query_ollama(prompt)
            
            # Parse JSON response
            import json
            import re
            
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                safety_eval = json.loads(json_match.group())
                
                return (
                    safety_eval.get('safe', False),
                    safety_eval.get('reason', 'LLM safety evaluation'),
                    safety_eval.get('suggestion', '')
                )
            else:
                # LLM didn't return proper JSON, use basic check
                return self._basic_permission_check(command)
                
        except Exception as e:
            print(f"[WARN] AI security evaluation failed: {e}, using basic checks")
            return self._basic_permission_check(command)
    
    def _basic_permission_check(self, command: str) -> Tuple[bool, str, str]:
        """
        Basic permission check as fallback when LLM unavailable.
        Permission-based logic, minimal hardcoding.
        """
        command_lower = command.lower()
        
        # CRITICAL: Read operations should always be allowed
        read_operations = ['get', 'describe', 'logs', 'top', 'explain', 'api-resources', 'api-versions']
        is_read_operation = any(f'kubectl {op}' in command_lower for op in read_operations)
        
        # If it's a read operation, allow it regardless of mode
        if is_read_operation:
            return (True, "Read operation permitted", "")
        
        # Check permissions based on operation type detected via general patterns
        # Not perfect but better than nothing when AI down
        
        if self.read_only_mode:
            # Block anything that looks like a write operation
            write_patterns = ['delete', 'create', 'apply', 'patch', 'edit', 'scale', 'remove', 'destroy', 'rm']
            if any(pattern in command_lower for pattern in write_patterns):
                return (False, "Write operation blocked in read-only mode", "Switch to read-write mode")
        
        if not self.allow_delete and 'delete' in command_lower:
            return (False, "Delete operation not permitted", "Enable allow_delete in config")
        
        if not self.allow_create:
            create_patterns = ['create', 'apply', 'new', 'add']
            if any(pattern in command_lower for pattern in create_patterns):
                return (False, "Create operation not permitted", "Enable allow_create in config")
        
        if not self.allow_update:
            update_patterns = ['patch', 'edit', 'scale', 'update', 'modify', 'change']
            if any(pattern in command_lower for pattern in update_patterns):
                return (False, "Update operation not permitted", "Enable allow_update in config")
        
        return (True, "Command permitted by basic check", "")
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f'{self.ollama_url}/api/tags', timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _query_ollama(self, prompt: str) -> str:
        """Query Ollama API"""
        payload = {
            'model': self.model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': 0.3,  # Lower temperature for security decisions
                'num_predict': 200
            }
        }
        
        response = requests.post(
            f'{self.ollama_url}/api/generate',
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json().get('response', '')
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """Process security evaluation request"""
        start_time = time.time()
        
        try:
            command = request.context.get('command', '')
            user_query = request.query
            
            is_safe, reason, suggestion = self.evaluate_command_safety(command, user_query)
            
            execution_time = time.time() - start_time
            
            return AgentResponse(
                success=is_safe,
                data={
                    'safe': is_safe,
                    'reason': reason,
                    'suggestion': suggestion
                },
                error=None if is_safe else reason,
                metadata={'ai_evaluated': self._check_ollama_available()},
                agent_type=self.agent_type,
                execution_time=execution_time
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            return AgentResponse(
                success=False,
                data={},
                error=str(e),
                metadata={},
                agent_type=self.agent_type,
                execution_time=execution_time
            )
    
    def health_check(self) -> bool:
        """Check if security agent is ready"""
        return True  # Basic permission checks always available
