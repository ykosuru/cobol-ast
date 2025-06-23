/**
 * Add these missing variables and methods to your ASTParser class
 * Insert these at the appropriate locations in your class
 * Author: Yekesa Kosuru
 */

 import org.antlr.v4.runtime.*;
 import org.antlr.v4.runtime.tree.*;
 import java.io.*;
 import java.util.*;
 import java.util.stream.Collectors;
 import java.util.regex.Pattern;
 import java.util.regex.Matcher;

public class ASTParser extends CobolBaseListener {
    
    private ParserConfiguration config;
    private DataDivisionPreprocessor dataPreprocessor;
    private List<StructuralDataItemV2> extractedDataItems = new ArrayList<>();
    private List<DataDivisionPreprocessor.FileDescriptor> fileDescriptors = new ArrayList<>();
    
    // CRITICAL: Make sure this is declared
    private String[] sourceLines;  // THIS MUST BE DECLARED AS A FIELD
    
    // Other required fields
    private StructuralAnalysisResultV2 result;
    private List<StructuralProcedureV2> procedures = new ArrayList<>();
    private List<StructuralStatementV2> sqlStatements = new ArrayList<>();
    private List<StructuralStatementV2> copyStatements = new ArrayList<>();
    private String programName = "UNKNOWN";
    private Map<String, Integer> performReferences = new HashMap<>();
    private Map<String, Integer> statementCounts = new HashMap<>();
    private List<String> parseWarnings = new ArrayList<>();
    private List<String> preprocessWarnings = new ArrayList<>();
    private CommonTokenStream tokenStream;
    private StructuralProcedureV2 currentProcedure;
    

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: java ASTParser <cobol-file> [config-file]");
            System.err.println("Examples:");
            System.err.println("  java ASTParser myprogram.cbl");
            System.err.println("  java ASTParser myprogram.cbl custom-config.properties");
            System.exit(1);
        }
        
        try {
            // Create parser instance
            ASTParser parser;
            if (args.length > 1) {
                // Use custom config file if provided
                parser = new ASTParser(args[1]);
            } else {
                // Use default configuration
                parser = new ASTParser("cobol-grammar.properties");
            }
            
            String cobolFile = args[0];
            System.out.println("🚀 Starting ASTParser analysis of: " + cobolFile);
            
            // Parse the COBOL file
            StructuralAnalysisResultV2 result = parser.parseCobolWithGrammar(cobolFile);
            
            // Print results
            parser.printEnhancedResults(result);
            
            // Save AST to file
            String astFilename = cobolFile + ".ast";
            saveEnhancedAST(result, astFilename);
            
            System.out.println("✅ Analysis complete! AST saved to: " + astFilename);
            
        } catch (Exception e) {
            System.err.println("❌ Error analyzing COBOL file: " + e.getMessage());
            if (e.getCause() != null) {
                System.err.println("Caused by: " + e.getCause().getMessage());
            }
            e.printStackTrace();
            System.exit(1);
        }
    }

    // Constructor
    public ASTParser(String configFile) {
        this.config = loadConfiguration(configFile);
        this.dataPreprocessor = new DataDivisionPreprocessor(config);
    }


    private ParserConfiguration loadConfiguration(String configFile) {
        ParserConfiguration config = new ParserConfiguration();
        
        // For now, just load defaults and ignore the config file
        // You can enhance this later
        config.loadDefaults();
        
        if (config.isVerboseLogging()) {
            System.out.println("📊 Using default configuration (config file loading not yet implemented)");
        }
        
        // Validate configuration
        List<String> issues = config.validate();
        if (!issues.isEmpty()) {
            System.err.println("⚠️ Configuration issues:");
            issues.forEach(issue -> System.err.println("  - " + issue));
        }
        
        return config;
    }

    // use the no-argument version with hardcoded config file
    private ParserConfiguration loadConfiguration() {
        // Ignore the config file parameter for now and use defaults
        return loadConfiguration("cobol-grammar.properties");  // Call the no-argument version
    }
    
    /**
     * Parse Cobol using Grammar and Regex pattern 
     */

    public StructuralAnalysisResultV2 parseCobolWithGrammar(String filename) throws Exception {
        if (config.isVerboseLogging()) {
            System.out.println("🔍 ASTParser grammar-enhanced analysis of COBOL file: " + filename);
            System.out.println("📊 Configuration: " + config.toString());
        }
        
        // Read source for line-based analysis
        sourceLines = readSourceLines(filename);
        System.out.println("🔍 DEBUG: Read " + sourceLines.length + " source lines");
        
        // STEP 1: Preprocess DATA DIVISION
        DataDivisionPreprocessor.PreprocessingResult preprocessResult = null;
        if (config.isDataDivisionPreprocessingEnabled()) {
            if (config.isVerboseLogging()) {
                System.out.println("🔄 Preprocessing DATA DIVISION sections...");
            }
            
            preprocessResult = dataPreprocessor.preprocessDataDivisions(sourceLines);
            extractedDataItems = preprocessResult.getDataItems();
            fileDescriptors = preprocessResult.getFileDescriptors();
            
            // Add preprocessing warnings
            preprocessWarnings.addAll(preprocessResult.getWarnings());
            
            System.out.println("🔍 DEBUG: After preprocessing:");
            System.out.println("  - Data items: " + extractedDataItems.size());
            System.out.println("  - File descriptors: " + fileDescriptors.size());
            System.out.println("  - Cleaned source lines: " + preprocessResult.getCleanedSource().length);
            
            if (config.isVerboseLogging()) {
                System.out.println("📊 Extracted " + extractedDataItems.size() + " data items");
                System.out.println("📊 Extracted " + fileDescriptors.size() + " file descriptors");
                if (!preprocessResult.getWarnings().isEmpty()) {
                    System.out.println("⚠️ Preprocessing warnings: " + preprocessResult.getWarnings().size());
                }
            }
        }
        
        // STEP 2: Apply regex preprocessing if enabled
        List<ProcedureBoundary> regexProcedures = new ArrayList<>();
        if (config.isRegexPreprocessingEnabled()) {
            // Use cleaned source if available, otherwise original
            String[] sourceToParse = (preprocessResult != null) ? 
                preprocessResult.getCleanedSource() : sourceLines;
            
            System.out.println("🔍 DEBUG: Starting regex preprocessing with " + sourceToParse.length + " lines");
            
            regexProcedures = preprocessWithConfigurableRegex(sourceToParse);
            
            System.out.println("🔍 DEBUG: Regex preprocessing found " + regexProcedures.size() + " procedure candidates:");
            for (ProcedureBoundary boundary : regexProcedures) {
                System.out.println("  - " + boundary.getName() + " at line " + boundary.getStartLine());
            }
            
            if (config.isVerboseLogging()) {
                System.out.println("📊 Regex preprocessing found " + regexProcedures.size() + " procedure candidates");
            }
        }
        
        // STEP 3: Grammar parsing with configurable error handling
        boolean grammarSuccess = false;
        if (config.isGrammarParsingEnabled()) {
            System.out.println("🔍 DEBUG: Starting grammar parsing...");
            
            // Use cleaned source for grammar parsing
            String[] sourceToParse = (preprocessResult != null) ? 
                preprocessResult.getCleanedSource() : sourceLines;
            grammarSuccess = attemptConfigurableGrammarParsingWithCleanedSource(filename, sourceToParse);
            
            System.out.println("🔍 DEBUG: Grammar parsing success: " + grammarSuccess);
            System.out.println("🔍 DEBUG: Procedures found via grammar: " + procedures.size());
            for (StructuralProcedureV2 proc : procedures) {
                System.out.println("  - " + proc.getName() + " (lines " + proc.getLineNumber() + "-" + proc.getEndLineNumber() + ")");
            }
        }
        
        // STEP 4: Hybrid approach based on configuration
        System.out.println("🔍 DEBUG: Checking hybrid mode...");
        System.out.println("  - Hybrid enabled: " + config.isHybridModeEnabled());
        System.out.println("  - Should use hybrid: " + shouldUseHybridMode(regexProcedures));
        System.out.println("  - Grammar procedures: " + procedures.size());
        System.out.println("  - Regex procedures: " + regexProcedures.size());
        
        if (config.isHybridModeEnabled() && shouldUseHybridMode(regexProcedures)) {
            if (config.isVerboseLogging()) {
                System.out.println("🔄 Applying configurable hybrid enhancement...");
            }
            int beforeCount = procedures.size();
            enhanceWithConfigurableRegexResults(regexProcedures);
            int afterCount = procedures.size();
            System.out.println("🔍 DEBUG: Hybrid enhancement added " + (afterCount - beforeCount) + " procedures");
        }
        
        System.out.println("🔍 DEBUG: Total procedures before filtering: " + procedures.size());
        
        // Build result with enhanced data items
        result = new StructuralAnalysisResultV2();
        result.setProgramName(determineProgramName());
        result.setProcedures(applyConfigurableFiltering());
        result.setSqlStatements(sqlStatements);
        result.setCopyStatements(copyStatements);
        result.setStatementCounts(statementCounts);
        result.setPerformReferences(performReferences);
        result.setParseWarnings(parseWarnings);
        
        // Add extracted data items
        result.setDataItems(extractedDataItems);
        result.setFileDescriptors(fileDescriptors);
        
        System.out.println("🔍 DEBUG: Final procedure count after filtering: " + result.getProcedures().size());
        
        return result;
    }

    /**
     * Enhanced preprocessWithConfigurableRegex with more debug output
     */
    private List<ProcedureBoundary> preprocessWithConfigurableRegex(String[] sourceToProcess) throws IOException {
        List<ProcedureBoundary> boundaries = new ArrayList<>();
        
        System.out.println("🔍 DEBUG: Scanning " + sourceToProcess.length + " lines for procedures...");
        
        for (int lineNumber = 0; lineNumber < sourceToProcess.length; lineNumber++) {
            String line = sourceToProcess[lineNumber];
            
            // Skip based on configurable patterns
            if (shouldSkipLineByConfig(line)) {
                continue;
            }
            
            // Skip cleaned data division comments
            if (line.trim().startsWith("*> DATA-ITEM:")) {
                continue;
            }
            
            // Check against configured procedure patterns
            String procedureName = extractProcedureNameFromLine(line);
            if (procedureName != null) {
                System.out.println("🔍 DEBUG: Found potential procedure '" + procedureName + "' at line " + (lineNumber + 1));
                
                if (!isExcludedByConfig(procedureName)) {
                    boundaries.add(new ProcedureBoundary(procedureName, lineNumber + 1)); // +1 for 1-based line numbers
                    System.out.println("  ✅ Added to boundaries");
                } else {
                    System.out.println("  ❌ Excluded by config");
                }
            }
        }
        
        System.out.println("🔍 DEBUG: Found " + boundaries.size() + " procedure boundaries total");
        return boundaries;
    }

    /**
     * Enhanced shouldUseHybridMode with debug output
     */
    private boolean shouldUseHybridMode(List<ProcedureBoundary> regexProcedures) {
        if (!config.isHybridModeEnabled()) {
            System.out.println("🔍 DEBUG: Hybrid mode disabled in config");
            return false;
        }
        
        if (regexProcedures.isEmpty()) {
            System.out.println("🔍 DEBUG: No regex procedures found, skipping hybrid");
            return false;
        }
        
        double ratio = (double) procedures.size() / regexProcedures.size();
        boolean useHybrid = ratio < config.getHybridThreshold();
        
        System.out.println("🔍 DEBUG: Hybrid decision:");
        System.out.println("  - Grammar procedures: " + procedures.size());
        System.out.println("  - Regex procedures: " + regexProcedures.size());
        System.out.println("  - Ratio: " + String.format("%.2f", ratio));
        System.out.println("  - Threshold: " + config.getHybridThreshold());
        System.out.println("  - Use hybrid: " + useHybrid);
        
        return useHybrid;
        
    }
    
    // ADD THIS METHOD - printEnhancedResults
    public void printEnhancedResults(StructuralAnalysisResultV2 result) {
        System.out.println("\n=== CONFIGURABLE GRAMMAR-ENHANCED ANALYSIS RESULTS ===");
        System.out.println("✅ Program: " + result.getProgramName());
        System.out.println("📊 Procedures: " + result.getProcedures().size());
        System.out.println("📊 Data Items: " + result.getDataItems().size());
        System.out.println("📊 File Descriptors: " + result.getFileDescriptors().size());
        System.out.println("📊 SQL statements: " + result.getSqlStatements().size());
        System.out.println("📊 COPY statements: " + result.getCopyStatements().size());
        
        if (config.isVerboseLogging()) {
            System.out.println("📊 PERFORM references: " + result.getPerformReferences().size());
            System.out.println("📊 Statement types: " + result.getStatementCounts().size());
            
            if (!result.getParseWarnings().isEmpty()) {
                System.out.println("⚠️ Parse warnings: " + result.getParseWarnings().size());
            }
        }
        
        // Enhanced data division analysis
        if (!result.getDataItems().isEmpty()) {
            printDataDivisionAnalysis(result);
        }
        
        System.out.println("\n=== IDENTIFIED PROCEDURES ===");
        List<StructuralProcedureV2> sortedProcs = result.getProcedures().stream()
            .sorted(Comparator.comparingInt(StructuralProcedureV2::getLineNumber))
            .collect(Collectors.toList());

        for (int i = 0; i < sortedProcs.size(); i++) {
            StructuralProcedureV2 proc = sortedProcs.get(i);
            
            // Get actual reference count
            int refCount = getPerformReferenceCount(proc.getName());
            
            System.out.println((i + 1) + ". " + proc.getName() + 
                              " (Lines " + proc.getLineNumber() + "-" + proc.getEndLineNumber() + 
                              ", Score: " + String.format("%.1f", proc.getContextScore()) +
                              ", " + proc.getStatements().size() + " statements" +
                              ", " + refCount + " refs)");
            
            if (config.isVerboseLogging()) {
                System.out.println("    Reasoning: " + proc.getReasoningInfo());
            }
        }
        
        // Detailed analysis if verbose logging is enabled
        if (config.isVerboseLogging()) {
            printDetailedAnalysis(result);
        }
        
        // Calculate accuracy if validation data is available
        if (config.getExpectedProcedures() != null && !config.getExpectedProcedures().isEmpty()) {
           calculateDynamicAccuracy(sortedProcs);
        }
    }
    
    private boolean attemptConfigurableGrammarParsingWithCleanedSource(String filename, String[] cleanedSource) {
        try {
            // For now, just do regex-based parsing
            // You can enhance this later with actual ANTLR grammar parsing
            if (config.isVerboseLogging()) {
                System.out.println("🔄 Grammar parsing with cleaned source (simplified implementation)");
            }
            return true;
            
        } catch (Exception e) {
            if (config.getErrorRecoveryMode() == ErrorRecoveryMode.STRICT) {
                throw new RuntimeException("Grammar parsing failed in strict mode", e);
            }
            
            if (config.isVerboseLogging()) {
                System.err.println("⚠️ Grammar parsing encountered issues: " + e.getMessage());
                System.out.println("🔄 Continuing with available results...");
            }
            return false;
        }
    }
    
   
    private String[] readSourceLines(String filename) throws IOException {
        List<String> lines = new ArrayList<>();
        try (BufferedReader reader = new BufferedReader(new FileReader(filename))) {
            String line;
            while ((line = reader.readLine()) != null) {
                lines.add(line);
            }
        }
        return lines.toArray(new String[0]);
    }
    /**
     * Check if line should be skipped based on configuration
     */
    private boolean shouldSkipLineByConfig(String line) {
        String trimmed = line.trim();
        
        for (Pattern skipPattern : config.getSkipPatterns()) {
            if (skipPattern.matcher(trimmed).matches()) {
                return true;
            }
        }
        
        return false;
    }
    
    private String extractProcedureNameFromLine(String line) {
        String trimmed = line.trim();
        
        // Skip empty lines and comments
        if (trimmed.isEmpty() || trimmed.startsWith("*")) {
            return null;
        }
        
        for (Pattern pattern : config.getProcedurePatterns()) {
            Matcher matcher = pattern.matcher(trimmed);
            if (matcher.find()) {
                // Extract name from first capture group
                for (int i = 1; i <= matcher.groupCount(); i++) {
                    String group = matcher.group(i);
                    if (group != null && !group.trim().isEmpty()) {
                        String candidateName = group.trim();
                        
                        // Additional validation
                        if (isValidProcedureName(candidateName)) {
                            return candidateName;
                        }
                    }
                }
            }
        }
        
        return null;
    }
    
    private boolean isValidProcedureName(String name) {
        if (name == null || name.trim().isEmpty()) {
            return false;
        }
        
        // Must start with letter
        if (!Character.isLetter(name.charAt(0))) {
            return false;
        }
        
        // Must be reasonable length
        if (name.length() < 3 || name.length() > 30) {
            return false;
        }
        
        // Must match COBOL naming conventions
        if (!name.matches("[A-Za-z][A-Za-z0-9-_]*")) {
            return false;
        }
        
        // Check against excluded names
        if (isExcludedByConfig(name)) {
            return false;
        }
        
        return true;
    }

    
    /**
     * Enhance with regex results using configurable logic
     */
    private void enhanceWithConfigurableRegexResults(List<ProcedureBoundary> regexProcedures) {
        Set<String> grammarProcNames = procedures.stream()
            .map(StructuralProcedureV2::getName)
            .collect(Collectors.toSet());
        
        for (ProcedureBoundary boundary : regexProcedures) {
            if (!grammarProcNames.contains(boundary.getName())) {
                StructuralProcedureV2 proc = createProcedureFromConfigurableRegex(boundary);
                if (proc != null) {
                    procedures.add(proc);
                    if (config.isVerboseLogging()) {
                        System.out.println("➕ Added from regex: " + boundary.getName() + 
                                         " (Line " + boundary.getStartLine() + ")");
                    }
                }
            }
        }
        
        // Sort by line number
        procedures.sort(Comparator.comparingInt(StructuralProcedureV2::getLineNumber));
    }
    
    /**
     * Create procedure from regex boundary using configurable analysis
     */
    private StructuralProcedureV2 createProcedureFromConfigurableRegex(ProcedureBoundary boundary) {
        StructuralProcedureV2 proc = new StructuralProcedureV2();
        proc.setName(boundary.getName());
        proc.setLineNumber(boundary.getStartLine());
        
        // Calculate end line using configurable patterns
        int endLine = calculateConfigurableEndLine(boundary.getStartLine());
        proc.setEndLineNumber(endLine);
        
        // Extract statements using configurable patterns
        List<StructuralStatementV2> statements = extractConfigurableStatementsFromSource(
            boundary.getStartLine(), endLine);
        proc.setStatements(statements);
        
        return proc;
    }
    
    /**
     * Calculate configurable end line
     */
    private int calculateConfigurableEndLine(int startLine) {
        for (int i = startLine + 1; i < sourceLines.length; i++) {
            String line = sourceLines[i].trim();
            
            if (shouldSkipLineByConfig(line)) {
                continue;
            }
            
            // Check for next procedure (only in PROCEDURE DIVISION)
            if (isProcedureDivisionContext(i)) {
                String nextProcName = extractProcedureNameFromLine(line);
                if (nextProcName != null && !isExcludedByConfig(nextProcName)) {
                    return i - 1;
                }
            }
            
            // Check for division boundaries
            if (line.matches(".*\\s+(DIVISION|SECTION)\\s*\\..*")) {
                return i - 1;
            }
            
            // Check for end of program
            if (line.matches(".*END\\s+PROGRAM.*")) {
                return i - 1;
            }
        }
        
        return sourceLines.length;
    }
    
    private boolean isProcedureDivisionContext(int lineIndex) {
        // Look backwards to see if we're in PROCEDURE DIVISION
        for (int i = lineIndex - 1; i >= 0; i--) {
            String line = sourceLines[i].toUpperCase().trim();
            if (line.contains("PROCEDURE DIVISION")) {
                return true;
            }
            if (line.contains("DATA DIVISION") || line.contains("ENVIRONMENT DIVISION")) {
                return false;
            }
        }
        return false;
    }
    
    /**
     * Determine program name using configurable patterns
     */
    private String determineProgramName() {
        // First try grammar-extracted name
        if (!programName.isEmpty() && !"UNKNOWN".equals(programName)) {
            return programName;
        }
        
        // Fall back to configurable source extraction
        for (String line : sourceLines) {
            String upper = line.toUpperCase();
            
            for (Pattern pattern : config.getProgramIdPatterns()) {
                Matcher matcher = pattern.matcher(upper);
                if (matcher.find()) {
                    for (int i = 1; i <= matcher.groupCount(); i++) {
                        String name = matcher.group(i);
                        if (name != null && !name.trim().isEmpty()) {
                            return name.trim().replaceAll("[^A-Z0-9-_]", "");
                        }
                    }
                }
            }
        }
        
        return "UNKNOWN";
    }
    
    /**
     * Apply configurable filtering. Move this to config properties
     */
    private List<StructuralProcedureV2> applyConfigurableFiltering() {
        if (config.isVerboseLogging()) {
            System.out.println("📊 Configurable analysis of " + procedures.size() + " procedures");
        }
        
        // Apply scoring first
        for (StructuralProcedureV2 proc : procedures) {
            double score = calculateConfigurableScore(proc);
            proc.setContextScore(score);
            
            String reasoning = buildConfigurableReasoning(proc);
            proc.setReasoningInfo(reasoning);
            
            System.out.println("🔍 DEBUG: Procedure '" + proc.getName() + "' scored " + 
                              String.format("%.1f", score) + " (threshold: " + config.getMinimumScore() + ")");
        }
        
        // Apply filtering with better false positive detection
        List<StructuralProcedureV2> filtered = procedures.stream()
                .filter(p -> {
                    boolean passesScore = p.getContextScore() >= config.getMinimumScore();
                    boolean notFalsePositive = !isFalsePositiveProcedure(p);
                    
                    if (!passesScore) {
                        System.out.println("🔍 DEBUG: '" + p.getName() + "' filtered out - low score");
                    }
                    if (!notFalsePositive) {
                        System.out.println("🔍 DEBUG: '" + p.getName() + "' filtered out - false positive");
                    }
                    
                    return passesScore && notFalsePositive;
                })
                .sorted((a, b) -> Double.compare(b.getContextScore(), a.getContextScore()))
                .collect(Collectors.toList());
        
        if (config.isVerboseLogging()) {
            System.out.println("📊 Configurable result: " + filtered.size() + " confirmed procedures");
        }
        
        return filtered;
    }
    
    /**
     * Enhanced false positive detection, to avoid detecting variables as procs within proc. div.
     */
    private boolean isFalsePositiveProcedure(StructuralProcedureV2 proc) {
        String name = proc.getName();
        
        // Known DATA DIVISION sections
        if (name.equals("FILE-CONTROL") || 
            name.equals("WORKING-STORAGE") ||
            name.equals("LINKAGE-SECTION") ||
            name.equals("FILE-SECTION")) {
            return true;
        }
        
        // Data item patterns
        if (name.matches("^[Ww][Ss][A-Z].*") ||     // wsVariableName
            name.matches("^[Ll][Ss][A-Z].*") ||     // lsVariableName  
            name.matches("^[Ff][Dd][A-Z].*") ||     // fdFileName
            name.length() > 30) {                   // Very long names are usually data
            return true;
        }
        
        // Procedures with no statements and no references are suspicious
        int refCount = getPerformReferenceCount(name);
        if (proc.getStatements().isEmpty() && refCount == 0 && 
            !isConfigurableMainProcedure(name)) {
            return true;
        }
        
        return false;
    }
    
    /**
     * Calculate score using configurable weights and thresholds
     */
    private double calculateConfigurableScore(StructuralProcedureV2 proc) {
        double score = config.getBaseScore();
        
        // PERFORM reference analysis using configured weights
        int refCount = performReferences.getOrDefault(proc.getName(), 0);
        if (refCount > 0) {
            score += Math.min(refCount * config.getPerformReferenceWeight(), config.getMaxPerformScore());
        } else if (isConfigurableMainProcedure(proc.getName())) {
            score += config.getMainProcedureBonus();
        }
        
        // Statement count scoring using configured thresholds
        int stmtCount = proc.getStatements().size();
        score += calculateConfigurableStatementScore(stmtCount);
        
        // Statement diversity using configured weight
        Set<String> stmtTypes = proc.getStatements().stream()
            .map(StructuralStatementV2::getType)
            .collect(Collectors.toSet());
        score += Math.min(stmtTypes.size() * config.getDiversityWeight(), config.getMaxDiversityScore());
        
        // Special statement bonuses from configuration
        score += calculateConfigurableSpecialStatementBonuses(proc);
        
        return score;
    }
    
    /**
     * Calculate statement count score using configured thresholds
     */
    private double calculateConfigurableStatementScore(int stmtCount) {
        for (Map.Entry<Integer, Double> entry : config.getStatementCountThresholds().entrySet()) {
            if (stmtCount >= entry.getKey()) {
                return entry.getValue();
            }
        }
        return 0.0;
    }
    
    /**
     * Calculate special statement bonuses using configuration
     */
    private double calculateConfigurableSpecialStatementBonuses(StructuralProcedureV2 proc) {
        double bonus = 0.0;
        Map<String, Long> stmtTypeCount = proc.getStatements().stream()
            .collect(Collectors.groupingBy(StructuralStatementV2::getType, Collectors.counting()));
        
        for (Map.Entry<String, Double> entry : config.getSpecialStatementBonuses().entrySet()) {
            if (stmtTypeCount.containsKey(entry.getKey())) {
                bonus += entry.getValue();
            }
        }
        
        return bonus;
    }
    
    /**
     * Check if procedure is main procedure using configured patterns
     */
    private boolean isConfigurableMainProcedure(String name) {
        String lower = name.toLowerCase();
        
        for (Pattern pattern : config.getMainProcedurePatterns()) {
            if (pattern.matcher(lower).matches()) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * Build reasoning using configurable logic
     */
    private String buildConfigurableReasoning(StructuralProcedureV2 proc) {
        List<String> reasons = new ArrayList<>();
        
        reasons.add("configurable analysis");
        
        int refCount = performReferences.getOrDefault(proc.getName(), 0);
        if (refCount > 0) {
            reasons.add(refCount + " PERFORM references");
        } else if (isConfigurableMainProcedure(proc.getName())) {
            reasons.add("main procedure pattern");
        }
        
        int stmtCount = proc.getStatements().size();
        Set<String> stmtTypes = proc.getStatements().stream()
            .map(StructuralStatementV2::getType)
            .collect(Collectors.toSet());
        
        reasons.add(stmtCount + " statements across " + stmtTypes.size() + " types");
        
        // Add special statement insights from configuration
        Map<String, Long> stmtTypeCount = proc.getStatements().stream()
            .collect(Collectors.groupingBy(StructuralStatementV2::getType, Collectors.counting()));
        
        for (String specialType : config.getSpecialStatementBonuses().keySet()) {
            if (stmtTypeCount.containsKey(specialType)) {
                reasons.add("includes " + specialType.toLowerCase().replace("_", " "));
            }
        }
        
        return String.join(", ", reasons);
    }
    
    /**
     * Get perform reference count with name variations
     */
    private int getPerformReferenceCount(String procName) {
        if (procName == null) return 0;
        
        // Check multiple naming conventions
        String[] variations = {
            procName.toUpperCase(),
            procName.toLowerCase(),
            convertCamelToCobol(procName),
            procName.replace("-", "").toUpperCase(),
            procName.replace("_", "").toUpperCase()
        };
        
        return Arrays.stream(variations)
            .mapToInt(variant -> performReferences.getOrDefault(variant, 0))
            .max()
            .orElse(0);
    }
    
    /**
     * Convert camelCase to COBOL uppercase
     */
    private String convertCamelToCobol(String camelCase) {
        return camelCase.replaceAll("([a-z])([A-Z])", "$1$2").toUpperCase();
    }
    
    /**
     * Print detailed analysis
     */
    private void printDetailedAnalysis(StructuralAnalysisResultV2 result) {
        System.out.println("\n=== COMPREHENSIVE STATEMENT ANALYSIS ===");
        result.getStatementCounts().entrySet().stream()
            .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
            .forEach(entry -> System.out.println("  " + entry.getKey() + ": " + entry.getValue()));
        
        System.out.println("\n=== PERFORM REFERENCE GRAPH ===");
        result.getPerformReferences().entrySet().stream()
            .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
            .forEach(entry -> System.out.println("  " + entry.getKey() + ": " + entry.getValue() + " references"));
        
        // Enhanced quality metrics
        System.out.println("\n=== ENHANCED QUALITY METRICS ===");
        
        double avgScore = result.getProcedures().stream()
            .mapToDouble(StructuralProcedureV2::getContextScore)
            .average().orElse(0.0);
        System.out.println("Average procedure score: " + String.format("%.1f", avgScore));
        
        long highConfidenceProcs = result.getProcedures().stream()
            .filter(p -> p.getContextScore() >= config.getMinimumScore() + 30.0)
            .count();
        System.out.println("High confidence procedures (≥" + (config.getMinimumScore() + 30.0) + "): " + highConfidenceProcs);
        
        // Total statements
        int totalStatements = result.getStatementCounts().values().stream()
            .mapToInt(Integer::intValue).sum();
        System.out.println("Total statements analyzed: " + totalStatements);
    }
    
    /**
     * Calculate dynamic accuracy
     */
    private void calculateDynamicAccuracy(List<StructuralProcedureV2> procedures) {
        System.out.println("\n=== DYNAMIC ANALYSIS ===");
        System.out.println("Procedures found: " + procedures.size());
        
        // Analyze PERFORM references vs found procedures
        Set<String> foundProcNames = procedures.stream()
            .map(p -> p.getName().toUpperCase())
            .collect(Collectors.toSet());
        
        Set<String> referencedButNotFound = performReferences.keySet().stream()
            .filter(ref -> !foundProcNames.contains(ref))
            .collect(Collectors.toSet());
        
        System.out.println("Referenced but not found as procedures: " + referencedButNotFound.size());
        referencedButNotFound.forEach(ref -> 
            System.out.println("  - " + ref + " (" + performReferences.get(ref) + " references)"));
        
        // Calculate coverage based on actual references
        int totalReferences = performReferences.size();
        int foundReferences = (int) performReferences.keySet().stream()
            .filter(foundProcNames::contains)
            .count();
        
        double coverage = totalReferences > 0 ? 
            ((double)foundReferences / totalReferences) * 100 : 100.0;
        
        System.out.println("Reference coverage: " + String.format("%.1f%%", coverage));
    }
    
    /**
     * Extract statements from source with configurable patterns
     */
    private List<StructuralStatementV2> extractConfigurableStatementsFromSource(int startLine, int endLine) {
        List<StructuralStatementV2> statements = new ArrayList<>();
        List<String> currentStatementLines = new ArrayList<>();
        int statementStartLine = startLine;
        
        for (int i = startLine; i < Math.min(endLine, sourceLines.length); i++) {
            String line = sourceLines[i].trim();
            
            if (shouldSkipLineByConfig(line) || line.isEmpty()) {
                continue;
            }
            
            // Skip procedure headers
            if (isConfigurableProcedureHeader(line)) {
                continue;
            }
            
            // Check if this line starts a new statement
            if (isStatementStart(line) && !currentStatementLines.isEmpty()) {
                // Process previous statement
                processAccumulatedStatement(statements, currentStatementLines, statementStartLine);
                currentStatementLines.clear();
                statementStartLine = i + 1;
            }
            
            currentStatementLines.add(line);
            
            // Check if statement ends on this line
            if (isStatementEnd(line)) {
                processAccumulatedStatement(statements, currentStatementLines, statementStartLine);
                currentStatementLines.clear();
            }
        }
        
        // Handle remaining statement
        if (!currentStatementLines.isEmpty()) {
            processAccumulatedStatement(statements, currentStatementLines, statementStartLine);
        }
        
        return statements;
    }
    
    private void processAccumulatedStatement(List<StructuralStatementV2> statements, 
                                           List<String> lines, int startLine) {
        if (lines.isEmpty()) return;
        
        // Join lines with proper spacing
        String content = String.join(" ", lines).trim();
        
        // Split compound statements that were concatenated
        List<String> splitStatements = splitCompoundStatement(content);
        
        for (String stmt : splitStatements) {
            if (!stmt.trim().isEmpty()) {
                String statementType = determineConfigurableStatementType(stmt);
                if (statementType != null) {
                    StructuralStatementV2 statement = new StructuralStatementV2();
                    statement.setContent(stmt);
                    statement.setType(statementType);
                    statement.setLineNumber(startLine);
                    statements.add(statement);
                    
                    incrementStatementCount(statementType);
                    extractConfigurablePerformReferences(stmt);
                }
            }
        }
    }
    
    private List<String> splitCompoundStatement(String content) {
        List<String> statements = new ArrayList<>();
        
        // Check for concatenated PERFORM statements
        if (content.matches(".*PERFORM[A-Za-z]+.*")) {
            content = content.replaceAll("PERFORM([A-Za-z][A-Za-z0-9-_]*)", "PERFORM $1");
        }
        
        // Split on statement boundaries while preserving structure
        String[] splitPatterns = {
            "(?<=\\.)\\s*(?=PERFORM\\s+)",
            "(?<=\\.)\\s*(?=IF\\s+)",
            "(?<=\\.)\\s*(?=MOVE\\s+)",
            "(?<=\\.)\\s*(?=EXEC\\s+)",
            "(?<=END-EXEC)\\s*(?=\\w)",
            "(?<=END-IF)\\s*(?=\\w)",
            "(?<=END-EVALUATE)\\s*(?=\\w)"
        };
        
        String current = content;
        for (String pattern : splitPatterns) {
            String[] parts = current.split(pattern);
            if (parts.length > 1) {
                statements.clear();
                for (String part : parts) {
                    if (!part.trim().isEmpty()) {
                        statements.add(part.trim());
                    }
                }
                break;
            }
        }
        
        // If no split occurred, return original
        if (statements.isEmpty()) {
            statements.add(content);
        }
        
        return statements;
    }
    
    private boolean isStatementStart(String line) {
        String upper = line.toUpperCase().trim();
        
        // Enhanced statement start patterns
        return upper.matches("^(PERFORM|MOVE|IF|ELSE|EXEC|OPEN|CLOSE|READ|WRITE|" +
                            "DISPLAY|ACCEPT|ADD|SUBTRACT|MULTIPLY|DIVIDE|COMPUTE|" +
                            "SET|EVALUATE|SEARCH|CALL|STRING|UNSTRING|INSPECT|" +
                            "SORT|MERGE|GOBACK|EXIT|INITIALIZE|COPY|WHEN|UNTIL)\\s+.*") ||
               upper.matches("^\\d+\\s+(PERFORM|MOVE|IF|EXEC)\\s+.*"); // Line numbers
    }
    
    private boolean isStatementEnd(String line) {
        String trimmed = line.trim();
        
        return trimmed.endsWith(".") || 
               trimmed.toUpperCase().matches(".*(END-[A-Z]+)\\s*\\.?\\s*$") ||
               trimmed.toUpperCase().equals("ELSE") ||
               trimmed.toUpperCase().matches("WHEN\\s+.*");
    }
    
    /**
     * Check if line is a procedure header using configuration
     */
    private boolean isConfigurableProcedureHeader(String line) {
        return extractProcedureNameFromLine(line) != null;
    }
    
    private String determineConfigurableStatementType(String line) {
        String upper = line.toUpperCase().trim();
        
        // Check configured patterns first
        for (Map.Entry<String, List<Pattern>> entry : config.getStatementPatterns().entrySet()) {
            for (Pattern pattern : entry.getValue()) {
                if (pattern.matcher(upper).matches()) {
                    if (config.isVerboseLogging()) {
                        System.out.println("      🎯 Matched " + entry.getKey() + " pattern: " + pattern.pattern());
                    }
                    return entry.getKey();
                }
            }
        }
        
        // Fallback to hardcoded patterns -- YK: need to rethink 
        if (upper.matches("^\\s*PERFORM\\s+.*")) return "PERFORM";
        if (upper.matches("^\\s*MOVE\\s+.*")) return "MOVE";
        if (upper.matches("^\\s*EXEC\\s+SQL\\s+.*")) return "EXEC_SQL";
        if (upper.matches("^\\s*IF\\s+.*")) return "IF";
        if (upper.matches("^\\s*SET\\s+.*")) return "SET";
        if (upper.matches("^\\s*EVALUATE\\s+.*")) return "EVALUATE";
        if (upper.matches("^\\s*INITIALIZE\\s+.*")) return "INITIALIZE";
        if (upper.matches("^\\s*ADD\\s+.*")) return "ADD";
        if (upper.matches("^\\s*CONTINUE\\s*")) return "CONTINUE";
        
        // Default to END_CLAUSE for clause endings
        if (upper.matches(".*(END-[A-Z]+|WHEN|ELSE|THEN|UNTIL).*")) {
            return "END_CLAUSE";
        }
        
        return "STATEMENT"; // Generic fallback
    }
    
    private void extractConfigurablePerformReferences(String line) {
        String upper = line.toUpperCase().trim();
        
        // Enhanced patterns with proper word boundaries
        Pattern[] performPatterns = {
            Pattern.compile("\\bPERFORM\\s+([A-Za-z][A-Za-z0-9-_]*)(?=\\s|\\.|$)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("\\bPERFORM\\s+([A-Za-z][A-Za-z0-9-_]*)\\s+(?:THRU|THROUGH)\\s+([A-Za-z][A-Za-z0-9-_]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("\\bPERFORM\\s+([A-Za-z][A-Za-z0-9-_]*)\\s+UNTIL\\s+.*", Pattern.CASE_INSENSITIVE)
        };
        
        for (Pattern pattern : performPatterns) {
            Matcher matcher = pattern.matcher(upper);
            if (matcher.find()) {
                // Extract all capture groups (for THRU patterns)
                for (int i = 1; i <= matcher.groupCount(); i++) {
                    String target = matcher.group(i);
                    if (target != null && !target.trim().isEmpty()) {
                        // Normalize the target name
                        String normalizedTarget = normalizeIdentifier(target);
                        
                        if (isValidProcedureName(normalizedTarget)) {
                            // Store in both original case and normalized form
                            performReferences.put(normalizedTarget.toUpperCase(), 
                                               performReferences.getOrDefault(normalizedTarget.toUpperCase(), 0) + 1);
                            
                            if (config.isVerboseLogging()) {
                                System.out.println("      🎯 PERFORM reference: " + normalizedTarget);
                            }
                        }
                    }
                }
                break; // Stop after first match
            }
        }
    }
    
    private String normalizeIdentifier(String identifier) {
        // Remove punctuation and normalize spacing
        return identifier.replaceAll("[^A-Za-z0-9-_]", "").trim();
    }
    
    
    
    private void incrementStatementCount(String type) {
        statementCounts.put(type, statementCounts.getOrDefault(type, 0) + 1);
    }
    
    // MISSING ERROR RECOVERY METHODS
    private void skipToNextProcedureDivision(Parser recognizer) {
        TokenStream tokens = recognizer.getInputStream();
        int currentIndex = recognizer.getCurrentToken().getTokenIndex();
        
        // Look ahead for PROCEDURE DIVISION
        for (int i = currentIndex; i < tokens.size() - 1; i++) {
            Token token = tokens.get(i);
            String tokenText = token.getText().toUpperCase();
            
            if ("PROCEDURE".equals(tokenText)) {
                // Check if next token is DIVISION
                Token nextToken = tokens.get(i + 1);
                if ("DIVISION".equals(nextToken.getText().toUpperCase())) {
                    // Found PROCEDURE DIVISION, seek to this position
                    for (int j = currentIndex; j < i; j++) {
                        recognizer.consume();
                    }
                    return;
                }
            }
        }
        
        // If no PROCEDURE DIVISION found, skip to end
        while (recognizer.getCurrentToken().getType() != Token.EOF) {
            recognizer.consume();
        }
    }
    
    private void skipDataDefinition(Parser recognizer) {
        TokenStream tokens = recognizer.getInputStream();
        int currentIndex = recognizer.getCurrentToken().getTokenIndex();
        
        // Skip until we find a period or division boundary
        for (int i = currentIndex; i < tokens.size(); i++) {
            Token token = tokens.get(i);
            String tokenText = token.getText().toUpperCase();
            
            // Stop at period (end of data definition)
            if (".".equals(tokenText)) {
                // Consume tokens up to and including the period
                for (int j = currentIndex; j <= i; j++) {
                    recognizer.consume();
                }
                return;
            }
            
            // Stop at division boundaries
            if ("PROCEDURE".equals(tokenText) || "WORKING-STORAGE".equals(tokenText) ||
                "FILE".equals(tokenText) || "LINKAGE".equals(tokenText)) {
                // Consume tokens up to (but not including) the division
                for (int j = currentIndex; j < i; j++) {
                    recognizer.consume();
                }
                return;
            }
        }
        
        // If nothing found, consume one token to make progress
        recognizer.consume();
    }
    
    private boolean isExcludedByConfig(String name) 
    {
        if (name == null || name.trim().isEmpty()) {
            return true;
        }
        
        String upperName = name.toUpperCase();
        
        // Check direct exclusions
        if (config.getExcludedNames().contains(upperName)) {
            return true;
        }
        
        // Pattern-based exclusions
        
        // Exclude END-* clauses
        if (upperName.startsWith("END-")) {
            return true;
        }
        
        // Exclude variable-like names (start with ws, ls, fd, etc.)
        if (upperName.matches("^(WS|LS|FD|SD)[A-Z].*")) {
            return true;
        }
        
        // Exclude very short names (likely not procedures)
        if (name.length() <= 2) {
            return true;
        }
        
        // Exclude names that are all caps and very long (likely constants)
        if (upperName.equals(name) && name.length() > 25) {
            return true;
        }
        
        return false;
    }

    
    /**
     * Save enhanced AST with data division information
     */
    private static void saveEnhancedAST(StructuralAnalysisResultV2 result, String filename) {
        try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
            writer.println("(CONFIGURABLE-GRAMMAR-ENHANCED-COBOL-ANALYSIS \"" + result.getProgramName() + "\"");
            writer.println("  (METADATA");
            writer.println("    (ANALYSIS-TYPE \"CONFIGURABLE-HYBRID-GRAMMAR\")");
            writer.println("    (TIMESTAMP \"" + new java.util.Date() + "\")");
            writer.println("    (PROCEDURES-COUNT " + result.getProcedures().size() + ")");
            writer.println("    (DATA-ITEMS-COUNT " + result.getDataItems().size() + ")");
            writer.println("    (FILE-DESCRIPTORS-COUNT " + result.getFileDescriptors().size() + ")");
            writer.println("    (SQL-STATEMENTS-COUNT " + result.getSqlStatements().size() + ")");
            writer.println("    (COPY-STATEMENTS-COUNT " + result.getCopyStatements().size() + ")");
            writer.println("    (STATEMENT-TYPES-COUNT " + result.getStatementCounts().size() + ")");
            writer.println("    (TOTAL-STATEMENTS " + 
                result.getStatementCounts().values().stream().mapToInt(Integer::intValue).sum() + ")");
            writer.println("  )");
            
            // Data Division section
            if (!result.getDataItems().isEmpty()) {
                writer.println("  (DATA-DIVISION");
                
                // Group by section
                Map<String, List<StructuralDataItemV2>> itemsBySection = result.getDataItems().stream()
                    .collect(Collectors.groupingBy(
                        item -> item.getSection() != null ? item.getSection() : "UNKNOWN"
                    ));
                
                for (Map.Entry<String, List<StructuralDataItemV2>> entry : itemsBySection.entrySet()) {
                    writer.println("    (SECTION \"" + entry.getKey() + "\"");
                    
                    for (StructuralDataItemV2 item : entry.getValue()) {
                        writer.println("      (DATA-ITEM");
                        writer.println("        (NAME \"" + item.getName() + "\")");
                        writer.println("        (LEVEL " + item.getLevel() + ")");
                        writer.println("        (LINE " + item.getLineNumber() + ")");
                        if (item.getPicture() != null) {
                            writer.println("        (PICTURE \"" + item.getPicture() + "\")");
                        }
                        if (item.getValue() != null) {
                            writer.println("        (VALUE \"" + item.getValue().replace("\"", "\\\"") + "\")");
                        }
                        if (item.getUsage() != null) {
                            writer.println("        (USAGE \"" + item.getUsage() + "\")");
                        }
                        if (item.getOccurs() != null) {
                            writer.println("        (OCCURS \"" + item.getOccurs() + "\")");
                        }
                        if (item.getRedefines() != null) {
                            writer.println("        (REDEFINES \"" + item.getRedefines() + "\")");
                        }
                        writer.println("      )");
                    }
                    
                    writer.println("    )");
                }
                
                writer.println("  )");
            }
            
            // File descriptors section
            if (!result.getFileDescriptors().isEmpty()) {
                writer.println("  (FILE-DESCRIPTORS");
                for (DataDivisionPreprocessor.FileDescriptor fd : result.getFileDescriptors()) {
                    writer.println("    (FILE-DESCRIPTOR");
                    writer.println("      (NAME \"" + fd.getName() + "\")");
                    writer.println("      (LINE " + fd.getLineNumber() + ")");
                    writer.println("      (DEFINITION \"" + fd.getDefinition().replace("\"", "\\\"") + "\")");
                    writer.println("    )");
                }
                writer.println("  )");
            }
            
            // Enhanced procedures with configurable scoring details
            writer.println("  (PROCEDURES");
            for (StructuralProcedureV2 proc : result.getProcedures()) {
                writer.println("    (PROCEDURE \"" + proc.getName() + "\"");
                writer.println("      (SCORE " + proc.getContextScore() + ")");
                writer.println("      (START-LINE " + proc.getLineNumber() + ")");
                writer.println("      (END-LINE " + proc.getEndLineNumber() + ")");
                writer.println("      (REASONING \"" + proc.getReasoningInfo() + "\")");
                int actualRefCount = getActualPerformReferenceCount(proc.getName(), result.getPerformReferences());
                writer.println("      (PERFORM-REFERENCES " + actualRefCount + ")");
        
                // Statement analysis for this procedure
                Map<String, Long> procStmtTypes = proc.getStatements().stream()
                    .collect(Collectors.groupingBy(StructuralStatementV2::getType, Collectors.counting()));
                
                writer.println("      (STATEMENT-DISTRIBUTION");
                procStmtTypes.entrySet().stream()
                    .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                    .forEach(entry -> writer.println("        (" + entry.getKey() + " " + entry.getValue() + ")"));
                writer.println("      )");
                
                writer.println("      (STATEMENTS");
                for (StructuralStatementV2 stmt : proc.getStatements()) {
                    String content = stmt.getContent().replace("\"", "\\\"").replace("\n", "\\n");
                    if (content.length() > 150) {
                        content = content.substring(0, 147) + "...";
                    }
                    writer.println("        (" + stmt.getType() + " \"" + content + "\" " + stmt.getLineNumber() + ")");
                }
                writer.println("      )");
                writer.println("    )");
            }
            writer.println("  )");
            
            // Comprehensive statement analysis
            writer.println("  (STATEMENT-ANALYSIS");
            writer.println("    (STATEMENT-DISTRIBUTION");
            result.getStatementCounts().entrySet().stream()
                .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
                .forEach(entry -> writer.println("      (" + entry.getKey() + " " + entry.getValue() + ")"));
            writer.println("    )");
            writer.println("  )");
            
            // PERFORM reference graph
            writer.println("  (PERFORM-GRAPH");
            result.getPerformReferences().entrySet().stream()
                .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
                .forEach(entry -> writer.println("    (\"" + entry.getKey() + "\" " + entry.getValue() + ")"));
            writer.println("  )");
            
            // Parse warnings
            if (!result.getParseWarnings().isEmpty()) {
                writer.println("  (PARSE-WARNINGS");
                for (String warning : result.getParseWarnings()) {
                    writer.println("    (WARNING \"" + warning.replace("\"", "\\\"") + "\")");
                }
                writer.println("  )");
            }
            
            writer.println(")");
            
            System.out.println("📄 Enhanced AST saved to: " + filename);
            
        } catch (IOException e) {
            System.err.println("❌ Error saving enhanced AST: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * Helper method to get actual reference count for AST output
     */
    private static int getActualPerformReferenceCount(String procName, Map<String, Integer> performReferences) {
        if (procName == null || procName.trim().isEmpty()) {
            return 0;
        }
        
        // Check all variations
        String upperProc = procName.toUpperCase();
        int count = performReferences.getOrDefault(upperProc, 0);
        
        // Check camelCase to COBOL conversion
        String cobolName = procName.replaceAll("([a-z])([A-Z])", "$1$2").toUpperCase();
        count = Math.max(count, performReferences.getOrDefault(cobolName, 0));
        
        // Check with hyphens removed
        count = Math.max(count, performReferences.getOrDefault(upperProc.replace("-", ""), 0));
        
        // Check with underscores removed
        count = Math.max(count, performReferences.getOrDefault(upperProc.replace("_", ""), 0));
        
        return count;
    }

    /**
     * Analyze data complexity
     */
    private void analyzeDataComplexity(List<StructuralDataItemV2> dataItems) {
        System.out.println("\nDATA COMPLEXITY METRICS:");
        
        if (dataItems.isEmpty()) {
            System.out.println("  No data items found");
            return;
        }
        
        // Calculate various metrics
        long structureItems = dataItems.stream().filter(item -> item.getLevel() == 1).count();
        long groupItems = dataItems.stream().filter(item -> item.getLevel() > 1 && item.getLevel() < 88).count();
        long conditionNames = dataItems.stream().filter(item -> item.getLevel() == 88).count();
        long pictureItems = dataItems.stream().filter(item -> item.getPicture() != null).count();
        long valueItems = dataItems.stream().filter(item -> item.getValue() != null).count();
        long redefineItems = dataItems.stream().filter(item -> item.getRedefines() != null).count();
        long arrayItems = dataItems.stream().filter(item -> item.getOccurs() != null).count();
        
        System.out.println("  Record structures (01 level): " + structureItems);
        System.out.println("  Group/Elementary items: " + groupItems);
        System.out.println("  Condition names (88 level): " + conditionNames);
        System.out.println("  Items with PICTURE clause: " + pictureItems);
        System.out.println("  Items with VALUE clause: " + valueItems);
        System.out.println("  REDEFINES usage: " + redefineItems);
        System.out.println("  Array items (OCCURS): " + arrayItems);
        
        // Analyze data types
        long numericItems = dataItems.stream()
            .filter(item -> item.getPicture() != null && item.getPicture().matches(".*[9S].*"))
            .count();
        long alphanumericItems = dataItems.stream()
            .filter(item -> item.getPicture() != null && item.getPicture().matches(".*[X].*"))
            .count();
        
        System.out.println("  Numeric items: " + numericItems);
        System.out.println("  Alphanumeric items: " + alphanumericItems);
        
        // Determine overall complexity
        String complexity = determineDataComplexity(structureItems, groupItems, conditionNames, redefineItems, arrayItems);
        System.out.println("  Overall Data Complexity: " + complexity);
        
        // Section analysis
        Map<String, Long> sectionCounts = dataItems.stream()
            .collect(Collectors.groupingBy(
                item -> item.getSection() != null ? item.getSection() : "UNKNOWN",
                Collectors.counting()
            ));
        
        if (sectionCounts.size() > 1) {
            System.out.println("  Sections used:");
            sectionCounts.forEach((section, count) -> 
                System.out.println("    " + section + ": " + count + " items"));
        }
    }

    /**
     * Determine data complexity based on metrics
     */
    private String determineDataComplexity(long recordStructures, long groupItems, 
                                        long conditionNames, long redefineItems, long arrayItems) {
        int complexityScore = 0;
        
        // Score based on different factors
        if (recordStructures > 20) complexityScore += 3;
        else if (recordStructures > 10) complexityScore += 2;
        else if (recordStructures > 5) complexityScore += 1;
        
        if (groupItems > 100) complexityScore += 3;
        else if (groupItems > 50) complexityScore += 2;
        else if (groupItems > 20) complexityScore += 1;
        
        if (conditionNames > 30) complexityScore += 2;
        else if (conditionNames > 15) complexityScore += 1;
        
        if (redefineItems > 5) complexityScore += 2;
        else if (redefineItems > 0) complexityScore += 1;
        
        if (arrayItems > 10) complexityScore += 2;
        else if (arrayItems > 0) complexityScore += 1;
        
        // Determine complexity level
        if (complexityScore >= 8) return "VERY COMPLEX";
        else if (complexityScore >= 5) return "COMPLEX";
        else if (complexityScore >= 3) return "MODERATE";
        else return "SIMPLE";
    }
    /**
     * Print DATA DIVISION analysis
     */
    private void printDataDivisionAnalysis(StructuralAnalysisResultV2 result) {
        System.out.println("\n=== DATA DIVISION ANALYSIS ===");
        
        // Group data items by section
        Map<String, List<StructuralDataItemV2>> itemsBySection = result.getDataItems().stream()
            .collect(Collectors.groupingBy(
                item -> item.getSection() != null ? item.getSection() : "UNKNOWN"
            ));
        
        for (Map.Entry<String, List<StructuralDataItemV2>> entry : itemsBySection.entrySet()) {
            String section = entry.getKey();
            List<StructuralDataItemV2> items = entry.getValue();
            
            System.out.println("\n" + section + " SECTION (" + items.size() + " items):");
            
            // Group by level for better visualization
            Map<Integer, Long> levelCounts = items.stream()
                .collect(Collectors.groupingBy(StructuralDataItemV2::getLevel, Collectors.counting()));
            
            levelCounts.entrySet().stream()
                .sorted(Map.Entry.comparingByKey())
                .forEach(levelEntry -> 
                    System.out.println("  Level " + String.format("%02d", levelEntry.getKey()) + 
                                    ": " + levelEntry.getValue() + " items"));
            
            if (config.isVerboseLogging()) {
                // Show sample data items
                items.stream()
                    .limit(5)
                    .forEach(item -> System.out.println("    " + 
                        String.format("%02d", item.getLevel()) + " " + item.getName() +
                        (item.getPicture() != null ? " PIC " + item.getPicture() : "") +
                        (item.getValue() != null ? " VALUE " + item.getValue() : "")));
                
                if (items.size() > 5) {
                    System.out.println("    ... and " + (items.size() - 5) + " more");
                }
            }
        }
        
        // File descriptor analysis
        if (!result.getFileDescriptors().isEmpty()) {
            System.out.println("\nFILE DESCRIPTORS:");
            result.getFileDescriptors().forEach(fd -> 
                System.out.println("  📁 " + fd.getName() + " (Line " + fd.getLineNumber() + ")"));
        }
        
        // Data complexity analysis
        analyzeDataComplexity(result.getDataItems());
    }

    //  ConfigurableErrorListener CLASS
    /**
     * Configurable error listener
     */
    private static class ConfigurableErrorListener extends BaseErrorListener {
        private final String phase;
        private final List<String> warnings;
        private final ParserConfiguration config;
        
        public ConfigurableErrorListener(String phase, List<String> warnings, ParserConfiguration config) {
            this.phase = phase;
            this.warnings = warnings;
            this.config = config;
        }
        
        @Override
        public void syntaxError(Recognizer<?, ?> recognizer, Object offendingSymbol,
                               int line, int charPositionInLine, String msg,
                               RecognitionException e) {
            if (config.getErrorRecoveryMode() != ErrorRecoveryMode.IGNORE) {
                String warning = phase + " error at line " + line + ": " + msg;
                warnings.add(warning);
                
                if (config.isVerboseLogging()) {
                    System.err.println("⚠️ " + warning);
                }
            }
        }
    }
    
    static class ProcedureBoundary {
        private String name;
        private int startLine;
        
        public ProcedureBoundary(String name, int startLine) {
            this.name = name;
            this.startLine = startLine;
        }
        
        public String getName() { return name; }
        public int getStartLine() { return startLine; }
    }

}
