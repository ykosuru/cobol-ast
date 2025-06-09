import java.util.*;

public class CobolProcedure {
    private String name;
    private String sourceCode;
    private String logicSummary;
    private List<String> calledProcedures = new ArrayList<>();

    public CobolProcedure(String name, String sourceCode) {
        this.name = name;
        this.sourceCode = sourceCode;
    }

    public String getName() { return name; }
    public String getSourceCode() { return sourceCode; }
    public String getLogicSummary() { return logicSummary; }
    public void setLogicSummary(String logicSummary) { this.logicSummary = logicSummary; }
    public List<String> getCalledProcedures() { return calledProcedures; }
}
