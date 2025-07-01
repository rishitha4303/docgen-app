import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import DocInput from '../components/DocInput'
import DocOutput from '../components/DocOutput'
import './Home.css'

export default function Home() {
  const [docs, setDocs] = useState({})
  const [mermaidCode, setMermaidCode] = useState("")
  const navigate = useNavigate()

  useEffect(() => {
    const loggedIn = localStorage.getItem("loggedIn")
    if (!loggedIn) navigate("/")
  }, [])

  return (
    <div className="home-wrapper">
      <div className="docgen-container">
        <h1 className="main-heading">AI Documentation Generator 🧠</h1>
        <DocInput setDocs={setDocs} setMermaidCode={setMermaidCode} />
        <DocOutput docs={docs} mermaidCode={mermaidCode} />
      </div>
    </div>
  )
}