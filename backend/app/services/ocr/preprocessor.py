import cv2
import numpy as np

class ImagePreprocessor:
    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        """
        Detects skew angle of text inside an image and rotates it back to horizontal.
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # Threshold the image, binary-inverse
            # Text will be white, background black
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            
            # Find all coordinates that are non-zero (white pixels representing text)
            coords = np.column_stack(np.where(thresh > 0))
            
            if len(coords) == 0:
                return image  # Return original if empty
                
            # Get bounding rectangle containing all text coordinates
            angle = cv2.minAreaRect(coords)[-1]
            
            # cv2.minAreaRect returns angle in range [-90, 0)
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
                
            # Ignore tiny rotations to avoid pixel degradation
            if abs(angle) < 0.5 or abs(angle) > 45:
                return image
                
            # Calculate rotation matrix
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # Perform rotation
            rotated = cv2.warpAffine(
                image, M, (w, h), 
                flags=cv2.INTER_CUBIC, 
                borderMode=cv2.BORDER_REPLICATE
            )
            return rotated
        except Exception:
            # Fallback to original image if anything fails
            return image

    @staticmethod
    def remove_noise(image: np.ndarray) -> np.ndarray:
        """
        Apply Gaussian Blur and morphological operations to reduce noise.
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            # Gaussian blur to remove high-frequency noise
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            return blurred
        except Exception:
            return image

    @staticmethod
    def preprocess_for_ocr(image_path: str) -> np.ndarray:
        """
        Loads image, applies noise removal and deskewing, and returns the preprocessed image.
        """
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image from {image_path}")
            
        # Apply deskew
        deskewed = ImagePreprocessor.deskew(img)
        
        # Apply noise removal
        cleaned = ImagePreprocessor.remove_noise(deskewed)
        
        return cleaned

preprocessor = ImagePreprocessor()
