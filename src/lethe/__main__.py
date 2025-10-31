import os
import sys
import tempfile
import textwrap
from itertools import groupby
from operator import attrgetter
from pathlib import Path

import rich
import typer
import uuid7
from loguru import logger
from rich.console import Console
from rich.table import Table
from stdnum import luhn
from typing_extensions import Annotated

from .dcm_deidentify import run_ctp
from .defaults import (
    DEFAULT_CPU_THREADS,
    DEFAULT_IGNORE_CSV_PREFIX,
    DEFAULT_PATIENT_ID_PREFIX,
    DEFAULT_STUDIES_METADATA_CSV,
    DEFAULT_UIDROOT,
)
from .dicom_utils import series_information
from .hash_clinical import hash_clinical_csvs
from .ocr_deidentify import perform_ocr
from .output_dir import copy_and_organize
from .version import __version__

INPUT_DIR: Path = Path("/input")
OUTPUT_DIR: Path = Path("/output")


cli = typer.Typer(add_completion=False)
utils_cli = typer.Typer()
cli.add_typer(utils_cli, name="utils", help="Additional utilities")

# Remove default handler
logger.remove()

# Add my own handler with a custom format (no {name})
logger.add(
    sink=sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
    "| <level>{level: <8}</level> | "
    "{function}:{line} - <level>{message}</level>",
)


def _create_secret_key() -> str:
    u = uuid7.create().hex
    d = luhn.calc_check_digit(u, alphabet="0123456789abcdef")
    return f"{u}{d}"


def _valid_secret_key(secret_key: str) -> bool:
    if len(secret_key) != 33:
        return False
    return luhn.is_valid(secret_key, alphabet="0123456789abcdef")


def _header_info() -> str:
    return textwrap.dedent(
        f"""
    ██╗     ███████╗████████╗██╗  ██╗███████╗
    ██║     ██╔════╝╚══██╔══╝██║  ██║██╔════╝
    ██║     █████╗     ██║   ███████║█████╗
    ██║     ██╔══╝     ██║   ██╔══██║██╔══╝
    ███████╗███████╗   ██║   ██║  ██║███████╗
    ╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝
    Version: {__version__}
    "Lethe" DICOM Anonymization Tool, by CBML, FORTH-ICS
    Licensed under the EUPL v1.2
    Provided "as is" without warranty. Use at your own risk.

    """,
    )


def version_callback(value: bool):
    console = Console()
    if value:
        console.print(_header_info(), justify="left")
        console.print("Default settings", style="bold underline", justify="left")
        console.print(f"UID root: {DEFAULT_UIDROOT}")
        console.print(f"Patient ID prefix: {DEFAULT_PATIENT_ID_PREFIX}")
        console.print(f"Studies metadata CSV: {DEFAULT_STUDIES_METADATA_CSV}")
        console.print(f"Ignore CSV prefix: {DEFAULT_IGNORE_CSV_PREFIX}")
        console.print(f"CPU threads: {DEFAULT_CPU_THREADS}")
        raise typer.Exit()


@utils_cli.command(help="Create a new 'secret' key to use for anonymization")
def secret():
    secret = _create_secret_key()
    console = Console()
    console.print(f"[bold][magenta]{secret}[/]")


@utils_cli.command(
    help="Extract and print the unique Series descriptions from input DICOM files"
)
def series_info(
    input_dir: Annotated[
        Path,
        typer.Argument(
            help="Input directory to read DICOM files from", show_default=True
        ),
    ] = INPUT_DIR,
):
    key = attrgetter("series_description")
    console = Console()

    table = Table(title="Series information (Series are grouped by their descriptions)")

    table.add_column("Series Description", justify="left", style="bold", no_wrap=True)
    table.add_column("Modalities", style="magenta")
    table.add_column("Studies count")
    table.add_column("Patients count")
    table.add_column("Series count", style="green")

    series_info = sorted(series_information(input_dir), key=key)
    pids = set(i.patient_id for i in series_info)
    studies = set((i.patient_id, i.study_uid) for i in series_info)
    total_count = 0
    for descr, g in groupby(series_info, key):
        infos = list(g)
        total_count += len(infos)
        modalities = set(i.modality for i in infos)
        pids_cnt = len(set(i.patient_id for i in infos))
        studies_cnt = len(set((i.patient_id, i.study_uid) for i in infos))
        table.add_row(
            descr,
            ",".join(modalities),
            f"{studies_cnt}",
            f"{pids_cnt}",
            f"{len(infos)}",
        )
    console.print()
    console.print(table)
    console.print(f"Total count of Series: {total_count}", style="bold")
    console.print(f"Total count of Studies: {len(studies)}", style="bold")
    console.print(f"Total count of Patients: {len(pids)}", style="bold")


@cli.command(help="Run the DICOM anonymization pipeline")
def run(
    ctx: typer.Context,
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
    dcm_deintify: Annotated[
        bool,
        typer.Option(
            "--ctp/--no-ctp",
            help=(
                "Perform deidentification in the DICOM metadata in image files. "
                "Uses the RSNA CTP anonymizer and the custom script"
            ),
        ),
    ] = True,
    ocr: Annotated[
        bool,
        typer.Option("--ocr", help="Perform OCR (using Tesseract OCR)"),
    ] = False,
    paddle_ocr: Annotated[
        bool,
        typer.Option(
            "--paddle-ocr",
            help="Perform OCR using PaddleOCR",
        ),
    ] = False,
    threads: Annotated[
        int,
        typer.Option(
            help="Number of threads that RSNA CTP and PaddleOCR (if enabled) will use",
            show_default=True,
        ),
    ] = DEFAULT_CPU_THREADS,
    pepper: Annotated[
        str | None,
        typer.Option(
            "--secret",
            help="Use the supplied key as the secret key for the anonymization",
        ),
    ] = None,
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
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Print version information",
        ),
    ] = None,
):
    print(vars(ctx))
    return
    if paddle_ocr and ocr:
        rich.print(
            "[red][bold]Error:[/bold] Cannot use both PaddleOCR and TesseractOCR: please choose one, use --help for usage information[/red]"
        )
        sys.exit(1)

    if not pepper:
        pepper = _create_secret_key()  # Create a time based (UUIDv7) string as secret
    elif not _valid_secret_key(pepper):
        rich.print("[red][bold]Error:[/bold] Invalid secret key[/red]")
        sys.exit(1)

    rich.print(_header_info())
    if verbose:
        logger.debug(f"Using secret key: {pepper}")
    # Step 1: Run OCR if enabled
    input_dir_images = input_dir
    if ocr or paddle_ocr:
        ocr_output_dir = Path(tempfile.mkdtemp())
        perform_ocr(input_dir_images, ocr_output_dir, paddle_ocr, verbose, threads)
        input_dir_images = ocr_output_dir

    # Step 2: Run RSNA CTP
    if dcm_deintify:
        anon_script = Path(os.getcwd()) / "ctp" / "anon.script"
        ctp_output_dir = (
            Path(tempfile.mkdtemp()) if hierarchical else output_dir.absolute()
        )
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
    hash_clinical_csvs(input_dir, output_dir, secret_key=pepper, verbose=verbose)


if __name__ == "__main__":
    cli(prog_name="")
