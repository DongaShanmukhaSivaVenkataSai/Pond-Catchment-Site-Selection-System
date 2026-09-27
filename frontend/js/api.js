/**
 * AquaCatch - API Service Client
 * Handles communication with the FastAPI backend
 */

export class ApiClient {
  constructor() {
    // Default API host candidates
    this.storageKey = 'aquacatch_api_base';
    this.apiBase = this.detectApiBase();
    this.isConnected = false;
    this.listeners = [];
  }

  detectApiBase() {
    // Check localStorage first
    const saved = localStorage.getItem(this.storageKey);
    if (saved) return saved;

    // If served via HTTP/HTTPS, always default to current origin (e.g. http://10.1.75.51:5252)
    if (window.location.protocol.startsWith('http')) {
      return window.location.origin;
    }

    // Default fallback to remote server URL
    return 'http://10.1.75.51:5252';
  }

  setApiBase(url) {
    let clean = url.trim().replace(/\/+$/, '');
    if (!clean.startsWith('http://') && !clean.startsWith('https://')) {
      clean = 'http://' + clean;
    }
    this.apiBase = clean;
    localStorage.setItem(this.storageKey, clean);
    return this.checkHealth();
  }

  onStatusChange(callback) {
    this.listeners.push(callback);
  }

  notifyStatus(status, details = {}) {
    this.isConnected = status;
    this.listeners.forEach(cb => cb(status, this.apiBase, details));
  }

  /**
   * Health check to test backend connectivity
   */
  async checkHealth() {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);

      const resp = await fetch(`${this.apiBase}/api/v1/health`, {
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (resp.ok) {
        const data = await resp.json();
        this.notifyStatus(true, data);
        return { success: true, data };
      } else {
        this.notifyStatus(false, { error: `HTTP ${resp.status}` });
        return { success: false, error: `HTTP ${resp.status}` };
      }
    } catch (err) {
      // If localhost:5252 failed and wasn't manually set, try 10.1.75.51:5252 as automatic fallback
      if (this.apiBase.includes('localhost') && !localStorage.getItem(this.storageKey)) {
        try {
          const altResp = await fetch('http://10.1.75.51:5252/api/v1/health', { timeout: 3000 });
          if (altResp.ok) {
            this.apiBase = 'http://10.1.75.51:5252';
            const altData = await altResp.json();
            this.notifyStatus(true, altData);
            return { success: true, data: altData };
          }
        } catch (_) {}
      }

      this.notifyStatus(false, { error: err.message });
      return { success: false, error: err.message };
    }
  }

  /**
   * Run the complete hydrological analysis pipeline
   * @param {Blob|File} kmlBlob - KML/KMZ contour file
   * @param {Object} options - Pipeline parameters
   */
  async runFullPipeline(kmlBlob, options = {}) {
    const {
      resolution_m = 10.0,
      top_n = 3,
      max_slope_degrees = 8.0,
      flow_percentile = 10.0,
      min_distance_m = 100.0,
      flow_weight = 0.60,
      slope_weight = 0.30,
      elevation_weight = 0.10,
      include_streams = true
    } = options;

    const formData = new FormData();
    const filename = kmlBlob.name || 'contours.kml';
    formData.append('contour_map', kmlBlob, filename);

    const queryParams = new URLSearchParams({
      resolution_m,
      top_n,
      max_slope_degrees,
      flow_percentile,
      min_distance_m,
      flow_weight,
      slope_weight,
      elevation_weight,
      include_streams
    });

    const url = `${this.apiBase}/api/v1/analyze?${queryParams.toString()}`;

    const resp = await fetch(url, {
      method: 'POST',
      body: formData
    });

    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(`Hydrological analysis failed (${resp.status}): ${errText}`);
    }

    return await resp.json();
  }

  /**
   * Delineate custom catchment for an arbitrary point
   * @param {Blob|File} kmlBlob - KML/KMZ contour file
   * @param {number} latitude - WGS84 Latitude
   * @param {number} longitude - WGS84 Longitude
   * @param {number} resolution_m - DEM grid resolution
   */
  async delineateCustomCatchment(kmlBlob, latitude, longitude, resolution_m = 10.0) {
    const formData = new FormData();
    const filename = kmlBlob.name || 'contours.kml';
    formData.append('file', kmlBlob, filename);

    const queryParams = new URLSearchParams({
      latitude,
      longitude,
      resolution_m
    });

    const url = `${this.apiBase}/api/v1/catchment/custom?${queryParams.toString()}`;

    const resp = await fetch(url, {
      method: 'POST',
      body: formData
    });

    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(`Custom catchment failed (${resp.status}): ${errText}`);
    }

    return await resp.json();
  }

  /**
   * Export candidate summary CSV
   */
  async exportCsv(kmlBlob, options = {}) {
    const formData = new FormData();
    formData.append('file', kmlBlob, kmlBlob.name || 'contours.kml');

    const queryParams = new URLSearchParams({
      resolution_m: options.resolution_m || 10.0,
      top_n: options.top_n || 5,
      min_distance_m: options.min_distance_m || 100.0
    });

    const url = `${this.apiBase}/api/v1/export/csv?${queryParams.toString()}`;
    const resp = await fetch(url, {
      method: 'POST',
      body: formData
    });

    if (!resp.ok) throw new Error('CSV Export failed');
    return await resp.blob();
  }
}
