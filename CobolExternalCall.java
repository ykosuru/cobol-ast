import java.util.*;

public class CobolExternalCall {
    private String programName;
    private boolean isDynamic;
    private List<String> parameters = new ArrayList<>();
    private String sourceLocation;
    private CallType callType;

    public CobolExternalCall(String programName) {
        this.programName = programName;
    }

    public enum CallType {
        STATIC_CALL,
        DYNAMIC_CALL,
        CICS_CALL,
        SQL_CALL,
        SYSTEM_CALL
    }

    public String getProgramName() { return programName; }
    public boolean isDynamic() { return isDynamic; }
    public void setDynamic(boolean dynamic) { isDynamic = dynamic; }
    public List<String> getParameters() { return parameters; }
    public String getSourceLocation() { return sourceLocation; }
    public void setSourceLocation(String sourceLocation) { this.sourceLocation = sourceLocation; }
    public CallType getCallType() { return callType; }
    public void setCallType(CallType callType) { this.callType = callType; }
}
