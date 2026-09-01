"""
Visualization Service
Renders high-quality hydrological and terrain maps using Matplotlib.
Implements the visualizations from 1.ipynb into clean, production-ready rendering methods.
Supports returning PNG binary bytes or base64 data URLs.
"""

import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp")

import io
import base64
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Headless backend
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import LightSource
from typing import List, Dict, Any, Optional, Tuple


def _fig_to_png_bytes(fig: plt.Figure, dpi: int = 150) -> bytes:
    """Converts a matplotlib figure to PNG bytes and closes figure."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _png_bytes_to_base64(png_bytes: bytes) -> str:
    """Converts PNG bytes to base64 data URL string."""
    encoded = base64.b64encode(png_bytes).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def plot_contours(contours_data: List[Dict[str, Any]]) -> bytes:
    """Plots projected or WGS84 contour lines."""
    fig, ax = plt.subplots(figsize=(10, 8))
    
    elevations = [c["elevation"] for c in contours_data]
    min_elev = min(elevations) if elevations else 0
    max_elev = max(elevations) if elevations else 1
    norm = mcolors.Normalize(vmin=min_elev, vmax=max_elev)
    cmap = plt.get_cmap("terrain")

    for contour in contours_data:
        coords = contour["coordinates"]
        x = [pt[0] for pt in coords]
        y = [pt[1] for pt in coords]
        color = cmap(norm(contour["elevation"]))
        ax.plot(x, y, color=color, linewidth=1.2)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, label="Elevation (m)")

    ax.set_xlabel("X (meters)")
    ax.set_ylabel("Y (meters)")
    ax.set_title(f"Contour Map ({len(contours_data)} contours)", fontsize=14, fontweight="bold")
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--", alpha=0.5)

    return _fig_to_png_bytes(fig)


def plot_dem(dem: np.ndarray, grid_x: np.ndarray, grid_y: np.ndarray) -> bytes:
    """Plots DEM elevation raster with hillshade relief."""
    fig, ax = plt.subplots(figsize=(10, 8))
    
    extent = [grid_x.min(), grid_x.max(), grid_y.min(), grid_y.max()]
    im = ax.imshow(dem, extent=extent, origin="lower", cmap="terrain", aspect="equal")
    
    fig.colorbar(im, ax=ax, label="Elevation (m)")
    ax.set_xlabel("UTM X (m)")
    ax.set_ylabel("UTM Y (m)")
    ax.set_title("Digital Elevation Model (DEM)", fontsize=14, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4)

    return _fig_to_png_bytes(fig)


def plot_slope(slope_deg: np.ndarray, grid_x: np.ndarray, grid_y: np.ndarray) -> bytes:
    """Plots terrain slope in degrees."""
    fig, ax = plt.subplots(figsize=(10, 8))
    
    extent = [grid_x.min(), grid_x.max(), grid_y.min(), grid_y.max()]
    im = ax.imshow(slope_deg, extent=extent, origin="lower", cmap="plasma", aspect="equal")
    
    fig.colorbar(im, ax=ax, label="Slope (degrees)")
    ax.set_xlabel("UTM X (m)")
    ax.set_ylabel("UTM Y (m)")
    ax.set_title("Terrain Slope Map", fontsize=14, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4)

    return _fig_to_png_bytes(fig)


def plot_flow_direction(
    flow_direction: np.ndarray,
    dem: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    resolution: float = 1.0,
    stride: int = 40,
) -> bytes:
    """
    Plots D8 flow direction with quiver vectors on analytical hillshading.
    Based on Cell 4 of 1.ipynb.
    """
    fig, ax = plt.subplots(figsize=(12, 10))
    extent = [grid_x.min(), grid_x.max(), grid_y.min(), grid_y.max()]

    # Hillshade
    ls = LightSource(azdeg=315, altdeg=45)
    rgb = ls.shade(dem, cmap=plt.cm.gist_earth, vert_exag=2.0, blend_mode="overlay")
    ax.imshow(rgb, extent=extent, origin="lower", aspect="equal")

    # D8 Direction vectors: dx, dy for indices 0 to 7
    # 0: NW, 1: N, 2: NE, 3: W, 4: E, 5: SW, 6: S, 7: SE
    dx_lookup = np.array([-1.0,  0.0,  1.0, -1.0, 1.0, -1.0, 0.0, 1.0])
    dy_lookup = np.array([ 1.0,  1.0,  1.0,  0.0, 0.0, -1.0, -1.0, -1.0])

    sub_r = slice(0, dem.shape[0], stride)
    sub_c = slice(0, dem.shape[1], stride)

    fd_sub = flow_direction[sub_r, sub_c]
    gx_sub = grid_x[sub_r, sub_c]
    gy_sub = grid_y[sub_r, sub_c]

    valid = fd_sub >= 0
    u = np.zeros_like(fd_sub, dtype=float)
    v = np.zeros_like(fd_sub, dtype=float)

    u[valid] = dx_lookup[fd_sub[valid]]
    v[valid] = dy_lookup[fd_sub[valid]]

    ax.quiver(
        gx_sub[valid], gy_sub[valid], u[valid], v[valid],
        color="cyan", scale=30, width=0.003, alpha=0.85
    )

    ax.set_xlabel("UTM X (m)")
    ax.set_ylabel("UTM Y (m)")
    ax.set_title("D8 Flow Direction Vectors & Hillshade", fontsize=14, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.3)

    return _fig_to_png_bytes(fig)


def plot_flow_accumulation(flow_acc: np.ndarray, grid_x: np.ndarray, grid_y: np.ndarray) -> bytes:
    """Plots log-transformed flow accumulation channels."""
    fig, ax = plt.subplots(figsize=(10, 8))
    extent = [grid_x.min(), grid_x.max(), grid_y.min(), grid_y.max()]

    display = np.log1p(flow_acc)
    im = ax.imshow(display, extent=extent, origin="lower", cmap="Blues", aspect="equal")
    
    fig.colorbar(im, ax=ax, label="Log Flow Accumulation ln(1 + cells)")
    ax.set_xlabel("UTM X (m)")
    ax.set_ylabel("UTM Y (m)")
    ax.set_title("Flow Accumulation & Drainage Paths", fontsize=14, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4)

    return _fig_to_png_bytes(fig)


def plot_pond_candidates(
    dem: np.ndarray,
    candidates: List[Dict[str, Any]],
    grid_x: np.ndarray,
    grid_y: np.ndarray,
) -> bytes:
    """Plots top ranked pond site candidates on DEM background."""
    fig, ax = plt.subplots(figsize=(12, 9))
    extent = [grid_x.min(), grid_x.max(), grid_y.min(), grid_y.max()]

    im = ax.imshow(dem, extent=extent, origin="lower", cmap="terrain", aspect="equal", alpha=0.85)
    fig.colorbar(im, ax=ax, label="Elevation (m)")

    for cand in candidates:
        rank = cand["rank"]
        x, y = cand["x_m"], cand["y_m"]
        score = cand["suitability_score"]

        color = "gold" if rank == 1 else "red"
        ax.scatter(x, y, color=color, s=150, edgecolors="black", linewidth=1.5, zorder=5)
        ax.text(
            x + 25, y + 25, f"#{rank} ({score:.2f})",
            fontsize=10, fontweight="bold", color="black",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8)
        )

    ax.set_xlabel("UTM X (m)")
    ax.set_ylabel("UTM Y (m)")
    ax.set_title(f"Optimal Pond Site Candidates (Top {len(candidates)})", fontsize=14, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4)

    return _fig_to_png_bytes(fig)


def plot_catchment(
    dem: np.ndarray,
    catchment_mask: np.ndarray,
    pond_outlet: Dict[str, Any],
    grid_x: np.ndarray,
    grid_y: np.ndarray,
) -> bytes:
    """Plots delineated watershed catchment overlay and pond outlet on DEM."""
    fig, ax = plt.subplots(figsize=(12, 9))
    extent = [grid_x.min(), grid_x.max(), grid_y.min(), grid_y.max()]

    ax.imshow(dem, extent=extent, origin="lower", cmap="terrain", aspect="equal", alpha=0.7)
    
    # Overlay catchment mask
    masked_data = np.ma.masked_where(~catchment_mask, catchment_mask)
    ax.imshow(masked_data, extent=extent, origin="lower", cmap="autumn", alpha=0.55, aspect="equal")

    px, py = pond_outlet["x_m"], pond_outlet["y_m"]
    ax.scatter(px, py, color="blue", s=180, edgecolors="white", linewidth=2, zorder=6, label="Pond Outlet")

    ax.set_xlabel("UTM X (m)")
    ax.set_ylabel("UTM Y (m)")
    ax.set_title("Delineated Watershed Catchment Boundary", fontsize=14, fontweight="bold")
    ax.legend(loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.4)

    return _fig_to_png_bytes(fig)


def plot_comprehensive_dashboard(
    dem: np.ndarray,
    slope_deg: np.ndarray,
    flow_acc: np.ndarray,
    candidates: List[Dict[str, Any]],
    catchment_mask: Optional[np.ndarray],
    grid_x: np.ndarray,
    grid_y: np.ndarray,
) -> bytes:
    """
    Renders a 6-panel comprehensive watershed and pond suitability analysis dashboard.
    """
    fig, axs = plt.subplots(2, 3, figsize=(18, 12))
    extent = [grid_x.min(), grid_x.max(), grid_y.min(), grid_y.max()]

    # 1. DEM
    im0 = axs[0, 0].imshow(dem, extent=extent, origin="lower", cmap="terrain", aspect="equal")
    axs[0, 0].set_title("1. Digital Elevation Model (m)", fontweight="bold")
    fig.colorbar(im0, ax=axs[0, 0], fraction=0.046, pad=0.04)

    # 2. Slope
    im1 = axs[0, 1].imshow(slope_deg, extent=extent, origin="lower", cmap="plasma", aspect="equal")
    axs[0, 1].set_title("2. Terrain Slope (°)", fontweight="bold")
    fig.colorbar(im1, ax=axs[0, 1], fraction=0.046, pad=0.04)

    # 3. Flow Accumulation (Log)
    im2 = axs[0, 2].imshow(np.log1p(flow_acc), extent=extent, origin="lower", cmap="Blues", aspect="equal")
    axs[0, 2].set_title("3. Flow Accumulation ln(1+cells)", fontweight="bold")
    fig.colorbar(im2, ax=axs[0, 2], fraction=0.046, pad=0.04)

    # 4. Hillshade
    ls = LightSource(azdeg=315, altdeg=45)
    hs = ls.hillshade(dem, vert_exag=2.0)
    axs[1, 0].imshow(hs, extent=extent, origin="lower", cmap="gray", aspect="equal")
    axs[1, 0].set_title("4. Terrain Hillshade", fontweight="bold")

    # 5. Pond Candidates
    axs[1, 1].imshow(dem, extent=extent, origin="lower", cmap="terrain", aspect="equal", alpha=0.8)
    for c in candidates:
        axs[1, 1].scatter(c["x_m"], c["y_m"], s=100, edgecolors="black", color="gold" if c["rank"] == 1 else "red", zorder=5)
        axs[1, 1].text(c["x_m"]+20, c["y_m"]+20, f"#{c['rank']}", fontsize=8, fontweight="bold")
    axs[1, 1].set_title(f"5. Top {len(candidates)} Pond Candidates", fontweight="bold")

    # 6. Catchment Overlay
    axs[1, 2].imshow(dem, extent=extent, origin="lower", cmap="terrain", aspect="equal", alpha=0.7)
    if catchment_mask is not None:
        masked = np.ma.masked_where(~catchment_mask, catchment_mask)
        axs[1, 2].imshow(masked, extent=extent, origin="lower", cmap="autumn", alpha=0.55, aspect="equal")
    if candidates:
        axs[1, 2].scatter(candidates[0]["x_m"], candidates[0]["y_m"], color="blue", s=140, edgecolors="white", zorder=6)
    axs[1, 2].set_title("6. Primary Catchment Boundary", fontweight="bold")

    for ax in axs.flat:
        ax.set_xticks([])
        ax.set_yticks([])

    plt.suptitle("Watershed Hydrology & Pond Site Selection Dashboard", fontsize=18, fontweight="bold", y=0.98)
    plt.tight_layout()

    return _fig_to_png_bytes(fig, dpi=130)


def generate_plot_response(
    plot_type: str,
    dem: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    resolution: float,
    contours: Optional[List[Dict[str, Any]]] = None,
    slope_deg: Optional[np.ndarray] = None,
    flow_dir: Optional[np.ndarray] = None,
    flow_acc: Optional[np.ndarray] = None,
    candidates: Optional[List[Dict[str, Any]]] = None,
    catchment_mask: Optional[np.ndarray] = None,
) -> Tuple[bytes, str]:
    """
    Dispatcher to generate plot PNG bytes and base64 string for any plot type.
    """
    plot_type = plot_type.lower().replace("-", "_")

    if plot_type == "contours" and contours:
        png_bytes = plot_contours(contours)
    elif plot_type == "dem":
        png_bytes = plot_dem(dem, grid_x, grid_y)
    elif plot_type == "slope" and slope_deg is not None:
        png_bytes = plot_slope(slope_deg, grid_x, grid_y)
    elif plot_type in ("flow_direction", "flow_dir") and flow_dir is not None:
        png_bytes = plot_flow_direction(flow_dir, dem, grid_x, grid_y, resolution)
    elif plot_type in ("flow_accumulation", "flow_acc") and flow_acc is not None:
        png_bytes = plot_flow_accumulation(flow_acc, grid_x, grid_y)
    elif plot_type in ("candidates", "pond_candidates") and candidates:
        png_bytes = plot_pond_candidates(dem, candidates, grid_x, grid_y)
    elif plot_type in ("catchment", "catchments") and catchment_mask is not None and candidates:
        png_bytes = plot_catchment(dem, catchment_mask, candidates[0], grid_x, grid_y)
    elif plot_type in ("dashboard", "overview", "all"):
        if slope_deg is None:
            gy, gx = np.gradient(dem, resolution, resolution)
            slope_deg = np.degrees(np.arctan(np.sqrt(gx**2 + gy**2)))
        png_bytes = plot_comprehensive_dashboard(
            dem, slope_deg, flow_acc if flow_acc is not None else np.ones_like(dem),
            candidates or [], catchment_mask, grid_x, grid_y
        )
    else:
        # Default to DEM
        png_bytes = plot_dem(dem, grid_x, grid_y)

    b64 = _png_bytes_to_base64(png_bytes)
    return png_bytes, b64
