import os
import shutil
import stat
import time
import ast
import re
from urllib.parse import urlparse
from git import Repo
from dotenv import load_dotenv
from multiprocessing import Pool, cpu_count

# LangChain + Ollama
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()

def handle_remove_readonly(func, path, exc):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except PermissionError:
        if path.endswith("index.lock"):
            os.remove(path)

llm = OllamaLLM(model="gemma:2b")

# Optimized prompt template
prompt_template = PromptTemplate(
    input_variables=["code"],
    template="""Summarize the following code:

```
{code}
```

Provide:
1. Purpose
2. Key functions/classes
3. Dependencies
4. Overall functionality"""
)

def clean_mermaid_text(text):
    if not text:
        return "classDiagram\n    class Empty"
    text = re.sub(r'[^\x00-\x7F]+', '', text)  # remove non-ASCII
    text = re.sub(r'<[^>]+>', '', text)        # remove HTML tags
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text.strip()

def get_type_hint(arg):
    """Returns the type hint as a string if present, else empty string."""
    if hasattr(arg, 'annotation') and arg.annotation:
        return ast.unparse(arg.annotation)
    return ""

def extract_metadata(repo_dir):
    metadata = {}
    for root, _, files in os.walk(repo_dir):
        if any(skip in root for skip in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']):
            continue
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, repo_dir)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        source = f.read()
                    if not source.strip():
                        continue
                    tree = ast.parse(source)
                    file_info = {
                        'classes': [],
                        'functions': [],
                        'imports': [],
                        'inherits': []
                    }
                    # Extract imports
                    for n in ast.walk(tree):
                        if isinstance(n, ast.Import):
                            for alias in n.names:
                                file_info['imports'].append(alias.name.split('.')[0])
                        elif isinstance(n, ast.ImportFrom) and n.module:
                            file_info['imports'].append(n.module.split('.')[0])
                    # Extract classes and their members
                    for n in ast.iter_child_nodes(tree):
                        if isinstance(n, ast.ClassDef):
                            class_info = {
                                'name': n.name,
                                'methods': [],
                                'properties': [],
                                'inherits': [b.id for b in n.bases if isinstance(b, ast.Name)]
                            }
                            # Inheritance
                            if class_info['inherits']:
                                file_info['inherits'].append((n.name, class_info['inherits']))
                            for body_item in n.body:
                                if isinstance(body_item, ast.FunctionDef):
                                    args = []
                                    for a in body_item.args.args[1:]:  # skip 'self'
                                        t = get_type_hint(a)
                                        if t:
                                            args.append(f"{a.arg}: {t}")
                                        else:
                                            args.append(a.arg)
                                    # Return type
                                    ret_type = ""
                                    if body_item.returns:
                                        ret_type = ast.unparse(body_item.returns)
                                    class_info['methods'].append({
                                        'name': body_item.name,
                                        'args': args,
                                        'ret': ret_type,
                                        'private': body_item.name.startswith('_')
                                    })
                                elif isinstance(body_item, ast.Assign):
                                    for target in body_item.targets:
                                        if isinstance(target, ast.Name):
                                            class_info['properties'].append({
                                                'name': target.id,
                                                'private': target.id.startswith('_')
                                            })
                            file_info['classes'].append(class_info)
                        elif isinstance(n, ast.FunctionDef):
                            args = []
                            for a in n.args.args:
                                t = get_type_hint(a)
                                if t:
                                    args.append(f"{a.arg}: {t}")
                                else:
                                    args.append(a.arg)
                            ret_type = ""
                            if n.returns:
                                ret_type = ast.unparse(n.returns)
                            file_info['functions'].append({
                                'name': n.name,
                                'args': args,
                                'ret': ret_type
                            })
                    metadata[rel_path] = file_info
                except Exception as e:
                    print(f"⚠️ Could not parse {rel_path}: {str(e)}")
    return metadata

