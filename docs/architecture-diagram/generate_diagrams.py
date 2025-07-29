#!/usr/bin/env python3
"""
Generate architecture diagrams from Mermaid markdown files.

This script provides a Python interface to generate diagrams,
useful for integration with the build process.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Optional

def check_npm_installed() -> bool:
    """Check if npm is installed."""
    try:
        subprocess.run(["npm", "--version"], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_dependencies(diagram_dir: Path) -> bool:
    """Install npm dependencies if needed."""
    node_modules = diagram_dir / "node_modules"
    if not node_modules.exists():
        print("Installing mermaid-cli and dependencies...")
        try:
            subprocess.run(["npm", "install"], 
                          cwd=diagram_dir, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install dependencies: {e}")
            return False
    return True

def generate_diagram(
    input_file: str,
    output_formats: Optional[List[str]] = None,
    config_file: str = "mermaid.config.json",
    width: int = 2400,
    height: int = 1800
) -> bool:
    """
    Generate diagram from Mermaid markdown file.
    
    Args:
        input_file: Path to the Mermaid markdown file
        output_formats: List of output formats (svg, png, pdf)
        config_file: Path to mermaid configuration file
        width: Width of the diagram
        height: Height of the diagram
    
    Returns:
        True if successful, False otherwise
    """
    if output_formats is None:
        output_formats = ["svg", "png"]
    
    diagram_dir = Path(__file__).parent
    input_path = diagram_dir / input_file
    
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return False
    
    success = True
    for format in output_formats:
        output_file = input_path.stem + f".{format}"
        output_path = diagram_dir / output_file
        
        print(f"Generating {format.upper()} format...")
        
        cmd = [
            "npx", "mmdc",
            "-i", str(input_path),
            "-o", str(output_path),
            "-c", config_file,
            "--width", str(width),
            "--height", str(height)
        ]
        
        if format == "png":
            cmd.extend(["--scale", "2"])
        
        try:
            subprocess.run(cmd, cwd=diagram_dir, check=True)
            print(f"✅ Generated: {output_file}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to generate {format}: {e}")
            success = False
    
    return success

def main():
    """Main function."""
    if not check_npm_installed():
        print("Error: npm is not installed. Please install Node.js and npm.")
        sys.exit(1)
    
    diagram_dir = Path(__file__).parent
    
    if not install_dependencies(diagram_dir):
        sys.exit(1)
    
    # Generate the main architecture diagram
    success = generate_diagram(
        "architecture-diagram-v0.3.2.rc2.md",
        output_formats=["svg", "png"]
    )
    
    if success:
        print("\n✅ All architecture diagrams generated successfully!")
    else:
        print("\n❌ Some diagrams failed to generate.")
        sys.exit(1)

if __name__ == "__main__":
    main()