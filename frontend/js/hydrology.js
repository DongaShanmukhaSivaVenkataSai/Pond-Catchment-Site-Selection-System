/**
 * AquaCatch - Hydrology & Water Balance Calculations
 * Implements standard hydrological Rational & Runoff equations
 */

export const HydrologyCalculator = {
  // Soil runoff coefficient presets (C in Rational Method)
  RUNOFF_COEFFICIENTS: {
    sandy: { value: 0.15, label: "Sandy / Coarse Soil (Low Runoff)" },
    loam: { value: 0.25, label: "Sandy-Loam / Pasture (Moderate)" },
    clay_loam: { value: 0.35, label: "Agricultural Clay-Loam (Standard)" },
    clay: { value: 0.45, label: "Heavy Clay / Compacted Soil (High Runoff)" },
    rocky: { value: 0.55, label: "Steep / Hilly / Impervious (Very High)" }
  },

  /**
   * Calculates expected collectible water volume from a watershed catchment.
   * Formula: V = C * P * A
   * @param {number} catchmentAreaM2 - Catchment area in square meters (m²)
   * @param {number} annualRainfallMm - Annual or seasonal rainfall in millimeters (mm)
   * @param {number} runoffCoeff - Runoff coefficient C (typically 0.15 to 0.50)
   * @param {number} pondDepthM - Proposed pond water depth in meters (default: 3.5m)
   * @returns {Object} Comprehensive water balance metrics
   */
  calculateWaterYield(catchmentAreaM2, annualRainfallMm = 1200, runoffCoeff = 0.35, pondDepthM = 3.5) {
    if (!catchmentAreaM2 || catchmentAreaM2 <= 0) {
      return null;
    }

    // Convert rainfall mm to meters
    const rainfallM = annualRainfallMm / 1000.0;

    // Gross precipitation falling on catchment (m³)
    const grossRainVolumeM3 = catchmentAreaM2 * rainfallM;

    // Collectible runoff volume (m³)
    const collectibleVolumeM3 = grossRainVolumeM3 * runoffCoeff;

    // Convert to Liters and Megaliters (ML)
    const volumeLiters = collectibleVolumeM3 * 1000;
    const volumeMegaLiters = collectibleVolumeM3 / 1000.0;

    // Single design heavy storm event (e.g. 50mm / 2-inch event)
    const stormRainfallMm = 50;
    const stormYieldM3 = catchmentAreaM2 * (stormRainfallMm / 1000.0) * runoffCoeff;
    const stormYieldLiters = stormYieldM3 * 1000;

    // Recommended Pond Storage Sizing
    // Standard rule: Pond designed to capture ~25% - 40% of peak annual yield or top 2 heavy storms
    const recommendedPondVolumeM3 = Math.min(collectibleVolumeM3 * 0.30, stormYieldM3 * 2.5);
    const recommendedSurfaceAreaM2 = recommendedPondVolumeM3 / Math.max(pondDepthM, 1.5);
    const approxSideM = Math.round(Math.sqrt(recommendedSurfaceAreaM2));

    // Agricultural utility estimates
    // Standard paddy/crop irrigation requirement ~ 2000 m³ per hectare per season
    const irrigationHectares = collectibleVolumeM3 / 2000.0;

    // Cattle/Livestock daily consumption ~ 50 Liters/day
    const cattleSupportedAnnual = Math.round(volumeLiters / (50 * 365));

    return {
      catchmentAreaM2,
      catchmentAreaHa: catchmentAreaM2 / 10000.0,
      catchmentAreaAcres: catchmentAreaM2 / 4046.86,
      annualRainfallMm,
      runoffCoeff,
      pondDepthM,
      grossRainVolumeM3: Math.round(grossRainVolumeM3),
      collectibleVolumeM3: Math.round(collectibleVolumeM3 * 10) / 10,
      volumeLiters: Math.round(volumeLiters),
      volumeMegaLiters: Math.round(volumeMegaLiters * 100) / 100,
      stormYieldM3: Math.round(stormYieldM3 * 10) / 10,
      stormYieldLiters: Math.round(stormYieldLiters),
      recommendedPondVolumeM3: Math.round(recommendedPondVolumeM3),
      recommendedSurfaceAreaM2: Math.round(recommendedSurfaceAreaM2),
      approxDimensions: `${approxSideM}m × ${approxSideM}m (Depth: ${pondDepthM}m)`,
      irrigationHectares: Math.round(irrigationHectares * 10) / 10,
      cattleSupportedAnnual
    };
  },

  /**
   * Format volume numbers with commas and appropriate units
   */
  formatVolume(m3) {
    if (m3 >= 10000) {
      const ml = m3 / 1000.0;
      return `${ml.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ML`;
    }
    return `${Math.round(m3).toLocaleString('en-US')} m³`;
  }
};
