#!/bin/bash
#
# CloudBolt Django 5.2.x / Python 3.12.x Compatibility Check Runner
# 
# This script runs the Python compatibility scanner on customer customizations
# and generates a report of any code that needs to be updated.
#
# The script automatically uses CloudBolt's Python environment - no manual setup needed.
#
# Usage:
#   ./run_compatibility_check.sh [options]
#
# Options:
#   --format <json|html|text>   Output format (default: text)
#   --output <filename>         Output file name
#   --verbose                   Enable verbose output
#   --help                      Show this help message
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
OUTPUT_FORMAT="text"
OUTPUT_FILE=""
VERBOSE=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/django52_python312_compatibility_check.py"

# Output directory
OUTPUT_DIR="/var/tmp"

print_banner() {
    echo -e "${BLUE}"
    echo "============================================================"
    echo " CloudBolt Django 5.2.x / Python 3.12.x Compatibility Check"
    echo "============================================================"
    echo -e "${NC}"
}

print_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --format <json|html|text>   Output format (default: text)"
    echo "  --output <filename>         Output file path (default: /var/tmp/)"
    echo "  --verbose                   Enable verbose output"
    echo "  --help                      Show this help message"
    echo ""
    echo "Output Location: ${OUTPUT_DIR}/"
    echo ""
    echo "Examples:"
    echo "  $0                          # Generate text report in /var/tmp/"
    echo "  $0 --format json            # Generate JSON report in /var/tmp/"
    echo "  $0 --format html            # Generate HTML report in /var/tmp/"
    echo "  $0 --verbose                # Show detailed scanning progress"
    echo ""
    echo "Note: This script automatically uses CloudBolt's Python environment."
}

find_python() {
    # Try CloudBolt's Python first, then system Python
    if [ -x "/opt/cloudbolt/venv/bin/python" ]; then
        echo "/opt/cloudbolt/venv/bin/python"
    elif [ -x "/opt/cloudbolt/venv/bin/python3" ]; then
        echo "/opt/cloudbolt/venv/bin/python3"
    elif command -v python3 &> /dev/null; then
        command -v python3
    elif command -v python &> /dev/null; then
        command -v python
    else
        echo ""
    fi
}

check_requirements() {
    echo -e "${BLUE}Checking requirements...${NC}"
    
    # Check if running as root or cloudbolt user
    if [ "$EUID" -ne 0 ] && [ "$(whoami)" != "cloudbolt" ]; then
        echo -e "${YELLOW}Warning: Running as non-root user. Some files may not be accessible.${NC}"
        echo "For complete scan, run as root or cloudbolt user."
        echo ""
    fi
    
    # Check if the scanner script exists
    if [ ! -f "${PYTHON_SCRIPT}" ]; then
        echo -e "${RED}Error: Scanner script not found at: ${PYTHON_SCRIPT}${NC}"
        exit 1
    fi
    
    # Find Python interpreter
    PYTHON_BIN=$(find_python)
    if [ -z "${PYTHON_BIN}" ]; then
        echo -e "${RED}Error: Python not found. Please install Python 3.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Using Python: ${PYTHON_BIN}${NC}"
    echo ""
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --format)
                OUTPUT_FORMAT="$2"
                shift 2
                ;;
            --output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            --verbose|-v)
                VERBOSE="--verbose"
                shift
                ;;
            --help|-h)
                print_help
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                print_help
                exit 1
                ;;
        esac
    done
    
    # Validate format
    case $OUTPUT_FORMAT in
        json|html|text)
            ;;
        *)
            echo -e "${RED}Invalid format: ${OUTPUT_FORMAT}. Use json, html, or text.${NC}"
            exit 1
            ;;
    esac
}

run_scan() {
    echo -e "${BLUE}Starting compatibility scan...${NC}"
    echo -e "${BLUE}Report output directory: ${OUTPUT_DIR}/${NC}"
    echo ""
    
    # Build command - explicitly use the found Python interpreter
    CMD="${PYTHON_BIN} ${PYTHON_SCRIPT} --output-format ${OUTPUT_FORMAT}"
    
    if [ -n "${OUTPUT_FILE}" ]; then
        CMD="${CMD} --output-file ${OUTPUT_FILE}"
    fi
    
    if [ -n "${VERBOSE}" ]; then
        CMD="${CMD} ${VERBOSE}"
    fi
    
    # Run the scanner
    eval ${CMD}
    EXIT_CODE=$?
    
    return ${EXIT_CODE}
}

print_next_steps() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}                      NEXT STEPS${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
    echo "1. Review the generated report for compatibility issues"
    echo ""
    echo "2. To automatically fix issues, run:"
    echo "   ${SCRIPT_DIR}/run_auto_fix.sh --dry-run"
    echo ""
    echo "3. For assistance, contact CloudBolt Support"
    echo ""
}

# Main execution
main() {
    print_banner
    parse_args "$@"
    check_requirements
    
    if run_scan; then
        echo -e "${GREEN}Scan completed successfully.${NC}"
    else
        echo -e "${YELLOW}Scan completed with warnings.${NC}"
    fi
    
    print_next_steps
}

main "$@"
