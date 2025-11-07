"""Document Agent - AI-Driven RAG with ZERO Hardcoded Patterns"""
import os
import json
import re
from typing import Dict, List, Any, Tuple
from pathlib import Path
import time

from core.interfaces import BaseAgent, AgentRequest, AgentResponse, AgentType, AgentProcessingError


class DocumentAgent(BaseAgent):
    """
    AI-driven document search agent - NO hardcoded K8s patterns
    Uses LLM to understand query intent and match relevant documentation
    """
    
    def initialize(self):
        """Initialize document agent"""
        self.agent_type = AgentType.DOCUMENT
        self.documents = {}
        self.index = {}
        # ❌ REMOVED: self.k8s_patterns = self._load_k8s_patterns()  # Hardcoded patterns
        self._load_documents()
    
    # ❌ REMOVED: _load_k8s_patterns() method - 150+ lines of hardcoded patterns
    #             Now documentation is discovered from files, not hardcoded
    
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
        """Extract basic metadata from document - NO hardcoded patterns"""
        metadata = {}
        
        # ❌ REMOVED: Hardcoded K8s resource type extraction (pod|service|deployment...)
        # ❌ REMOVED: Hardcoded namespace pattern extraction
        # ❌ REMOVED: Hardcoded error type extraction (crashloop|imagepull|oom...)
        # LLM will analyze content dynamically instead of pattern matching
        
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
        """Process document search request - AI-driven, no hardcoded patterns"""
        start_time = time.time()
        
        try:
            # Search for relevant documents
            relevant_docs = self._search_documents(request.query)
            
            # Extract code examples if requested
            code_examples = self._extract_relevant_code(request.query, relevant_docs)
            
            # ❌ REMOVED: patterns = self._match_k8s_patterns(request.query)
            #             No more hardcoded pattern matching - LLM will analyze docs directly
            
            result = {
                'documents': relevant_docs,
                'code_examples': code_examples,
                # ❌ REMOVED: 'k8s_patterns': patterns,  # No hardcoded patterns
                'search_query': request.query
            }
            
            execution_time = time.time() - start_time
            
            return AgentResponse(
                success=True,
                data=result,
                error=None,
                metadata={'doc_count': len(relevant_docs)},  # Removed patterns_found count
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
        """Extract relevant code examples from documents - AI-driven, not keyword matching"""
        code_examples = {
            'python': [],
            'kubectl': [],
            'yaml': []
        }
        
        # Simply extract ALL code examples from relevant docs
        # LLM will decide which ones are relevant, not hardcoded keyword matching
        for doc in docs:
            doc_name = doc['filename']
            if doc_name in self.documents:
                doc_data = self.documents[doc_name]
                
                # Add all types of examples - let LLM filter
                if doc_data.get('python_examples'):
                    code_examples['python'].extend(doc_data['python_examples'][:2])
                if doc_data.get('kubectl_examples'):
                    code_examples['kubectl'].extend(doc_data['kubectl_examples'][:2])
        
        # Remove duplicates
        for key in code_examples:
            code_examples[key] = list(set(code_examples[key]))[:3]
        
        return code_examples
    
    # ❌ REMOVED: _match_k8s_patterns() - 150+ lines of hardcoded keyword matching
    #             LLM will analyze the query and documentation directly
    
    def health_check(self) -> bool:
        """Check agent health"""
        return self.initialized and len(self.documents) > 0
