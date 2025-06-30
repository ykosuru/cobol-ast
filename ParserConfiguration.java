import java.util.*;
import java.util.regex.Pattern;
import java.io.*;

public class ParserConfiguration 
{    
    private List<String> expectedProcedures;
    private List<Pattern> skipPatterns;
    private List<Pattern> procedurePatterns;
    private Set<String> excludedNames;
    private List<Pattern> programIdPatterns;
    private Map<String, List<Pattern>> statementPatterns;
    private List<Pattern> mainProcedurePatterns;
    private Set<String> sqlStatementTypes;
    private Set<String> copyStatementTypes;
    private Double baseScore;
    private Double performReferenceWeight;
    private Double maxPerformScore;
    private Double mainProcedureBonus;
    private Double diversityWeight;
    private Double maxDiversityScore;
    private Map<Integer, Double> statementCountThresholds;
    private Map<String, Double> specialStatementBonuses;
    
    // EXISTING FIELDS (you should already have these)
    private boolean verboseLogging = false;
    private boolean regexPreprocessingEnabled = true;
    private boolean grammarParsingEnabled = true;
    private boolean hybridModeEnabled = true;
    private double hybridThreshold = 0.8;
    private double minimumScore = 50.0;
    private ErrorRecoveryMode errorRecoveryMode = ErrorRecoveryMode.TOLERANT;
    
    // Data Division preprocessing options
    private boolean dataDivisionPreprocessingEnabled = true;
    private boolean preserveDataComments = true;
    private boolean extractDataItemDetails = true;
    private boolean processFileDescriptors = true;
    private boolean processConditionNames = true;
    private int maxEmptyLinesInProcedure = 10;
    private Set<String> dataDivisionSections = new HashSet<>();
    
    public List<Pattern> getSkipPatterns() {
        if (skipPatterns == null) {
            skipPatterns = new ArrayList<>();
            skipPatterns.add(Pattern.compile("^\\s*\\*.*"));   // Comments starting with *
            skipPatterns.add(Pattern.compile("^\\s*$"));       // Empty lines
            skipPatterns.add(Pattern.compile("^\\s*//.*"));    // Comments starting with //
            skipPatterns.add(Pattern.compile("^\\s*\\*>.*"));  // Modern COBOL comments
        }
        return skipPatterns;
    }
    
    public List<Pattern> getProcedurePatterns() {
        if (procedurePatterns == null) {
            procedurePatterns = new ArrayList<>();
            
            // ENHANCED: More specific patterns that avoid false positives
            
            // Pattern 1: Standard procedure with period (but not END-clauses)
            procedurePatterns.add(Pattern.compile("^\\s*([A-Za-z][A-Za-z0-9-_]*)\\s*\\.$"));
            
            // Pattern 2: Section definitions
            procedurePatterns.add(Pattern.compile("^\\s*([A-Za-z][A-Za-z0-9-_]*)\\s+SECTION\\s*\\.$"));
            
            // Pattern 3: Procedure with comment (but exclude END-clauses)
            procedurePatterns.add(Pattern.compile("^\\s*([A-Za-z][A-Za-z0-9-_]*)\\s*\\.\\s*\\*.*"));
        }
        return procedurePatterns;
    }
    
    
    public Set<String> getExcludedNames() {
        if (excludedNames == null) {
            excludedNames = new HashSet<>();
            excludedNames.addAll(Arrays.asList(
                // Standard exclusions
                "FILLER", "SPACES", "ZEROS", "LOW-VALUES", "HIGH-VALUES",
                "FILE-CONTROL", "WORKING-STORAGE", "LINKAGE-SECTION", 
                "FILE-SECTION", "INPUT-OUTPUT", "ENVIRONMENT", "DATA",
                "PROCEDURE", "IDENTIFICATION", "AUTHOR", "DATE-WRITTEN",
                
                // END clauses (major fix!)
                "END-IF", "END-EXEC", "END-EVALUATE", "END-PERFORM", 
                "END-READ", "END-WRITE", "END-CALL", "END-STRING",
                "END-UNSTRING", "END-SEARCH", "END-COMPUTE", "END-ADD",
                "END-SUBTRACT", "END-MULTIPLY", "END-DIVIDE",
                
                // Control flow statements  
                "GOBACK", "EXIT", "STOP", "CONTINUE",
                
                // Common variable prefixes (pattern-based exclusion)
                "WS", "LS", "FD", "SD"
            ));
        }
        return excludedNames;
    }

    public List<Pattern> getProgramIdPatterns() {
        if (programIdPatterns == null) {
            programIdPatterns = new ArrayList<>();
            programIdPatterns.add(Pattern.compile(".*PROGRAM-ID\\s*\\.\\s*([A-Za-z0-9-_]+).*"));
            programIdPatterns.add(Pattern.compile(".*IDENTIFICATION\\s+DIVISION.*PROGRAM-ID\\s*\\.\\s*([A-Za-z0-9-_]+).*"));
            programIdPatterns.add(Pattern.compile(".*ID\\s+DIVISION.*PROGRAM-ID\\s*\\.\\s*([A-Za-z0-9-_]+).*"));
        }
        return programIdPatterns;
    }
    
