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

from deidentify import run_ctp
from hash_clinical import parse_and_hash_clinical_csv
from paddle_ocr import PADDLE_DEFAULT_CPU_THREADS, PresidioPaddleOCR

INPUT_DIR: Path = Path("/input")
OUTPUT_DIR: Path = Path("/output")


cli = typer.Typer(add_completion=False)


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
            file_path,
            str(output_path_dir),
            fill="contrast",
            use_metadata=True,
            save_bboxes=False,
            verbose=False,
        )
        cnt += 1
    time_end = time.time()
    logger.info(f"Redacted {cnt} files in {time_end - time_start:.3f} seconds")


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
