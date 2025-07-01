import os
import shutil
import stat
import time
import ast
import re
from urllib.parse import urlparse
from git import Repo
from dotenv import load_dotenv

load_dotenv()
print("🧠 Environment loaded")

def handle_remove_readonly(func, path, exc):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except PermissionError:
        if path.endswith("index.lock"):
            os.remove(path)

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

def generate_docs(repo_url):
    repo_name = "D:/temp_repo"

    # Clean up existing repo
    if os.path.exists(repo_name):
        time.sleep(1)
        shutil.rmtree(repo_name, onerror=handle_remove_readonly)

    # Handle GitHub token if available
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        parsed = urlparse(repo_url)
        clone_url = f"https://{github_token}@{parsed.netloc}{parsed.path}"
    else:
        clone_url = repo_url

    # Clone repository
    try:
        print(f"🔄 Cloning repository: {repo_url}")
        Repo.clone_from(clone_url, repo_name)
        print("✅ Repository cloned successfully")
    except Exception as e:
        print(f"❌ Git clone failed: {str(e)}")
        return

    print("📊 Generating project structure class diagram...")
    try:
        metadata = extract_metadata(repo_name)
        if metadata:
            mermaid_code = generate_mermaid_class_diagram(metadata)
            cleaned_mermaid = clean_mermaid_text(mermaid_code)
            with open("diagram.mmd", "w", encoding="utf-8") as f:
                f.write(cleaned_mermaid)
            print("📝 Mermaid class diagram saved to diagram.mmd")
        else:
            with open("diagram.mmd", "w", encoding="utf-8") as f:
                f.write("classDiagram\n    class Empty")
            print("📝 No Python files found, empty diagram saved.")

    except Exception as e:
        print(f"❌ Mermaid generation failed: {e}")

    # Cleanup
    try:
        shutil.rmtree(repo_name, onerror=handle_remove_readonly)
        print("🧹 Temporary files cleaned up")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

    print(f"✅ Documentation generation completed!")

if __name__ == "__main__":
    test_url = "https://github.com/juliotrigo/pycalculator"
    generate_docs(test_url)
