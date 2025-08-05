#!/usr/bin/env python3
"""
PDFPowerExtractor - Preserve visual form field relationships in PDF extraction
"""

import os
import sys
import click
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add core modules to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.processor import HybridPDFProcessor
from core.analyzer import PDFAnalyzer
from models.config import MODEL_CONFIGS, DEFAULT_MODEL

@click.group()
@click.version_option(version='1.0.0')
def cli():
    """PDFPowerExtractor - AI-readable PDF form extraction"""
    pass

@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file path (default: auto-generated)')
@click.option('--model', '-m', default=DEFAULT_MODEL, help='AI model to use')
@click.option('--force', '-f', is_flag=True, help='Force regeneration even if cached')
def extract(pdf_path, output, model, force):
    """Extract text from PDF preserving form field relationships"""
    
    # Check API key
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        click.echo("❌ Error: OPENROUTER_API_KEY environment variable not set")
        click.echo("Please set it with: export OPENROUTER_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Check if model is supported
    if model not in MODEL_CONFIGS:
        click.echo(f"❌ Error: Model '{model}' not supported")
        click.echo(f"Supported models: {', '.join(MODEL_CONFIGS.keys())}")
        sys.exit(1)
    
    click.echo(f"📄 Processing: {os.path.basename(pdf_path)}")
    click.echo(f"🤖 Using model: {model}")
    
    try:
        processor = HybridPDFProcessor(pdf_path, api_key)
        
        # Check for cached extraction
        if not force:
            existing = processor.check_existing_extraction()
            if existing:
                click.echo(f"✅ Found cached extraction: {existing}")
                click.echo("Use --force to regenerate")
                return
        
        # Process the PDF
        with click.progressbar(length=100, label='Processing') as bar:
            result = processor.process(
                model=model,
                progress_callback=lambda p: bar.update(p - bar.pos)
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
        status = "✅" if config['accuracy'] == 100 else "⚠️"
        click.echo(f"{status} {model_id}")
        click.echo(f"   Name: {config['name']}")
        click.echo(f"   Cost: ${config['cost_per_page']:.5f}/page")
        click.echo(f"   Accuracy: {config['accuracy']}%")
        click.echo(f"   Context: {config['context_window']}")
        click.echo()

if __name__ == '__main__':
    cli()