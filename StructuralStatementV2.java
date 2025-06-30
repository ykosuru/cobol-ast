/*
 * Author: Yekesa Kosuru
 */
import java.util.List;

class StructuralStatementV2 
{
    private String type;
    private String content;
    private int lineNumber;
    private List<String> accessedDataItems;
    private List<String> accessedFiles;
    private String sqlTable;
    private String performTarget;
    
    // Basic getters and setters
    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
    
    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }
    
    public int getLineNumber() { return lineNumber; }
    public void setLineNumber(int lineNumber) { this.lineNumber = lineNumber; }
    
    // Business logic getters and setters
    public List<String> getAccessedDataItems() { return accessedDataItems; }
    public void setAccessedDataItems(List<String> accessedDataItems) { 
        this.accessedDataItems = accessedDataItems; 
    }
    
    public List<String> getAccessedFiles() { return accessedFiles; }
    public void setAccessedFiles(List<String> accessedFiles) { 
        this.accessedFiles = accessedFiles; 
    }
    
    public String getSqlTable() { return sqlTable; }
    public void setSqlTable(String sqlTable) { this.sqlTable = sqlTable; }
    
    public String getPerformTarget() { return performTarget; }
    public void setPerformTarget(String performTarget) { 
        this.performTarget = performTarget; 
    }
}
