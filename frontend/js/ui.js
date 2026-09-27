/**
 * AquaCatch - UI & View Manager
 * Handles UI interactions, tabs, modals, notifications, and results formatting
 */

export class UIManager {
  constructor() {
    this.elements = {};
    this.callbacks = {
      onAnalyzeClicked: null,
      onPresetClicked: null,
      onParameterChanged: null,
      onExportGeoJSON: null,
      onExportCSV: null
    };
  }

  init() {
    this.cacheElements();
    this.bindEvents();
    return this;
  }

  cacheElements() {
    this.elements = {
      sidebar: document.getElementById('sidebar'),
      sidebarToggleBtn: document.getElementById('sidebarToggleBtn'),
      tabSelectBtn: document.getElementById('tabSelectBtn'),
      tabResultsBtn: document.getElementById('tabResultsBtn'),
      tabSelectContent: document.getElementById('tabSelectContent'),
      tabResultsContent: document.getElementById('tabResultsContent'),
      resultsBadge: document.getElementById('resultsBadge'),

      // Drawing controls
      btnDrawPolygon: document.getElementById('btnDrawPolygon'),
      btnDrawRectangle: document.getElementById('btnDrawRectangle'),
      btnPinSite: document.getElementById('btnPinSite'),
      btnClearSelection: document.getElementById('btnClearSelection'),

      // Selection info
      selectionInfoBox: document.getElementById('selectionInfoBox'),
      selectedAreaM2: document.getElementById('selectedAreaM2'),
      selectedAreaHa: document.getElementById('selectedAreaHa'),

      // Presets
      presetFull: document.getElementById('presetFull'),
      presetNorth: document.getElementById('presetNorth'),
      presetCentral: document.getElementById('presetCentral'),
      presetSouth: document.getElementById('presetSouth'),

      // Sliders & inputs
      rainfallSlider: document.getElementById('rainfallSlider'),
      rainfallVal: document.getElementById('rainfallVal'),
      runoffSlider: document.getElementById('runoffSlider'),
      runoffVal: document.getElementById('runoffVal'),
      depthSlider: document.getElementById('depthSlider'),
      depthVal: document.getElementById('depthVal'),
      resolutionSelect: document.getElementById('resolutionSelect'),
      topNSelect: document.getElementById('topNSelect'),

      // Action button
      btnAnalyze: document.getElementById('btnAnalyze'),
      loadingOverlay: document.getElementById('loadingOverlay'),
      loadingText: document.getElementById('loadingText'),

      // Results display
      pondRankBadge: document.getElementById('pondRankBadge'),
      pondCoordinates: document.getElementById('pondCoordinates'),
      pondElevation: document.getElementById('pondElevation'),
      pondSlope: document.getElementById('pondSlope'),
      pondFlowAcc: document.getElementById('pondFlowAcc'),
      pondScoreFill: document.getElementById('pondScoreFill'),
      pondScoreText: document.getElementById('pondScoreText'),
      pondGmapsLink: document.getElementById('pondGmapsLink'),

      catchmentAreaHa: document.getElementById('catchmentAreaHa'),
      catchmentAreaM2: document.getElementById('catchmentAreaM2'),
      catchmentElevMin: document.getElementById('catchmentElevMin'),
      catchmentElevMax: document.getElementById('catchmentElevMax'),
      catchmentElevRelief: document.getElementById('catchmentElevRelief'),

      // Star water volume display
      volumeMegaLiters: document.getElementById('volumeMegaLiters'),
      volumeM3: document.getElementById('volumeM3'),
      volumeLiters: document.getElementById('volumeLiters'),
      volumeStormM3: document.getElementById('volumeStormM3'),
      pondRecommendedDims: document.getElementById('pondRecommendedDims'),
      irrigationCapacity: document.getElementById('irrigationCapacity'),

      // Candidate selector if multiple
      candidateSelectorList: document.getElementById('candidateSelectorList'),

      // Export buttons
      btnExportGeoJSON: document.getElementById('btnExportGeoJSON'),
      btnExportCSV: document.getElementById('btnExportCSV'),

      // Modals
      settingsModal: document.getElementById('settingsModal'),
      btnServerSettings: document.getElementById('btnServerSettings'),
      apiBaseInput: document.getElementById('apiBaseInput'),
      btnSaveApiBase: document.getElementById('btnSaveApiBase'),
      serverStatusPill: document.getElementById('serverStatusPill'),
      serverUrlText: document.getElementById('serverUrlText'),

      infoModal: document.getElementById('infoModal'),
      btnInfo: document.getElementById('btnInfo')
    };
  }

