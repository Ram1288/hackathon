"""Execution Agent for RHEL VM with Kubernetes access"""
import subprocess
import json
import yaml
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

from core.interfaces import BaseAgent, AgentRequest, AgentResponse, AgentType, AgentProcessingError


class ExecutionAgent(BaseAgent):
    """
    Execution agent for RHEL VM with K8s access
    Supports both kubectl commands and Python K8s client
    Can execute commands locally or via SSH (for demo, we use local execution)
    """
    
    def initialize(self):
        """Initialize execution agent"""
        self.agent_type = AgentType.EXECUTION
        self.ssh_enabled = self.config.get('ssh_enabled', False)
        self.ssh_client = None
        self.k8s_available = self._check_kubectl_available()
        
        self.execution_modes = {
            'kubectl': self._execute_kubectl,
            'shell': self._execute_shell,
            'python_k8s': self._execute_python_k8s
        }
        
        # Safety: forbidden commands for security
        self.forbidden_commands = self.config.get('forbidden_commands', [
            'rm -rf', 'destroy', 'mkfs', 'dd if='
        ])
        
        # Permission flags - allow controlled operations when explicitly requested
        self.allow_delete = self.config.get('allow_delete', False)
        self.allow_create = self.config.get('allow_create', False)
        self.allow_update = self.config.get('allow_update', False)
        self.read_only_mode = self.config.get('read_only_mode', True)
        
        if self.ssh_enabled:
            self._setup_ssh_connection()
    
    def _check_kubectl_available(self) -> bool:
        """Check if kubectl is available"""
        try:
            result = subprocess.run(
                ['kubectl', 'version', '--client'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def _setup_ssh_connection(self):
        """Setup SSH connection (placeholder for production)"""
        # In production, use paramiko for SSH
        # For demo, we'll use local execution
        print("Note: SSH connection setup (using local execution for demo)")
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """Process execution request"""
        start_time = time.time()
        
        try:
            # Determine execution mode
            execution_mode = self._determine_execution_mode(request)
            
            # Safety check
            if not self._is_safe_command(request.query):
                raise AgentProcessingError(
                    f"Potentially unsafe command detected. Command contains forbidden pattern."
                )
            
            # Execute based on mode
            result = self.execution_modes[execution_mode](request)
            
            execution_time = time.time() - start_time
            
            return AgentResponse(
                success=True,
                data=result,
                error=None,
                metadata={'mode': execution_mode, 'k8s_available': self.k8s_available},
                agent_type=self.agent_type,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return AgentResponse(
                success=False,
                data=None,
                error=str(e),
                metadata={'k8s_available': self.k8s_available},
                agent_type=self.agent_type,
                execution_time=execution_time
            )
    
    def _is_safe_command(self, command: str) -> bool:
        """
        AI-driven security check - uses SecurityPolicyAgent instead of hardcoded lists.
        Delegates to AI for intelligent safety evaluation.
        """
        # Use AI-driven security evaluation
        try:
            from agents.security_policy_agent import SecurityPolicyAgent
            security_agent = SecurityPolicyAgent(self.config)
            security_agent.initialize()
            
            # AI evaluates command safety
            is_safe, reason, suggestion = security_agent.evaluate_command_safety(
                command=command,
                user_query=getattr(self, '_current_user_query', '')
            )
            
            if not is_safe:
                print(f"   ⚠️  {reason}")
                if suggestion:
                    print(f"   💡 Suggestion: {suggestion}")
            
            return is_safe
            
        except Exception as e:
            print(f"   ⚠️  AI security check failed: {e}, using basic permission check")
            return self._basic_permission_fallback(command)
    
    def _basic_permission_fallback(self, command: str) -> bool:
        """
        Basic fallback when AI unavailable - permission-based, not command lists.
        """
        command_lower = command.lower()
        
        # Check forbidden patterns from config
        for forbidden in self.forbidden_commands:
            if forbidden.lower() in command_lower:
                return False
        
        # Permission-based checks (not hardcoded operation lists)
        if not self.allow_delete and 'delete' in command_lower:
            print(f"   ⚠️  DELETE operation blocked (allow_delete=False)")
            return False
        
        if not self.allow_create and any(op in command_lower for op in ['create', 'apply']):
            print(f"   ⚠️  CREATE operation blocked (allow_create=False)")
            return False
        
        if not self.allow_update and any(op in command_lower for op in ['patch', 'edit', 'scale']):
            print(f"   ⚠️  UPDATE operation blocked (allow_update=False)")
            return False
        
        # In read-only, block writes (general check, not specific commands)
        if self.read_only_mode:
            write_indicators = ['delete', 'create', 'apply', 'patch', 'edit', 'scale', 'remove', 'destroy']
            if any(indicator in command_lower for indicator in write_indicators):
                print(f"   ⚠️  Write operation blocked in read-only mode")
                return False
        
        return True
    
    def _determine_execution_mode(self, request: AgentRequest) -> str:
        """
        Determine execution mode - AI-driven, minimal hardcoding.
        """
        # If AI has generated commands, use kubectl mode
        if 'ai_generated_commands' in request.context:
            return 'kubectl'
        
        # Check for explicit kubectl command
        if 'kubectl' in request.query.lower() or 'oc' in request.query.lower():
            return 'kubectl'
        
        # ❌ REMOVED: Hardcoded shell command list ['ls', 'pwd', 'whoami'...]
        # Use shell mode only if explicitly shell-like (starts with common shell pattern)
        query_stripped = request.query.strip()
        if any(query_stripped.startswith(cmd) for cmd in ['ls', 'cat', 'echo', 'pwd', 'whoami', 'date']):
            return 'shell'
        
        # Default to kubectl for K8s queries - LLM will generate commands
        return 'kubectl'
    
    def _execute_kubectl(self, request: AgentRequest) -> Dict:
        """Execute kubectl commands"""
        if not self.k8s_available:
            return {
                'error': 'kubectl is not available on this system',
                'suggestion': 'Install kubectl or check your PATH'
            }
        
        # Check if AI generated commands are provided
        if 'ai_generated_commands' in request.context:
            print("   📝 Executing AI-generated commands...")
            ai_commands = request.context['ai_generated_commands']
            results = {}
            
            for cmd_obj in ai_commands:
                cmd = cmd_obj.get('cmd', '')
                reason = cmd_obj.get('reason', 'Diagnostic')
                
                if cmd:
                    try:
                        print(f"   ▶ {reason}")
                        result = self._execute_local_command(cmd)
                        results[cmd] = result
                    except Exception as e:
                        results[cmd] = {
                            'error': str(e),
                            'command': cmd,
                            'reason': reason
                        }
            
            return results
        
        # No fallback - 100% AI driven
        # If we're here without AI commands, something went wrong
        raise AgentProcessingError(
            "No AI-generated commands available. This is a 100% AI-driven system. "
            "Ensure LLM Agent is working properly and Ollama is running."
        )
    
    def _execute_python_k8s(self, request: AgentRequest) -> Dict:
        """Execute Python K8s API calls (placeholder)"""
        return {
            'info': 'Python K8s API execution',
            'note': 'For demo, use kubectl commands instead',
            'suggestion': 'Install kubernetes-client library for full Python API support'
        }
    
    def _execute_shell(self, request: AgentRequest) -> Dict:
        """
        Execute shell commands with AI-driven safety check.
        No hardcoded safe command list - AI evaluates safety.
        """
        command = request.query
        
        # AI evaluates if shell command is safe
        if not self._is_safe_command(command):
            return {
                'error': 'Command blocked by security policy',
                'suggestion': 'Use AI-driven security evaluation'
            }
        
        return self._execute_local_command(command)
    
    def _execute_local_command(self, command: str, timeout: int = 30) -> Dict:
        """Execute command locally"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'command': command
            }
        except subprocess.TimeoutExpired:
            return {
                'error': f'Command timed out after {timeout} seconds',
                'command': command
            }
        except Exception as e:
            return {
                'error': str(e),
                'command': command
            }
    
    def health_check(self) -> bool:
        """Check agent health"""
        try:
            # Try to run a simple command
            result = subprocess.run(
                ['echo', 'health_check'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except:
                pass
