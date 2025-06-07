#!/bin/bash
# Convenience script to run Cobol parser

ANTLR_JAR="antlr-4.13.2-complete.jar"
export CLASSPATH=".:$ANTLR_JAR:$CLASSPATH"

if [ $# -eq 0 ]; then
    echo "Usage: ./run.sh [options] <tal-file>"
    echo "Options:"
    echo "  -gui      Show parse tree in GUI"
    echo "  -tree     Print parse tree"
    echo "  -tokens   Show token stream"
    echo "  -verbose  Verbose output"
    echo ""
    echo "Examples:"
    echo "  ./run.sh sample.cbl"
    echo "  ./run.sh -gui sample.cbl"
    echo "  ./run.sh -tree -tokens sample.cbl"
else
    #python3 talTranspiler.py "$@"
    java -cp ".:$ANTLR_JAR" Driver "$@"
fi
