import os
import uuid
from typing import List, Dict, Any
from fastmcp import FastMCP
import chromadb
import pathspec
from bs4 import BeautifulSoup
from tree_sitter_languages import get_parser

# Initialize the MCP server
mcp = FastMCP("Semantic Project Brain")

# Ensure the database directory exists relative to the current working directory
DB_PATH = os.path.join(os.getcwd(), ".context_db")
os.makedirs(DB_PATH, exist_ok=True)

# Initialize ChromaDB client
client = chromadb.PersistentClient(path=DB_PATH)

# Collections
code_collection = client.get_or_create_collection(name="code_semantics")
decisions_collection = client.get_or_create_collection(name="project_decisions")

# Supported extensions mapping to tree-sitter languages
# tree-sitter-languages bundles these grammars (Java, Python, PHP, JS, TS, HTML, CSS)
EXT_TO_LANG = {
    '.py': 'python',
    '.java': 'java',
    '.php': 'php',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'tsx', # Uses specialized TSX grammar
    '.css': 'css',
    '.html': 'html',
    '.htm': 'html'
}

# Default directories to exclude from indexing to keep it focused on project code
DEFAULT_EXCLUDES = {
    'node_modules', 'bower_components',                      # JS/Frontend
    'venv', '.venv', '__pycache__', '.tox', '.pytest_cache',  # Python
    'vendor',                                                # PHP/Composer, Go
    '.git', '.svn', '.hg',                                   # Version Control
    '.context_db',                                           # Local DB
    'build', 'dist', 'out', 'target', 'bin', 'obj',          # Build/Compiled Artifacts
    '.idea', '.vscode', '.settings',                         # IDEs
    '.gradle', '.m2',                                        # Java/Maven/Gradle
    'gems', '.bundle',                                       # Ruby
    'deps', '_build'                                         # Elixir
}

# Target AST Node Types for semantic extraction
TARGET_TYPES = {
    'python': {'class_definition', 'function_definition'},
    'java': {'class_declaration', 'method_declaration'},
    'javascript': {'class_declaration', 'method_definition', 'function_declaration'},
    'typescript': {'class_declaration', 'method_definition', 'function_declaration'},
    'tsx': {'class_declaration', 'method_definition', 'function_declaration'},
    'php': {'class_declaration', 'method_declaration', 'function_declaration'},
    'css': {'rule_set', 'media_statement'},
    'html': {'element'} # For tree-sitter HTML, but we use BeautifulSoup as a 'specialized parser' as requested
}

def _get_gitignore_spec(path: str) -> pathspec.PathSpec:
    """Reads .gitignore and returns a PathSpec for matching."""
    gitignore_path = os.path.join(path, '.gitignore')
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, lines)
    return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, [])

def extract_ast_nodes(source_code: bytes, lang: str) -> List[Dict[str, Any]]:
    """Extract semantic AST nodes using tree-sitter."""
    try:
        parser = get_parser(lang)
        tree = parser.parse(source_code)
        
        extracted = []
        target_types = TARGET_TYPES.get(lang, set())
        
        def traverse(node):
            if node.type in target_types:
                extracted.append({
                    'node_type': node.type,
                    'text': source_code[node.start_byte:node.end_byte].decode('utf-8', errors='ignore'),
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
            for child in node.children:
                traverse(child)
                
        traverse(tree.root_node)
        return extracted
    except Exception as e:
        print(f"Failed to parse {lang}: {e}")
        return []

def extract_html_semantics(content: str) -> List[Dict[str, Any]]:
    """
    Extract semantic structures from HTML using BeautifulSoup.
    Fulfills the 'specialized parser' requirement for HTML structure.
    """
    soup = BeautifulSoup(content, 'html.parser')
    extracted = []
    # Index major structural elements
    for tag in soup.find_all(['h1', 'h2', 'h3', 'section', 'article', 'div', 'form', 'nav', 'header', 'footer']):
        text = tag.get_text(separator=' ', strip=True)
        if len(text) > 30: # Only index chunks with substantial text content
            extracted.append({
                'node_type': f"html_{tag.name}",
                'text': text[:1500], # Cap chunk size for vectorization efficiency
                'start_line': 0,      # BS4 doesn't easily provide line numbers
                'end_line': 0
            })
    return extracted

@mcp.tool()
def index_project(path: str) -> str:
    """
    Scans the directory, respects .gitignore, and performs AST-based decomposition
    to index class definitions, methods, and structural HTML/CSS into 'code_semantics'.
    
    Args:
        path: The absolute or relative path of the directory to index.
    """
    if not os.path.exists(path) or not os.path.isdir(path):
        return f"Error: Path '{path}' is not a valid directory."
        
    spec = _get_gitignore_spec(path)
    files_indexed = 0
    chunks_indexed = 0
    
    for root, dirs, files in os.walk(path):
        # Prevent traversal into excluded directories
        dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDES and not d.startswith('.')]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in EXT_TO_LANG:
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, path)
            
            # Skip files ignored by git
            if spec.match_file(rel_path) or any(p in rel_path.split(os.sep) for p in DEFAULT_EXCLUDES):
                continue
                
            try:
                with open(file_path, 'rb') as f:
                    raw_content = f.read()
            except Exception:
                continue
            
            chunks = []
            if ext in {'.html', '.htm'}:
                # Use BeautifulSoup for HTML as requested
                content = raw_content.decode('utf-8', errors='ignore')
                chunks = extract_html_semantics(content)
            else:
                # Use Tree-sitter for all other languages (Python, Java, PHP, JS, TS, CSS)
                lang = EXT_TO_LANG[ext]
                chunks = extract_ast_nodes(raw_content, lang)
                
            if not chunks:
                continue
                
            docs = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                doc_id = f"{rel_path}_{i}_{uuid.uuid4().hex[:8]}"
                docs.append(chunk['text'])
                metadatas.append({
                    "file_path": rel_path,
                    "node_type": chunk['node_type'],
                    "start_line": chunk['start_line'],
                    "end_line": chunk['end_line']
                })
                ids.append(doc_id)
                
            if docs:
                code_collection.add(documents=docs, metadatas=metadatas, ids=ids)
                files_indexed += 1
                chunks_indexed += len(chunks)
                
    return f"Successfully semantically indexed {files_indexed} files into {chunks_indexed} semantic units from '{path}'."

