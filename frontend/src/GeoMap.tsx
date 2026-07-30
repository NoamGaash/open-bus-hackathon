// Map renderer for AnalysisResult.kind === 'geo' — a GeoJSON FeatureCollection,
// via react-leaflet. Per-feature styling (color/weight/dashed/popup) is read
// straight from each feature's `properties`, set server-side by openbus_hack's
// geo() helper.
//
// Point geometries render as CircleMarker rather than the default pin icon —
// Leaflet's default marker image paths break under bundlers unless you copy
// its asset files by hand, and a colored dot fits this data better anyway.

import { useEffect } from 'react'
import { GeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet'
import type { GeoJsonObject } from 'geojson'
import type { LatLngBoundsExpression, PathOptions } from 'leaflet'
import * as L from 'leaflet'
import 'leaflet/dist/leaflet.css'

import type { AnalysisResult } from './api'

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

export function GeoMap({ result }: { result: AnalysisResult }) {
  const data = result.geojson as GeoJsonObject | null
  if (!data) return <p className="muted">No map data.</p>

  return (
    <MapContainer
      center={[32.08, 34.78]}
      zoom={13}
      style={{ height: 420, width: '100%', borderRadius: 8, minWidth: 0 }}
      scrollWheelZoom={false}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
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
  )
}
