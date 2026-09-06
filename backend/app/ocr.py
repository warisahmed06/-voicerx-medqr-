from paddleocr import PaddleOCR
from pydantic import BaseModel
import numpy as np 

class OCRResult(BaseModel):
    text: str
    confidence: float

# Initialize PaddleOCR (downloads models on first run)
ocr = PaddleOCR(use_angle_cls=True, lang='en', ir_optim=False) # <-- Changed here!


def run_ocr(image_bytes: bytes) -> OCRResult:
    """
    Extract text from prescription image using PaddleOCR.
    Much better for handwritten prescriptions!
    """
    from io import BytesIO
    from PIL import Image
    
    try:
        # Convert bytes to image
        image = Image.open(BytesIO(image_bytes))
        
        # Run OCR
        image_np = np.array(image.convert("RGB"))
        result = ocr.ocr(image_np, cls=True)

        
        # Extract text and confidence
        full_text = ""
        confidences = []
        
        for line in result:
            for word_info in line:
                text = word_info[1][0]
                confidence = word_info[1][1]
                full_text += text + " "
                confidences.append(confidence)
        
        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return OCRResult(
            text=full_text.strip(),
            confidence=avg_confidence
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return OCRResult(text="", confidence=0.0)