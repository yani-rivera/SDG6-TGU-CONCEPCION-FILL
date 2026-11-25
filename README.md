# The Valley Under La Concepción — fill and empty (v1.2.0)

An interactive companion to the new version of the *Concepción Reservoir Bathymetry & Shoreline Dataset (Honduras)*. Drag the slider, or press Fill or Empty, to raise and lower the water over the reconstructed pre-dam valley of La Concepción, Tegucigalpa's main reservoir. As the level changes, the page shows:
- the water surface coloured by depth, with the old valley floor in brown where it is exposed;
- the level (metres below full), volume (million m³), surface area (hectares) and percent of the reconstructed full volume;
- the level–volume curve, with the official capacity marked.

## Run

```
python src/run.py --config config/config.yaml
```

Requires Python 3.10+, rasterio, numpy, pandas, geopandas, shapely, pyproj, pillow, pyyaml.

## Layout

| Path | What it is |
|---|---|
| `config/config.yaml` | inputs, curve step, hillshade, official figures, dataset DOIs, script version |
| `data/ConcepcionDEM.tif` | depth below the maximum operating level (m, 0 to −35), EPSG:32616, 5 m cells, 918 × 293 |
| `data/ConcepcionContourPolygones20261123.gpkg` | depth bands (−35…0 m), 8 polygons; their union is the full-reservoir outline |
| `src/curve.py` | level–area–volume table from the depth raster |
| `src/render.py` | the 16-bit depth PNG, the hillshaded valley floor and the outline path |
| `src/run.py` | builds everything and writes provenance |
| `web/template.html` | the page; data and images are inlined at build time |
| `out/index.html` | the interactive: one self-contained file that works with a double-click, on GitHub Pages or in a Zenodo release |
| `out/level_area_volume.csv` | the curve at 0.1 m steps, raw, range and calibrated columns (utf-8-sig) |
| `catalogs/umaps_level_volume.csv` | official UMAPS level–volume readings used for calibration, with source per row |
| `src/calibrate.py` | depth-stretch calibration against the UMAPS readings |
| `out/calibration_points.csv` | the readings with the model residual for each (utf-8-sig) |
| `out/provenance.json` | script version, run time, SHA-256 of inputs and outputs, key numbers |

## Method

For a water level h (metres below full, ≤ 0), with cell area A = 24.91 m²:
- **surface area** = A × (number of cells deeper than h);
- **volume** = A × Σ max(0, h − z).

The table is computed every 0.1 m from −35 m to 0. The page colours each cell on the fly: water where z < h (shaded by water depth), and the valley floor (hillshade, 2× vertical exaggeration) where it is dry. Depth is packed into a lossless 16-bit PNG (millimetres in the red and green channels), so the page uses the raster's own values.

Key numbers from this version: full surface 175.95 ha (cells strictly below 0 m; the 0 m rim cells add about 10 ha), full volume 17.31 million m³, deepest point 35 m.

## How sure are these numbers? (also shown on the page)

**The reconstruction holds 17.3 million m³ when full, about 48% of the official 36.2 million m³.**
- El Heraldo, citing the authorities, reports 36.2 million m³ to reach the maximum level.
- It also reported the reservoir full at 32 million m³ in November 2024, as in 2017 and 2018.

Likely reasons for the gap:
- **Contour spacing.** The 20 m contours of the 1956 sheet smooth away the deep channel and steep sides, so the basin comes out too shallow. The jump in area between −15 m and −10 m (11 → 88 ha) looks like a flat surface created by TIN interpolation between contours.
- **Outline and zero level.** The full-reservoir outline and its zero level may sit below the official maximum operating level.
- **Sediment** is not included. It would reduce the real volume, so it does not explain the gap.

### The capacity range (v1.2.0)

Instead of one volume, the page and the CSV give a range for every level:
- **Low end:** the reconstruction (`volume_mm3`).
- **High end:** the same curve rescaled so that full equals a target: `volume_mm3_scaled_to_32` (reported full, 2024) and `volume_mm3_scaled_to_36.2` (official capacity). The page shows the reconstruction to 36.2 range.

Rescaling keeps the valley's shape and corrects only the total, so **percent full is identical at both ends**; it is the most robust number. The rescaling assumes the error is spread proportionally through the basin. It is a bound, not a survey.

**Zero-level check.** If the full level were raised with vertical walls at the outline (186.6 ha including the rim cells), reaching 32 million m³ would take +7.9 m, and 36.2 million m³ would take +10.1 m. That is about half of one 20 m contour interval, so an offset between the reconstruction's zero and the official maximum operating level is a likely cause. Knowing the official maximum level in metres above sea level, plus one UMAPS level–volume reading (for example 1,143.30 m ↔ 17.662 million m³, reported by El Heraldo), would let a later version calibrate instead of bound.

