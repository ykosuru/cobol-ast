/**
     * Simple procedure boundary class
     */
    class ProcedureBoundary {
        private String name;
        private int startLine;
        
        public ProcedureBoundary(String name, int startLine) {
            this.name = name;
            this.startLine = startLine;
        }
        
        public String getName() { return name; }
        public int getStartLine() { return startLine; }
    }