    public Map<String, List<Pattern>> getStatementPatterns() {
        if (statementPatterns == null) {
            statementPatterns = new HashMap<>();
            
            // SQL patterns
            statementPatterns.put("EXEC_SQL", Arrays.asList(
                Pattern.compile("^\\s*EXEC\\s+SQL\\s+.*"),
                Pattern.compile("^\\s*EXEC\\s+SQL.*")
            ));
            
            // PERFORM patterns
            statementPatterns.put("PERFORM", Arrays.asList(
                Pattern.compile("^\\s*PERFORM\\s+.*")
            ));
            
            // MOVE patterns
            statementPatterns.put("MOVE", Arrays.asList(
                Pattern.compile("^\\s*MOVE\\s+.*")
            ));
            
            // IF patterns
            statementPatterns.put("IF", Arrays.asList(
                Pattern.compile("^\\s*IF\\s+.*")
            ));
            
            // SET patterns
            statementPatterns.put("SET", Arrays.asList(
                Pattern.compile("^\\s*SET\\s+.*")
            ));
            
            // EVALUATE patterns
            statementPatterns.put("EVALUATE", Arrays.asList(
                Pattern.compile("^\\s*EVALUATE\\s+.*")
            ));
        }
        return statementPatterns;
    }
    
    public List<Pattern> getMainProcedurePatterns() {
        if (mainProcedurePatterns == null) {
            mainProcedurePatterns = new ArrayList<>();
            mainProcedurePatterns.add(Pattern.compile(".*main.*"));
            mainProcedurePatterns.add(Pattern.compile(".*initialization.*"));
            mainProcedurePatterns.add(Pattern.compile(".*startup.*"));
            mainProcedurePatterns.add(Pattern.compile(".*begin.*"));
            mainProcedurePatterns.add(Pattern.compile(".*start.*"));
            mainProcedurePatterns.add(Pattern.compile(".*init.*"));
            mainProcedurePatterns.add(Pattern.compile(".*mainline.*"));
        }
        return mainProcedurePatterns;
    }
    
    public Set<String> getSqlStatementTypes() {
        if (sqlStatementTypes == null) {
            sqlStatementTypes = new HashSet<>();
            sqlStatementTypes.addAll(Arrays.asList("EXEC_SQL", "SQL", "INCLUDE"));
        }
        return sqlStatementTypes;
    }
    
    public Set<String> getCopyStatementTypes() {
        if (copyStatementTypes == null) {
            copyStatementTypes = new HashSet<>();
            copyStatementTypes.addAll(Arrays.asList("COPY", "INCLUDE"));
        }
        return copyStatementTypes;
    }
    
    public double getBaseScore() { 
        return baseScore != null ? baseScore : 10.0; 
    }
    
    public void setBaseScore(double baseScore) { 
        this.baseScore = baseScore; 
    }
    
    public double getPerformReferenceWeight() { 
        return performReferenceWeight != null ? performReferenceWeight : 20.0; 
    }
    
    public void setPerformReferenceWeight(double weight) { 
        this.performReferenceWeight = weight; 
    }
    
    public double getMaxPerformScore() { 
        return maxPerformScore != null ? maxPerformScore : 60.0; 
    }
    
    public void setMaxPerformScore(double score) { 
        this.maxPerformScore = score; 
    }
    
    public double getMainProcedureBonus() { 
        return mainProcedureBonus != null ? mainProcedureBonus : 25.0; 
    }
    
    public void setMainProcedureBonus(double bonus) { 
        this.mainProcedureBonus = bonus; 
    }
    
    public double getDiversityWeight() { 
        return diversityWeight != null ? diversityWeight : 5.0; 
    }
    
    public void setDiversityWeight(double weight) { 
        this.diversityWeight = weight; 
    }
    
    public double getMaxDiversityScore() { 
        return maxDiversityScore != null ? maxDiversityScore : 25.0; 
    }
    
    public void setMaxDiversityScore(double score) { 
        this.maxDiversityScore = score; 
    }
    
    public Map<Integer, Double> getStatementCountThresholds() {
        if (statementCountThresholds == null) {
            statementCountThresholds = new HashMap<>();
            statementCountThresholds.put(1, 10.0);
            statementCountThresholds.put(5, 20.0);
            statementCountThresholds.put(10, 30.0);
            statementCountThresholds.put(20, 40.0);
        }
        return statementCountThresholds;
    }
    
