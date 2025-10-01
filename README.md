# Normal Map Correction for Cultural Heritage Imaging

A simple Python implementation of the methodology described in "Revisiting Paintings: Automated 2.5D capture for large planar artworks" by Xavier Aure Calvet, Chatrapathi Akula & Kyle Hirani (EVA London 2024).

This tool corrects low-frequency distortions in RTI (Reflectance Transformation Imaging) normal maps by blending them with photogrammetry-derived normal maps, combining the strengths of both imaging techniques for optimal cultural heritage documentation.

## Background

The Problem: RTI excels at capturing high-frequency surface details (fine brushstrokes, canvas texture, craquelure) but often produces inaccurate low-frequency geometric information due to imprecise lighting estimation.

The Solution: This script implements the methodology to:
1. Extract low-frequency components from both RTI and photogrammetry normal maps using Gaussian blur
2. Blend these components: `Blended = α × PG_low_freq + (1-α) × RTI_low_freq`
3. Replace RTI's low-frequency content with the corrected blend
4. Preserve RTI's high-frequency detail

Result: multiple normal maps with accurate geometry and fine surface detail, suitable for stitching and blending high-resolution artwork documentation.

## Features

- Cultural Heritage Focus: Specifically designed for planar artworks documentation workflows
- Dual-Technique Integration: Combines RTI high-frequency detail with photogrammetry accuracy
- Multiple Image Format Support: Handles 8-bit and 16-bit grayscale/RGB images (PNG, JPG, TIFF)
- Batch Processing: Process entire sets of "link images" automatically
- Agisoft Metashape Compatible: Outputs suitable for re-import into photogrammetry workflows
- Configurable Parameters: Adjustable blur radius and blending factors based on artwork characteristics

## Installation

### Prerequisites

- Python 3.7 or higher
- pip package manager

### Dependencies

Install the required packages using pip:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install opencv-python numpy pillow tifffile
```

## Usage

### Typical Workflow for Artwork Documentation

1. Capture RTI images using dome lighting with multiple angles (e.g., 24 positions)
2. Capture photogrammetry images with consistent quad-LED lighting
3. Process RTI images in Relight to generate initial normal maps
4. Process photogrammetry images in Agisoft Metashape to create mesh
5. Export normal maps from Metashape mesh for each "link image" position
6. Run this script to correct RTI normal maps
7. Re-import corrected maps into Metashape to generate final orthomosaic

### Command Line Interface

Basic usage:

```bash
python normal_map_corrector.py RTI_normals PG_normals corrected_normals
```

With custom parameters (as used for Canaletto painting in the paper):

```bash
python normal_map_corrector.py RTI_normals PG_normals corrected_normals --blur-radius 8 --alpha 0.99
```

### Parameters

- `detailed_folder`: RTI-derived normal maps (from Relight or similar RTI software)
- `less_detailed_folder`: Photogrammetry-derived normal maps (exported from Agisoft Metashape)
- `output_folder`: Where corrected normal maps will be saved
- `--blur-radius` (`-b`): Gaussian blur radius σ (default: 8.0)
  - Typical range for paintings: 8-12
  - Larger values blend more low-frequency content
  - Should be tuned based on painting size and detail level
- `--alpha` (`-a`): Blending factor (default: 0.99)
  - 0 = Keep original RTI low frequencies (no correction)
  - 1 = Use only photogrammetry low frequencies (full correction)
  - 0.95-0.99 = Typical range for artwork (strong correction while preserving some RTI character)
  - Paper used α=0.99 for the Canaletto painting (190cm × 120cm)

### Example: Canaletto Painting

Replicating the paper's case study:

```bash
python normal_map_corrector.py \
    RTI_link_normals \
    Metashape_mesh_normals \
    corrected_normals \
    --blur-radius 8 \
    --alpha 0.99
