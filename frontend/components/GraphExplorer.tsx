"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import cytoscape from "cytoscape";
import type { GraphData } from "@/lib/types";

export const TYPE_COLOR: Record<string, string> = {
  PERSON: "#E8B65E", PHONE: "#3FBFA8", ACCOUNT: "#9C8CF0",
  VEHICLE: "#E86A9B", LOCATION: "#6FA8DC", ORGANIZATION: "#E5844D",
  UPI: "#7FD4C1", AADHAAR: "#E5484D", IFSC: "#8FA3B8",
};
const FALLBACK = "#6C819A";

/** Short tags so a node's kind reads without decoding its colour. */
export const TYPE_TAG: Record<string, string> = {
  PERSON: "PER", PHONE: "PH", ACCOUNT: "ACC", VEHICLE: "VEH",
  LOCATION: "LOC", ORGANIZATION: "ORG", UPI: "UPI", AADHAAR: "ADH", IFSC: "IFSC",
};

/**
 * Long identifiers are truncated on the canvas — the full value is always one
 * hover away, and the inspector shows it in full. A readable graph beats a
 * complete one.
 */
function shorten(type: string, label: string) {
  const s = String(label ?? "");
  if (type === "PHONE") return s.length > 6 ? "…" + s.slice(-5) : s;
  if (type === "ACCOUNT" || type === "AADHAAR" || type === "IFSC")
    return s.length > 9 ? "…" + s.slice(-6) : s;
  return s.length > 20 ? s.slice(0, 19) + "…" : s;
}

