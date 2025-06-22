import { useState } from "react";
import { jsPDF } from "jspdf";
import MermaidDiagram from "./MermaidDiagram";
import "./DocOutput.css";

export default function DocOutput({ docs }) {
  const [showFlow, setShowFlow] = useState(false);

  if (!docs || Object.keys(docs).length === 0) return null;

  const cleanText = (text) =>
    text.replace(/[*_#`~✅❌📄🧠]+/gu, "").trim();

  const downloadPDF = () => {
    const doc = new jsPDF();
    doc.setFontSize(12);
    let y = 10;

    Object.entries(docs).forEach(([file, explanation]) => {
      if (file === "__MERMAID__") return;
      doc.setFont("helvetica", "bold");
      doc.text(file, 10, y);
      y += 7;

      const clean = cleanText(explanation);
      const lines = doc.splitTextToSize(clean, 180);
      doc.setFont("helvetica", "normal");

      lines.forEach(line => {
        if (y > 280) {
          doc.addPage();
          y = 10;
        }
        doc.text(line, 10, y);
        y += 6;
      });

      y += 10;
    });

    doc.save("documentation.pdf");
  };

  return (
    <div>
      <h2>Generated Documentation</h2>
      <button onClick={downloadPDF}>Download PDF</button>

      {Object.entries(docs).map(([file, explanation]) => {
        if (file === "__MERMAID__") return null;
        return (
          <div key={file} className="doc-card">
            <h3>{file}</h3>
            <pre className="doc-text">{cleanText(explanation)}</pre>
          </div>
        );
      })}

      {docs["__MERMAID__"] && (
        <div className="doc-card">
          <button onClick={() => setShowFlow(!showFlow)}>
            {showFlow ? "Hide Diagram" : "Show Class Diagram"}
          </button>

          {showFlow && (
            <div style={{ marginTop: "15px", textAlign: "left" }}>
              <h3>📊 Class Diagram (Mermaid)</h3>
              <MermaidDiagram code={docs["__MERMAID__"]} id="main-mermaid" />
              <p style={{ fontSize: "14px", color: "#888" }}>
                👉 You can also copy this code to <a href="https://mermaid.live" target="_blank" rel="noreferrer">mermaid.live</a> for editing.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
