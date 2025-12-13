#!/usr/bin/env python3
"""
PDFPowerExtractor - Preserve visual form field relationships in PDF extraction
"""

import os
import sys
from typing import List, Optional
import re
import click
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add core modules to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .core.processor import PDFProcessor
from .core.analyzer import PDFAnalyzer
from .models.config import MODEL_CONFIGS, DEFAULT_MODEL

@click.group()
@click.version_option(version='1.0.0')
def cli():
    """PDFPowerExtractor - AI-readable PDF form extraction"""
    pass

def parse_pages_parameter(pages_str: str) -> List[int]:
    """Parse pages parameter string into list of page numbers"""
    page_numbers = []
    
    # Split by commas to handle multiple ranges/individual pages
    parts = [part.strip() for part in pages_str.split(',') if part.strip()]
    
    for part in parts:
        if '-' in part:  # Handle ranges like "2-7"
            range_parts = part.split('-')
            if len(range_parts) != 2:
                raise click.BadParameter(f"Invalid page range: {part}. Use format like '2-7'")
            
            try:
                start = int(range_parts[0])
                end = int(range_parts[1])
                if start <= 0 or end <= 0:
                    raise click.BadParameter("Page numbers must be positive integers (1 or greater)")
                if start > end:
                    raise click.BadParameter(f"Invalid range: start ({start}) > end ({end})")
                
                # Add all pages in range
                page_numbers.extend(range(start, end + 1))
            except ValueError:
                raise click.BadParameter(f"Invalid page number in range: {part}")
        else:  # Handle individual pages
            try:
                page_num = int(part)
                if page_num <= 0:
                    raise click.BadParameter("Page numbers must be positive integers (1 or greater)")
                page_numbers.append(page_num)
            except ValueError:
                raise click.BadParameter(f"Invalid page number: {part}")
    
    # Remove duplicates and sort
    page_numbers = sorted(list(set(page_numbers)))
    return page_numbers

@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file path (default: auto-generated)')
@click.option('--model', '-m', default=DEFAULT_MODEL, help='AI model to use')
@click.option('--force', '-f', is_flag=True, help='Force regeneration even if cached')
@click.option('--pages', help='Pages to extract (e.g., "1,3,5" or "2-7" or "1,3-5,8")')
@click.option('--debug-save-images', is_flag=True, help='Save converted images to /tmp/powerpdf_extracted_images/ for debugging')
def extract(pdf_path, output, model, force, pages, debug_save_images):
    """Extract text from PDF preserving form field relationships"""
    
    # Check if model is supported
    if model not in MODEL_CONFIGS:
        click.echo(f"❌ Error: Model '{model}' not supported")
        click.echo(f"Supported models: {', '.join(MODEL_CONFIGS.keys())}")
        sys.exit(1)

    # Get model config to check required API key
    from .models.config import get_model_config
    model_config = get_model_config(model)
    endpoint = model_config.get_endpoint()
    api_key = os.getenv(endpoint.api_key_env_var)

    if not api_key:
        click.echo(f"❌ Error: {endpoint.api_key_env_var} environment variable not set")
        click.echo(f"Please set it with: export {endpoint.api_key_env_var}='your-key-here'")
        click.echo(f"Get your API key from: {endpoint.name}")
        sys.exit(1)
    
    click.echo(f"📄 Processing: {os.path.basename(pdf_path)}")
    click.echo(f"🤖 Using model: {model}")

    # Parse pages parameter if provided
    selected_pages = None
    if pages:
        try:
            selected_pages = parse_pages_parameter(pages)
            click.echo(f"📄 Processing specific pages: {pages}")
        except click.BadParameter as e:
            click.echo(f"❌ Error: {str(e)}")
            sys.exit(1)

    try:
        # Create extraction config with selected model
        from .core.config import ExtractionConfig
        config = ExtractionConfig(model_config_id=model)

        processor = PDFProcessor(pdf_path, config=config, api_key=api_key)

        audit_log_path = os.getenv("PDFPOWER_AUDIT_LOG")
        audit_retention_env = os.getenv("PDFPOWER_AUDIT_RETENTION_HOURS")
        audit_retention = int(audit_retention_env) if audit_retention_env else 24

         # Process the PDF
        with click.progressbar(length=100, label='Processing') as bar:
            result = processor.process(
                progress_callback=lambda p: bar.update(p - bar.pos),
                debug_save_images=debug_save_images,
                audit_log_path=audit_log_path,
                audit_retention_hours=audit_retention if audit_log_path else None,
                selected_pages=selected_pages,
            )
        
        # Save results
        if not output:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output = f"extracted-{timestamp}.txt"
        
        processor.save_results(result, output)
        
        # Show summary
        click.echo(f"\n✅ Extraction complete!")
        click.echo(f"📊 Cost: ${processor.last_cost:.4f}")
        click.echo(f"⏱️  Time: {processor.last_duration:.1f}s")
        click.echo(f"💾 Saved to: {output}")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)

@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True))
def analyze(pdf_path):
    """Analyze PDF to show page types and potential savings"""
    
    click.echo(f"🔍 Analyzing: {os.path.basename(pdf_path)}")
    
    try:
        analyzer = PDFAnalyzer(pdf_path)
        summary = analyzer.analyze()
        
        click.echo("\n📊 Analysis Results:")
        click.echo(f"Total pages: {summary['total_pages']}")
        click.echo(f"Pure text pages: {len(summary['text_pages'])} ({summary['text_percentage']:.1f}%)")
        click.echo(f"Form field pages: {len(summary['form_pages'])} ({summary['form_percentage']:.1f}%)")
        click.echo(f"Empty pages: {len(summary['empty_pages'])}")
        
        click.echo(f"\n💰 Cost Estimates (using {DEFAULT_MODEL}):")
        click.echo(f"Full AI processing: ${summary['full_ai_cost']:.4f}")
        click.echo(f"Hybrid processing: ${summary['hybrid_cost']:.4f}")
        click.echo(f"Potential savings: ${summary['savings']:.4f} ({summary['savings_percentage']:.1f}%)")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)

@cli.command()
def models():
    """List supported AI models and their costs"""

    click.echo("🤖 Supported Models:\n")

    for model_id, config in MODEL_CONFIGS.items():
        status = "✅" if config.accuracy == 100 else "⚠️"
        click.echo(f"{status} {model_id}")
        click.echo(f"   Name: {config.name}")
        click.echo(f"   Cost: ${config.pricing.input_cost_per_1m:.2f}/1M input, ${config.pricing.output_cost_per_1m:.2f}/1M output")
        click.echo(f"   Accuracy: {config.accuracy}%")
        click.echo(f"   Context: {config.context_window}")
        click.echo(f"   Notes: {config.notes}")
        click.echo()

if __name__ == '__main__':
    cli()
