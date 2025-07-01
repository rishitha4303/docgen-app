from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from docgen_utils import generate_docs
from mermaid_gen import generate_mermaid_from_repo, generate_simplified_mermaid_from_repo
from fastapi.responses import FileResponse

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DocRequest(BaseModel):
    repo_url: str

@app.post("/generate-docs")
def generate_doc(data: DocRequest):
    return generate_docs(data.repo_url)

class MermaidRequest(BaseModel):
    repo_url: str

@app.post("/generate-mermaid")
def generate_mermaid(data: MermaidRequest):
    code = generate_mermaid_from_repo(data.repo_url)
    return {"mermaid_code": code}

@app.post("/generate-simplified-mermaid")
def generate_simplified_mermaid_endpoint(data: MermaidRequest):
    """Endpoint to generate a simplified Mermaid diagram."""
    mermaid_code = generate_simplified_mermaid_from_repo(data.repo_url)
    with open("diagram.mmd", "w", encoding="utf-8") as f:
        f.write(mermaid_code)
    return {"mermaid_code": mermaid_code}

@app.get("/get-mermaid-diagram")
def get_mermaid_diagram():
    """Endpoint to serve the contents of diagram.mmd."""
    return FileResponse("diagram.mmd", media_type="text/plain")