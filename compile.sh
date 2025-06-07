#!/bin/bash
# build.sh - Build script for Cobol parser
rm *.class
rm -fr __pycache__
rm -f *.class *.tokens CobolPreprocessorL*.* *.interp *.tokens


# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building Cobol Preprocessor ...${NC}"

# Check if ANTLR jar exists
ANTLR_JAR="antlr-4.13.2-complete.jar"
if [ ! -f "$ANTLR_JAR" ]; then
    echo -e "${RED}Error: $ANTLR_JAR not found!${NC}"
    echo "Download it from: https://www.antlr.org/download.html"
    exit 1
fi

# Set classpath
export CLASSPATH=".:$ANTLR_JAR:$CLASSPATH"

echo -e "${YELLOW}Step 1: Generating ANTLR parser files...${NC}"
java -jar $ANTLR_JAR -Dlanguage=Java -visitor CobolPreprocessor.g4
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: ANTLR generation failed!${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 2: Compiling Java classes ...${NC}"
javac -cp .:$ANTLR_JAR *.java

echo -e "${GREEN}Build successful!${NC}"
echo ""
echo "Usage examples:"
echo "  python3 talTranspiler.py <input tal> ast"


echo -e "${GREEN}Created run.sh convenience script${NC}"
echo ""
echo "Quick test:"
echo "./run.sh sample.cbl out.cbl"
