import java.util.List;
import java.util.ArrayList;


/**
 * Represents a COBOL statement with business logic details
 */
class CobolStatement2 {
    private String type;
    private String content;
    private int lineNumber;
    private List<String> accessedDataItems;
    private List<String> accessedFiles;
    private String sqlTable;
    private String performTarget;
    
    public CobolStatement2(String type, String content, int lineNumber) {
        this.type = type;
        this.content = content;
        this.lineNumber = lineNumber;
        this.accessedDataItems = new ArrayList<>();
        this.accessedFiles = new ArrayList<>();
        this.sqlTable = null;
        this.performTarget = null;
    }
    
    public CobolStatement2(String type, String content, int lineNumber, 
                         List<String> accessedDataItems, List<String> accessedFiles,
                         String sqlTable, String performTarget) {
        this.type = type;
        this.content = content;
        this.lineNumber = lineNumber;
        this.accessedDataItems = accessedDataItems;
        this.accessedFiles = accessedFiles;
        this.sqlTable = sqlTable;
        this.performTarget = performTarget;
    }
    
    public String getType() { return type; }
    public String getContent() { return content; }
    public int getLineNumber() { return lineNumber; }
    public List<String> getAccessedDataItems() { return accessedDataItems; }
    public List<String> getAccessedFiles() { return accessedFiles; }
    public String getSqlTable() { return sqlTable; }
    public String getPerformTarget() { return performTarget; }
    public void setSqlTable(String sqlTable) { this.sqlTable = sqlTable; }
    
}
