from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from docgen_utils import generate_docs
import os

load_dotenv()
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # frontend address
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DocRequest(BaseModel):
    repo_url: str


@app.post("/generate-docs")
def generate_doc(data: DocRequest):
    print(f"🔍 Cloning from: {data.repo_url}")
    return generate_docs(data.repo_url)
