#!/bin/bash
# Install all required dependencies for BalanceIQ backend

echo "Installing Python dependencies..."

# Core dependencies
pip install snowflake-connector-python
pip install python-dotenv
pip install dedalus-labs

# FastAPI and dependencies (for API testing)
pip install fastapi
pip install uvicorn[standard]

# Additional dependencies
pip install pydantic

echo "✅ All dependencies installed!"
echo ""
echo "Next steps:"
echo "1. Create database/api/.env with your Snowflake credentials"
echo "2. Follow TESTING_GUIDE.md for deployment steps"
