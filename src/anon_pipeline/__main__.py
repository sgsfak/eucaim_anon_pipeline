import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

import pydicom
import rich
import typer
from loguru import logger
from presidio_image_redactor import DicomImageRedactorEngine
from tqdm import tqdm
from typing_extensions import Annotated

from .dcm_deidentify import run_ctp
from .hash_clinical import parse_and_hash_clinical_csv
from .ocr_deidentify import PADDLE_DEFAULT_CPU_THREADS, perform_ocr

INPUT_DIR: Path = Path("/input")
OUTPUT_DIR: Path = Path("/output")


cli = typer.Typer(add_completion=False)


def hash_clinical_if_found(input_dir: Path, output_dir: Path, site_id: str) -> None:
    # check if there's a CSV in the input folder:
    csvs = list(c for c in input_dir.glob("*.csv") if c.is_file())
    if not csvs:
        logger.warning("No CSV found in input directory")
        return
    input_clinical_csv = csvs[0]
    output_clinical_csv = output_dir / input_clinical_csv.name
    parse_and_hash_clinical_csv(input_clinical_csv, output_clinical_csv, site_id)


@cli.command()
def pipeline(
    site_id: Annotated[
        str,
        typer.Argument(
            help="The SITE-ID provided by the EUCAIM Technical team",
        ),
    ],
    ocr: Annotated[
        bool,
        typer.Option(
            "--ocr", help="Perform OCR (using Tesseract) and image deidentication"
        ),
    ] = False,
    paddle_ocr: Annotated[
        bool,
        typer.Option(
            "--paddle-ocr",
            help="Perform OCR using PaddleOCR and image deidentification",
        ),
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
            help="Number of threads that RSNA CTP and PaddleOCR (if enabled) will use",
            show_default=True,
        ),
    ] = PADDLE_DEFAULT_CPU_THREADS,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging"),
    ] = False,
):
    if paddle_ocr and ocr:
        rich.print(
            "[red][bold]Error:[/bold] Cannot use both PaddleOCR and TesseractOCR: please choose one, use --help for usage information[/red]"
        )
        sys.exit(1)

    pepper = uuid.uuid4().hex  # Create a random string for "pepper"
    input_dir_images = input_dir
    if ocr or paddle_ocr:
        ocr_output_dir = Path(tempfile.mkdtemp())
        perform_ocr(input_dir_images, ocr_output_dir, paddle_ocr, verbose, threads)
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
    cli(prog_name="pipeline")
