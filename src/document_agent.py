"""Document Agent with RAG for Kubernetes and system documentation"""
import os
import json
import re
from typing import Dict, List, Any, Tuple
from pathlib import Path
import time

from core.interfaces import BaseAgent, AgentRequest, AgentResponse, AgentType, AgentProcessingError


class DocumentAgent(BaseAgent):
    """
    Document search agent with focus on K8s and system documentation
    Uses simple keyword-based RAG for fast document retrieval
    """
    
    def initialize(self):
        """Initialize document agent"""
        self.agent_type = AgentType.DOCUMENT
        self.documents = {}
        self.index = {}
        self.k8s_patterns = self._load_k8s_patterns()
        self._load_documents()
    
    def _load_k8s_patterns(self) -> Dict:
        """Load K8s specific patterns and solutions"""
        return {
            'crashloopbackoff': {
                'keywords': ['crashloop', 'backoff', 'restart', 'crashing'],
                'doc_refs': ['pod_troubleshooting.md', 'common_errors.md'],
                'python_examples': [
                    """
# Check pod logs for crash reason
from kubernetes import client, config
config.load_kube_config()
v1 = client.CoreV1Api()
pod_logs = v1.read_namespaced_pod_log(
    name=pod_name, 
    namespace=namespace,
    tail_lines=100
)
print(pod_logs)
"""
                ],
                'kubectl_commands': [
                    'kubectl logs {pod_name} -n {namespace} --tail=100',
                    'kubectl describe pod {pod_name} -n {namespace}',
                    'kubectl get events -n {namespace} --sort-by=.lastTimestamp'
                ],
                'common_causes': [
                    'Application error on startup',
                    'Missing dependencies or configuration',
                    'Insufficient resources',
                    'Failed health checks'
                ]
            },
            'imagepullbackoff': {
                'keywords': ['image', 'pull', 'registry', 'imagepull'],
                'doc_refs': ['image_issues.md', 'registry_auth.md'],
                'kubectl_commands': [
                    'kubectl describe pod {pod_name} -n {namespace}',
                    'kubectl get events -n {namespace} --field-selector involvedObject.name={pod_name}'
                ],
                'python_examples': [
                    """
# Check image pull status
from kubernetes import client, config
config.load_kube_config()
v1 = client.CoreV1Api()
pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
for status in pod.status.container_statuses:
    if status.state.waiting:
        print(f"Container: {status.name}")
        print(f"Reason: {status.state.waiting.reason}")
        print(f"Message: {status.state.waiting.message}")
"""
                ],
                'common_causes': [
                    'Incorrect image name or tag',
                    'Private registry without credentials',
                    'Network connectivity issues',
                    'Registry authentication failure'
                ]
            },
            'oom_killed': {
                'keywords': ['oom', 'memory', 'killed', 'limits', 'out of memory'],
                'doc_refs': ['resource_limits.md', 'memory_optimization.md'],
                'kubectl_commands': [
                    'kubectl describe pod {pod_name} -n {namespace}',
                    'kubectl top pod {pod_name} -n {namespace}',
                    'kubectl get pod {pod_name} -n {namespace} -o yaml'
                ],
                'python_examples': [
                    """
# Get pod resource usage and limits
from kubernetes import client, config
config.load_kube_config()
v1 = client.CoreV1Api()
pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)

for container in pod.spec.containers:
    print(f"Container: {container.name}")
    if container.resources.limits:
        print(f"  Memory Limit: {container.resources.limits.get('memory', 'Not set')}")
    if container.resources.requests:
        print(f"  Memory Request: {container.resources.requests.get('memory', 'Not set')}")
"""
                ],
                'common_causes': [
                    'Memory limit too low for application needs',
                    'Memory leak in application',
                    'Unexpected load or data volume',
                    'Missing or incorrect resource limits'
                ]
            },
            'pending': {
                'keywords': ['pending', 'scheduling', 'unschedulable'],
                'doc_refs': ['scheduling.md', 'resource_allocation.md'],
                'kubectl_commands': [
                    'kubectl describe pod {pod_name} -n {namespace}',
                    'kubectl get nodes -o wide',
                    'kubectl top nodes'
                ],
                'python_examples': [
                    """
# Check pod scheduling status
from kubernetes import client, config
config.load_kube_config()
v1 = client.CoreV1Api()
pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)

for condition in pod.status.conditions or []:
    print(f"{condition.type}: {condition.status}")
    if condition.message:
        print(f"  Message: {condition.message}")
"""
                ],
                'common_causes': [
                    'Insufficient resources on nodes',
                    'Node selector not matching any nodes',
                    'Taints preventing scheduling',
                    'PersistentVolume not available'
                ]
            }
        }
    
    def _load_documents(self):
        """Load and index documentation"""
        doc_dir = Path(self.config.get('doc_dir', './docs'))
        
        if not doc_dir.exists():
            print(f"Warning: Documentation directory {doc_dir} does not exist")
            return
        
        # Load markdown docs
        for filepath in doc_dir.glob('**/*.md'):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Extract code blocks
                    python_blocks = re.findall(r'```python\n(.*?)```', content, re.DOTALL)
                    kubectl_blocks = re.findall(r'```(?:bash|shell)\n(.*?)```', content, re.DOTALL)
                    
                    filename = filepath.name
                    self.documents[filename] = {
                        'content': content,
                        'python_examples': python_blocks,
                        'kubectl_examples': kubectl_blocks,
                        'metadata': self._extract_metadata(content),
                        'path': str(filepath)
                    }
                    
                    # Build index
                    self._index_document(filename, content)
            except Exception as e:
                print(f"Error loading document {filepath}: {e}")
    
    def _extract_metadata(self, content: str) -> Dict:
        """Extract metadata from document"""
        metadata = {}
        
        # Extract K8s resources mentioned
        resources = re.findall(
            r'\b(pod|service|deployment|configmap|secret|ingress|statefulset|daemonset)\b',
            content.lower()
        )
        metadata['resources'] = list(set(resources))
        
        # Extract namespaces
        namespaces = re.findall(r'namespace[:\s]+([a-z0-9-]+)', content.lower())
        metadata['namespaces'] = list(set(namespaces))
        
        # Extract error types
        errors = re.findall(
            r'\b(crashloop|imagepull|oom|pending|error|failed)\b',
            content.lower()
        )
        metadata['error_types'] = list(set(errors))
        
        return metadata
    
    def _index_document(self, filename: str, content: str):
        """Build search index"""
        # Simple keyword index
        words = re.findall(r'\w+', content.lower())
        for word in set(words):
            if len(word) > 3:  # Skip very short words
                if word not in self.index:
                    self.index[word] = []
                if filename not in self.index[word]:
                    self.index[word].append(filename)
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """Process document search request"""
        start_time = time.time()
        
        try:
            # Search for relevant documents
            relevant_docs = self._search_documents(request.query)
            
            # Extract code examples if requested
            code_examples = self._extract_relevant_code(request.query, relevant_docs)
            
            # Get K8s specific patterns
            patterns = self._match_k8s_patterns(request.query)
            
            result = {
                'documents': relevant_docs,
                'code_examples': code_examples,
                'k8s_patterns': patterns,
                'search_query': request.query
            }
            
            execution_time = time.time() - start_time
            
            return AgentResponse(
                success=True,
                data=result,
                error=None,
                metadata={'doc_count': len(relevant_docs), 'patterns_found': len(patterns)},
                agent_type=self.agent_type,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return AgentResponse(
                success=False,
                data=None,
                error=str(e),
                metadata={},
                agent_type=self.agent_type,
                execution_time=execution_time
            )
    
    def _search_documents(self, query: str) -> List[Dict]:
        """Search for relevant documents"""
        query_words = re.findall(r'\w+', query.lower())
        doc_scores = {}
        
        # Score documents based on keyword matches
        for word in query_words:
            if len(word) > 3 and word in self.index:
                for doc in self.index[word]:
                    if doc not in doc_scores:
                        doc_scores[doc] = 0
                    doc_scores[doc] += 1
        
        # Get top documents
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        
        results = []
        for doc_name, score in sorted_docs:
            if doc_name in self.documents:
                doc = self.documents[doc_name]
                # Get relevant snippet
                snippet = self._extract_relevant_snippet(doc['content'], query, max_length=500)
                
                results.append({
                    'filename': doc_name,
                    'snippet': snippet,
                    'score': score,
                    'metadata': doc['metadata'],
                    'path': doc['path']
                })
        
        return results
    
    def _extract_relevant_snippet(self, content: str, query: str, max_length: int = 500) -> str:
        """Extract the most relevant snippet from content"""
        query_words = set(re.findall(r'\w+', query.lower()))
        
        # Split content into sentences
        sentences = re.split(r'[.!?]\s+', content)
        
        # Score sentences based on query word matches
        sentence_scores = []
        for sentence in sentences:
            words = set(re.findall(r'\w+', sentence.lower()))
            score = len(query_words.intersection(words))
            sentence_scores.append((sentence, score))
        
        # Get best sentences
        best_sentences = sorted(sentence_scores, key=lambda x: x[1], reverse=True)[:3]
        
        # Combine and truncate
        snippet = ' '.join([s[0] for s in best_sentences])
        if len(snippet) > max_length:
            snippet = snippet[:max_length] + '...'
        
        return snippet
    
    def _extract_relevant_code(self, query: str, docs: List[Dict]) -> Dict:
        """Extract relevant code examples from documents"""
        code_examples = {
            'python': [],
            'kubectl': []
        }
        
        query_lower = query.lower()
        
        for doc in docs:
            doc_name = doc['filename']
            if doc_name in self.documents:
                doc_data = self.documents[doc_name]
                
                # Add Python examples
                if 'python' in query_lower or 'api' in query_lower or 'script' in query_lower:
                    code_examples['python'].extend(doc_data['python_examples'][:2])
                
                # Add kubectl examples
                if 'kubectl' in query_lower or 'command' in query_lower or 'cli' in query_lower:
                    code_examples['kubectl'].extend(doc_data['kubectl_examples'][:2])
        
        # Remove duplicates
        code_examples['python'] = list(set(code_examples['python']))[:3]
        code_examples['kubectl'] = list(set(code_examples['kubectl']))[:3]
        
        return code_examples
    
    def _match_k8s_patterns(self, query: str) -> List[Dict]:
        """Match query against known K8s patterns"""
        matched_patterns = []
        query_lower = query.lower()
        
        for pattern_name, pattern_data in self.k8s_patterns.items():
            # Check if any keywords match
            if any(keyword in query_lower for keyword in pattern_data['keywords']):
                matched_patterns.append({
                    'pattern': pattern_name,
                    'data': pattern_data
                })
        
        return matched_patterns
    
    def health_check(self) -> bool:
        """Check agent health"""
        return self.initialized and len(self.k8s_patterns) > 0