```

This configuration achieved:
- Before correction: Mean Angular Error = 0.95°
- After correction: Mean Angular Error = 0.62°
- Final resolution: 69,386 × 44,290 pixels at 0.0277 mm/pixel

## How It Works

The algorithm implements a simple frequency-domain blending technique:

### Technical Process

1. Load Normal Map Pairs
   - RTI normal maps: Excellent high-frequency detail, inaccurate low-frequency geometry
   - Photogrammetry normal maps: Accurate geometry, limited high-frequency detail

2. Normalize to [-1, 1] Range
   - Unlike typical image processing, normal maps use [-1, 1] to represent 3D vector directions
   - Each RGB channel represents X, Y, Z components of surface normals

3. Extract Low-Frequency Components
   - Apply Gaussian blur with radius σ (blur_radius parameter)
   - This isolates broad geometric features while removing fine detail
   - `RTI_low_freq = GaussianBlur(RTI_normals, σ)`
   - `PG_low_freq = GaussianBlur(PG_normals, σ)`

4. Blend Low-Frequency Content
   - `Blended_low_freq = α × PG_low_freq + (1-α) × RTI_low_freq`
   - High α values (0.95-0.99) strongly favor photogrammetry's accurate geometry
   - This creates a "best of both worlds" low-frequency component

5. Reconstruct Corrected Normal Map
   - Remove RTI's original low-frequency: `RTI_normals - RTI_low_freq`
   - Add corrected low-frequency: `+ Blended_low_freq`
   - Result: `Corrected = RTI_high_freq + Blended_low_freq`

6. Normalize Vectors
   - Ensure all normal vectors have unit length (|n| = 1)
   - Essential for accurate surface representation in 3D rendering

7. Save as 16-bit TIFF
   - Convert from [-1, 1] back to [0, 65535] for 16-bit storage

## File Structure

### For GitHub Repository
```
normal-map-corrector/
├── normal_map_corrector.py  # Main script
├── README.md               # This documentation
├── requirements.txt        # Python dependencies
├── LICENSE                # MIT license
```

### For your artwork scanning project
```
artwork-documentation/
├── normal_map_corrector.py
├── requirements.txt
├── raw_captures/
│   ├── RTI/                # RTI image sets (24 images per position)
│   │   ├── pos_001/
│   │   ├── pos_002/
│   │   └── ...
│   └── photogrammetry/     # Photogrammetry images
│       ├── img_001.tif
│       ├── img_002.tif
│       └── ...
├── RTI_normals/           # Processed RTI normal maps from Relight
│   ├── link_001_normals.tif
│   ├── link_002_normals.tif
│   └── ...
├── PG_normals/            # Exported from Metashape mesh
│   ├── link_001_normals.tif
│   ├── link_002_normals.tif
│   └── ...
├── corrected_normals/     # Output from this script
│   ├── link_001_normals_corrected.tif
│   ├── link_002_normals_corrected.tif
│   └── ...
└── final_orthomosaics/    # Re-imported into Metashape
    ├── colour_orthomosaic.tif (69,386 × 44,290 pixels @ 917 DPI)
    └── normal_orthomosaic.tif
```

### Integration with Existing Software

Relight (RTI Processing):
- Processes RTI image sets to generate initial normal maps
- Export format: PNG
- Use HSH (Hemispherical Harmonics) method (usually 12 coefficients works best)

Agisoft Metashape (Photogrammetry):
1. Process photogrammetry images to create dense point cloud
2. Generate high-polygon mesh 
3. Export normal maps using "Render Depth Maps" → Normal Map option
4. After correction, replace link images with corrected normal maps
5. Generate final orthomosaic with mosaic blending mode
```

## Supported Formats

### Input Formats
- PNG (8-bit, 16-bit)
- JPEG (8-bit) - suitable for RTI normal maps from Relight
- TIFF (8-bit, 16-bit) 
- Grayscale and RGB images

### Output Format
- 16-bit TIFF files (optimal quality preservation for re-import)

## Error Handling

The tool includes comprehensive error handling for:
- Missing or invalid input folders
- Mismatched number of images between folders
- Unsupported image formats
- Invalid parameter ranges
- File I/O errors

## Performance Considerations

- Processing time depends on image resolution and blur radius
- Memory usage scales with image size
- For large datasets, consider processing in smaller batches

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/improvement`)
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### Common Issues

"No image files found"
- Ensure your folders contain supported image formats (.png, .jpg, .jpeg, .tif, .tiff)
- Check that folder paths are correct

"Number of images must be equal"
- Both input folders must contain the same number of images
- Images are matched by alphabetical sorting

Memory errors with large images
- Try reducing blur radius
- Process smaller batches of images
- Use lower resolution images if possible

## Version History

- v1.0.0: Initial release implementing Aure et al. (2024) methodology

## Software Dependencies

### Required Software for Full Workflow
- Relight (CNR-ISTI VCLab): RTI normal map generation
  - https://github.com/cnr-isti-vclab/relight
- Agisoft Metashape Professional: Photogrammetry processing
  - https://www.agisoft.com/

### Python Libraries (included in requirements.txt)
- OpenCV: Image processing and Gaussian blur operations
- NumPy: Array operations and vector mathematics
- Pillow: Image loading in various formats
- tifffile: 16-bit TIFF export

## Acknowledgments

- Case Study Artwork: Canaletto, "The Grand Canal, Ascension Day" (c.1730-31), Woburn Abbey Collection
- RTI Software: CNR-ISTI VCLab for Relight
- Photogrammetry Software: Agisoft Metashape

