import java.util.*;

public class CobolVariable {
    private String name;
    private int level;
    private String dataType;
    private String pictureClause;
    private String initialValue;

    public CobolVariable(String name, int level, String dataType) {
        this.name = name;
        this.level = level;
        this.dataType = dataType;
    }

    public String getName() { return name; }
    public int getLevel() { return level; }
    public String getDataType() { return dataType; }
    public String getPictureClause() { return pictureClause; }
    public void setPictureClause(String pictureClause) { this.pictureClause = pictureClause; }
    public String getInitialValue() { return initialValue; }
    public void setInitialValue(String initialValue) { this.initialValue = initialValue; }
}
