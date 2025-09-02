import json
import os
import sys
import click
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from cyberhunter_3d.core.scan_manager import run_url_discovery_phase
from cyberhunter_3d.core.reconnaissance.utils import load_config
from cyberhunter_3d.utils.logger import setup_logger
from cyberhunter_3d.reporting.r2_uploader import upload_to_r2
from cyberhunter_3d.utils.file_utils import get_results_dir
from cyberhunter_3d.core.session_closure import SessionCloser

@click.command()
@click.option("-d", "--domain", required=True, help="The target domain for reconnaissance.")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output.")
@click.option("--upload-to-r2", is_flag=True, help="Upload results to Cloudflare R2.")
@click.option("--save-to-db", is_flag=True, help="Save the scan results to the database.")
@click.option("--previous-scan-dir", help="Path to the previous scan's output directory for delta detection.")
@click.option("--url-discovery", is_flag=True, help="Run the URL discovery and vulnerability scanning phase.")
@click.option("--generate-report", is_flag=True, help="Generate a PDF report after the scan.")
@click.option("--keep-temp-files", is_flag=True, help="Keep temporary files after the scan.")
def main(domain, verbose, upload_to_r2, save_to_db, previous_scan_dir, url_discovery, generate_report, keep_temp_files):
    """
    Main function to run the CyberHunter 3D reconnaissance V3 pipeline.
    """
    log_level = 'DEBUG' if verbose else 'INFO'
    logger = setup_logger('main.log', level=log_level)
    logger.info("--- Welcome to CyberHunter 3D - Reconnaissance Module (V3) ---")

    from run_web import create_app
    from cyberhunter_3d.web.models import db, Scan, Target
    app = create_app()
    exit_code = 0
    scan_id = None
    with app.app_context():
        target = Target(value=domain, type='domain')
        scan = Scan(status='RUNNING', user_id=1)
        scan.targets.append(target)
        db.session.add(target)
        db.session.add(scan)
        db.session.commit()
        scan_id = scan.id

    try:
        if url_discovery:
            logger.info(f"Starting URL discovery for: {domain}")
            run_url_discovery_phase(scan_id, app)
            logger.info("URL discovery finished.")
        else:
            logger.info(f"Starting V3 reconnaissance pipeline for: {domain}")
            output_paths, _, _ = enumerate_subdomains_v2(
                domain=domain,
                scan_id=scan_id,
                app=app
            )
            if not output_paths:
                logger.error("Reconnaissance pipeline did not produce any output.")
                raise RuntimeError("Reconnaissance pipeline failed.")
            logger.info(f"Reconnaissance complete for {domain}.")

        if generate_report:
            from cyberhunter_3d.reporting.pdf_generator import generate_pdf_report
            logger.info("Generating PDF report...")
            generate_pdf_report(scan_id, domain, app)

    except Exception as e:
        logger.error(f"An error occurred during the scan: {e}", exc_info=True)
        exit_code = 1
        with app.app_context():
            scan = Scan.query.get(scan_id)
            if scan:
                scan.status = 'FAILED'
                scan.results = f"Scan failed with error: {e}"
                db.session.commit()
    finally:
        if scan_id:
            logger.info("--- Initiating Session Closure ---")
            session_closer = SessionCloser(
                scan_id=scan_id,
                app=app,
                domain=domain,
                output_paths=output_paths if 'output_paths' in locals() else {},
                should_upload_to_r2=upload_to_r2,
                keep_temp_files=keep_temp_files
            )
            session_closer.finalize_session()

        logger.info("--- Pipeline Finished ---")


if __name__ == "__main__":
    main()