## Calibration with UMAPS readings (v1.2.0)

`catalogs/umaps_level_volume.csv` holds 25 official level–volume pairs:
- 23 transcribed from the UMAPS response to a public information request (SIELHO), covering daily data for 2015–2018;
- the UMAPS crisis dashboard reading of 23 Nov 2026 (1,140.66 m, 15.204 million m³, 42.00%);
- a UMAPS reading reported by El Heraldo (1,143.30 m, 17.662 million m³).

The pipeline stops if the same level appears with different volumes. UMAPS volumes come from a fixed rating curve, so a mismatch means a misread digit. (1,144.36 m → 18.700 and 1,148.30 m → 23.061 each appear in two different years and agree.)

**Model (`src/calibrate.py`).** The reconstruction's outline is right but its depths are too shallow, so every depth is multiplied by a stretch factor *s*: real volume(E) = *s* × V_rec((E − E_full)/*s*). Surface area is unchanged by the stretch.

| Fit | stretch *s* | full level (m a.s.l.) | capacity (million m³) | RMSE (million m³) | deepest point below full |
|---|---|---|---|---|---|
| **Constrained** to the official 36.2 (used on the page) | 2.09 | 1,156.75 | 36.2 | 0.33 | 73 m |
| Free | 2.31 | 1,159.45 | 40.0 | 0.13 | 81 m |

Residuals per reading are in `out/calibration_points.csv`. The worst is at the lowest reading (1,140.66 m: model 14.4 vs UMAPS 15.2 million m³), so the model is weakest at low levels, where readings are fewest. The full level is a model estimate, not the official maximum operating level. Below about 1,140 m there are no readings, and the curve is the reconstruction's shape, stretched.

**Improving it.** More readings at low levels, for example from the dry years 2019 and 2026, plus the official maximum operating level, would tighten the fit most. A new SIELHO request could provide both.

The capacity range from v1.1.0 is still computed (`volume_mm3_scaled_to_*` columns), but the page now shows the calibrated curve (`level_m_asl_calibrated`, `volume_mm3_calibrated`).

## Mobile and security

- **Mobile.** On phones the map can be swiped sideways and opens on the dam end. Controls are at least 44 px tall, and the readouts and chart stack into one column. With reduced motion turned on, Fill and Empty jump straight to the end.
- **Security.** No outside scripts, input, storage or network calls. A Content-Security-Policy meta tag allows only inline images and Google Fonts. All text is escaped before display, and links are only shown if they are https URLs.

## Sources

- **Data.** Rivera, Yanira A. *Concepción Reservoir Bathymetry & Shoreline Dataset (Honduras): Digitized Pre-Dam Contours, Depth Raster, Boundary Polygons & Derived Layers.* Zenodo. Version 1 (2025): https://doi.org/10.5281/zenodo.17674907. This interactive uses the new version, files dated 23 Nov 2026. **DOI to be added when it is uploaded** (`dataset.new_version_doi` in the config). CC BY 4.0.
- **Source map.** AMS (Army Map Service) 1:50,000, sheet Ojojona 2757-IV, 1956. Public domain.
- **Calibration readings.** UMAPS (Unidad Municipal Agua Potable y Saneamiento, Distrito Central), daily reservoir level (N.E.) and volume (V.E.) for La Concepción, 2015–2018, obtained through a public information request via SIELHO (IAIP). *Add the request number and answer date.* The UMAPS crisis dashboard, https://www.umaps.hn/crisis_hidrica/ (read 23 Nov 2026).
- **Official capacity.** El Heraldo, "Represas lograrán su máximo nivel y no habrá extremos racionamientos", https://www.elheraldo.hn/tegucigalpa/1385495-468/represas-lograrán-su-máximo-nivel-y-no-habrá-extremos-racionamientos
- **UMAPS level–volume reading.** El Heraldo, "Represas del Distrito Central están en niveles entre 42% y 48% en plena temporada seca", https://www.elheraldo.hn/tegucigalpa/represa-distrito-central-bajan-mitad-plena-temporada-seca-honduras-OC30454291
- **Full in 2024.** El Heraldo, "Represa La Concepción alcanza su máximo nivel por segundo año consecutivo", https://www.elheraldo.hn/tegucigalpa/represa-concepcion-alcanza-nivel-maximo-segundo-ano-consecutivo-HG27748384

## Licence

Code: MIT. Page, curve and derived images: CC BY 4.0, the same as the dataset.