  bindEvents() {
    const el = this.elements;

    // Sidebar Toggle
    if (el.sidebarToggleBtn) {
      el.sidebarToggleBtn.addEventListener('click', () => {
        el.sidebar.classList.toggle('collapsed');
        const icon = el.sidebarToggleBtn.querySelector('span');
        if (icon) {
          icon.textContent = el.sidebar.classList.contains('collapsed') ? '▶' : '◀';
        }
      });
    }

    // Tabs
    if (el.tabSelectBtn && el.tabResultsBtn) {
      el.tabSelectBtn.addEventListener('click', () => this.switchTab('select'));
      el.tabResultsBtn.addEventListener('click', () => this.switchTab('results'));
    }

    // Rainfall Slider
    if (el.rainfallSlider) {
      el.rainfallSlider.addEventListener('input', (e) => {
        if (el.rainfallVal) el.rainfallVal.textContent = `${e.target.value} mm`;
        if (this.callbacks.onParameterChanged) this.callbacks.onParameterChanged();
      });
    }

    // Runoff Slider
    if (el.runoffSlider) {
      el.runoffSlider.addEventListener('input', (e) => {
        if (el.runoffVal) el.runoffVal.textContent = parseFloat(e.target.value).toFixed(2);
        if (this.callbacks.onParameterChanged) this.callbacks.onParameterChanged();
      });
    }

    // Pond Depth Slider
    if (el.depthSlider) {
      el.depthSlider.addEventListener('input', (e) => {
        if (el.depthVal) el.depthVal.textContent = `${parseFloat(e.target.value).toFixed(1)} m`;
        if (this.callbacks.onParameterChanged) this.callbacks.onParameterChanged();
      });
    }

    // Analyze Button
    if (el.btnAnalyze) {
      el.btnAnalyze.addEventListener('click', () => {
        if (this.callbacks.onAnalyzeClicked) this.callbacks.onAnalyzeClicked();
      });
    }

    // Export Buttons
    if (el.btnExportGeoJSON) {
      el.btnExportGeoJSON.addEventListener('click', () => {
        if (this.callbacks.onExportGeoJSON) this.callbacks.onExportGeoJSON();
      });
    }

    if (el.btnExportCSV) {
      el.btnExportCSV.addEventListener('click', () => {
        if (this.callbacks.onExportCSV) this.callbacks.onExportCSV();
      });
    }

    // Presets
    const setupPreset = (btn, presetKey) => {
      if (btn) {
        btn.addEventListener('click', () => {
          if (this.callbacks.onPresetClicked) this.callbacks.onPresetClicked(presetKey);
        });
      }
    };
    setupPreset(el.presetFull, 'full');
    setupPreset(el.presetNorth, 'north');
    setupPreset(el.presetCentral, 'central');
    setupPreset(el.presetSouth, 'south');

    // Modals
    if (el.btnServerSettings) {
      el.btnServerSettings.addEventListener('click', () => this.openModal(el.settingsModal));
    }
    if (el.btnInfo) {
      el.btnInfo.addEventListener('click', () => this.openModal(el.infoModal));
    }

    document.querySelectorAll('.modal-close, .modal-backdrop').forEach((elem) => {
      elem.addEventListener('click', (e) => {
        if (e.target === elem || elem.classList.contains('modal-close')) {
          this.closeModals();
        }
      });
    });
  }

  switchTab(tabName) {
    const el = this.elements;
    if (tabName === 'select') {
      el.tabSelectBtn.classList.add('active');
      el.tabResultsBtn.classList.remove('active');
      el.tabSelectContent.style.display = 'block';
      el.tabResultsContent.style.display = 'none';
    } else {
      el.tabResultsBtn.classList.add('active');
      el.tabSelectBtn.classList.remove('active');
      el.tabResultsContent.style.display = 'block';
      el.tabSelectContent.style.display = 'none';
    }
  }

  updateSelectionDisplay(selectionData) {
    const el = this.elements;
    if (!el.selectionInfoBox) return;

    if (selectionData) {
      el.selectionInfoBox.classList.add('active');
      el.selectedAreaHa.textContent = `${selectionData.areaHa.toFixed(2)} ha`;
      el.selectedAreaM2.textContent = `${Math.round(selectionData.areaM2).toLocaleString()} m²`;
    } else {
      el.selectionInfoBox.classList.remove('active');
      el.selectedAreaHa.textContent = 'None';
      el.selectedAreaM2.textContent = '0 m²';
    }
  }

  showLoading(text = 'Running Hydrological Analysis...') {
    if (this.elements.loadingOverlay) {
      this.elements.loadingText.textContent = text;
      this.elements.loadingOverlay.style.display = 'flex';
    }
  }

  hideLoading() {
    if (this.elements.loadingOverlay) {
      this.elements.loadingOverlay.style.display = 'none';
    }
  }

