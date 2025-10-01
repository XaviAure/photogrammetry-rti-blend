#!/usr/bin/env python3
"""
Normal Map Low-Frequency Distortion Corrector for Cultural Heritage Imaging

This script implements the methodology described in:
"Revisiting Paintings: Automated 2.5D capture for large planar artworks"
by Xavier Aure Calvet, Chatrapathi Akula & Kyle Hirani (EVA London 2024)

The method corrects low-frequency distortions in RTI (Reflectance Transformation 
Imaging) normal maps by blending them with photogrammetry-derived normal maps.
RTI excels at capturing high-frequency surface details but often fails to accurately
represent low-frequency aspects due to inaccurate lighting estimation. This script
combines the strengths of both techniques to produce accurate, detailed normal maps
for cultural heritage documentation.

Author: Based on Aure et al. (2024)
License: MIT
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
import tifffile
from PIL import Image


class NormalMapProcessor:
    """
    Handles normal map processing and correction for cultural heritage imaging.

    This processor combines high-frequency detail from RTI with accurate low-frequency geometric information
    from photogrammetry to create optimal normal maps that can be stitched to produce high-resolution artwork documentation.
    """
    
    def __init__(self):
        """Initialize the NormalMapProcessor."""
        pass
    
    @staticmethod
    def load_normal_map(filename: str) -> np.ndarray:
        """
        Load a normal map from various image formats and convert to float32 range [-1, 1].
        
        Args:
            filename (str): Path to the normal map image file
            
        Returns:
            np.ndarray: Normal map as float32 array with values in range [-1, 1]
            
        Raises:
            ValueError: If the image format is not supported
            FileNotFoundError: If the file doesn't exist
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File not found: {filename}")
        
        try:
            img = Image.open(filename)
            img_array = np.array(img)
            
            if img.mode == 'L':  # 8-bit grayscale
                img_array = img_array.astype(np.float32)
                img_array = img_array / 255.0 * 2.0 - 1.0
            elif img.mode == 'I;16':  # 16-bit grayscale
                img_array = img_array.astype(np.float32)
                img_array = img_array / 65535.0 * 2.0 - 1.0
            elif img.mode == 'RGB':  # 8-bit RGB
                img_array = img_array.astype(np.float32)
                img_array = img_array / 255.0 * 2.0 - 1.0
            elif img.mode == 'I;16B':  # 16-bit RGB
                img_array = img_array.astype(np.float32)
                img_array = img_array / 65535.0 * 2.0 - 1.0
            else:
                raise ValueError(f"Unsupported image mode: {img.mode}. "
                               "Please use 8-bit or 16-bit images.")
            
            return img_array
            
        except Exception as e:
            raise ValueError(f"Error loading image {filename}: {str(e)}")
    
    @staticmethod
    def save_normal_map(filename: str, normal_map: np.ndarray) -> None:
        """
        Save a normal map as a 16-bit TIFF file.
        
        Args:
            filename (str): Output filename
            normal_map (np.ndarray): Normal map array with values in range [-1, 1]
        """
        # Convert from [-1, 1] to [0, 65535] for 16-bit output
        img = (normal_map + 1.0) / 2.0 * 65535.0
        img = np.clip(img, 0, 65535).astype(np.uint16)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        tifffile.imwrite(filename, img)
    
    @staticmethod
    def normalize_normals(normals: np.ndarray) -> np.ndarray:
        """
        Normalize normal vectors to unit length.
        
        Args:
            normals (np.ndarray): Array of normal vectors
            
        Returns:
            np.ndarray: Normalized normal vectors
        """
        norm = np.linalg.norm(normals, axis=-1, keepdims=True)
        # Avoid division by zero
        norm = np.where(norm == 0, 1, norm)
        return normals / norm
    
    def correct_low_frequency_distortions(self, detailed_map: np.ndarray, 
                                        less_detailed_map: np.ndarray, 
                                        blur_radius: float, 
                                        alpha: float) -> np.ndarray:
        """
        Correct low-frequency distortions in RTI normal maps.
        
        This method implements the core algorithm from the paper:
        1. Extract low-frequency components from both maps using Gaussian blur
        2. Blend the low-frequency components: α × PG_low_freq + (1-α) × RTI_low_freq
        3. Replace RTI's low-frequency content with the blended version
        4. Normalize the resulting normal vectors to unit length
        
        The process preserves RTI's excellent high-frequency detail while correcting
        its low-frequency geometric inaccuracies using photogrammetry data.
        
        Args:
            detailed_map (np.ndarray): RTI-derived normal map (high-frequency detail)
            less_detailed_map (np.ndarray): Photogrammetry-derived normal map (accurate low-frequency)
            blur_radius (float): Standard deviation for Gaussian blur (σ in the paper)
            alpha (float): Blending factor [0, 1] - higher values favor photogrammetry low-freq
            
        Returns:
            np.ndarray: Corrected normal map with accurate low and high frequency content
            
        Reference:
            Aure et al. (2024): "For the Canaletto painting, α=0.99 and blur_radius=8 
            were used, giving Mean Angular Error of 0.62° after correction."
        """
        # Validate inputs
        if detailed_map.shape != less_detailed_map.shape:
            raise ValueError("Input normal maps must have the same dimensions")
        
        if not 0 <= alpha <= 1:
            raise ValueError("Alpha must be between 0 and 1")
        
        if blur_radius <= 0:
            raise ValueError("Blur radius must be positive")
        
        # Calculate the low-frequency content of both maps
        detailed_low_freq = cv2.GaussianBlur(detailed_map, (0, 0), blur_radius)
        less_detailed_low_freq = cv2.GaussianBlur(less_detailed_map, (0, 0), blur_radius)
        
        # Blend the low-frequency content
        blended_low_freq = alpha * less_detailed_low_freq + (1 - alpha) * detailed_low_freq
        
        # Replace the low-frequency content in the detailed normal map
        corrected_detailed_map = detailed_map - detailed_low_freq + blended_low_freq
        
        # Normalize the corrected normals
        return self.normalize_normals(corrected_detailed_map)
    
    def process_image_pairs(self, detailed_folder: str, less_detailed_folder: str, 
                          output_folder: str, blur_radius: float, alpha: float) -> None:
        """
        Process pairs of normal maps from RTI and photogrammetry workflows.
        
        This method processes "link images" as described in Aure et al. (2024):
        - RTI normal maps exported from Relight software (detailed, high-frequency)
        - Photogrammetry normal maps exported from Agisoft Metashape mesh (accurate geometry)
        
        The corrected normal maps are then suitable for re-import into photogrammetry
        software to generate high-resolution, accurate orthomosaics.
        
        Args:
            detailed_folder (str): Path to RTI-derived normal maps
            less_detailed_folder (str): Path to photogrammetry-derived normal maps
            output_folder (str): Path to output folder for corrected maps
            blur_radius (float): Gaussian blur radius (typically 8-12 for paintings)
            alpha (float): Blending factor (typically 0.95-0.99 for artwork scanning)
        """
        # Validate input folders
        if not os.path.exists(detailed_folder):
            raise FileNotFoundError(f"Detailed folder not found: {detailed_folder}")
        if not os.path.exists(less_detailed_folder):
            raise FileNotFoundError(f"Less detailed folder not found: {less_detailed_folder}")
        
        # Get sorted file lists
        detailed_filenames = sorted([f for f in os.listdir(detailed_folder) 
                                   if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))])
        less_detailed_filenames = sorted([f for f in os.listdir(less_detailed_folder)
                                        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))])
        
        if not detailed_filenames:
            raise ValueError(f"No image files found in {detailed_folder}")
        if not less_detailed_filenames:
            raise ValueError(f"No image files found in {less_detailed_folder}")
        
        if len(detailed_filenames) != len(less_detailed_filenames):
            raise ValueError(f"Number of images must be equal. Found {len(detailed_filenames)} "
                           f"detailed and {len(less_detailed_filenames)} less detailed images.")
        
        # Create output directory
        os.makedirs(output_folder, exist_ok=True)
        
        print(f"Processing {len(detailed_filenames)} image pairs...")
        
        for i, (detailed_filename, less_detailed_filename) in enumerate(
            zip(detailed_filenames, less_detailed_filenames), 1):
            
            try:
                detailed_path = os.path.join(detailed_folder, detailed_filename)
                less_detailed_path = os.path.join(less_detailed_folder, less_detailed_filename)
                
                print(f"[{i}/{len(detailed_filenames)}] Processing: {detailed_filename}")
                
                # Load normal maps
                detailed_map = self.load_normal_map(detailed_path)
                less_detailed_map = self.load_normal_map(less_detailed_path)
                
                # Correct distortions
                corrected_map = self.correct_low_frequency_distortions(
                    detailed_map, less_detailed_map, blur_radius, alpha
                )
                
                # Save result
                output_file = os.path.join(output_folder, f"{Path(detailed_filename).stem}_corrected.tif")
                self.save_normal_map(output_file, corrected_map)
                
                print(f"    → Saved: {output_file}")
                
            except Exception as e:
                print(f"    ✗ Error processing {detailed_filename}: {str(e)}")
                continue
        
        print(f"Processing complete! Results saved to: {output_folder}")


