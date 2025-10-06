import os
import tempfile
import uuid
from pathlib import Path

import pydicom
import typer
from loguru import logger
from presidio_image_redactor import DicomImageRedactorEngine
from typing_extensions import Annotated

from deidentify import run_ctp
from hash_clinical import parse_and_hash_clinical_csv
from paddle_ocr import PresidioPaddleOCR

INPUT_DIR: Path = Path("/input")
OUTPUT_DIR: Path = Path("/output")


def perform_ocr(
    input_dir: Path,
    output_dir: Path,
    paddle_ocr: bool = True,
) -> None:
    engine = DicomImageRedactorEngine()
    if paddle_ocr:
        engine.image_analyzer_engine.ocr = PresidioPaddleOCR(
            config_file="PaddleOCR.yaml"
        )
    logger.info("Starting OCR pipeline, output will be saved to {}".format(output_dir))
    for file_path in input_dir.rglob("*.dcm"):
        output_path_dir = output_dir / file_path.parent.relative_to(input_dir)
        if not output_path_dir.exists():
            output_path_dir.mkdir(parents=True, exist_ok=True)
        engine.redact_from_file(
            file_path,
            str(output_path_dir),
            fill="contrast",
            use_metadata=True,
            save_bboxes=False,
            verbose=False,
        )
        logger.info(f"Redacted {file_path.relative_to(input_dir)}")


def hash_clinical_if_found(input_dir: Path, output_dir: Path, site_id: str) -> None:
    # check if there's a CSV in the input folder:
    csvs = list(c for c in input_dir.glob("*.csv") if c.is_file())
    if not csvs:
        logger.warning("No CSV found in input directory")
        return
    input_clinical_csv = csvs[0]
    output_clinical_csv = output_dir / input_clinical_csv.name
    parse_and_hash_clinical_csv(input_clinical_csv, output_clinical_csv, site_id)


def pipeline(
    site_id: Annotated[
        str,
        typer.Argument(
            help="The SITE-ID provided by the EUCAIM Technical team",
        ),
    ],
    ocr: Annotated[
        bool,
        typer.Option(help="Perform OCR (using Tesseract) and image deidentication"),
    ] = False,
    paddle_ocr: Annotated[
        bool,
        typer.Option(help="Perform OCR using PaddleOCR and image deidentification"),
    ] = False,
    input_dir: Annotated[
        Path,
        typer.Argument(
            help="Input directory to read DICOM files from", show_default=True
        ),
    ] = INPUT_DIR,
    output_dir: Annotated[
        Path,
        typer.Argument(
            help="Output directory to write processed DICOM files to",
            show_default=True,
        ),
    ] = OUTPUT_DIR,
    threads: Annotated[
        int,
        typer.Option(
            help="Number of threads that RSNA CTP will use",
            show_default=True,
        ),
    ] = 2,
):
    pepper = uuid.uuid4().hex  # Create a random string for "pepper"
    input_dir_images = input_dir
    if ocr or paddle_ocr:
        ocr_output_dir = Path(tempfile.mkdtemp())
        perform_ocr(input_dir_images, ocr_output_dir, paddle_ocr)
        input_dir_images = ocr_output_dir
    anon_script = Path(os.getcwd()) / "ctp" / "anon.script"
    run_ctp(
        input_dir=input_dir_images,
        output_dir=output_dir.absolute(),
        anon_script=anon_script,
        site_id=site_id,
        pepper=pepper,
        threads=threads,
    )
    hash_clinical_if_found(input_dir, output_dir, pepper)


if __name__ == "__main__":
    typer.run(pipeline)
