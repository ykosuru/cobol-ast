public class CobolCopybook {
    private String name;
    private String library;
    private String replacingClause;
    private String sourceLocation;
    private CopybookType type;

    public CobolCopybook(String name) {
        this.name = name;
    }

    public enum CopybookType {
        DATA_STRUCTURE,
        PROCEDURE_CODE,
        CONSTANTS,
        UNKNOWN
    }

    public String getName() { return name; }
    public String getLibrary() { return library; }
    public void setLibrary(String library) { this.library = library; }
    public String getReplacingClause() { return replacingClause; }
    public void setReplacingClause(String replacingClause) { this.replacingClause = replacingClause; }
    public String getSourceLocation() { return sourceLocation; }
    public void setSourceLocation(String sourceLocation) { this.sourceLocation = sourceLocation; }
    public CopybookType getType() { return type; }
    public void setType(CopybookType type) { this.type = type; }
}
