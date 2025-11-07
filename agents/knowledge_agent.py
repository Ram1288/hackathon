"""
Knowledge Agent - Dynamic learning from environment and interactions
This agent eliminates ALL hardcoded kubectl commands, patterns, and troubleshooting guides.
Instead, it learns dynamically from:
1. kubectl api-resources (discovers available resources)
2. kubectl explain (learns resource schemas)
3. Past successful troubleshooting sessions (learns patterns)
4. LLM reasoning about kubernetes concepts
"""
import subprocess
import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from core.interfaces import BaseAgent, AgentRequest, AgentResponse, AgentType, AgentProcessingError


class KnowledgeAgent(BaseAgent):
    """
    Dynamically learns K8s capabilities and patterns - ZERO hardcoded knowledge
    """
    
    def initialize(self):
        """Initialize knowledge agent"""
        self.agent_type = AgentType.DOCUMENT  # Reuse document type for now
        self.knowledge_base_path = Path('knowledge_base')
        self.knowledge_base_path.mkdir(exist_ok=True)
        
        # Dynamic knowledge - learned at runtime
        self.available_resources = {}  # Discovered via kubectl api-resources
        self.resource_schemas = {}     # Learned via kubectl explain
        self.successful_patterns = []  # Learned from successful troubleshooting
        self.command_capabilities = {} # Discovered kubectl/oc commands
        
        # Discover environment capabilities
        self._discover_environment()
    
    def _discover_environment(self):
        """
        Dynamically discover what's possible in this environment.
        NO hardcoded kubectl commands - we ASK the system what it can do.
        """
        print("\n🔍 Discovering environment capabilities...")
        
        # Discover available resources dynamically
        self.available_resources = self._discover_k8s_resources()
        print(f"   ✓ Discovered {len(self.available_resources)} K8s resource types")
        
        # Discover kubectl/oc command capabilities
        self.command_capabilities = self._discover_command_capabilities()
        print(f"   ✓ Discovered {len(self.command_capabilities)} command operations")
        
        # Load learned patterns from previous sessions
        self._load_learned_patterns()
        print(f"   ✓ Loaded {len(self.successful_patterns)} learned patterns")
    
    def _discover_k8s_resources(self) -> Dict:
        """
        Ask kubectl: What resources are available?
        Instead of hardcoding [pods, services, deployments...], we DISCOVER them.
        """
        try:
            result = subprocess.run(
                ['kubectl', 'api-resources', '--verbs=list', '--output=json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                resources = json.loads(result.stdout)
                discovered = {}
                
                for resource in resources:
                    name = resource.get('name', '')
                    discovered[name] = {
                        'kind': resource.get('kind', ''),
                        'namespaced': resource.get('namespaced', False),
                        'verbs': resource.get('verbs', []),
                        'short_names': resource.get('shortNames', []),
                        'api_group': resource.get('apiGroup', '')
                    }
                
                return discovered
        except Exception as e:
            print(f"   ⚠ Could not discover K8s resources: {e}")
        
        return {}
    
    def _discover_command_capabilities(self) -> Dict:
        """
        Discover what operations are available dynamically.
        Parse ALL subcommands from kubectl --help without hardcoded categorization.
        LLM will categorize them based on semantic understanding.
        """
        discovered_commands = []
        
        # Discover kubectl subcommands dynamically
        try:
            result = subprocess.run(
                ['kubectl', '--help'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                output = result.stdout
                
                # Parse ALL available commands from help output
                import re
                # Extract command names from help output (e.g., "  get         Display one or many resources")
                command_pattern = re.compile(r'^\s{2}([a-z-]+)\s+(.+)$', re.MULTILINE)
                matches = command_pattern.findall(output)
                
                for cmd_name, description in matches:
                    discovered_commands.append({
                        'name': cmd_name,
                        'description': description.strip(),
                        # LLM will categorize based on description, not hardcoded rules
                    })
                
                print(f"   ✓ Discovered {len(discovered_commands)} kubectl commands")
                
                # Return raw discovered commands - LLM will categorize them
                return {
                    'all_commands': discovered_commands,
                    'discovery_method': 'kubectl --help parsing',
                    'note': 'Commands categorized dynamically by LLM based on descriptions'
                }
        
        except Exception as e:
            print(f"   ⚠ Could not discover command capabilities: {e}")
        
        return {'all_commands': [], 'discovery_method': 'failed'}
    
    def _load_learned_patterns(self):
        """
        Load troubleshooting patterns learned from previous successful sessions.
        This is LEARNED knowledge, not hardcoded.
        """
        patterns_file = self.knowledge_base_path / 'learned_patterns.json'
        
        if patterns_file.exists():
            try:
                with open(patterns_file, 'r') as f:
                    self.successful_patterns = json.load(f)
            except Exception as e:
                print(f"   ⚠ Could not load learned patterns: {e}")
                self.successful_patterns = []
        else:
            self.successful_patterns = []
    
    def learn_from_successful_resolution(self, problem_query: str, solution_commands: List[str], outcome: str):
        """
        Learn from successful troubleshooting.
        Store patterns that worked for future similar issues.
        """
        pattern = {
            'query': problem_query,
            'commands_used': solution_commands,
            'outcome': outcome,
            'timestamp': datetime.now().isoformat(),
            'success_score': 1.0  # Can be refined based on user feedback
        }
        
        self.successful_patterns.append(pattern)
        
        # Persist learned knowledge
        patterns_file = self.knowledge_base_path / 'learned_patterns.json'
        with open(patterns_file, 'w') as f:
            json.dump(self.successful_patterns, f, indent=2)
        
        print(f"📚 Learned new pattern from: {problem_query[:50]}...")
    
    def get_resource_schema(self, resource_type: str) -> Optional[Dict]:
        """
        Dynamically fetch resource schema using 'kubectl explain'
        Instead of hardcoding schemas, we ASK kubectl.
        """
        if resource_type in self.resource_schemas:
            return self.resource_schemas[resource_type]
        
        try:
            result = subprocess.run(
                ['kubectl', 'explain', resource_type, '--output=json'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                schema = json.loads(result.stdout)
                self.resource_schemas[resource_type] = schema
                return schema
        except Exception as e:
            print(f"   ⚠ Could not explain {resource_type}: {e}")
        
        return None
    
    def find_similar_past_solutions(self, query: str, llm_agent=None) -> List[Dict]:
        """
        Find similar past solutions using semantic understanding.
        Uses LLM/embeddings instead of keyword matching.
        """
        if not self.successful_patterns:
            return []
        
        similar_patterns = []
        
        # TODO: Use embeddings for true semantic similarity
        # For now, use simple word overlap as placeholder
        # This should be replaced with:
        # 1. Generate embedding for current query
        # 2. Compare with embeddings of past queries
        # 3. Return top-k similar based on cosine similarity
        
        # Temporary simple implementation
        query_words = set(query.lower().split())
        
        for pattern in self.successful_patterns[-20:]:
            pattern_words = set(pattern['query'].lower().split())
            overlap = len(query_words & pattern_words)
            
            if overlap >= 2:  # At least 2 common words
                similar_patterns.append({
                    **pattern,
                    'similarity_score': overlap / max(len(query_words), len(pattern_words))
                })
        
        # Sort by similarity score
        similar_patterns.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        return similar_patterns[:5]  # Top 5 similar patterns
    
    def generate_dynamic_prompt_context(self) -> str:
        """
        Generate prompt context dynamically based on discovered environment.
        NO hardcoded kubectl commands - everything is discovered.
        """
        context = f"""**Available Kubernetes Resources (discovered dynamically via kubectl api-resources):**
{self._format_discovered_resources()}

**Available kubectl Commands (discovered dynamically via kubectl --help):**
{self._format_discovered_commands()}

**Learned Patterns (from past successful resolutions):**
{self._format_learned_patterns()}

**Note:** YOU (the LLM) must categorize commands as read/write/debug based on their descriptions, not hardcoded rules.
"""
        return context
    
    def _format_discovered_commands(self) -> str:
        """Format discovered commands for LLM to categorize"""
        all_commands = self.command_capabilities.get('all_commands', [])
        
        if not all_commands:
            return "No commands discovered yet."
        
        formatted = []
        for cmd_info in all_commands[:30]:  # Top 30 most common
            formatted.append(f"  - {cmd_info['name']}: {cmd_info['description']}")
        
        return '\n'.join(formatted)
    
    def _format_discovered_resources(self) -> str:
        """Format discovered resources for LLM prompt"""
        if not self.available_resources:
            return "No resources discovered yet."
        
        formatted = []
        for resource_name, info in list(self.available_resources.items())[:20]:  # Top 20
            verbs = ', '.join(info.get('verbs', []))
            short_names = f" (short: {', '.join(info['short_names'])})" if info.get('short_names') else ""
            namespaced = "namespaced" if info.get('namespaced') else "cluster-wide"
            formatted.append(f"  - {resource_name}{short_names} [{namespaced}] - verbs: {verbs}")
        
        return '\n'.join(formatted)
    
    def _format_learned_patterns(self) -> str:
        """Format learned patterns for LLM to understand past successes"""
        if not self.successful_patterns:
            return "No patterns learned yet. This is the first troubleshooting session."
        
        formatted = []
        for pattern in self.successful_patterns[-5:]:  # Last 5 successful patterns
            formatted.append(
                f"  - Problem: {pattern['query'][:60]}...\n"
                f"    Solution: {' → '.join(pattern['commands_used'][:3])}\n"
                f"    Outcome: {pattern['outcome'][:40]}..."
            )
        
        return '\n'.join(formatted) if formatted else "Learning in progress..."
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """Process knowledge request"""
        start_time = time.time()
        
        try:
            # Generate dynamic context based on discovered environment
            dynamic_context = self.generate_dynamic_prompt_context()
            
            # Find similar past solutions (if any)
            similar_solutions = self.find_similar_past_solutions(request.query, None)
            
            execution_time = time.time() - start_time
            
            return AgentResponse(
                success=True,
                data={
                    'dynamic_context': dynamic_context,
                    'available_resources': self.available_resources,
                    'command_capabilities': self.command_capabilities,
                    'similar_past_solutions': similar_solutions,
                    'learned_patterns_count': len(self.successful_patterns)
                },
                error=None,
                metadata={
                    'resources_discovered': len(self.available_resources),
                    'patterns_learned': len(self.successful_patterns)
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
                metadata={},
                agent_type=self.agent_type,
                execution_time=execution_time
            )
    
    def health_check(self) -> bool:
        """Check if knowledge agent is ready"""
        return len(self.available_resources) > 0 or len(self.command_capabilities) > 0