@mcp.tool()
def remember_decision(topic: str, context: str) -> str:
    """
    Allows the LLM to save manual architectural notes or 'Why' something was built a certain way.
    
    Args:
        topic: A short topic or category name for this decision.
        context: The detailed reasoning, architectural decision, or context.
    """
    try:
        doc_id = str(uuid.uuid4())
        decisions_collection.add(
            documents=[context],
            metadatas=[{"topic": topic}],
            ids=[doc_id]
        )
        return f"Decision successfully stored under topic '{topic}' with ID: {doc_id}"
    except Exception as e:
        return f"Error storing decision: {str(e)}"

@mcp.tool()
def search_context(query: str) -> str:
    """
    A unified search that looks through both code structures (AST nodes) and past project decisions.
    
    Args:
        query: The search query to find relevant context.
    """
    try:
        combined_results = []
        
        # Query code_semantics collection
        try:
            code_results = code_collection.query(
                query_texts=[query], n_results=4, include=["documents", "metadatas", "distances"]
            )
            if code_results and code_results["documents"] and code_results["documents"][0]:
                for doc, meta, dist in zip(code_results["documents"][0], code_results["metadatas"][0], code_results["distances"][0]):
                    combined_results.append({"source": "Code Semantics", "content": doc, "meta": meta, "distance": dist})
        except Exception:
            pass 
            
        # Query project_decisions collection
        try:
            decision_results = decisions_collection.query(
                query_texts=[query], n_results=2, include=["documents", "metadatas", "distances"]
            )
            if decision_results and decision_results["documents"] and decision_results["documents"][0]:
                for doc, meta, dist in zip(decision_results["documents"][0], decision_results["metadatas"][0], decision_results["distances"][0]):
                    combined_results.append({"source": "Project Decision", "content": doc, "meta": meta, "distance": dist})
        except Exception:
            pass
            
        if not combined_results:
            return "No relevant context found in Code Semantics or Project Decisions."
            
        # Sort by distance (lower distance is more relevant in ChromaDB's default L2)
        combined_results.sort(key=lambda x: x["distance"])
        
        response_parts = []
        for idx, res in enumerate(combined_results):
            source = res["source"]
            meta = res["meta"] or {}
            
            if source == "Project Decision":
                topic = meta.get("topic", "Uncategorized")
                header = f"--- Result {idx + 1} ({source} | Topic: {topic}) ---"
            else:
                file_path = meta.get("file_path", "Unknown")
                node_type = meta.get("node_type", "Unknown")
                start_line = meta.get("start_line", 0)
                end_line = meta.get("end_line", 0)
                lines = f"Lines {start_line}-{end_line}" if start_line > 0 else "Structural"
                header = f"--- Result {idx + 1} ({source} | File: {file_path} | Type: {node_type} | {lines}) ---"
                
            response_parts.append(f"{header}\n{res['content']}\n")
            
        return "\n".join(response_parts)
    except Exception as e:
        return f"Error querying context: {str(e)}"

if __name__ == "__main__":
    mcp.run()
