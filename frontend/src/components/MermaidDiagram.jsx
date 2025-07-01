import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import axios from "axios";

export default function MermaidDiagram({ id }) {
  const container = useRef(null);
  const [code, setCode] = useState("");
  const [renderFailed, setRenderFailed] = useState(false);

  useEffect(() => {
    // Fetch Mermaid code from backend
    axios
      .get("http://localhost:8000/get-mermaid-diagram")
      .then((response) => {
        setCode(response.data);
      })
      .catch((error) => {
        console.error("Error fetching Mermaid code:", error);
        setRenderFailed(true);
      });
  }, []);

  useEffect(() => {
    if (container.current && code) {
      console.log("Rendering Mermaid diagram with code:", code);
      container.current.innerHTML = ""; // Clear previous content
      const mermaidDiv = document.createElement("div");
      mermaidDiv.className = "mermaid";
      container.current.appendChild(mermaidDiv);

      try {
        mermaid.render(id, code, (svgCode) => {
          if (!svgCode) {
            throw new Error("Mermaid rendering failed: No SVG code generated.");
          }
          mermaidDiv.innerHTML = svgCode;
          setRenderFailed(false);
        });
        console.log("Mermaid diagram rendered successfully.");
      } catch (error) {
        console.error("Error rendering Mermaid diagram:", error);
        setRenderFailed(true);
      }
    }
  }, [code, id]);

  if (renderFailed) {
    return (
      <div>
        <p>
          Error rendering diagram. You can view it in the Mermaid Live Editor:
        </p>
        <a
          href="https://mermaid-js.github.io/mermaid-live-editor"
          target="_blank"
          rel="noopener noreferrer"
        >
          Open Mermaid Live Editor
        </a>
      </div>
    );
  }

  return (
    <div>
      <div ref={container} id={id} />
      <a
        href={`/mermaid-diagram.html?code=${encodeURIComponent(code)}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        View Full Diagram
      </a>
    </div>
  );
}
