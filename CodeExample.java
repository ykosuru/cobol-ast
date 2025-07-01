import java.util.List;
import java.util.ArrayList;

class CodeExample {
    private String name;
    private String cobolCode;
    private String javaCode;
    private String description;
    private List<String> applicablePatterns = new ArrayList<>();

    public CodeExample() {}
    public CodeExample(String name, String cobolCode, String javaCode) {
        this.name = name;
        this.cobolCode = cobolCode;
        this.javaCode = javaCode;
    }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getCobolCode() { return cobolCode; }
    public void setCobolCode(String cobolCode) { this.cobolCode = cobolCode; }
    public String getJavaCode() { return javaCode; }
    public void setJavaCode(String javaCode) { this.javaCode = javaCode; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public List<String> getApplicablePatterns() { return applicablePatterns; }
    public void setApplicablePatterns(List<String> applicablePatterns) { this.applicablePatterns = applicablePatterns; }
}
