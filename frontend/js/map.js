/**
 * AquaCatch - Interactive Map Module
 * Manages Leaflet map layers, Leaflet.Draw land area selection, and hydrological overlays
 */

export class MapManager {
  constructor(containerId = 'map') {
    this.containerId = containerId;
    this.map = null;
    this.drawControl = null;

    // Layer Groups
    this.drawnItems = new L.FeatureGroup();
    this.pondMarkersGroup = new L.FeatureGroup();
    this.catchmentPolygonsGroup = new L.FeatureGroup();
    this.volumeBadgesGroup = new L.FeatureGroup();
    this.streamsGroup = new L.FeatureGroup();
    this.contoursGroup = new L.FeatureGroup();

    // State
    this.selectedAreaGeoJSON = null;
    this.activeDrawMode = null; // 'polygon', 'rectangle', 'pin'
    this.callbacks = {
      onAreaSelected: null,
      onPinPlaced: null,
      onPondClicked: null
    };

    // Survey default center (Durg/Bhilai, Chhattisgarh, India)
    this.defaultCenter = [21.2517, 81.2970];
    this.defaultZoom = 14;
  }

  init() {
    // Define Tile Providers
    const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
      maxZoom: 19
    });

    const cartoKey = 'cb1_407m_1_c5363034cbd5008135ddcbb2';
    const darkMatter = L.tileLayer(`https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png?key=${cartoKey}`, {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 20
    });

    const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19
    });

    const topo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
      attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)',
      maxZoom: 17
    });

    // Initialize Map
    this.map = L.map(this.containerId, {
      center: this.defaultCenter,
      zoom: this.defaultZoom,
      layers: [satellite], // Default to satellite for agricultural terrain inspection
      zoomControl: false
    });

    // Reposition zoom control to top-right
    L.control.zoom({ position: 'topright' }).addTo(this.map);

    // Scale control
    L.control.scale({ imperial: false, metric: true, position: 'bottomright' }).addTo(this.map);

    // Layer Controls
    const baseMaps = {
      '🛰️ Satellite (Esri)': satellite,
      '🌙 Dark GIS (CartoDB)': darkMatter,
      '🗺️ Street Map (OSM)': osm,
      '⛰️ Topography (OpenTopo)': topo
    };

    const overlayMaps = {
      '📐 Selected Land Parcel': this.drawnItems,
      '📍 Suggested Pond Sites': this.pondMarkersGroup,
      '🏞️ Catchment Watersheds': this.catchmentPolygonsGroup,
      '💧 Water Volume Callouts': this.volumeBadgesGroup,
      '🌊 Drainage Streams': this.streamsGroup,
      '〰️ Topo Contours (2m)': this.contoursGroup
    };

    L.control.layers(baseMaps, overlayMaps, { position: 'topright', collapsed: false }).addTo(this.map);

    // Add layer groups to map
    this.drawnItems.addTo(this.map);
    this.catchmentPolygonsGroup.addTo(this.map);
    this.streamsGroup.addTo(this.map);
    this.contoursGroup.addTo(this.map);
    this.pondMarkersGroup.addTo(this.map);
    this.volumeBadgesGroup.addTo(this.map);

    // Setup Leaflet Draw
    this.setupDrawControls();

    // Map Event Listeners
    this.setupMapEvents();

    return this;
  }

  setupDrawControls() {
    const drawOptions = {
      position: 'topleft',
      draw: {
        polyline: false,
        circle: false,
        circlemarker: false,
        marker: {
          icon: L.divIcon({
            className: 'custom-pin-icon',
            html: '<div style="font-size:24px;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.5))">📍</div>',
            iconSize: [24, 24],
            iconAnchor: [12, 24]
          })
        },
        polygon: {
          allowIntersection: false,
          showArea: true,
          shapeOptions: {
            color: '#f59e0b',
            weight: 2.5,
            dashArray: '6, 6',
            fillColor: '#f59e0b',
            fillOpacity: 0.15
          }
        },
        rectangle: {
          shapeOptions: {
            color: '#f59e0b',
            weight: 2.5,
            dashArray: '6, 6',
            fillColor: '#f59e0b',
            fillOpacity: 0.15
          }
        }
      },
      edit: {
        featureGroup: this.drawnItems,
        remove: true
      }
    };

    this.drawControl = new L.Control.Draw(drawOptions);
    this.map.addControl(this.drawControl);

    // Listen for created layers
    this.map.on(L.Draw.Event.CREATED, (e) => {
      const type = e.layerType;
      const layer = e.layer;

      if (type === 'marker') {
        // User clicked a custom site pin
        const latlng = layer.getLatLng();
        if (this.callbacks.onPinPlaced) {
          this.callbacks.onPinPlaced(latlng.lat, latlng.lng);
        }
        return;
      }

      // Clear previous drawn land area
      this.drawnItems.clearLayers();
      this.drawnItems.addLayer(layer);

      const geojson = layer.toGeoJSON();
      this.selectedAreaGeoJSON = geojson;

      // Calculate area
      const areaM2 = this.calculatePolygonArea(layer);
      const areaHa = areaM2 / 10000.0;
      const areaAc = areaM2 / 4046.86;

      // Add interactive tooltip
      layer.bindTooltip(`<b>Selected Land Parcel</b><br>${areaHa.toFixed(2)} ha (${Math.round(areaM2).toLocaleString()} m²)`, {
        permanent: false,
        direction: 'center',
        className: 'land-parcel-tooltip'
      });

      if (this.callbacks.onAreaSelected) {
        this.callbacks.onAreaSelected({
          geojson,
          areaM2,
          areaHa,
          areaAc,
          bounds: layer.getBounds()
        });
      }
    });

    this.map.on(L.Draw.Event.DELETED, () => {
      this.selectedAreaGeoJSON = null;
      if (this.callbacks.onAreaSelected) {
        this.callbacks.onAreaSelected(null);
      }
    });
  }

  setupMapEvents() {
    const coordsEl = document.getElementById('cursorCoords');

    this.map.on('mousemove', (e) => {
      if (coordsEl) {
        coordsEl.textContent = `Lat: ${e.latlng.lat.toFixed(5)}°, Lon: ${e.latlng.lng.toFixed(5)}°`;
      }
    });

    // Custom site click when in pin mode
    this.map.on('click', (e) => {
      if (this.activeDrawMode === 'pin') {
        if (this.callbacks.onPinPlaced) {
          this.callbacks.onPinPlaced(e.latlng.lat, e.latlng.lng);
        }
        this.setDrawMode(null);
      }
    });
  }

  setDrawMode(mode) {
    this.activeDrawMode = mode;
    const container = document.getElementById(this.containerId);
    if (mode === 'pin') {
      container.style.cursor = 'crosshair';
    } else {
      container.style.cursor = '';
    }
  }

  /**
   * Start manual drawing programmatically
   */
  startDrawPolygon() {
    new L.Draw.Polygon(this.map, this.drawControl.options.draw.polygon).enable();
  }

  startDrawRectangle() {
    new L.Draw.Rectangle(this.map, this.drawControl.options.draw.rectangle).enable();
  }

  clearSelection() {
    this.drawnItems.clearLayers();
    this.selectedAreaGeoJSON = null;
    if (this.callbacks.onAreaSelected) {
      this.callbacks.onAreaSelected(null);
    }
  }

  /**
   * Calculate polygon area in m² using Turf.js or spherical approximation
   */
  calculatePolygonArea(layer) {
    if (window.turf) {
      try {
        const geojson = layer.toGeoJSON();
        return turf.area(geojson);
      } catch (e) {
        console.warn('Turf area calculation failed, falling back:', e);
      }
    }
    // Fallback: Leaflet GeometryUtil approximation
    const latlngs = layer.getLatLngs()[0] || layer.getLatLngs();
    return L.GeometryUtil ? L.GeometryUtil.geodesicArea(latlngs) : 0;
  }

  /**
   * Check if a coordinate [lat, lon] is inside the currently selected polygon
   */
  isPointInsideSelection(lat, lon) {
    if (!this.selectedAreaGeoJSON) return true; // If no selection, all points are accepted

    if (window.turf) {
      try {
        const pt = turf.point([lon, lat]);
        return turf.booleanPointInPolygon(pt, this.selectedAreaGeoJSON);
      } catch (e) {
        console.warn('Turf point-in-polygon error:', e);
      }
    }
    return true;
  }

  /**
   * Set a predefined land parcel
   */
  setPresetArea(boundsCoords, name = 'Preset Parcel') {
    this.drawnItems.clearLayers();

    const polygon = L.polygon(boundsCoords, {
      color: '#f59e0b',
      weight: 2.5,
      dashArray: '6, 6',
      fillColor: '#f59e0b',
      fillOpacity: 0.15
    });

    this.drawnItems.addLayer(polygon);
    this.selectedAreaGeoJSON = polygon.toGeoJSON();

    const areaM2 = this.calculatePolygonArea(polygon);
    const areaHa = areaM2 / 10000.0;
    const areaAc = areaM2 / 4046.86;

    polygon.bindTooltip(`<b>${name}</b><br>${areaHa.toFixed(2)} ha (${Math.round(areaM2).toLocaleString()} m²)`, {
      permanent: false,
      direction: 'center'
    });

    this.map.fitBounds(polygon.getBounds(), { padding: [40, 40], maxZoom: 16 });

    if (this.callbacks.onAreaSelected) {
      this.callbacks.onAreaSelected({
        geojson: this.selectedAreaGeoJSON,
        areaM2,
        areaHa,
        areaAc,
        bounds: polygon.getBounds()
      });
    }
  }

  /**
   * Render Suggested Pond Location marker on the map
   */
  renderPondCandidate(candidate, isRankOne = true) {
    const lat = candidate.latitude;
    const lon = candidate.longitude;
    const rank = candidate.rank || 1;

    // Custom pulsing SVG icon
    const iconHtml = `
      <div class="pond-pulsing-marker">
        <div class="pulse"></div>
        <div class="pin">
          <span>💧</span>
        </div>
      </div>
    `;

    const icon = L.divIcon({
      className: 'custom-pond-div-icon',
      html: iconHtml,
      iconSize: [32, 32],
      iconAnchor: [16, 32]
    });

    const marker = L.marker([lat, lon], { icon, zIndexOffset: 1000 });

    const suitabilityPct = Math.round((candidate.suitability_score || 0.85) * 100);

    const popupHtml = `
      <div style="min-width: 200px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <span style="background:#0284c7; color:#fff; font-size:10px; font-weight:700; padding:2px 8px; border-radius:99px;">
            SUGGESTED POND #${rank}
          </span>
          <span style="color:#10b981; font-weight:700; font-size:12px;">${suitabilityPct}% Suitable</span>
        </div>
        <div style="font-size:12px; display:flex; flex-direction:column; gap:4px; margin-bottom:8px;">
          <div><b>Elevation:</b> ${candidate.elevation_m.toFixed(1)} m</div>
          <div><b>Slope:</b> ${candidate.slope_degrees.toFixed(2)}°</div>
          <div><b>Coordinates:</b> ${lat.toFixed(5)}°N, ${lon.toFixed(5)}°E</div>
        </div>
        <a href="${candidate.google_maps_url || `https://www.google.com/maps?q=${lat},${lon}`}" target="_blank"
           style="display:inline-block; width:100%; text-align:center; background:#1e293b; color:#38bdf8; border:1px solid #38bdf8; padding:5px 0; border-radius:6px; font-size:11px; text-decoration:none; font-weight:600;">
           Open Satellite in Google Maps ↗
        </a>
      </div>
    `;

    marker.bindPopup(popupHtml);
    marker.bindTooltip(`<b>Suggested Pond Site #${rank}</b><br>Elev: ${candidate.elevation_m.toFixed(1)}m • Score: ${suitabilityPct}%`, {
      direction: 'top',
      offset: [0, -32]
    });

    marker.on('click', () => {
      if (this.callbacks.onPondClicked) {
        this.callbacks.onPondClicked(candidate);
      }
    });

    this.pondMarkersGroup.addLayer(marker);
    return marker;
  }

  /**
   * Render Catchment Area polygon on the map
   */
  renderCatchmentPolygon(geojsonFeature, rank = 1) {
    const layer = L.geoJSON(geojsonFeature, {
      style: {
        color: '#0284c7',
        weight: 2.5,
        opacity: 0.9,
        fillColor: '#38bdf8',
        fillOpacity: 0.35,
        dashArray: null
      },
      onEachFeature: (feature, l) => {
        const props = feature.properties || {};
        const areaHa = props.area_hectares ? props.area_hectares.toFixed(2) : (props.area_m2 / 10000).toFixed(2);
        const areaM2 = props.area_m2 ? Math.round(props.area_m2).toLocaleString() : '';

        l.bindTooltip(`<b>Catchment Watershed #${rank}</b><br>${areaHa} ha (${areaM2} m²)`, {
          sticky: true,
          direction: 'auto'
        });

        l.on('mouseover', () => {
          l.setStyle({ fillOpacity: 0.55, weight: 3.5, color: '#38bdf8' });
        });
        l.on('mouseout', () => {
          l.setStyle({ fillOpacity: 0.35, weight: 2.5, color: '#0284c7' });
        });
      }
    });

    this.catchmentPolygonsGroup.addLayer(layer);
    return layer;
  }

  /**
   * Render Expected Water Volume badge directly overlaid on the map
   */
  renderVolumeCallout(lat, lon, waterMetrics, rank = 1) {
    const formattedYield = `${waterMetrics.volumeMegaLiters} ML`;
    const formattedM3 = `${waterMetrics.collectibleVolumeM3.toLocaleString()} m³`;

    const badgeHtml = `
      <div class="map-volume-badge" title="Click to view detailed water balance">
        <div class="header">
          <span>💧 EXPECTED WATER VOLUME</span>
        </div>
        <div class="vol">${formattedYield}</div>
        <div class="area">${formattedM3} • Catchment: ${waterMetrics.catchmentAreaHa.toFixed(2)} ha</div>
      </div>
    `;

    const icon = L.divIcon({
      className: 'custom-volume-callout-icon',
      html: badgeHtml,
      iconSize: [180, 50],
      iconAnchor: [90, -10] // Placed slightly above/below the pond point
    });

    const marker = L.marker([lat, lon], { icon, interactive: true, zIndexOffset: 900 });
    marker.on('click', () => {
      // Trigger volume details
      const tabBtn = document.getElementById('tabResultsBtn');
      if (tabBtn) tabBtn.click();
    });

    this.volumeBadgesGroup.addLayer(marker);
    return marker;
  }

  /**
   * Render Drainage Stream lines
   */
  renderStreams(streamGeoJSON) {
    this.streamsGroup.clearLayers();
    if (!streamGeoJSON) return;

    const layer = L.geoJSON(streamGeoJSON, {
      style: {
        color: '#06b6d4',
        weight: 2.0,
        opacity: 0.8
      }
    });

    this.streamsGroup.addLayer(layer);
  }

  /**
   * Render Topographic Contours GeoJSON
   */
  renderContours(contoursGeoJSON) {
    this.contoursGroup.clearLayers();
    if (!contoursGeoJSON) return;

    const layer = L.geoJSON(contoursGeoJSON, {
      style: (feature) => {
        const isIndex = feature.properties && feature.properties.is_index;
        return {
          color: isIndex ? '#94a3b8' : '#64748b',
          weight: isIndex ? 1.5 : 0.8,
          opacity: isIndex ? 0.6 : 0.35
        };
      },
      onEachFeature: (feature, l) => {
        const elev = feature.properties ? feature.properties.elevation : '';
        if (elev) {
          l.bindTooltip(`${elev} m`, { sticky: true, className: 'contour-tooltip' });
        }
      }
    });

    this.contoursGroup.addLayer(layer);
  }

  /**
   * Clear results overlays
   */
  clearResults() {
    this.pondMarkersGroup.clearLayers();
    this.catchmentPolygonsGroup.clearLayers();
    this.volumeBadgesGroup.clearLayers();
  }

  /**
   * Fit view to show both the selected land area, pond, and catchment
   */
  fitToFeatures(boundsList = []) {
    const group = new L.FeatureGroup();

    if (this.drawnItems.getLayers().length > 0) {
      group.addLayer(this.drawnItems);
    }
    if (this.catchmentPolygonsGroup.getLayers().length > 0) {
      group.addLayer(this.catchmentPolygonsGroup);
    }
    if (this.pondMarkersGroup.getLayers().length > 0) {
      group.addLayer(this.pondMarkersGroup);
    }

    if (group.getLayers().length > 0) {
      this.map.fitBounds(group.getBounds(), { padding: [50, 50], maxZoom: 16 });
    }
  }
}
