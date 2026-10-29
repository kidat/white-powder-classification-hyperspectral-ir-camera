"""
White Powder Hyperspectral Analysis - IR Camera Data
Analyzes medical imaging simulation powder using IR scanner data (918-2532 nm)
Performs white/dark correction, ROI analysis, and multi-band RGB visualization
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.animation import FuncAnimation, PillowWriter
from spectral import open_image

# ============================================================================
# LOAD HYPERSPECTRAL DATA
# ============================================================================
base_path = Path('dataset')
sample_path = base_path / 'ir med_sim_powder_scan_0551.hdr'
white_path = base_path / 'WHITEREF_ir med_sim_powder_scan_0551.hdr'
dark_path = base_path / 'DARKREF_ir med_sim_powder_scan_0551.hdr'

sample_img = open_image(sample_path)
wavelength = np.array(sample_img.bands.centers)

sample_cube = sample_img.load().astype(np.float32)
white_cube = open_image(white_path).load().astype(np.float32)
dark_cube = open_image(dark_path).load().astype(np.float32)

lines, samples, bands = sample_cube.shape
print(f"Data dimensions - Lines: {lines}, Samples: {samples}, Bands: {bands}")

# ============================================================================
# REFLECTANCE CALIBRATION
# ============================================================================
# Average references; NumPy broadcasts them across the image lines.
white_ref = white_cube.mean(axis=0)
dark_ref = dark_cube.mean(axis=0)

# Apply white-dark correction formula
denominator = white_ref - dark_ref
reflectance = np.divide(sample_cube - dark_ref, denominator, out=np.zeros_like(sample_cube),
                         where=np.abs(denominator) > 1e-6)
reflectance = np.clip(reflectance, 0, 1)

# ============================================================================
# RGB COMPOSITE FOR ROI SELECTION
# ============================================================================
RGB = np.empty((lines, samples, 3))
RGB[:,:,0] = reflectance[:, :, 66] 
RGB[:,:,1] = reflectance[:, :, 46] 
RGB[:,:,2] = reflectance[:, :, 30] 

# ============================================================================
# ROI ANALYSIS AND SPECTRAL EXTRACTION
# ============================================================================
rois = [
    (191, 195, 134, 138), (188, 192,  30,  34), (113, 117,  36,  40),
    (201, 205,  78,  82), (172, 176,  98, 102), (115, 119,  72,  76),
    (142, 146, 109, 113), ( 93,  97, 151, 155),
]

RGB2 = RGB.copy()
colors = plt.cm.tab10.colors[:8]
border = 2
spectra = []

# Draw ROI boxes and extract median spectra
for i, ((x1, x2, y1, y2), color) in enumerate(zip(rois, colors), 1):
    RGB2[y1-border:y2+border, x1-border:x2+border] = np.array(color[:3])
    spectra.append(np.median(reflectance[y1:y2, x1:x2, :], axis=(0, 1)))

# Visualize ROI locations and click a point to show its reflectance
plt.rcParams['figure.dpi'] = 150
fig, ax = plt.subplots(figsize=(8, 5))
ax.imshow(RGB2)
ax.axis("off")
spectrum_fig, spectrum_ax = plt.subplots(figsize=(8, 5))
spectrum_ax.set_xlabel("Wavelength (nm)")
spectrum_ax.set_ylabel("Reflectance")
spectrum_ax.set_title("Clicked-pixel reflectance")

def show_spectrum(event):
    if event.inaxes == ax and event.xdata is not None and event.ydata is not None:
        x, y = round(event.xdata), round(event.ydata)
        spectrum_ax.plot(wavelength, reflectance[y, x, :],
                         color=plt.cm.tab10(len(spectrum_ax.lines) % 10),
                         label=f"x={x}, y={y}")
        spectrum_ax.legend()
        spectrum_fig.tight_layout()
        spectrum_fig.canvas.draw_idle()

fig.canvas.mpl_connect("button_press_event", show_spectrum)
fig.savefig("Result/03_roi_visualization.png", dpi=150)
ax.set_title("Click a point to plot its reflectance")
plt.show()

# Plot spectral signatures from all ROIs
plt.figure(figsize=(8, 5))
for i, spec in enumerate(spectra, 1):
    plt.plot(wavelength, spec, label=f"ROI {i}")
plt.xlabel("Wavelength (nm)")
plt.ylabel("Reflectance")
plt.title("Spectral Reflectance After White/Dark Correction")
plt.legend()
plt.savefig("Result/05_camera_spectra.png", dpi=150)
plt.show()

# ============================================================================
# MULTI-BAND RGB GRID VISUALIZATION
# ============================================================================
fig, axes = plt.subplots(3, 3, figsize=(12, 12), dpi=150)
axes = axes.flatten()

g_values = [200, 240]  # Green channel bands
b_values = [120, 160]  # Blue channel bands
r_values = [80, 107]   # Red channel bands
RGB = np.empty((lines, samples, 3), dtype=np.float32)

# Generate 8 combinations (2x2x2) from band selections
idx = 0
for r in r_values:
    for b in b_values:
        for g in g_values:
            RGB[:,:,0] = reflectance[:,:,r]
            RGB[:,:,1] = reflectance[:,:,g]
            RGB[:,:,2] = reflectance[:,:,b]
            
            # Apply percentile-based contrast enhancement
            RGB_display = RGB.copy()
            for i in range(3):
                p2, p98 = np.percentile(RGB_display[:,:,i], (2, 98))
                RGB_display[:,:,i] = np.clip((RGB_display[:,:,i] - p2) / (p98 - p2 + 1e-8), 0, 1)
            
            axes[idx].imshow(RGB_display[20:170,40:260,:])
            axes[idx].set_title(f'R:{r} G:{g} B:{b}', fontsize=14)
            axes[idx].axis('off')
            idx += 1

# Fill 9th subplot with custom band combination
RGB[:,:,0] = reflectance[:,:,80]
RGB[:,:,1] = reflectance[:,:,160]
RGB[:,:,2] = reflectance[:,:,240]

RGB_display = RGB.copy()
for i in range(3):
    p2, p98 = np.percentile(RGB_display[:,:,i], (2, 98))
    RGB_display[:,:,i] = np.clip((RGB_display[:,:,i] - p2) / (p98 - p2 + 1e-8), 0, 1)

axes[8].imshow(RGB_display[20:170,40:260,:])
axes[8].set_title(f'R:80 G:160 B:240', fontsize=14)
axes[8].axis('off')

plt.tight_layout()
plt.savefig('Result/rgb_grid_3x3.png', dpi=200, bbox_inches='tight')
plt.show()

# ============================================================================ 
# WAVELENGTH-SWEEP ANIMATION
# ============================================================================
fig, axes = plt.subplots(3, 3, figsize=(12, 12))
axes = axes.ravel()
fig.subplots_adjust(left=0, right=1, bottom=0, top=0.96, wspace=0.02, hspace=0.12)
images = []
for axis in axes:
    axis.axis('off')
    images.append(axis.imshow(np.zeros((150, 220, 3))))
rng = np.random.default_rng(42)
def wavelength_range(first, last):
    return np.arange(np.ceil(wavelength[first] / 10) * 10,
                     np.floor(wavelength[last] / 10) * 10 + 1, 10)
r_values = wavelength_range(10, 110)
g_values = wavelength_range(200, bands - 1)
b_values = wavelength_range(120, 190)
frames = range(60)
ranges = [(r_values, g_values, b_values), (b_values, g_values, r_values),
          (g_values, r_values, b_values)]

def update(frame):
    updated = []
    for i, (image, axis) in enumerate(zip(images, axes)):
        red_range, green_range, blue_range = ranges[i // 3]
        red, green, blue = (rng.choice(values) for values in
                            (red_range, green_range, blue_range))
        rgb_bands = [np.abs(wavelength - value).argmin()
                     for value in (red, green, blue)]
        rgb = reflectance[20:170, 40:260, rgb_bands].copy()
        for channel in range(3):
            low, high = np.percentile(rgb[:, :, channel], (2, 98))
            rgb[:, :, channel] = np.clip(
                (rgb[:, :, channel] - low) / (high - low + 1e-8), 0, 1)
        image.set_data(rgb)
        axis.set_title(
            f"R:{red:.0f} G:{green:.0f} B:{blue:.0f} nm")
        updated.append(image)
    return updated

animation = FuncAnimation(fig, update, frames=frames, interval=1000, blit=True)
animation.save("Result/wavelength_sweep.gif", writer=PillowWriter(fps=1))
plt.close(fig)