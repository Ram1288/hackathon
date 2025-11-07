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
            'rm -rf', 'delete', 'destroy', 'mkfs', 'dd if='
        ])
        
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
        """Check if command is safe to execute"""
        command_lower = command.lower()
        for forbidden in self.forbidden_commands:
            if forbidden.lower() in command_lower:
                return False
        return True
    
    def _determine_execution_mode(self, request: AgentRequest) -> str:
        """
        Determine execution mode - simplified for AI-driven approach.
        LLM decides commands, we just execute them.
        """
        # If AI has generated commands, use kubectl mode
        if 'ai_generated_commands' in request.context:
            return 'kubectl'
        
        # Check for explicit kubectl command
        if 'kubectl' in request.query.lower():
            return 'kubectl'
        
        # Check for shell commands
        if any(request.query.strip().startswith(cmd) for cmd in ['ls', 'pwd', 'whoami', 'date', 'df', 'free', 'uptime']):
            return 'shell'
        
        # Default to kubectl for K8s queries (LLM will handle or fallback will trigger)
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
        
        # Fallback: Simple generic commands when LLM completely unavailable
        # This is MINIMAL - just enough to not fail completely
        print("   ⚠️  LLM unavailable - using minimal fallback...")
        commands_to_run = self._minimal_fallback(request)
        
        # Execute commands
        results = {}
        for cmd_obj in commands_to_run:
            cmd = cmd_obj['cmd']
            reason = cmd_obj['reason']
            try:
                print(f"   ▶ {reason}")
                result = self._execute_local_command(cmd)
                results[cmd] = result
            except Exception as e:
                results[cmd] = {
                    'error': str(e),
                    'command': cmd
                }
        
        return results
    
    def _minimal_fallback(self, request: AgentRequest) -> List[Dict]:
        """
        Absolute minimal fallback when LLM is unavailable.
        Just returns generic pod status - no intelligence here.
        """
        namespace = request.context.get('namespace', 'default')
        
        # When LLM is down, we can only do basic pod listing
        return [{
            'cmd': f'kubectl get pods -n {namespace} -o wide',
            'reason': 'Basic pod status (LLM unavailable for smart diagnostics)'
        }]
    
    def _execute_python_k8s(self, request: AgentRequest) -> Dict:
        """Execute Python K8s API calls (placeholder)"""
        return {
            'info': 'Python K8s API execution',
            'note': 'For demo, use kubectl commands instead',
            'suggestion': 'Install kubernetes-client library for full Python API support'
        }
    
    def _execute_shell(self, request: AgentRequest) -> Dict:
        """Execute shell commands (with safety restrictions)"""
        # For demo, limit to safe commands
        safe_commands = ['ls', 'pwd', 'whoami', 'date', 'df -h', 'free -m', 'uptime']
        
        command = request.query
        
        # Check if it's a safe command
        is_safe = any(command.strip().startswith(safe) for safe in safe_commands)
        
        if not is_safe:
            return {
                'error': 'Command not in safe list',
                'safe_commands': safe_commands
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
