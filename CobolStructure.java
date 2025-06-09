import java.util.*;

public class CobolStructure {
    private String programId;
    private String author;
    private List<CobolVariable> workingStorageVariables = new ArrayList<>();
    private List<CobolFile> fileDescriptions = new ArrayList<>();
    private List<CobolProcedure> procedures = new ArrayList<>();
    private List<CobolCopybook> copybooks = new ArrayList<>();
    private List<CobolExternalCall> externalCalls = new ArrayList<>();
    private List<CobolPerformCall> performCalls = new ArrayList<>();

    // Getters and setters
    public String getProgramId() { return programId; }
    public void setProgramId(String programId) { this.programId = programId; }

    public String getAuthor() { return author; }
    public void setAuthor(String author) { this.author = author; }

    public List<CobolVariable> getWorkingStorageVariables() { return workingStorageVariables; }
    public List<CobolFile> getFileDescriptions() { return fileDescriptions; }
    public List<CobolProcedure> getProcedures() { return procedures; }
    public List<CobolCopybook> getCopybooks() { return copybooks; }
    public List<CobolExternalCall> getExternalCalls() { return externalCalls; }
    public List<CobolPerformCall> getPerformCalls() { return performCalls; }
}
