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
            'diagnostic': self._execute_diagnostic,
            'shell': self._execute_shell,
            'python_k8s': self._execute_python_k8s
        }
        
        # Command templates for common K8s operations
        self.k8s_templates = {
            'pod_status': 'kubectl get pods -n {namespace} -o wide',
            'pod_logs': 'kubectl logs {pod_name} -n {namespace} --tail={lines}',
            'service_status': 'kubectl get svc -n {namespace}',
            'node_status': 'kubectl get nodes -o wide',
            'deployment_status': 'kubectl get deployments -n {namespace}',
            'describe_pod': 'kubectl describe pod {pod_name} -n {namespace}',
            'top_pods': 'kubectl top pods -n {namespace}',
            'top_nodes': 'kubectl top nodes',
            'events': 'kubectl get events -n {namespace} --sort-by=.lastTimestamp',
            'failing_pods': 'kubectl get pods -n {namespace} --field-selector=status.phase!=Running,status.phase!=Succeeded'
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
        """Determine which execution mode to use"""
        query_lower = request.query.lower()
        
        # Check for diagnostic keywords
        if any(diag in query_lower for diag in ['diagnose', 'troubleshoot', 'debug', 'check health']):
            return 'diagnostic'
        
        # Check for kubectl keywords
        if 'kubectl' in query_lower or any(
            k in query_lower for k in ['pod', 'service', 'deployment', 'namespace', 'events']
        ):
            return 'kubectl'
        
        # Check for Python K8s API
        if 'python' in query_lower and ('k8s' in query_lower or 'kubernetes' in query_lower):
            return 'python_k8s'
        
        # Default to shell for other commands
        return 'shell'
    
    def _execute_kubectl(self, request: AgentRequest) -> Dict:
        """Execute kubectl commands"""
        if not self.k8s_available:
            return {
                'error': 'kubectl is not available on this system',
                'suggestion': 'Install kubectl or check your PATH'
            }
        
        # Extract parameters from request
        namespace = request.context.get('namespace', 'default')
        pod_name = request.context.get('pod_name', '')
        
        # Map query to kubectl commands
        commands_to_run = []
        query_lower = request.query.lower()
        
        if 'pod' in query_lower and 'status' in query_lower:
            commands_to_run.append(
                self.k8s_templates['pod_status'].format(namespace=namespace)
            )
        
        if 'failing' in query_lower or 'error' in query_lower or 'problem' in query_lower:
            commands_to_run.append(
                self.k8s_templates['failing_pods'].format(namespace=namespace)
            )
        
        if 'log' in query_lower and pod_name:
            commands_to_run.append(
                self.k8s_templates['pod_logs'].format(
                    pod_name=pod_name,
                    namespace=namespace,
                    lines=100
                )
            )
        
        if 'event' in query_lower:
            commands_to_run.append(
                self.k8s_templates['events'].format(namespace=namespace)
            )
        
        if 'node' in query_lower:
            commands_to_run.append(self.k8s_templates['node_status'])
            if 'resource' in query_lower or 'usage' in query_lower:
                commands_to_run.append(self.k8s_templates['top_nodes'])
        
        if 'describe' in query_lower and pod_name:
            commands_to_run.append(
                self.k8s_templates['describe_pod'].format(
                    pod_name=pod_name,
                    namespace=namespace
                )
            )
        
        # If no specific commands matched, do a general pod check
        if not commands_to_run:
            commands_to_run.append(
                self.k8s_templates['pod_status'].format(namespace=namespace)
            )
        
        # Execute commands
        results = {}
        for cmd in commands_to_run:
            try:
                result = self._execute_local_command(cmd)
                results[cmd] = result
            except Exception as e:
                results[cmd] = {
                    'error': str(e),
                    'command': cmd
                }
        
        return results
    
    def _execute_diagnostic(self, request: AgentRequest) -> Dict:
        """Run comprehensive diagnostics"""
        namespace = request.context.get('namespace', 'default')
        diagnostics = {
            'timestamp': time.time(),
            'namespace': namespace,
            'checks': {}
        }
        
        if not self.k8s_available:
            diagnostics['error'] = 'kubectl not available'
            return diagnostics
        
        # Standard diagnostic commands
        diagnostic_commands = {
            'failing_pods': f"kubectl get pods -n {namespace} --field-selector=status.phase!=Running,status.phase!=Succeeded",
            'recent_events': f"kubectl get events -n {namespace} --sort-by=.lastTimestamp --field-selector type=Warning",
            'node_status': "kubectl get nodes -o wide",
            'pod_status': f"kubectl get pods -n {namespace} -o wide",
        }
        
        # Try to get node resources if available
        try:
            diagnostic_commands['node_resources'] = "kubectl top nodes"
        except:
            pass
        
        # Execute diagnostic commands
        for check_name, cmd in diagnostic_commands.items():
            try:
                result = self._execute_local_command(cmd)
                diagnostics['checks'][check_name] = result
            except Exception as e:
                diagnostics['checks'][check_name] = {
                    'error': str(e),
                    'command': cmd
                }
        
        # Parse and summarize issues
        diagnostics['summary'] = self._summarize_diagnostics(diagnostics['checks'])
        
        return diagnostics
    
    def _summarize_diagnostics(self, checks: Dict) -> Dict:
        """Summarize diagnostic results"""
        summary = {
            'total_issues': 0,
            'critical_issues': [],
            'warnings': []
        }
        
        # Check for failing pods
        if 'failing_pods' in checks and 'stdout' in checks['failing_pods']:
            output = checks['failing_pods']['stdout']
            lines = output.strip().split('\n')
            if len(lines) > 1:  # More than just header
                summary['total_issues'] += len(lines) - 1
                summary['critical_issues'].append(
                    f"{len(lines) - 1} pod(s) not in Running/Succeeded state"
                )
        
        # Check for warning events
        if 'recent_events' in checks and 'stdout' in checks['recent_events']:
            output = checks['recent_events']['stdout']
            lines = output.strip().split('\n')
            if len(lines) > 1:
                summary['warnings'].append(
                    f"{len(lines) - 1} warning event(s) detected"
                )
        
        return summary
    
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
