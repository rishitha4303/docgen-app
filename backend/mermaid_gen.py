import os
import sys
import tempfile
import shutil
import requests
import ast
from git import Repo
from PIL import Image
import io
import matplotlib.pyplot as plt
import base64

def clone_repo(git_url):
    temp_dir = tempfile.mkdtemp(prefix="cloned_repo_")
    print(f"Cloning repository {git_url} to {temp_dir} ...")
    Repo.clone_from(git_url, temp_dir)
    return temp_dir

def find_python_files(directory):
    py_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    return py_files

def extract_classes_and_calls(py_files):
    """Extract class details and cross-class method calls."""
    classes = {}
    inheritance = []
    method_calls = set()
    for py_file in py_files:
        with open(py_file, encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read(), filename=py_file)
            except Exception:
                continue
        # Collect class info
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
                attrs = set()
                methods = set()
                for body_item in node.body:
                    if isinstance(body_item, ast.FunctionDef):
                        methods.add(body_item.name)
                        # Find attributes in __init__
                        if body_item.name == "__init__":
                            for stmt in ast.walk(body_item):
                                if isinstance(stmt, ast.Assign):
                                    for target in stmt.targets:
                                        if (isinstance(target, ast.Attribute) and
                                            isinstance(target.value, ast.Name) and
                                            target.value.id == "self"):
                                            attrs.add(target.attr)
                classes[class_name] = {
                    "bases": bases,
                    "attrs": attrs,
                    "methods": methods,
                }
        # Find cross-class method calls
        class_names = set(classes.keys())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                src_class = node.name
                for body_item in node.body:
                    if isinstance(body_item, ast.FunctionDef):
                        src_method = body_item.name
                        for child in ast.walk(body_item):
                            if isinstance(child, ast.Call):
                                # Look for OtherClass.method() style calls
                                if isinstance(child.func, ast.Attribute):
                                    if isinstance(child.func.value, ast.Name):
                                        tgt_class = child.func.value.id
                                        tgt_method = child.func.attr
                                        # Only connect if tgt_class is a class in the project
                                        if tgt_class in class_names and tgt_class != src_class:
                                            method_calls.add((src_class, src_method, tgt_class, tgt_method))
    return classes, method_calls

def generate_mermaid_class_diagram(classes, method_calls, project_name, direction="TD"):
    diagram = [f"classDiagram\ndirection {direction}"]
    # Class blocks
    for cname, cinfo in classes.items():
        diagram.append(f"class {cname} {{")
        for attr in sorted(cinfo['attrs']):
            diagram.append(f"  +{attr}")
        for method in sorted(cinfo['methods']):
            diagram.append(f"  +{method}()")
        diagram.append("}")
    # Inheritance arrows
    for cname, cinfo in classes.items():
        for base in cinfo['bases']:
            if base in classes:
                diagram.append(f"{base} <|-- {cname}")
    # Method call arrows between classes
    for src_class, src_method, tgt_class, tgt_method in method_calls:
        label = f"{src_class} : {src_method}() --> {tgt_class} : {tgt_method}()"
        diagram.append(label)
    # Connect isolated classes to PROJECT
    all_related = set()
    for cname, cinfo in classes.items():
        all_related.update(cinfo['bases'])
    for src_class, src_method, tgt_class, tgt_method in method_calls:
        all_related.add(src_class)
        all_related.add(tgt_class)
    for cname in classes:
        if cname not in all_related:
            diagram.append(f"{project_name} <.. {cname}")
    # Project node
    diagram.append(f"class {project_name}")
    return "\n".join(diagram)

def generate_mermaid_from_repo(git_url, max_lines=20):
    temp_dir = clone_repo(git_url)
    try:
        py_files = find_python_files(temp_dir)
        project_name = os.path.basename(os.path.normpath(temp_dir))
        classes, method_calls = extract_classes_and_calls(py_files)
        mermaid_code = generate_mermaid_class_diagram(classes, method_calls, project_name, direction="TD")
        if not mermaid_code.strip():
            return "No classes found in any Python file. Diagram will be empty."
        
        # Save the full Mermaid code to diagram.mmd
        diagram_path = os.path.join(os.getcwd(), "diagram.mmd")
        with open(diagram_path, "w", encoding="utf-8") as f:
            f.write(mermaid_code)
        
        # Limit the number of lines for the image if too large
        lines = mermaid_code.splitlines()
        if len(lines) > max_lines:
            limited_code = '\n'.join(lines[:max_lines])
            limited_code += '\n%% Diagram truncated. View full code in diagram.mmd.'
            return limited_code
        return mermaid_code
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Could not delete temp directory: {e}")

def generate_simplified_mermaid_from_repo(git_url):
    temp_dir = clone_repo(git_url)
    try:
        py_files = find_python_files(temp_dir)
        print(f"Found {len(py_files)} Python files in the repository.")
        project_name = os.path.basename(os.path.normpath(temp_dir))
        classes, _ = extract_classes_and_calls(py_files)  # Ignore method calls for simplicity
        print(f"Extracted {len(classes)} classes from the repository.")
        diagram = ["classDiagram"]
        for cname, cinfo in classes.items():
            diagram.append(f"class {cname} {{")
            for attr in sorted(cinfo['attrs']):
                diagram.append(f"  +{attr}")
            diagram.append("}")
        for cname, cinfo in classes.items():
            for base in cinfo['bases']:
                if base in classes:
                    diagram.append(f"{base} <|-- {cname}")
        print("Generated simplified Mermaid diagram:")
        print("\n".join(diagram))
        return "\n".join(diagram)
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Could not delete temp directory: {e}")
