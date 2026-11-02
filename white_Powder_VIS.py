"""
White Powder Segmentation - Scanner VIS Data
Medical imaging simulation with hyperspectral analysis
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from spectral import open_image

# ============================================================================
# LOAD HYPERSPECTRAL DATA
# ============================================================================
base_path = Path('dataset')
sample_img = open_image(base_path / 'Medical_Img_Sim_scan_0128.hdr')
wavelength = np.array(sample_img.bands.centers)
sample_cube = sample_img.load().astype(np.float32)
white_cube = open_image(base_path / 'WHITEREF_Medical_Img_Sim_scan_0128.hdr').load().astype(np.float32)
dark_cube = open_image(base_path / 'DARKREF_Medical_Img_Sim_scan_0128.hdr').load().astype(np.float32)

lines, samples, bands = sample_cube.shape
print(f"Cube shape: {sample_cube.shape}")

# ============================================================================
# COMPUTE REFLECTANCE CORRECTION
# ============================================================================
white_ref = np.tile(white_cube.mean(axis=0, keepdims=True), (lines, 1, 1))
dark_ref = np.tile(dark_cube.mean(axis=0, keepdims=True), (lines, 1, 1))
reflectance = np.clip((sample_cube - dark_ref) / (white_ref - dark_ref), 0, 1).astype(np.float32)
print(f"Reflectance range: [{reflectance.min():.4f}, {reflectance.max():.4f}]")

# ============================================================================
# STANDARD RGB COMPOSITE (650, 550, 470 nm)
# ============================================================================
RGB = np.stack([reflectance[:,:,66], reflectance[:,:,46], reflectance[:,:,30]], axis=2) 

plt.rcParams['figure.dpi'] = 150
plt.imshow(RGB)
plt.title(f'RGB at {wavelength[66]:.0f}, {wavelength[46]:.0f}, {wavelength[30]:.0f} nm')
plt.axis('off')
plt.savefig('Result/02_rgb_composite.png', dpi=150, bbox_inches='tight')
plt.show()

# ============================================================================
# ROI SELECTION AND SPECTRAL ANALYSIS
# ============================================================================
# Define ROI coordinates (x1, x2, y1, y2)
rois = [
    (1218, 1222, 92, 96), (1400, 1404, 343, 347), (1333, 1337, 636, 640), (891, 895, 743, 747),
    (1135, 1139, 302, 306), (914, 918, 416, 420), (1332, 1336, 452, 456), (869, 873, 140, 144)
]

RGB2 = RGB.copy()
colors = plt.cm.tab10.colors[:8]
border = 15
spectra = []

for i, ((x1, x2, y1, y2), color) in enumerate(zip(rois, colors), 1):
    RGB2[y1-border:y2+border, x1-border:x2+border] = np.array(color[:3])
    spectra.append(np.median(reflectance[y1:y2, x1:x2, :], axis=(0, 1)))

plt.rcParams['figure.dpi'] = 150
plt.figure(figsize=(8, 5))
plt.imshow(RGB2)
plt.axis('off')
plt.savefig('Result/03_roi_visualization.png', dpi=150)
plt.show()

plt.figure(figsize=(8, 5))
for i, spec in enumerate(spectra, 1):
    plt.plot(wavelength, spec, label=f"ROI {i}")
plt.xlabel("Wavelength (nm)")
plt.ylabel("Reflectance")
plt.legend()
plt.savefig('Result/05_camera_spectra.png', dpi=150)
plt.show()

# ============================================================================
# ENHANCED RGB COMPOSITE (SELECTED BANDS)
# ============================================================================
RGB1 = np.stack([reflectance[:,:,80], 1.2*reflectance[:,:,22], 1.2*reflectance[:,:,53]], axis=2)
RGB1 = np.clip(RGB1, 0, 1)

plt.rcParams['figure.dpi'] = 300
plt.imshow(RGB1)
plt.axis('off')
plt.title('Enhanced RGB Composite')
plt.savefig('Result/04_rgb_enhanced.png', dpi=150, bbox_inches='tight')
plt.show()

# ============================================================================
# MULTI-BAND RGB GRID VISUALIZATION
# ============================================================================
# Helper function for contrast enhancement
def enhance_contrast(img):
    img_enhanced = img.copy()
    for i in range(3):
        p2, p98 = np.percentile(img[:,:,i], (2, 98))
        img_enhanced[:,:,i] = np.clip((img[:,:,i] - p2) / (p98 - p2 + 1e-8), 0, 1)
    return img_enhanced

# Band combinations for material discrimination
b_values = [49, 61, 90]
r_values = [80, 100, 124]
g_fixed = 22

fig, axes = plt.subplots(3, 3, figsize=(12, 12), dpi=150)
axes = axes.flatten()

RGB_temp = np.empty((lines, samples, 3), dtype=np.float32)
idx = 0

for b in b_values:
    for r in r_values:
        RGB_temp[:,:,0] = reflectance[:,:,r]
        RGB_temp[:,:,1] = reflectance[:,:,g_fixed]
        RGB_temp[:,:,2] = reflectance[:,:,b]
        
        RGB_display = enhance_contrast(RGB_temp)
        axes[idx].imshow(RGB_display[:850,600:1700,:])
        axes[idx].set_title(
            f'R:{wavelength[r]:.0f} G:{wavelength[g_fixed]:.0f} '
            f'B:{wavelength[b]:.0f} nm', fontsize=10)
        axes[idx].axis('off')
        idx += 1

plt.tight_layout()
plt.savefig('Result/rgb_grid_3x3.png', dpi=200, bbox_inches='tight')
plt.show()