import java.util.*;

public class CobolPerformCall {
    private String targetName;
    private String throughTarget;
    private PerformType performType;
    private String sourceLocation;
    private boolean isExternal;

    public CobolPerformCall(String targetName) {
        this.targetName = targetName;
    }

    public enum PerformType {
        SIMPLE,
        THROUGH,
        TIMES,
        UNTIL,
        VARYING
    }

    public String getTargetName() { return targetName; }
    public String getThroughTarget() { return throughTarget; }
    public void setThroughTarget(String throughTarget) { this.throughTarget = throughTarget; }
    public PerformType getPerformType() { return performType; }
    public void setPerformType(PerformType performType) { this.performType = performType; }
    public String getSourceLocation() { return sourceLocation; }
    public void setSourceLocation(String sourceLocation) { this.sourceLocation = sourceLocation; }
    public boolean isExternal() { return isExternal; }
    public void setExternal(boolean external) { isExternal = external; }
}
