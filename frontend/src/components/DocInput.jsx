import axios from 'axios'
import { useState } from 'react'
import './DocInput.css'

export default function DocInput({ setDocs, setMermaidCode }) {
  const [repoURL, setRepoURL] = useState("")
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [loadingMermaid, setLoadingMermaid] = useState(false)
  const [generatedMermaidCode, setGeneratedMermaidCode] = useState("")

  const submit = async () => {
    setLoadingDocs(true)
    setDocs({})
    try {
      const res = await axios.post(
        'http://localhost:8000/generate-docs',
        { repo_url: repoURL },
        {
          headers: {
            "Content-Type": "application/json"
          }
        }
      )
      setDocs(res.data?.docs || {})
    } catch (err) {
      console.error("Error:", err)
      alert("❌ Failed to generate docs. Check console for more info.")
    } finally {
      setLoadingDocs(false)
    }
  }

  const generateMermaid = async () => {
    setLoadingMermaid(true)
    setMermaidCode("")
    setGeneratedMermaidCode("")
    try {
      const res = await axios.post(
        'http://localhost:8000/generate-mermaid',
        { repo_url: repoURL },
        {
          headers: {
            "Content-Type": "application/json"
          }
        }
      )
      console.log("Mermaid code received from backend:", res.data?.mermaid_code)
      setMermaidCode(res.data?.mermaid_code || "")
      setGeneratedMermaidCode(res.data?.mermaid_code || "")
    } catch (err) {
      console.error("Error generating Mermaid diagram:", err)
      alert("❌ Failed to generate Mermaid diagram.")
    } finally {
      setLoadingMermaid(false)
    }
  }

  return (
    <div className="doc-input-section">
      <h2 className="input-heading">🧠 Code Documentation Generator</h2>
      <input
        type="text"
        value={repoURL}
        onChange={(e) => setRepoURL(e.target.value)}
        placeholder="Enter GitHub repo URL"
        className="url-input"
      />
      <button onClick={submit} disabled={loadingDocs} className="generate-btn" style={{ marginBottom: "20px" }}>
        {loadingDocs ? "Generating..." : "Generate Docs"}
      </button>
      <button onClick={generateMermaid} disabled={loadingMermaid} className="generate-btn" style={{ marginLeft: "20px"} }>
        {loadingMermaid ? "Generating..." : "Generate Mermaid"}
      </button>
      {loadingDocs && <p className="info-msg">⏳ Generating docs...</p>}
      {loadingMermaid && <p className="info-msg">⏳ Generating Mermaid diagram...</p>}

      {generatedMermaidCode && (
        <div className="mermaid-code-display">
          <pre style={{ display: "none" }}>{generatedMermaidCode}</pre>
        </div>
      )}
    </div>
  )
}