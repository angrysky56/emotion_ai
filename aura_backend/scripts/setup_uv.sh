#!/bin/bash

# Aura Backend Setup Script with UV
# ==================================

set -e # Exit on error

echo "🚀 Aura Backend Setup Script (using UV)"
echo "====================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
	echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
	echo -e "${RED}❌ $1${NC}"
}

print_warning() {
	echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] && [ ! -f "../pyproject.toml" ] && [ ! -f "../../pyproject.toml" ]; then
	print_error "pyproject.toml not found in current, parent, or grandparent directory."
	exit 1
fi

if [ -f "pyproject.toml" ]; then
	ROOT_DIR="."
elif [ -f "../pyproject.toml" ]; then
	ROOT_DIR=".."
else
	ROOT_DIR="../.."
fi

# Check for UV installation
echo "1. Checking for UV installation..."
if ! command -v uv &>/dev/null; then
	print_error "UV is not installed!"
	echo ""
	echo "Please install UV first:"
	echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
	echo ""
	echo "Or with pip:"
	echo "  pip install uv"
	exit 1
fi

UV_VERSION=$(uv --version)
print_status "UV is installed: ${UV_VERSION}"

# Check Python version
echo ""
echo "2. Checking Python version..."
PYTHON_VERSION_RAW=$(python3 --version 2>&1)
PYTHON_VERSION=$(echo "$PYTHON_VERSION_RAW" | awk '{print $2}')
# REQUIRED_VERSION="3.12"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,12) else 1)"; then
	print_error "Python 3.12+ is required. Current version: ${PYTHON_VERSION}"
	exit 1
fi
print_status "Python version: ${PYTHON_VERSION}"

# Create/activate virtual environment with UV
echo ""
echo "3. Setting up virtual environment with UV..."

if [ -d "$ROOT_DIR/.venv" ]; then
	print_warning "Virtual environment already exists in ${ROOT_DIR}. Using existing environment."
else
	print_status "Creating new virtual environment with Python 3.12 in ${ROOT_DIR}..."
	(cd "${ROOT_DIR}" && uv venv --python 3.12 --seed)
fi

# Install dependencies with UV
echo ""
echo "4. Installing dependencies with UV..."
print_status "Installing from pyproject.toml..."

# Use UV to sync dependencies
uv pip sync requirements.txt 2>/dev/null || {
	# If requirements.txt doesn't exist or sync fails, install from pyproject.toml
	print_warning "No requirements.txt found, installing from pyproject.toml..."
	uv pip install -e .
}

# Create necessary directories
echo ""
echo "5. Creating necessary directories..."

directories=(
	"aura_data"
	"aura_data/users"
	"aura_data/exports"
	"aura_data/logs"
	"aura_chroma_db"
	"backups"
)

for dir in "${directories[@]}"; do
	if [ ! -d "$dir" ]; then
		mkdir -p "${dir}"
		print_status "Created ${dir}"
	else
		print_warning "${dir} already exists"
	fi
done

# Setup environment file
echo ""
echo "6. Setting up environment configuration..."

if [ ! -f ".env" ]; then
	if [ -f ".env.example" ]; then
		cp .env.example .env
		print_status "Created .env from .env.example"
		print_warning "Please edit .env and add your GOOGLE_API_KEY"
	else
		print_error ".env.example not found. Creating basic .env file..."
		cat >.env <<EOL
# Aura Backend Configuration
GOOGLE_API_KEY=your_google_api_key_here
HOST=0.0.0.0
PORT=8000

# Database Configuration
CHROMA_PERSIST_DIRECTORY=./aura_chroma_db
AURA_DATA_DIRECTORY=./aura_data

# Model Configuration
AURA_MODEL=gemini-2.0-flash-exp-0827
AURA_MAX_OUTPUT_TOKENS=8192

# Features
ENABLE_EMOTIONAL_ANALYSIS=true
ENABLE_COGNITIVE_TRACKING=true
ENABLE_VECTOR_SEARCH=true
EOL
		print_status "Created basic .env file"
		print_warning "Please edit .env and add your GOOGLE_API_KEY"
	fi
else
	print_warning ".env already exists"
fi

# Generate requirements.txt from pyproject.toml for compatibility
echo ""
echo "7. Generating requirements.txt for compatibility..."
uv pip compile pyproject.toml -o requirements.txt
print_status "Generated requirements.txt"

# Make scripts executable
echo ""
echo "8. Making scripts executable..."

scripts=(
	"start.sh"
	"test_setup.py"
	"test_parameter_fix.py"
	"test_mcp_brave_fix.py"
)

for script in "${scripts[@]}"; do
	if [ -f "$script" ]; then
		chmod +x "${script}"
		print_status "Made ${script} executable"
	fi
done

# Create activation helper
echo ""
echo "9. Creating activation helper..."

cat >activate_env.sh <<'EOL'
#!/bin/bash
# Aura Backend Environment Activation Helper

if [ -f "$ROOT_DIR/.venv/bin/activate" ]; then
    source "$ROOT_DIR/.venv/bin/activate"
    echo "✅ Virtual environment activated"
    echo "Python: $(which python)"
    echo "Version: $(python --version)"
else
    echo "❌ Virtual environment not found. Run setup_uv.sh first."
fi
EOL

chmod +x activate_env.sh
print_status "Created activate_env.sh"

# Summary
echo ""
echo "====================================="
echo "✅ Setup Complete!"
echo "====================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source ${ROOT_DIR}/.venv/bin/activate"
echo "   (or use: ./activate_env.sh)"
echo ""
echo "2. Configure your environment:"
echo "   nano .env"
echo "   Add your GOOGLE_API_KEY"
echo ""
echo "3. Test the installation:"
echo "   python test_setup.py"
echo ""
echo "4. Start the backend:"
echo "   ./start.sh"
echo ""
echo "5. Test parameter handling fix:"
echo "   python test_parameter_fix.py"
echo ""
echo "For more information, see README.md"
echo ""

# Check if GOOGLE_API_KEY is set
if [ -f ".env" ]; then
	if grep -q "your_google_api_key_here" .env || grep -q "your_actual_api_key_here" .env; then
		print_warning "Don't forget to add your GOOGLE_API_KEY to .env!"
	fi
fi
