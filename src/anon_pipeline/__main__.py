import os
import sys
import tempfile
import uuid
from pathlib import Path

import rich
import typer
from typing_extensions import Annotated

from .dcm_deidentify import run_ctp
from .hash_clinical import hash_clinical_csvs
from .ocr_deidentify import PADDLE_DEFAULT_CPU_THREADS, perform_ocr
from .output_dir import copy_and_organize

INPUT_DIR: Path = Path("/input")
OUTPUT_DIR: Path = Path("/output")


cli = typer.Typer(add_completion=False)


@cli.command()
def pipeline(
    site_id: Annotated[
        str,
        typer.Argument(
            help="The SITE-ID provided by the EUCAIM Technical team",
        ),
    ],
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
    threads: Annotated[
        int,
        typer.Option(
            help="Number of threads that RSNA CTP and PaddleOCR (if enabled) will use",
            show_default=True,
        ),
    ] = PADDLE_DEFAULT_CPU_THREADS,
    hierarchical: Annotated[
        bool,
        typer.Option(
            "--hierarchical/--no-hierarchical",
            help=(
                "Output files will be organized into a hierarchical "
                "Patient / Study / Series folder structure using the anonymized UIDs "
                "as the folder names"
            ),
        ),
    ] = True,
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

    # Step 1: Run OCR if enabled
    input_dir_images = input_dir
    if ocr or paddle_ocr:
        ocr_output_dir = Path(tempfile.mkdtemp())
        perform_ocr(input_dir_images, ocr_output_dir, paddle_ocr, verbose, threads)
        input_dir_images = ocr_output_dir

    # Step 2: Run RSNA CTP
    anon_script = Path(os.getcwd()) / "ctp" / "anon.script"
    ctp_output_dir = Path(tempfile.mkdtemp()) if hierarchical else output_dir.absolute()
    run_ctp(
        input_dir=input_dir_images,
        output_dir=ctp_output_dir,
        anon_script=anon_script,
        site_id=site_id,
        pepper=pepper,
        threads=threads,
    )
    # Step 2.1: Copy and organize files if hierarchical
    if hierarchical:
        copy_and_organize(ctp_output_dir, output_dir)

    # Step 3: Hash any clinical CSVs found in the input directory:
    hash_clinical_csvs(input_dir, output_dir, site_id=pepper, ignore_prefix="_")


if __name__ == "__main__":
    cli(prog_name="pipeline")
