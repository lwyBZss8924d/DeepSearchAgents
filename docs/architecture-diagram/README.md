# Architecture Diagram Generation

This directory contains the tools and scripts for generating DeepSearchAgents architecture diagrams from Mermaid markdown files.

## Prerequisites

- Node.js and npm installed
- Python 3.x (for Python script integration)

## Setup

Install the required dependencies:

```bash
npm install
```

## Usage

### Using npm scripts

```bash
# Generate both SVG and PNG formats
npm run generate:all

# Generate only SVG
npm run generate

# Generate only PNG
npm run generate:png

# Watch for changes and auto-regenerate
npm run watch
```

### Using shell script

```bash
./generate-diagrams.sh
```

### Using Python script

```bash
python generate_diagrams.py
```

### Using Makefile (from project root)

```bash
make diagrams
make diagrams-watch
```

## Configuration

The Mermaid configuration is stored in `mermaid.config.json`. You can modify:
- Theme and colors
- Diagram dimensions
- Flowchart settings

## Adding New Diagrams

1. Create a new `.md` file with Mermaid code
2. Update the scripts to include the new diagram
3. Run the generation scripts

## Troubleshooting

If you encounter issues:
1. Ensure npm is installed: `npm --version`
2. Clear node_modules and reinstall: `rm -rf node_modules && npm install`
3. Check that the Mermaid syntax is valid in your `.md` files