    public Map<String, Double> getSpecialStatementBonuses() {
        if (specialStatementBonuses == null) {
            specialStatementBonuses = new HashMap<>();
            specialStatementBonuses.put("EXEC_SQL", 15.0);
            specialStatementBonuses.put("EVALUATE", 10.0);
            specialStatementBonuses.put("SQL", 15.0);
        }
        return specialStatementBonuses;
    }
    
    public List<String> getExpectedProcedures() {
        return expectedProcedures != null ? expectedProcedures : new ArrayList<>();
    }
    
    public void setExpectedProcedures(List<String> expectedProcedures) {
        this.expectedProcedures = expectedProcedures;
    }
    
    // EXISTING GETTERS AND SETTERS (you should already have these)
    public boolean isVerboseLogging() { return verboseLogging; }
    public void setVerboseLogging(boolean verbose) { this.verboseLogging = verbose; }
    
    public boolean isRegexPreprocessingEnabled() { return regexPreprocessingEnabled; }
    public void setRegexPreprocessingEnabled(boolean enabled) { this.regexPreprocessingEnabled = enabled; }
    
    public boolean isGrammarParsingEnabled() { return grammarParsingEnabled; }
    public void setGrammarParsingEnabled(boolean enabled) { this.grammarParsingEnabled = enabled; }
    
    public boolean isHybridModeEnabled() { return hybridModeEnabled; }
    public void setHybridModeEnabled(boolean enabled) { this.hybridModeEnabled = enabled; }
    
    public double getHybridThreshold() { return hybridThreshold; }
    public void setHybridThreshold(double threshold) { this.hybridThreshold = threshold; }
    
    public double getMinimumScore() { return minimumScore; }
    public void setMinimumScore(double score) { this.minimumScore = score; }
    
    public ErrorRecoveryMode getErrorRecoveryMode() { return errorRecoveryMode; }
    public void setErrorRecoveryMode(ErrorRecoveryMode mode) { this.errorRecoveryMode = mode; }
    
    // Data Division getters/setters
    public boolean isDataDivisionPreprocessingEnabled() { return dataDivisionPreprocessingEnabled; }
    public void setDataDivisionPreprocessingEnabled(boolean enabled) { this.dataDivisionPreprocessingEnabled = enabled; }
    
    public boolean isPreserveDataComments() { return preserveDataComments; }
    public void setPreserveDataComments(boolean preserve) { this.preserveDataComments = preserve; }
    
    public boolean isExtractDataItemDetails() { return extractDataItemDetails; }
    public void setExtractDataItemDetails(boolean extract) { this.extractDataItemDetails = extract; }
    
    public boolean isProcessFileDescriptors() { return processFileDescriptors; }
    public void setProcessFileDescriptors(boolean process) { this.processFileDescriptors = process; }
    
    public boolean isProcessConditionNames() { return processConditionNames; }
    public void setProcessConditionNames(boolean process) { this.processConditionNames = process; }
    
    public int getMaxEmptyLinesInProcedure() { return maxEmptyLinesInProcedure; }
    public void setMaxEmptyLinesInProcedure(int maxEmptyLines) { this.maxEmptyLinesInProcedure = maxEmptyLines; }
    
    public Set<String> getDataDivisionSections() { return dataDivisionSections; }
    public void setDataDivisionSections(Set<String> sections) { this.dataDivisionSections = sections; }
    
    // Initialize defaults
    public void loadDefaults() {
        // Initialize data division sections
        if (dataDivisionSections == null) {
            dataDivisionSections = new HashSet<>();
        }
        dataDivisionSections.addAll(Arrays.asList(
            "WORKING-STORAGE",
            "FILE",
            "LINKAGE",
            "LOCAL-STORAGE",
            "THREAD-LOCAL-STORAGE"
        ));
        
        // Initialize other defaults as needed
        // The getters will handle initialization of patterns and other collections
    }
    
    public List<String> validate() {
        List<String> issues = new ArrayList<>();
        
        // Validate data division configuration
        if (dataDivisionPreprocessingEnabled) {
            if (getDataDivisionSections().isEmpty()) {
                issues.add("Data division preprocessing enabled but no sections configured");
            }
        }
        
        if (maxEmptyLinesInProcedure < 0) {
            issues.add("Max empty lines in procedure must be non-negative");
        }
        
        if (minimumScore < 0) {
            issues.add("Minimum score must be non-negative");
        }
        
        if (hybridThreshold <= 0 || hybridThreshold > 1.0) {
            issues.add("Hybrid threshold must be between 0 and 1");
        }
        
        return issues;
    }
    
    @Override
    public String toString() {
        return String.format("ParserConfiguration{verbose=%s, dataDivision=%s, regex=%s, grammar=%s, hybrid=%s}", 
                           verboseLogging, dataDivisionPreprocessingEnabled, regexPreprocessingEnabled, 
                           grammarParsingEnabled, hybridModeEnabled);
    }
}