export default function GraphExplorer({
  data, onSelect, onReady, edgeLabels = false, className = "absolute inset-0",
}: {
  data: GraphData;
  onSelect?: (id: string, label: string) => void;
  onReady?: (cy: cytoscape.Core) => void;
  edgeLabels?: boolean;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [hover, setHover] = useState<any>(null);

  // Callback identities change on every parent render. Holding them in refs
  // keeps the build effect keyed on `data` alone — otherwise cytoscape is
  // destroyed and rebuilt on every render, which loops.
  const selectRef = useRef(onSelect);
  const readyRef = useRef(onReady);
  selectRef.current = onSelect;
  readyRef.current = onReady;

  /* Decorate the payload once: display label + tag, computed outside cytoscape
     so the style function stays cheap during layout. */
  const elements = useMemo(() => {
    if (!data) return [];
    const nodes = (data.nodes || []).map((n: any) => {
      const t = n.data.type || "";
      return {
        data: {
          ...n.data,
          tag: TYPE_TAG[t] || "ENT",
          full: n.data.label,
          disp: `${TYPE_TAG[t] || "ENT"} · ${shorten(t, n.data.label)}`,
        },
      };
    });
    return [...nodes, ...(data.edges || [])];
  }, [data]);

  useEffect(() => {
    if (!ref.current || !elements.length) return;

    const cy = cytoscape({
      container: ref.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": (el: any) => TYPE_COLOR[el.data("type")] || FALLBACK,
            "background-opacity": 0.85,
            label: "data(disp)",
            color: "#C3D0DE",
            "font-family": "IBM Plex Mono, monospace",
            "font-size": "9px",
            "text-valign": "bottom",
            "text-halign": "center",
            "text-margin-y": 6,
            "text-wrap": "wrap",
            "text-max-width": "112px",
            "text-outline-color": "#090E15",
            "text-outline-width": 3.5,
            // degree centrality is normalised 0..1 — sqrt keeps hubs readable
            // instead of letting them swallow the canvas.
            width:  (el: any) => Math.min(54, 15 + Math.sqrt(el.data("degree") || 0) * 46),
            height: (el: any) => Math.min(54, 15 + Math.sqrt(el.data("degree") || 0) * 46),
            "border-width": 1.6,
            "border-color": (el: any) => TYPE_COLOR[el.data("type")] || FALLBACK,
            "border-opacity": 0.45,
            "transition-property": "border-opacity, background-opacity, opacity",
            "transition-duration": "170ms",
          },
        },
        {
          selector: "edge",
          style: {
            width: (el: any) => 0.9 + (el.data("confidence") || 0.5) * 1.6,
            "line-color": "#2B3D52",
            "target-arrow-color": "#37506B",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 0.6,
            opacity: 0.85,
          },
        },
        {
          // relationship name, drawn on its own dark plate so it stays legible
          selector: "edge.showlabel",
          style: {
            label: "data(label)",
            "font-family": "IBM Plex Mono, monospace",
            "font-size": "8px",
            color: "#E8B65E",
            "text-rotation": "autorotate",
            "text-background-color": "#090E15",
            "text-background-opacity": 0.9,
            "text-background-padding": "2px",
            "text-background-shape": "roundrectangle",
          },
        },
        {
          selector: 'edge[status = "proposed"]',
          style: { "line-style": "dashed", "line-color": "#C8963E",
                   "target-arrow-color": "#C8963E", opacity: 0.55 },
        },
        {
          selector: "node:selected",
          style: { "border-width": 3, "border-color": "#E8B65E",
                   "border-opacity": 1, "background-opacity": 1,
                   "font-size": "10px", color: "#F2E4C6" },
        },
        { selector: ".dim", style: { opacity: 0.08, "text-opacity": 0.06 } },
        {
          selector: ".lit",
          style: { "line-color": "#E8B65E", "target-arrow-color": "#E8B65E",
                   opacity: 1, width: 1.8 },
        },
      ],
      layout: {
        name: "cose",
        animate: false,
        // counting the label box is what stops names from colliding
        nodeDimensionsIncludeLabels: true,
        nodeRepulsion: 22000,
        idealEdgeLength: 135,
        edgeElasticity: 120,
        gravity: 0.55,
        componentSpacing: 140,
        padding: 70,
        randomize: false,
      } as any,
      wheelSensitivity: 0.22,
      minZoom: 0.12,
      maxZoom: 3,
    });

    /* ------------------------------------------------------ interactions */
    cy.on("tap", "node", (e) => {
      const n = e.target;
      cy.elements().addClass("dim");
      n.removeClass("dim");
      n.neighborhood().removeClass("dim");
      // when you focus a node, its links name themselves
      n.connectedEdges().addClass("lit").addClass("showlabel");
      selectRef.current?.(n.id(), n.data("full"));
    });

    cy.on("tap", (e) => {
      if (e.target === cy) {
        cy.elements().removeClass("dim").removeClass("lit");
        cy.edges().removeClass("showlabel");
      }
    });

    cy.on("mouseover", "node", (e) => {
      const n = e.target;
      const p = n.renderedPosition();
      setHover({
        x: p.x, y: p.y - n.renderedHeight() / 2 - 10,
        full: n.data("full"), type: n.data("type"),
        degree: n.degree(false),
      });
      if (ref.current) ref.current.style.cursor = "pointer";
    });
    cy.on("mouseout", "node", () => {
      setHover(null);
      if (ref.current) ref.current.style.cursor = "";
    });
    cy.on("pan zoom", () => setHover(null));

    cyRef.current = cy;
    readyRef.current?.(cy);
    return () => { cy.destroy(); cyRef.current = null; };
  }, [elements]);

  /* Toggling link names must not rebuild the graph. */
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    if (edgeLabels) cy.edges().addClass("showlabel");
    else cy.edges().not(".lit").removeClass("showlabel");
  }, [edgeLabels, elements]);

  return (
    <div className={className}>
      <div ref={ref} className="absolute inset-0" />

      {hover && (
        <div className="pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-full"
             style={{ left: hover.x, top: hover.y }}>
          <div className="float px-2.5 py-1.5 whitespace-nowrap">
            <p className="font-mono text-[11px] text-txt">{hover.full}</p>
            <p className="lbl mt-0.5">
              {String(hover.type || "").toLowerCase()} · {hover.degree} connection
              {hover.degree === 1 ? "" : "s"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
