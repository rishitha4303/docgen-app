import { jsPDF } from "jspdf";
import "./DocOutput.css";
import MermaidDiagram from "./MermaidDiagram";

function Documentation({ docs }) {
  const cleanText = (text) =>
    text.replace(/[*_#`~✅❌📄🧠]+/gu, "").trim();

  const downloadPDF = () => {
    const doc = new jsPDF();
    doc.setFontSize(12);
    let y = 10;

    Object.entries(docs).forEach(([file, explanation]) => {
      doc.setFont("helvetica", "bold");
      doc.text(file, 10, y);
      y += 7;

      const clean = cleanText(explanation);
      const lines = doc.splitTextToSize(clean, 180);
      doc.setFont("helvetica", "normal");

      lines.forEach((line) => {
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

  if (!docs || Object.keys(docs).length === 0) return null;

  return (
    <div>
      <h2>Generated Documentation</h2>
      <button onClick={downloadPDF}>Download PDF</button>

      {Object.entries(docs).map(([file, explanation]) => (
        <div key={file} className="doc-card">
          <h3>{file}</h3>
          <pre className="doc-text">{cleanText(explanation)}</pre>
        </div>
      ))}
    </div>
  );
}

function MermaidDiagramSection({ mermaidCode }) {
  if (!mermaidCode) return null;

  return (
    <div className="doc-card">
      <h3>📊 Class Diagram (Mermaid)</h3>
      <MermaidDiagram code={mermaidCode} id="mermaid-diagram" />
    </div>
  );
}

export default function DocOutput({ docs, mermaidCode }) {
  console.log("Rendering DocOutput with Mermaid code:", mermaidCode);

  return (
    <div>
      <Documentation docs={docs} />
      <MermaidDiagramSection mermaidCode={mermaidCode} />
    </div>
  );
}