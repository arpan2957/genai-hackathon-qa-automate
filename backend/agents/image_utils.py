"""
Image processing utilities for the GenerationAgent.
This module handles image loading from various sources (GCS, HTTP, base64).
"""

import io
import base64
import requests
from PIL import Image
from typing import Optional
from database import storage_client


class ImageLoader:
    """Handles loading images from various sources for AI processing."""
    
    @staticmethod
    def load_image_from_url(url: str) -> Image.Image:
        """
        Load an image from various URL formats.
        
        Supports:
        - Google Cloud Storage URLs (gs://)
        - HTTP/HTTPS URLs
        - Base64 data URLs
        
        Args:
            url: The image URL or data URI
            
        Returns:
            PIL Image object
            
        Raises:
            ValueError: If URL format is unsupported
            Exception: If image loading fails
        """
        if url.startswith("gs://"):
            return ImageLoader._load_from_gcs(url)
        elif url.startswith(("http://", "https://")):
            return ImageLoader._load_from_http(url)
        elif url.startswith("data:image/"):
            return ImageLoader._load_from_base64(url)
        else:
            raise ValueError(f"Unsupported image URL format: {url}")
    
    @staticmethod
    def _load_from_gcs(gcs_url: str) -> Image.Image:
        """Load image from Google Cloud Storage."""
        try:
            # Parse GCS URL: gs://bucket-name/path/to/image.jpg
            url_parts = gcs_url.replace("gs://", "").split("/")
            bucket_name = url_parts[0]
            blob_name = "/".join(url_parts[1:])
            
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            image_bytes = blob.download_as_bytes()
            return Image.open(io.BytesIO(image_bytes))
            
        except Exception as e:
            print(f"Error loading image from GCS URL {gcs_url}: {e}")
            # Return a placeholder image instead of failing
            return ImageLoader._create_placeholder_image()
    
    @staticmethod
    def _load_from_http(http_url: str) -> Image.Image:
        """Load image from HTTP/HTTPS URL."""
        try:
            response = requests.get(http_url, timeout=30)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content))
            
        except Exception as e:
            print(f"Error loading image from HTTP URL {http_url}: {e}")
            return ImageLoader._create_placeholder_image()
    
    @staticmethod
    def _load_from_base64(data_url: str) -> Image.Image:
        """Load image from base64 data URL."""
        try:
            # Parse data URL: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...
            header, encoded = data_url.split(",", 1)
            image_data = base64.b64decode(encoded)
            return Image.open(io.BytesIO(image_data))
            
        except Exception as e:
            print(f"Error loading image from base64 data URL: {e}")
            return ImageLoader._create_placeholder_image()
    
    @staticmethod
    def _create_placeholder_image() -> Image.Image:
        """Create a placeholder image when loading fails."""
        return Image.new('RGB', (200, 100), color='lightgray')
    
    @staticmethod
    def load_images_from_urls(urls: list) -> list:
        """
        Load multiple images from URLs, skipping failed loads.
        
        Args:
            urls: List of image URLs
            
        Returns:
            List of successfully loaded PIL Image objects
        """
        images = []
        for url in urls:
            try:
                image = ImageLoader.load_image_from_url(url)
                images.append(image)
            except Exception as e:
                print(f"Skipping failed image load for {url}: {e}")
                continue
        return images
    
    @staticmethod
    def validate_image_format(image: Image.Image) -> bool:
        """
        Validate that the image is in a supported format for AI processing.
        
        Args:
            image: PIL Image object
            
        Returns:
            True if format is supported, False otherwise
        """
        supported_formats = {'JPEG', 'PNG', 'WEBP', 'GIF'}
        return image.format in supported_formats
    
    @staticmethod
    def prepare_image_for_ai(image: Image.Image, max_size: tuple = (1024, 1024)) -> Image.Image:
        """
        Prepare image for AI processing by resizing and optimizing.
        
        Args:
            image: PIL Image object
            max_size: Maximum dimensions (width, height)
            
        Returns:
            Optimized PIL Image object
        """
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        return image


# Convenience functions for backward compatibility
def load_image_from_url(url: str) -> Image.Image:
    """Convenience function for loading a single image."""
    return ImageLoader.load_image_from_url(url)


def load_images_from_urls(urls: list) -> list:
    """Convenience function for loading multiple images."""
    return ImageLoader.load_images_from_urls(urls)
