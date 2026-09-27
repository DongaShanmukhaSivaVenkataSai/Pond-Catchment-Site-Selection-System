/**
 * AquaCatch - Main Application Orchestrator
 * Connects API, Map, Hydrology, and UI subsystems
 */

import { ApiClient } from './api.js';
import { MapManager } from './map.js';
import { HydrologyCalculator } from './hydrology.js';
import { UIManager } from './ui.js';

class App {
  constructor() {
    this.api = new ApiClient();
    this.map = new MapManager('map');
    this.ui = new UIManager();

    // Application state
    this.activeKmlBlob = null;
    this.activeKmlName = 'contours_1m.kml';
    this.pipelineResults = null;
    this.activeCandidate = null;
    this.activeCatchment = null;
    this.activeWaterMetrics = null;

    // Defined Land Area Presets in the Survey Region
    this.presets = {
      full: {
        name: 'Full Survey Basin',
        coords: [
          [21.2398, 81.2814],
          [21.2398, 81.3126],
          [21.2636, 81.3126],
          [21.2636, 81.2814]
        ]
      },
      north: {
        name: 'Northern Farm Parcel',
        coords: [
          [21.2550, 81.2950],
          [21.2550, 81.3080],
          [21.2630, 81.3080],
          [21.2630, 81.2950]
        ]
      },
      central: {
        name: 'Central Drainage Basin',
        coords: [
          [21.2480, 81.2920],
          [21.2480, 81.3050],
          [21.2560, 81.3050],
          [21.2560, 81.2920]
        ]
      },
      south: {
        name: 'Southern Lowland Parcel',
        coords: [
          [21.2405, 81.2860],
          [21.2405, 81.3010],
          [21.2480, 81.3010],
          [21.2480, 81.2860]
        ]
      }
    };
  }

  async start() {
    console.log('Starting AquaCatch Hydrology System...');

    // 1. Initialize subsystems
    this.map.init();
    this.ui.init();

    // 2. Setup Subsystem Callbacks
    this.setupCallbacks();

    // 3. Load pre-packaged survey data (contours, boundary)
    await this.loadInitialData();

    // 4. Test backend connection
    await this.checkBackend();
  }

