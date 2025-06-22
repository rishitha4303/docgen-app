// components/MermaidDiagram.jsx
import { useEffect, useRef } from "react";

export default function MermaidDiagram({ code, id = "mermaid-diagram" }) {
  const ref = useRef(null);

  useEffect(() => {
    if (window.mermaid && ref.current) {
      // Clear previous content
      ref.current.innerHTML = `<div class="mermaid">${code}</div>`;
      try {
        window.mermaid.init(undefined, ref.current);
      // eslint-disable-next-line no-unused-vars
      } catch (err) {
        ref.current.innerHTML = "Invalid Mermaid syntax";
      }
    }
  }, [code]);

  return <div ref={ref} id={id} />;
}
