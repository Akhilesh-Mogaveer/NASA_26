import { useEffect } from 'react';
import { useMap } from 'react-leaflet';

/**
 * ChangeMapView — Leaflet Programmatic Map View Controller
 * 
 * Reusable helper component to reposition and zoom a Leaflet map
 * when center or zoom coordinates update.
 */
export default function ChangeMapView({ center, zoom }) {
  const map = useMap();

  useEffect(() => {
    if (center && map) {
      map.setView(center, zoom !== undefined ? zoom : map.getZoom());
    }
  }, [center, zoom, map]);

  return null;
}