def main():
    """Main function to handle command line arguments and execute processing."""
    parser = argparse.ArgumentParser(
        description="Correct low-frequency distortions in RTI normal maps using photogrammetry data. "
                   "Implements methodology from Aure et al. (EVA London 2024).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="Example: python normal_map_corrector.py RTI_normals PG_normals output --blur-radius 8 --alpha 0.99"
    )
    
    parser.add_argument("detailed_folder", 
                       help="Path to RTI-derived normal maps (high-frequency detail)")
    parser.add_argument("less_detailed_folder",
                       help="Path to photogrammetry-derived normal maps (accurate low-frequency)")
    parser.add_argument("output_folder",
                       help="Path to output folder for corrected normal maps")
    
    parser.add_argument("--blur-radius", "-b", type=float, default=8.0,
                       help="Gaussian blur radius for low-frequency extraction (σ). "
                           "Typical range: 8-12 for paintings")
    parser.add_argument("--alpha", "-a", type=float, default=0.99,
                       help="Blending factor: α × PG_low + (1-α) × RTI_low. "
                           "Higher values (0.95-0.99) favor photogrammetry's accurate geometry")
    
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not 0 <= args.alpha <= 1:
        print("Error: Alpha must be between 0 and 1")
        sys.exit(1)
    
    if args.blur_radius <= 0:
        print("Error: Blur radius must be positive")
        sys.exit(1)
    
    try:
        processor = NormalMapProcessor()
        processor.process_image_pairs(
            args.detailed_folder,
            args.less_detailed_folder,
            args.output_folder,
            args.blur_radius,
            args.alpha
        )
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


# Example usage with paper's parameters
if __name__ == "__main__":
    # For Canaletto painting case study (190cm x 120cm):
    # blur_radius = 8
    # alpha = 0.99
    # Result: Mean Angular Error reduced from 0.95° to 0.62°
    main()