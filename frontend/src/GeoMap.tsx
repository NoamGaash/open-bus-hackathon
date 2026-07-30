// Map renderer for AnalysisResult.kind === 'geo' — a GeoJSON FeatureCollection,
// via react-leaflet. Per-feature styling (color/weight/dashed/popup) is read
// straight from each feature's `properties`, set server-side by openbus_hack's
// geo() helper.
//
// Point geometries render as CircleMarker rather than the default pin icon —
// Leaflet's default marker image paths break under bundlers unless you copy
// its asset files by hand, and a colored dot fits this data better anyway.

import { useEffect, useState } from 'react'
import { GeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet'
import type { GeoJsonObject } from 'geojson'
import type { LatLngBoundsExpression, PathOptions } from 'leaflet'
import * as L from 'leaflet'
import 'leaflet/dist/leaflet.css'

import type { AnalysisResult, GeoLegendData } from './api'

const DEFAULT_COLOR = '#2a78d6'

interface FeatureProps {
  color?: string
  weight?: number
  dashed?: boolean
  popup?: string
}

function styleFor(props: FeatureProps): PathOptions {
  return {
    color: props.color ?? DEFAULT_COLOR,
    weight: props.weight ?? 3,
    opacity: 0.9,
    dashArray: props.dashed ? '6 6' : undefined,
  }
}

/** Leaflet needs an explicit fitBounds call — GeoJSON data doesn't drive the
    map's viewport on its own. */
function FitBounds({ data }: { data: GeoJsonObject }) {
  const map = useMap()
  useEffect(() => {
    const bounds = L.geoJSON(data).getBounds()
    if (bounds.isValid()) {
      map.fitBounds(bounds as LatLngBoundsExpression, { padding: [24, 24] })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])
  return null
}

/** Tracks the page's light/dark state so the basemap doesn't stay blinding
    white inside a dark card. The toggle stamps data-theme on <html>. */
function useIsDark(): boolean {
  const read = () => {
    const attr = document.documentElement.dataset.theme
    if (attr === 'dark') return true
    if (attr === 'light') return false
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  }
  const [dark, setDark] = useState(read)
  useEffect(() => {
    const obs = new MutationObserver(() => setDark(read()))
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)')
    const onMq = () => setDark(read())
    mq?.addEventListener('change', onMq)
    return () => {
      obs.disconnect()
      mq?.removeEventListener('change', onMq)
    }
  }, [])
  return dark
}

export function GeoMap({ result }: { result: AnalysisResult }) {
  const data = result.geojson as GeoJsonObject | null
  const isDark = useIsDark()
  if (!data) return <p className="muted">No map data.</p>

  return (
    <div style={{ minWidth: 0 }}>
    <MapContainer
      center={[32.08, 34.78]}
      zoom={13}
      style={{ height: 420, width: '100%', borderRadius: 8, minWidth: 0 }}
      scrollWheelZoom={false}
    >
      {/* CARTO's basemaps ship a matching dark variant; plain OSM has none, and
          CSS-inverting tiles turns the map's own labels unreadable. */}
      <TileLayer
        key={isDark ? 'dark' : 'light'}
        attribution={
          isDark
            ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }
        url={
          isDark
            ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
            : 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
        }
      />
      <GeoJSON
        data={data}
        style={(feature) => styleFor((feature?.properties ?? {}) as FeatureProps)}
        pointToLayer={(feature, latlng) => {
          const props = (feature.properties ?? {}) as FeatureProps
          const marker = L.circleMarker(latlng, {
            radius: props.weight ?? 6,
            color: props.color ?? DEFAULT_COLOR,
            weight: 2,
            fillOpacity: 0.7,
          })
          if (props.popup) marker.bindPopup(props.popup)
          return marker
        }}
        onEachFeature={(feature, layer) => {
          const props = (feature.properties ?? {}) as FeatureProps
          if (props.popup && feature.geometry.type !== 'Point') layer.bindPopup(props.popup)
        }}
      />
      <FitBounds data={data} />
    </MapContainer>
    {result.geo_legend && <GeoLegend legend={result.geo_legend} />}
    </div>
  )
}

function GeoLegend({ legend }: { legend: GeoLegendData }) {
  return (
    <div className="legend" style={{ marginTop: 10, alignItems: 'center' }}>
      {legend.colors.length > 0 && (
        <>
          <span className="muted" style={{ fontSize: 11 }}>
            {legend.min_label ?? ''}
          </span>
          <span
            aria-label={legend.label}
            style={{
              width: 120,
              height: 12,
              borderRadius: 2,
              background: `linear-gradient(to right, ${legend.colors.join(', ')})`,
            }}
          />
          <span className="muted" style={{ fontSize: 11 }}>
            {legend.max_label ?? ''}
          </span>
          <span className="muted" style={{ fontSize: 11 }}>
            {legend.label}
          </span>
        </>
      )}
      {legend.items.map((it, i) => (
        <span key={i} className="legend-item">
          {/* Dashed entries get a line, not a block — the distinction the
              swatch is there to make is the stroke style itself. */}
          <i
            className="swatch"
            style={{
              width: 18,
              height: it.dashed ? 0 : 10,
              borderRadius: 2,
              background: it.dashed ? 'transparent' : (it.color ?? 'var(--ink-2)'),
              borderTop: it.dashed ? `2px dashed ${it.color ?? 'var(--ink-2)'}` : undefined,
            }}
          />
          {it.label}
        </span>
      ))}
    </div>
  )
}
