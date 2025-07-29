#!/bin/bash

# Script to generate architecture diagrams from Mermaid markdown files

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    print_error "npm is not installed. Please install Node.js and npm first."
    exit 1
fi

# Navigate to the architecture-diagram directory
cd "$(dirname "$0")"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    print_status "Installing mermaid-cli and dependencies..."
    npm install
fi

# Generate diagrams
print_status "Generating architecture diagrams..."

# Generate SVG
print_status "Generating SVG format..."
npx mmdc -i architecture-diagram-v0.3.2.rc2.md \
         -o architecture-diagram-v0.3.2.rc2.svg \
         -c mermaid.config.json \
         --width 2400 \
         --height 1800

# Generate PNG
print_status "Generating PNG format..."
npx mmdc -i architecture-diagram-v0.3.2.rc2.md \
         -o architecture-diagram-v0.3.2.rc2.png \
         -c mermaid.config.json \
         --width 2400 \
         --height 1800 \
         --scale 2

print_status "✅ Architecture diagrams generated successfully!"
print_status "Files created:"
echo "  - architecture-diagram-v0.3.2.rc2.svg"
echo "  - architecture-diagram-v0.3.2.rc2.png"