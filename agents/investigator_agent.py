"""
Intelligent Investigation Agent - Iterative AI-driven debugging
Analyzes partial results, detects patterns, and determines next investigation steps
"""
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from core.interfaces import BaseAgent, AgentRequest, AgentResponse, AgentType, AgentProcessingError


class InvestigatorAgent(BaseAgent):
    """
    AI-driven iterative investigation coordinator.
    Analyzes partial diagnostic results and intelligently determines next steps.
    """
    
    def initialize(self):
        """Initialize investigator agent"""
        self.agent_type = AgentType.LLM
        self.max_iterations = self.config.get('max_investigation_iterations', 3)
        self.investigation_history = []
        
        # Pattern recognition for quick analysis (before LLM)
        self.error_patterns = self._build_error_pattern_detector()
    
    def _build_error_pattern_detector(self) -> Dict:
        """
        Build regex patterns for common error detection.
        These are LEARNED patterns, can be enhanced by AI over time.
        """
        return {
            'certificate_expired': {
                'patterns': [
                    r'certificate has expired',
                    r'x509.*expired',
                    r'tls.*expired'
                ],
                'severity': 'high',
                'likely_fix': 'Certificate renewal needed'
            },
            'permission_denied': {
                'patterns': [
                    r'runAsNonRoot.*will run as root',
                    r'permission denied',
                    r'forbidden.*user',
                    r'RBAC.*denied'
                ],
                'severity': 'high',
                'likely_fix': 'Security policy or RBAC configuration issue'
            },
            'image_pull_failed': {
                'patterns': [
                    r'ImagePullBackOff',
                    r'ErrImagePull',
                    r'failed to pull image',
                    r'manifest.*not found'
                ],
                'severity': 'high',
                'likely_fix': 'Image not available or authentication issue'
            },
            'resource_exhaustion': {
                'patterns': [
                    r'OOMKilled',
                    r'Insufficient.*cpu',
                    r'Insufficient.*memory',
                    r'FailedScheduling'
                ],
                'severity': 'high',
                'likely_fix': 'Resource limits or cluster capacity issue'
            },
            'crash_loop': {
                'patterns': [
                    r'CrashLoopBackOff',
                    r'Back-off restarting',
                    r'Error.*exit code [1-9]'
                ],
                'severity': 'high',
                'likely_fix': 'Application crash or misconfiguration'
            },
            'network_issue': {
                'patterns': [
                    r'connection refused',
                    r'dial tcp.*timeout',
                    r'no route to host',
                    r'network is unreachable'
                ],
                'severity': 'medium',
                'likely_fix': 'Network connectivity or service discovery issue'
            }
        }
    
    def analyze_diagnostic_output(self, diagnostic_data: Dict) -> Dict:
        """
        Quickly analyze diagnostic output for obvious errors.
        This happens BEFORE sending to LLM (fast path).
        """
        findings = {
            'errors_found': [],
            'warnings_found': [],
            'root_cause_likely': None,
            'confidence': 0.0,
            'needs_more_investigation': False,
            'suggested_next_commands': []
        }
        
        # Combine all output for analysis
        all_output = ""
        for cmd, result in diagnostic_data.items():
            if isinstance(result, dict):
                all_output += result.get('stdout', '') + "\n"
                all_output += result.get('stderr', '') + "\n"
        
        # Pattern matching for known errors
        for error_type, pattern_info in self.error_patterns.items():
            for pattern in pattern_info['patterns']:
                matches = re.findall(pattern, all_output, re.IGNORECASE)
                if matches:
                    findings['errors_found'].append({
                        'type': error_type,
                        'severity': pattern_info['severity'],
                        'evidence': matches[:3],  # First 3 matches
                        'likely_fix': pattern_info['likely_fix']
                    })
        
        # Determine root cause
        if findings['errors_found']:
            # Highest severity error is likely root cause
            high_severity = [e for e in findings['errors_found'] if e['severity'] == 'high']
            if high_severity:
                findings['root_cause_likely'] = high_severity[0]
                findings['confidence'] = 0.8
            else:
                findings['root_cause_likely'] = findings['errors_found'][0]
                findings['confidence'] = 0.6
        
        # Check if we have enough information
        findings['needs_more_investigation'] = self._needs_more_info(findings, all_output)
        
        if findings['needs_more_investigation']:
            findings['suggested_next_commands'] = self._suggest_followup_commands(
                findings, 
                diagnostic_data
            )
        
        return findings
    
    def _needs_more_info(self, findings: Dict, output: str) -> bool:
        """
        Determine if we need more investigation.
        """
        # If we found clear root cause with high confidence, no more needed
        if findings['confidence'] >= 0.8:
            return False
        
        # If we have errors but low confidence, need more
        if findings['errors_found'] and findings['confidence'] < 0.7:
            return True
        
        # If output is very short, probably need more
        if len(output) < 200:
            return True
        
        # If no errors found at all, need to look deeper
        if not findings['errors_found']:
            return True
        
        return False
    
    def _suggest_followup_commands(self, findings: Dict, previous_diagnostics: Dict) -> List[str]:
        """
        Intelligently suggest follow-up commands based on what we found.
        This is AI-driven command generation based on context.
        """
        suggestions = []
        
        # If we found permission errors
        if any(e['type'] == 'permission_denied' for e in findings['errors_found']):
            suggestions.extend([
                "kubectl get pod -n {namespace} -o yaml | grep -A 5 securityContext",
                "kubectl describe serviceaccount -n {namespace}",
                "kubectl get rolebindings,clusterrolebindings -n {namespace}"
            ])
        
        # If certificate errors
        if any(e['type'] == 'certificate_expired' for e in findings['errors_found']):
            suggestions.extend([
                "kubectl get secrets -n {namespace}",
                "kubectl describe secret -n {namespace} | grep -i cert",
            ])
        
        # If image pull errors
        if any(e['type'] == 'image_pull_failed' for e in findings['errors_found']):
            suggestions.extend([
                "kubectl get secrets -n {namespace} -o yaml | grep imagePullSecrets",
                "kubectl describe pod {pod_name} -n {namespace} | grep -i image"
            ])
        
        # If crash loops
        if any(e['type'] == 'crash_loop' for e in findings['errors_found']):
            suggestions.extend([
                "kubectl logs {pod_name} -n {namespace} --previous --tail=50",
                "kubectl get events -n {namespace} --sort-by='.lastTimestamp' | tail -20"
            ])
        
        # If no specific errors, get more general info
        if not findings['errors_found']:
            suggestions.extend([
                "kubectl get events -n {namespace} --sort-by='.lastTimestamp' | tail -30",
                "kubectl top pods -n {namespace}",
                "kubectl get pods -n {namespace} -o wide"
            ])
        
        return suggestions[:3]  # Limit to 3 follow-ups
    
    def investigate_iteratively(
        self, 
        query: str, 
        namespace: str, 
        initial_diagnostics: Dict,
        execution_agent,
        llm_agent
    ) -> Dict:
        """
        Perform iterative investigation with AI reasoning at each step.
        """
        investigation_log = []
        current_findings = None
        all_diagnostics = initial_diagnostics.copy()
        
        for iteration in range(self.max_iterations):
            print(f"\n🔬 Investigation Iteration {iteration + 1}/{self.max_iterations}")
            
            # Analyze current diagnostic data
            analysis = self.analyze_diagnostic_output(all_diagnostics)
            investigation_log.append({
                'iteration': iteration + 1,
                'analysis': analysis,
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"   📊 Found {len(analysis['errors_found'])} error patterns")
            if analysis['root_cause_likely']:
                print(f"   🎯 Likely root cause: {analysis['root_cause_likely']['type']}")
                print(f"   💡 {analysis['root_cause_likely']['likely_fix']}")
            
            # If we have high confidence root cause, we're done
            if analysis['confidence'] >= 0.8:
                print(f"   ✅ High confidence ({analysis['confidence']:.0%}) - investigation complete")
                current_findings = analysis
                break
            
            # If we need more investigation and not last iteration
            if analysis['needs_more_investigation'] and iteration < self.max_iterations - 1:
                print(f"   🔍 Confidence {analysis['confidence']:.0%} - gathering more evidence...")
                
                # Generate follow-up commands
                followup_commands = analysis['suggested_next_commands']
                if followup_commands:
                    print(f"   📋 Executing {len(followup_commands)} follow-up commands")
                    
                    # Execute follow-ups
                    for cmd_template in followup_commands:
                        # Fill in placeholders
                        cmd = cmd_template.replace('{namespace}', namespace)
                        # Try to extract pod name from previous results if needed
                        if '{pod_name}' in cmd:
                            pod_name = self._extract_pod_name(all_diagnostics)
                            if pod_name:
                                cmd = cmd.replace('{pod_name}', pod_name)
                            else:
                                continue  # Skip if no pod name available
                        
                        try:
                            result = execution_agent._execute_local_command(cmd)
                            all_diagnostics[cmd] = result
                            print(f"      ✓ {cmd[:60]}...")
                        except Exception as e:
                            print(f"      ✗ Failed: {e}")
                else:
                    # No obvious follow-ups, break
                    current_findings = analysis
                    break
            else:
                current_findings = analysis
                break
        
        return {
            'final_findings': current_findings or analysis,
            'investigation_log': investigation_log,
            'total_iterations': len(investigation_log),
            'all_diagnostics': all_diagnostics
        }
    
    def _extract_pod_name(self, diagnostics: Dict) -> Optional[str]:
        """Extract pod name from diagnostic output"""
        for cmd, result in diagnostics.items():
            if isinstance(result, dict) and 'stdout' in result:
                # Look for "Name:" in kubectl describe output
                match = re.search(r'^Name:\s+(.+)$', result['stdout'], re.MULTILINE)
                if match:
                    return match.group(1).strip()
        return None
    
    def generate_human_readable_report(self, investigation_result: Dict) -> str:
        """
        Generate a clear, actionable report from investigation findings.
        """
        findings = investigation_result['final_findings']
        
        report = []
        report.append("=" * 80)
        report.append("🔍 INVESTIGATION RESULTS")
        report.append("=" * 80)
        report.append("")
        
        if findings['root_cause_likely']:
            rc = findings['root_cause_likely']
            report.append(f"🎯 **ROOT CAUSE IDENTIFIED** (Confidence: {findings['confidence']:.0%})")
            report.append(f"   Type: {rc['type'].replace('_', ' ').title()}")
            report.append(f"   Severity: {rc['severity'].upper()}")
            report.append(f"   Evidence: {rc['evidence']}")
            report.append(f"   Recommended Fix: {rc['likely_fix']}")
            report.append("")
        
        if findings['errors_found']:
            report.append(f"📋 **ALL ERRORS FOUND** ({len(findings['errors_found'])} total):")
            for i, error in enumerate(findings['errors_found'], 1):
                report.append(f"   {i}. {error['type'].replace('_', ' ').title()}")
                report.append(f"      → {error['likely_fix']}")
            report.append("")
        
        report.append(f"🔬 **INVESTIGATION SUMMARY:**")
        report.append(f"   Total iterations: {investigation_result['total_iterations']}")
        report.append(f"   Commands executed: {len(investigation_result['all_diagnostics'])}")
        report.append(f"   Confidence level: {findings['confidence']:.0%}")
        report.append("")
        
        if findings['needs_more_investigation']:
            report.append("⚠️  **MORE INVESTIGATION RECOMMENDED**")
            if findings['suggested_next_commands']:
                report.append("   Suggested commands:")
                for cmd in findings['suggested_next_commands']:
                    report.append(f"      • {cmd}")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """Process investigation request"""
        start_time = time.time()
        
        try:
            # This would be called by orchestrator
            # For now, just return structure
            execution_time = time.time() - start_time
            
            return AgentResponse(
                success=True,
                data={},
                error=None,
                metadata={},
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
        """Check if investigator is ready"""
        return len(self.error_patterns) > 0
