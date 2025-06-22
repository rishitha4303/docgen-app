import os
import shutil
import stat
import time
import ast
from urllib.parse import urlparse
from git import Repo
from dotenv import load_dotenv

# LangChain + Ollama
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()
print("🧠 Ollama + Gemma 2B Enabled")

def handle_remove_readonly(func, path, exc):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except PermissionError:
        if path.endswith("index.lock"):
            os.remove(path)

llm = Ollama(model="gemma:2b")

prompt_template = PromptTemplate(
    input_variables=["code"],
    template="""Summarize the following Python code and explain what it does:\n\n``````"""
)

# --- Simple AST-based metadata extractor ---
def extract_metadata(repo_dir):
    metadata = {}
    for root, _, files in os.walk(repo_dir):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        source = f.read()
                    tree = ast.parse(source)
                    funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                    classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                    imports = []
                    for n in ast.walk(tree):
                        if isinstance(n, ast.Import):
                            imports += [alias.name for alias in n.names]
                        elif isinstance(n, ast.ImportFrom) and n.module:
                            imports.append(n.module)
                    metadata[path] = {
                        'functions': funcs,
                        'classes': classes,
                        'imports': imports
                    }
                except Exception as e:
                    metadata[path] = {
                        'functions': [],
                        'classes': [],
                        'imports': [],
                        'error': str(e)
                    }
    return metadata

# --- Build import graph for Mermaid ---
def build_import_graph(metadata):
    graph = {}
    for filepath, data in metadata.items():
        filename = os.path.basename(filepath).replace('.py', '')
        graph[filename] = {
            'functions': data.get('functions', []),
            'classes': data.get('classes', []),
            'imports': set(imp.split('.')[0] for imp in data.get('imports', []))
        }
    return graph

def generate_mermaid_diagram(graph):
    lines = ["graph TD"]
    for module, data in graph.items():
        funcs = ", ".join(data['functions']) if data['functions'] else "None"
        classes = ", ".join(data['classes']) if data['classes'] else "None"
        lines.append(f'{module}["📦 <b>{module}</b><br/>🛠️ <b>Functions:</b> {funcs}<br/>📘 <b>Classes:</b> {classes}"]')
    all_imports = set()
    for data in graph.values():
        all_imports.update(data['imports'])
    for lib in sorted(all_imports):
        lines.append(f'{lib}[" {lib}"]')
    for module, data in graph.items():
        for lib in data['imports']:
            lines.append(f"{module} --> {lib}")
    return "\n".join(lines)

# --- Main function ---
def generate_docs(repo_url):
    repo_name = "D:/temp_repo"

    if os.path.exists(repo_name):
        time.sleep(1)
        shutil.rmtree(repo_name, onerror=handle_remove_readonly)

    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        parsed = urlparse(repo_url)
        clone_url = f"https://{github_token}@{parsed.netloc}{parsed.path}"
    else:
        clone_url = repo_url

    try:
        Repo.clone_from(clone_url, repo_name)
    except Exception as e:
        return {"status": "error", "message": f"❌ Git clone failed: {str(e)}"}

    docs = {}

    for root, dirs, files in os.walk(repo_name):
        dirs[:] = [d for d in dirs if d not in (".git", "docs", "tests", "__pycache__")]
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, repo_name)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    if not code.strip():
                        docs[rel_path] = "❌ Error: File is empty."
                        continue
                    if len(code) < 20:
                        docs[rel_path] = "❌ Error: File too short to analyze."
                        continue
                    short_code = code[:700]
                    prompt = prompt_template.format(code=short_code)
                    print(f"📥 Prompt for {rel_path}:\n{prompt}\n")
                    try:
                        explanation = llm.invoke(prompt)
                    except Exception as llm_exc:
                        docs[rel_path] = f"❌ LLM Error: {str(llm_exc)}"
                        print(f"❌ LLM Error in {rel_path}: {llm_exc}")
                        continue
                    print(f"✅ {rel_path}:\n{explanation}\n")
                    docs[rel_path] = explanation
                except Exception as e:
                    docs[rel_path] = f"❌ Error: {str(e)}"
                    print(f"❌ Error in {rel_path}: {e}")

    # --- Mermaid diagram step ---
    try:
        print("📊 Generating Mermaid diagram...")
        metadata = extract_metadata(repo_name)
        graph = build_import_graph(metadata)
        mermaid_code = generate_mermaid_diagram(graph)
        docs["__MERMAID__"] = mermaid_code
        print("✅ Mermaid diagram generated.")
    except Exception as e:
        print(f"❌ Mermaid generation failed: {e}")
        docs["__MERMAID__"] = "❌ Error generating Mermaid diagram."

    return {"status": "success", "docs": docs}
