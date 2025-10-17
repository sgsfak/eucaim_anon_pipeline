import os
import time
from pathlib import Path

from loguru import logger
from presidio_image_redactor import DicomImageRedactorEngine
from tqdm import tqdm

from .paddle_ocr import PADDLE_DEFAULT_CPU_THREADS, PresidioPaddleOCR


def perform_ocr(
    input_dir: Path,
    output_dir: Path,
    paddle_ocr: bool = True,
    verbose: bool = False,
    threads: int = PADDLE_DEFAULT_CPU_THREADS,
) -> None:
    engine = DicomImageRedactorEngine()
    if paddle_ocr:
        engine.image_analyzer_engine.ocr = PresidioPaddleOCR(
            config_file="PaddleOCR.yaml",
            num_threads=threads,
        )
    logger.info("Starting OCR pipeline, output will be saved to {}".format(output_dir))
    cnt = 0
    files_to_process = input_dir.rglob("*")
    files_with_progress = files_to_process if verbose else tqdm(files_to_process)
    time_start = time.time()
    for file_path in files_with_progress:
        if not file_path.is_file():
            continue
        is_dicom: bool = False
        with open(file_path, "rb") as f:
            is_dicom = f.seek(128) == 128 and f.read(4) == b"DICM"
        if not is_dicom:
            continue
        output_path_dir = output_dir / file_path.parent.relative_to(input_dir)
        if not output_path_dir.exists():
            output_path_dir.mkdir(parents=True, exist_ok=True)
        if verbose:
            logger.info(f"OCR processing file {file_path}")
        engine.redact_from_file(
            os.fspath(file_path),
            os.fspath(output_path_dir),
            fill="contrast",
            use_metadata=True,
            save_bboxes=False,
            verbose=False,
        )
        cnt += 1
    time_end = time.time()
    logger.info(f"Redacted {cnt} files in {time_end - time_start:.3f} seconds")
