import os
from pathlib import Path

import pydicom
import typer
from loguru import logger
from presidio_image_redactor import DicomImageRedactorEngine
from typing_extensions import Annotated

from deidentify import run_ctp

INPUT_DIR: Path = Path("/input")
OUTPUT_DIR: Path = Path("/output")


def perform_ocr(input_dir: Path, output_dir: Path) -> None:
    engine = DicomImageRedactorEngine()
    output_dir = Path(output_dir)
    logger.info("Starting OCR pipeline, output will be saved to {}".format(output_dir))
    for file_path in Path(input_dir).rglob("*.dcm"):
        dicom_data = pydicom.dcmread(file_path)
        redacted_data = engine.redact(dicom_data, fill="contrast")
        output_path = output_dir / file_path.relative_to(input_dir)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        redacted_data.save_as(output_path)
        logger.info(f"Redacted {file_path.relative_to(input_dir)}")


def pipeline(
    site_id: Annotated[
        str,
        typer.Argument(
            help="The SITE-ID provided by the EUCAIM Technical team",
        ),
    ],
    ocr: Annotated[
        bool, typer.Option(help="Perform OCR and image deidentication")
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
    input_dir_images = input_dir
    if ocr:
        ocr_output_dir = output_dir / ".ocr_output"
        ocr_output_dir.mkdir(parents=True, exist_ok=True)
        perform_ocr(input_dir_images, ocr_output_dir)
        input_dir_images = ocr_output_dir
    anon_script = Path(os.getcwd()) / "ctp" / "anon.script"
    run_ctp(
        input_dir=input_dir_images,
        output_dir=output_dir.absolute(),
        anon_script=anon_script,
        site_id=site_id,
        threads=threads,
    )


if __name__ == "__main__":
    typer.run(pipeline)
