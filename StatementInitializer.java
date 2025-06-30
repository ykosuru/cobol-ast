/**
 * Statement Initializer Utility
 * Ensures all StructuralStatementV2 objects have properly initialized fields
 */

import java.util.*;

public class StatementInitializer {
    
    /**
     * Initialize business logic fields for a StructuralStatementV2 object
     */
    public static void initializeStatement(StructuralStatementV2 statement) {
        if (statement.getAccessedDataItems() == null) {
            statement.setAccessedDataItems(new ArrayList<>());
        }
        if (statement.getAccessedFiles() == null) {
            statement.setAccessedFiles(new ArrayList<>());
        }
        // SqlTable and PerformTarget can remain null
    }
    
    /**
     * Initialize business logic fields for all statements in a procedure
     */
    public static void initializeProcedureStatements(StructuralProcedureV2 procedure) {
        if (procedure.getStatements() != null) {
            for (StructuralStatementV2 statement : procedure.getStatements()) {
                initializeStatement(statement);
            }
        }
    }
    
    /**
     * Initialize business logic fields for all procedures in a list
     */
    public static void initializeAllProcedures(List<StructuralProcedureV2> procedures) {
        for (StructuralProcedureV2 procedure : procedures) {
            initializeProcedureStatements(procedure);
        }
    }
    
    /**
     * Create a properly initialized StructuralStatementV2
     */
    public static StructuralStatementV2 createInitializedStatement() {
        StructuralStatementV2 statement = new StructuralStatementV2();
        initializeStatement(statement);
        return statement;
    }
    
    /**
     * Create a properly initialized StructuralStatementV2 with basic data
     */
    public static StructuralStatementV2 createInitializedStatement(String type, String content, int lineNumber) {
        StructuralStatementV2 statement = createInitializedStatement();
        statement.setType(type);
        statement.setContent(content);
        statement.setLineNumber(lineNumber);
        return statement;
    }
}

