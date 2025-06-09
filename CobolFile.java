import java.util.*;

public class CobolFile {
    private String name;
    private String accessMode;
    private String organization;
    private String recordFormat;

    public CobolFile(String name) {
        this.name = name;
    }

    public String getName() { return name; }
    public String getAccessMode() { return accessMode; }
    public void setAccessMode(String accessMode) { this.accessMode = accessMode; }
    public String getOrganization() { return organization; }
    public void setOrganization(String organization) { this.organization = organization; }
    public String getRecordFormat() { return recordFormat; }
    public void setRecordFormat(String recordFormat) { this.recordFormat = recordFormat; }
}
