"""
An adapter for using PaddleOCR as the underlying OCR of Presidio.
"""

import numpy as np
from paddleocr import PaddleOCR
from PIL.Image import Image
from presidio_image_redactor import OCR


def create_ocr(config_file: str | None = None):
    ocr: PaddleOCR = PaddleOCR(
        return_word_box=False,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        paddlex_config=config_file,
    )

    def _ocr(image: str | Image | np.ndarray) -> dict[str, list[int]]:
        if isinstance(image, Image):
            if image.mode != "RGB":
                image = image.convert("RGB")
            image = np.asarray(image)  # Convert of np.array
        result = ocr.predict(image)
        if not result or result[0]["rec_boxes"].size == 0:
            return {
                "left": [],
                "top": [],
                "height": [],
                "width": [],
                "text": [],
            }
        a = result[0]

        rec_bboxes: np.ndarray = a["rec_boxes"]
        # rec_bboxes.shape should be (<num of texts rec>, 4)
        d = {
            "left": rec_bboxes[:, 0].tolist(),
            "top": rec_bboxes[:, 1].tolist(),
            "height": (rec_bboxes[:, 3] - rec_bboxes[:, 1]).tolist(),
            "width": (rec_bboxes[:, 2] - rec_bboxes[:, 0]).tolist(),
            "text": a["rec_texts"],
        }
        return d

    return _ocr


class PresidioPaddleOCR(OCR):
    """OCR class that performs OCR on a given image."""

    def __init__(self, config_file: str | None = None):
        self.ocr_ = create_ocr(config_file)

    def perform_ocr(self, image: object, **kwargs) -> dict:
        """Perform OCR on a given image.

        :param image: PIL Image/numpy array or file path(str) to be processed
        :param kwargs: Additional values for OCR image_to_data

        :return: results dictionary containing bboxes and text for each detected word
        """
        return self.ocr_(image)