def generate_mermaid_class_diagram(metadata):
    lines = ["classDiagram"]
    # Classes and their methods/properties
    for file, info in metadata.items():
        for cls in info['classes']:
            lines.append(f'class {cls["name"]} {{')
            # Properties
            for prop in cls['properties']:
                vis = "-" if prop['private'] else "+"
                lines.append(f'    {vis}{prop["name"]}')
            # Methods
            for m in cls['methods']:
                vis = "-" if m['private'] else "+"
                arg_str = ", ".join(m['args'])
                ret = f" {m['ret']}" if m['ret'] else ""
                lines.append(f'    {vis}{m["name"]}({arg_str}){ret}')
            lines.append('}')
    # Standalone functions as pseudo-classes
    for file, info in metadata.items():
        for func in info['functions']:
            arg_str = ", ".join(func['args'])
            ret = f" {func['ret']}" if func['ret'] else ""
            lines.append(f'class {func["name"]} {{')
            lines.append(f'    +function({arg_str}){ret}')
            lines.append('}')
    # Inheritance relationships
    for file, info in metadata.items():
        for child, bases in info.get('inherits', []):
            for base in bases:
                lines.append(f"{base} <|-- {child}")
    # Optionally, show imports as dependencies
    for file, info in metadata.items():
        file_base = os.path.splitext(os.path.basename(file))[0]
        for imp in set(info['imports']):
            lines.append(f'{file_base} ..> {imp} : imports')
    return "\n".join(lines)
# 🚀 Main documentation generation
def analyze_file(file_path, repo_name):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()

        if not code.strip():
            return file_path, None  # Return None for empty files

        if len(code.strip()) < 20:
            return file_path, "📄 File too short to analyze meaningfully"

        analysis_code = code[:1500] if len(code) > 1500 else code

        prompt = prompt_template.format(code=analysis_code)
        explanation = llm.invoke(prompt)

        if explanation and len(explanation.strip()) > 10:
            return file_path, explanation.strip()
        else:
            return file_path, "🤖 AI analysis returned empty result"

    except Exception as e:
        return file_path, f"❌ Error: {str(e)}"

def generate_docs(repo_url):
    repo_name = "D:/temp_repo"

    # Clean up existing repo
    if os.path.exists(repo_name):
        time.sleep(1)
        shutil.rmtree(repo_name, onerror=handle_remove_readonly)

    # Handle GitHub token if available
    github_token = os.getenv("GITHUB_TOKEN")
    clone_url = f"https://{github_token}@{urlparse(repo_url).netloc}{urlparse(repo_url).path}" if github_token else repo_url

    # Clone repository
    try:
        print(f"🔄 Cloning repository: {repo_url}")
        Repo.clone_from(clone_url, repo_name)
        print("✅ Repository cloned successfully")
    except Exception as e:
        return {"status": "error", "message": f"❌ Git clone failed: {str(e)}"}

    docs = {}
    important_exts = [".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".json"]

    print("🔍 Scanning files...")
    files_to_process = []

    for root, dirs, files in os.walk(repo_name):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", "coverage", ".pytest_cache"}]
        for file in files:
            if any(file.endswith(ext) for ext in important_exts):
                path = os.path.join(root, file)
                try:
                    if os.path.getsize(path) <= 50000:
                        files_to_process.append(path)
                except:
                    continue

    print(f"🔄 Processing {len(files_to_process)} files using {cpu_count()} cores...")
    with Pool(cpu_count()) as pool:
        results = pool.starmap(analyze_file, [(file, repo_name) for file in files_to_process])

    for index, (file_path, result) in enumerate(results, start=1):
        if result is None:
            print(f"Skipping empty file: {file_path}")
            continue  # Skip empty files
        rel_path = os.path.relpath(file_path, repo_name)
        docs[rel_path] = result
        print(f"{index}/{len(files_to_process)}")

    # Generate Mermaid diagram
    print("📊 Generating project structure diagram...")
    try:
        metadata = extract_metadata(repo_name)
        if metadata:
            mermaid_code = generate_mermaid_class_diagram(metadata)
            cleaned_mermaid = clean_mermaid_text(mermaid_code)
            docs["__MERMAID__"] = cleaned_mermaid
            print("✅ Mermaid diagram generated successfully")
            with open("diagram.mmd", "w", encoding="utf-8") as f:
                f.write(cleaned_mermaid)
            print("📝 Mermaid diagram saved to diagram.mmd")
        else:
            docs["__MERMAID__"] = "graph TD\n    A[No analyzable Python files found]"
    except Exception as e:
        print(f"❌ Mermaid generation failed: {e}")
        docs["__MERMAID__"] = f"graph TD\n    A[Diagram generation failed: {str(e)[:50]}]"

    # Cleanup
    try:
        shutil.rmtree(repo_name, onerror=handle_remove_readonly)
        print("🧹 Temporary files cleaned up")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

    print(f"✅ Documentation generation completed! Processed {len(files_to_process)} files.")
    return {"status": "success", "docs": docs, "files_processed": len(files_to_process)}

# Ensure the message is printed only once
if __name__ == "__main__":
    print("🧠 Ollama + Gemma 2B Enabled")
    #test_url = "https://github.com/juliotrigo/pycalculator"
    #result = generate_docs(test_url)
    #print(result)








