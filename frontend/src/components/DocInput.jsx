import axios from 'axios'
import { useState } from 'react'
import './DocInput.css'

export default function DocInput({ setDocs }) {
  const [repoURL, setRepoURL] = useState("")
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    setLoading(true)
    setDocs({})
    try {
      const res = await axios.post(
        'http://localhost:8000/generate-docs',
        { repo_url: repoURL },
        {
          headers: { token: 'mysecretkey123' }
        }
      )
      setDocs(res.data?.docs || {})
    } catch (err) {
      console.error("Error:", err)
    } finally {
      setLoading(false)
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
      <button onClick={submit} disabled={loading} className="generate-btn">
        {loading ? "Generating..." : "Generate Docs"}
      </button>
      {loading && <p className="info-msg">⏳ Please wait, generating...</p>}
    </div>
  )
}