  /**
   * Display full analysis results in the sidebar cards
   */
  displayResults(pond, catchmentStats, waterMetrics) {
    const el = this.elements;

    // Switch to results tab & update badge
    this.switchTab('results');
    if (el.resultsBadge) {
      el.resultsBadge.style.display = 'inline-block';
      el.resultsBadge.textContent = 'Ready';
    }

    // 1. Suggested Pond Location
    if (el.pondRankBadge) el.pondRankBadge.textContent = `POND SITE #${pond.rank || 1}`;
    if (el.pondCoordinates) el.pondCoordinates.textContent = `${pond.latitude.toFixed(5)}°N, ${pond.longitude.toFixed(5)}°E`;
    if (el.pondElevation) el.pondElevation.textContent = `${pond.elevation_m.toFixed(1)} m`;
    if (el.pondSlope) el.pondSlope.textContent = `${pond.slope_degrees.toFixed(2)}°`;
    if (el.pondFlowAcc) el.pondFlowAcc.textContent = `${Math.round(pond.flow_accumulation_cells || 0).toLocaleString()} cells`;

    const scorePct = Math.round((pond.suitability_score || 0.85) * 100);
    if (el.pondScoreFill) el.pondScoreFill.style.width = `${scorePct}%`;
    if (el.pondScoreText) el.pondScoreText.textContent = `${scorePct}% (Optimal)`;
    if (el.pondGmapsLink) el.pondGmapsLink.href = pond.google_maps_url || `https://www.google.com/maps?q=${pond.latitude},${pond.longitude}`;

    // 2. Catchment Watershed
    if (el.catchmentAreaHa) el.catchmentAreaHa.textContent = `${waterMetrics.catchmentAreaHa.toFixed(2)} ha`;
    if (el.catchmentAreaM2) el.catchmentAreaM2.textContent = `${Math.round(waterMetrics.catchmentAreaM2).toLocaleString()} m²`;
    if (el.catchmentElevMin) el.catchmentElevMin.textContent = `${catchmentStats.min_elevation_m.toFixed(1)} m`;
    if (el.catchmentElevMax) el.catchmentElevMax.textContent = `${catchmentStats.max_elevation_m.toFixed(1)} m`;
    const relief = catchmentStats.max_elevation_m - catchmentStats.min_elevation_m;
    if (el.catchmentElevRelief) el.catchmentElevRelief.textContent = `${relief.toFixed(1)} m`;

    // 3. Expected Water Volume (Prominent Star Metric)
    if (el.volumeMegaLiters) el.volumeMegaLiters.textContent = `${waterMetrics.volumeMegaLiters} ML`;
    if (el.volumeM3) el.volumeM3.textContent = `${waterMetrics.collectibleVolumeM3.toLocaleString()} m³`;
    if (el.volumeLiters) el.volumeLiters.textContent = `${waterMetrics.volumeLiters.toLocaleString()} Liters`;
    if (el.volumeStormM3) el.volumeStormM3.textContent = `${waterMetrics.stormYieldM3.toLocaleString()} m³ (${waterMetrics.stormYieldLiters.toLocaleString()} L)`;
    if (el.pondRecommendedDims) el.pondRecommendedDims.textContent = waterMetrics.approxDimensions;
    if (el.irrigationCapacity) el.irrigationCapacity.textContent = `~${waterMetrics.irrigationHectares} hectares of crops`;
  }

  getParameters() {
    const el = this.elements;
    return {
      annualRainfallMm: el.rainfallSlider ? parseFloat(el.rainfallSlider.value) : 1200,
      runoffCoeff: el.runoffSlider ? parseFloat(el.runoffSlider.value) : 0.35,
      pondDepthM: el.depthSlider ? parseFloat(el.depthSlider.value) : 3.5,
      resolution_m: el.resolutionSelect ? parseFloat(el.resolutionSelect.value) : 10.0,
      top_n: el.topNSelect ? parseInt(el.topNSelect.value, 10) : 3
    };
  }

  updateServerStatus(isConnected, apiBase) {
    const el = this.elements;
    if (el.serverStatusPill) {
      const dot = el.serverStatusPill.querySelector('.status-dot');
      if (dot) {
        dot.className = `status-dot ${isConnected ? '' : 'disconnected'}`;
      }
    }
    if (el.serverUrlText) {
      el.serverUrlText.textContent = isConnected ? `Connected (${apiBase})` : `Offline (${apiBase})`;
    }
    if (el.apiBaseInput) {
      el.apiBaseInput.value = apiBase;
    }
  }

  showToast(message, type = 'info') {
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'toastContainer';
      toastContainer.style.cssText = `
        position: fixed;
        bottom: 24px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 3000;
        display: flex;
        flex-direction: column;
        gap: 8px;
        pointer-events: none;
      `;
      document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    const colors = {
      info: 'rgba(2, 132, 199, 0.95)',
      success: 'rgba(16, 185, 129, 0.95)',
      error: 'rgba(244, 63, 94, 0.95)',
      warning: 'rgba(245, 158, 11, 0.95)'
    };

    toast.style.cssText = `
      background: ${colors[type] || colors.info};
      color: #fff;
      padding: 10px 18px;
      border-radius: 99px;
      font-size: 13px;
      font-weight: 500;
      box-shadow: 0 4px 16px rgba(0,0,0,0.4);
      animation: fadeIn 0.25s ease-out;
      pointer-events: auto;
    `;
    toast.textContent = message;

    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease-out';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  openModal(modalElem) {
    if (modalElem) modalElem.classList.add('open');
  }

  closeModals() {
    document.querySelectorAll('.modal-backdrop').forEach(m => m.classList.remove('open'));
  }
}