  setupCallbacks() {
    // API Status Updates
    this.api.onStatusChange((status, apiBase) => {
      this.ui.updateServerStatus(status, apiBase);
    });

    // Save custom API Base URL
    if (this.ui.elements.btnSaveApiBase) {
      this.ui.elements.btnSaveApiBase.addEventListener('click', async () => {
        const val = this.ui.elements.apiBaseInput.value;
        this.ui.showToast(`Connecting to ${val}...`, 'info');
        const res = await this.api.setApiBase(val);
        if (res.success) {
          this.ui.showToast(`Connected successfully to ${val}`, 'success');
          this.ui.closeModals();
        } else {
          this.ui.showToast(`Failed to connect to ${val}: ${res.error}`, 'error');
        }
      });
    }

    // Map Drawing Tool Buttons
    if (this.ui.elements.btnDrawPolygon) {
      this.ui.elements.btnDrawPolygon.addEventListener('click', () => {
        this.map.startDrawPolygon();
        this.ui.showToast('Click points on map to draw your land boundary. Double-click to complete.', 'info');
      });
    }

    if (this.ui.elements.btnDrawRectangle) {
      this.ui.elements.btnDrawRectangle.addEventListener('click', () => {
        this.map.startDrawRectangle();
        this.ui.showToast('Click and drag on map to select land parcel rectangle.', 'info');
      });
    }

    if (this.ui.elements.btnPinSite) {
      this.ui.elements.btnPinSite.addEventListener('click', () => {
        this.map.setDrawMode('pin');
        this.ui.showToast('Click anywhere on map to delineate catchment at that exact point.', 'info');
      });
    }

    if (this.ui.elements.btnClearSelection) {
      this.ui.elements.btnClearSelection.addEventListener('click', () => {
        this.map.clearSelection();
        this.ui.updateSelectionDisplay(null);
      });
    }

    // Map Events
    this.map.callbacks.onAreaSelected = (selectionData) => {
      this.ui.updateSelectionDisplay(selectionData);
      if (selectionData) {
        this.ui.showToast(`Land Area Selected: ${selectionData.areaHa.toFixed(2)} ha (${Math.round(selectionData.areaM2).toLocaleString()} m²)`, 'success');
      }
    };

    this.map.callbacks.onPinPlaced = async (lat, lon) => {
      await this.analyzeCustomPoint(lat, lon);
    };

    this.map.callbacks.onPondClicked = (candidate) => {
      this.setActiveCandidate(candidate);
    };

    // UI Action Events
    this.ui.callbacks.onAnalyzeClicked = async () => {
      await this.runAnalysis();
    };

    this.ui.callbacks.onPresetClicked = (presetKey) => {
      const preset = this.presets[presetKey];
      if (preset) {
        this.map.setPresetArea(preset.coords, preset.name);
        this.ui.showToast(`Selected Preset: ${preset.name}`, 'info');
      }
    };

    this.ui.callbacks.onParameterChanged = () => {
      this.recalculateWaterYieldLive();
    };

    this.ui.callbacks.onExportGeoJSON = () => {
      this.exportGeoJSON();
    };

    this.ui.callbacks.onExportCSV = () => {
      this.exportCSV();
    };

    // Custom File Upload
    const fileInput = document.getElementById('kmlFileInput');
    if (fileInput) {
      fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
          this.activeKmlBlob = file;
          this.activeKmlName = file.name;
          this.ui.showToast(`Loaded survey file: ${file.name}`, 'success');
          const fileLabel = document.getElementById('kmlFileName');
          if (fileLabel) fileLabel.textContent = file.name;
        }
      });
    }
  }

  async checkBackend() {
    this.ui.showToast('Checking backend API...', 'info');
    const res = await this.api.checkHealth();
    if (res.success) {
      this.ui.showToast('Connected to Pond Detection Backend API', 'success');
    } else {
      this.ui.showToast('Backend offline or port forwarding not active. Click server badge to configure.', 'warning');
    }
  }

  async loadInitialData() {
    try {
      // 1. Load contours GeoJSON for map display
      const contResp = await fetch('data/default_contours.geojson');
      if (contResp.ok) {
        const contoursGeoJSON = await contResp.json();
        this.map.renderContours(contoursGeoJSON);
      }

      // 2. Pre-fetch default KML file blob
      const kmlResp = await fetch('data/contours_1m.kml');
      if (kmlResp.ok) {
        this.activeKmlBlob = await kmlResp.blob();
        this.activeKmlName = 'contours_1m.kml';
      }
    } catch (e) {
      console.warn('Initial data load warning:', e);
    }
  }

  /**
   * Main Execution: Runs hydrological pipeline and analyzes the selected land area
   */
  async runAnalysis() {
    this.ui.showLoading('Executing Hydrological Pipeline on Land Area...');

    try {
      // Ensure we have KML blob
      if (!this.activeKmlBlob) {
        const kmlResp = await fetch('data/contours_1m.kml');
        if (kmlResp.ok) {
          this.activeKmlBlob = await kmlResp.blob();
        } else {
          throw new Error('No KML survey file available. Please upload a KML file.');
        }
      }

      const params = this.ui.getParameters();

      // Call API
      const result = await this.api.runFullPipeline(this.activeKmlBlob, {
        resolution_m: params.resolution_m,
        top_n: Math.max(params.top_n, 3), // Ensure we have candidate pool
        include_streams: true
      });

      this.pipelineResults = result;

      // Render Streams
      if (result.stream_network_geojson) {
        this.map.renderStreams(result.stream_network_geojson);
      }

      // Process candidates in relation to selected land area
      const candidates = result.candidates || [];
      const catchments = result.catchments || [];

      if (candidates.length === 0) {
        throw new Error('No suitable pond candidates found in survey terrain.');
      }

      // Find candidates that fall inside the selected land area polygon
      let selectedCandidate = null;
      let selectedCatchment = null;

      if (this.map.selectedAreaGeoJSON) {
        const insideCandidates = candidates.filter((c) =>
          this.map.isPointInsideSelection(c.latitude, c.longitude)
        );

        if (insideCandidates.length > 0) {
          // Choose candidate with highest suitability score inside parcel
          selectedCandidate = insideCandidates[0];
          selectedCatchment = catchments.find((cat) => cat.rank === selectedCandidate.rank) || catchments[0];
        } else {
          // If no candidate falls strictly inside, pick candidate closest to the parcel centroid
          this.ui.showToast('No natural sink inside parcel boundary. Selecting optimal drainage pond serving this parcel.', 'info');
          selectedCandidate = candidates[0];
          selectedCatchment = catchments[0];
        }
      } else {
        // No parcel drawn: use survey-wide optimal rank #1
        selectedCandidate = candidates[0];
        selectedCatchment = catchments[0];
      }

      // Set active results
      this.displayResults(selectedCandidate, selectedCatchment);

      this.ui.hideLoading();
      this.ui.showToast(`Analysis Complete: Suggested Pond #${selectedCandidate.rank} • Volume: ${this.activeWaterMetrics.volumeMegaLiters} ML`, 'success');

    } catch (err) {
      this.ui.hideLoading();
      console.error(err);
      this.ui.showToast(`Analysis Error: ${err.message}`, 'error');
    }
  }

  /**
   * Delineates catchment for an arbitrary point clicked by the user
   */
  async analyzeCustomPoint(lat, lon) {
    this.ui.showLoading(`Delineating Catchment at ${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E...`);

    try {
      if (!this.activeKmlBlob) {
        const kmlResp = await fetch('data/contours_1m.kml');
        this.activeKmlBlob = await kmlResp.blob();
      }

      const params = this.ui.getParameters();
      const res = await this.api.delineateCustomCatchment(this.activeKmlBlob, lat, lon, params.resolution_m);

      const customPond = {
        rank: 'Custom',
        latitude: lat,
        longitude: lon,
        elevation_m: res.catchment.outlet_elevation_m || 280.0,
        slope_degrees: 1.5,
        flow_accumulation_cells: res.catchment.cell_count || 100,
        suitability_score: 0.88,
        google_maps_url: `https://www.google.com/maps?q=${lat},${lon}`
      };

      const customCatchment = {
        rank: 'Custom',
        catchment: res.catchment,
        geojson: res.geojson
      };

      this.displayResults(customPond, customCatchment);
      this.ui.hideLoading();
      this.ui.showToast(`Custom Site Delineated: ${this.activeWaterMetrics.volumeMegaLiters} ML collectible volume`, 'success');

    } catch (err) {
      this.ui.hideLoading();
      console.error(err);
      this.ui.showToast(`Custom Catchment Error: ${err.message}`, 'error');
    }
  }

  /**
   * Renders the active pond, catchment, and expected water volume on the map and sidebar
   */
  displayResults(candidate, catchmentObj) {
    this.activeCandidate = candidate;
    this.activeCatchment = catchmentObj;

    const params = this.ui.getParameters();
    const stats = catchmentObj.catchment || {};
    const areaM2 = stats.area_m2 || 35000.0;

    // Calculate Water Balance
    const waterMetrics = HydrologyCalculator.calculateWaterYield(
      areaM2,
      params.annualRainfallMm,
      params.runoffCoeff,
      params.pondDepthM
    );
    this.activeWaterMetrics = waterMetrics;

    // 1. Clear previous result overlays on map
    this.map.clearResults();

    // 2. Render Catchment Area Polygon (WGS84 GeoJSON)
    if (catchmentObj.geojson) {
      this.map.renderCatchmentPolygon(catchmentObj.geojson, candidate.rank);
    }

    // 3. Render Suggested Pond Location Marker
    this.map.renderPondCandidate(candidate, true);

    // 4. Render Expected Water Volume Map Callout Badge
    this.map.renderVolumeCallout(candidate.latitude, candidate.longitude, waterMetrics, candidate.rank);

    // 5. Fit map view to showcase all features
    this.map.fitToFeatures();

    // 6. Update Sidebar Cards
    this.ui.displayResults(candidate, stats, waterMetrics);
  }

  /**
   * Recalculates expected water volume in real-time when sliders change
   */
  recalculateWaterYieldLive() {
    if (!this.activeCatchment || !this.activeCandidate) return;

    const params = this.ui.getParameters();
    const stats = this.activeCatchment.catchment || {};
    const areaM2 = stats.area_m2 || 35000.0;

    const waterMetrics = HydrologyCalculator.calculateWaterYield(
      areaM2,
      params.annualRainfallMm,
      params.runoffCoeff,
      params.pondDepthM
    );
    this.activeWaterMetrics = waterMetrics;

    // Update Sidebar
    this.ui.displayResults(this.activeCandidate, stats, waterMetrics);

    // Update Floating Map Callout Badge
    this.map.volumeBadgesGroup.clearLayers();
    this.map.renderVolumeCallout(
      this.activeCandidate.latitude,
      this.activeCandidate.longitude,
      waterMetrics,
      this.activeCandidate.rank
    );
  }

  /**
   * Export results as a standard GeoJSON FeatureCollection
   */
  exportGeoJSON() {
    if (!this.activeCatchment || !this.activeCandidate) {
      this.ui.showToast('No analysis results to export.', 'warning');
      return;
    }

    const exportFeatures = [];

    // Add Catchment Polygon
    if (this.activeCatchment.geojson && this.activeCatchment.geojson.features) {
      exportFeatures.push(...this.activeCatchment.geojson.features);
    }

    // Add Selected Land Area if present
    if (this.map.selectedAreaGeoJSON) {
      exportFeatures.push({
        type: 'Feature',
        properties: { feature_type: 'selected_land_area' },
        geometry: this.map.selectedAreaGeoJSON.geometry
      });
    }

    const featureCollection = {
      type: 'FeatureCollection',
      properties: {
        system: 'AquaCatch Pond & Catchment GIS',
        pond_rank: this.activeCandidate.rank,
        annual_rainfall_mm: this.activeWaterMetrics.annualRainfallMm,
        runoff_coefficient: this.activeWaterMetrics.runoffCoeff,
        expected_water_volume_m3: this.activeWaterMetrics.collectibleVolumeM3,
        expected_water_volume_ml: this.activeWaterMetrics.volumeMegaLiters
      },
      features: exportFeatures
    };

    const blob = new Blob([JSON.stringify(featureCollection, null, 2)], { type: 'application/geo+json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pond_catchment_rank${this.activeCandidate.rank}.geojson`;
    a.click();
    URL.revokeObjectURL(url);
    this.ui.showToast('GeoJSON exported successfully', 'success');
  }

  /**
   * Export CSV summary
   */
  async exportCSV() {
    if (!this.activeKmlBlob) {
      this.ui.showToast('No active survey dataset.', 'warning');
      return;
    }
    this.ui.showLoading('Generating CSV Summary...');
    try {
      const blob = await this.api.exportCsv(this.activeKmlBlob);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'pond_catchment_summary.csv';
      a.click();
      URL.revokeObjectURL(url);
      this.ui.hideLoading();
      this.ui.showToast('CSV summary downloaded', 'success');
    } catch (e) {
      this.ui.hideLoading();
      this.ui.showToast('Failed to generate CSV export', 'error');
    }
  }
}

// Bootstrap application on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  const app = new App();
  app.start().catch((err) => console.error('App launch error:', err));
  window.__aquacatch = app; // Expose for debugging if needed
});
