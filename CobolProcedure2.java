import java.util.List;
import java.util.ArrayList;

/**
 * Represents a COBOL procedure with business logic details
 */
class CobolProcedure2 {
    private String name;
    private int lineNumber;
    private List<CobolStatement2> statements = new ArrayList<>();
    
    public CobolProcedure2(String name, int lineNumber) {
        this.name = name;
        this.lineNumber = lineNumber;
    }
    
    public String getName() { return name; }
    public int getLineNumber() { return lineNumber; }
    public List<CobolStatement2> getStatements() { return statements; }
    public void addStatement(CobolStatement2 stmt) { statements.add(stmt); }
}

