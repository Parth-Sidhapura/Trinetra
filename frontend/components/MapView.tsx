"use client";
import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

/**
 * Co-location map.
 *
 * GPS fixes render as small solid dots — a precise claim.
 * Cell-tower associations render as large translucent coverage circles —
 * because tower data cannot support a point-level location claim.
 */
export default function MapView({ data }: { data: any }) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!ref.current || !data?.points) return;

    const pts = data.points;
    const center: [number, number] = pts.length
      ? [pts[0].lon, pts[0].lat]
      : [77.2295, 28.6129];

    const map = new maplibregl.Map({
      container: ref.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
      center,
      zoom: 10,
    });

    map.on("load", () => {
      map.addSource("points", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: pts.map((p: any) => ({
            type: "Feature",
            geometry: { type: "Point", coordinates: [p.lon, p.lat] },
            properties: { ...p },
          })),
        },
      });

      // Cell-tower coverage areas — deliberately fuzzy, never a point fix
      map.addLayer({
        id: "coverage",
        type: "circle",
        source: "points",
        filter: ["==", ["get", "precision"], "cell_tower"],
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 12, 14, 46],
          "circle-color": "#C8963E",
          "circle-opacity": 0.15,
          "circle-stroke-color": "#C8963E",
          "circle-stroke-width": 1,
          "circle-stroke-opacity": 0.5,
        },
      });

      // GPS fixes — small solid dots
      map.addLayer({
        id: "gps",
        type: "circle",
        source: "points",
        filter: ["==", ["get", "precision"], "gps"],
        paint: {
          "circle-radius": 5,
          "circle-color": "#6FA8DC",
          "circle-stroke-color": "#060910",
          "circle-stroke-width": 1,
        },
      });

      const popup = new maplibregl.Popup({ closeButton: false });
      for (const layer of ["gps", "coverage"]) {
        map.on("mouseenter", layer, (e: any) => {
          const p = e.features[0].properties;
          map.getCanvas().style.cursor = "pointer";
          popup
            .setLngLat(e.lngLat)
            .setHTML(
              `<div style="font:11px monospace;color:#111">
                 <b>${p.entity_name}</b><br/>
                 ${p.precision === "gps"
                   ? "GPS fix — precise"
                   : `Serving cell ${p.tower_id} — coverage area, not a point fix`}
                 <br/>${new Date(p.occurred_at).toLocaleString()}
               </div>`
            )
            .addTo(map);
        });
        map.on("mouseleave", layer, () => {
          map.getCanvas().style.cursor = "";
          popup.remove();
        });
      }
    });

    mapRef.current = map;
    return () => map.remove();
  }, [data]);

  return (
    <div>
      <div ref={ref} className="w-full h-[clamp(400px,58vh,640px)] rounded-lg border border-rule shadow-lift" />
      <div className="flex gap-5 mt-2.5 flex-wrap text-[10.5px] text-faint">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-steel" /> GPS fix — precise
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3.5 h-3.5 rounded-full border border-brass bg-brass/20" />
          Cell coverage — <b>not</b> a point location
        </span>
      </div>
    </div>
  );
}
