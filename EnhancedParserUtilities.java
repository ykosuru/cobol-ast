/**
 * Enhanced Parser Utilities
 * Helper methods and utility functions for the ASTParser
 */

import java.io.*;
import java.util.*;
import java.util.regex.Pattern;
import java.util.regex.Matcher;
import java.util.stream.Collectors;

public class EnhancedParserUtilities {
    
    private final ParserConfiguration config;
    private final String[] sourceLines;
    private final Map<String, Integer> performReferences;
    private final Map<String, Integer> statementCounts;
    
    public EnhancedParserUtilities(ParserConfiguration config, String[] sourceLines, 
                                   Map<String, Integer> performReferences, 
                                   Map<String, Integer> statementCounts) {
        this.config = config;
        this.sourceLines = sourceLines;
        this.performReferences = performReferences;
        this.statementCounts = statementCounts;
    }
    
    /**
     * Read source lines from file
     */
    public static String[] readSourceLines(String filename) throws IOException {
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
     * Enhanced preprocessWithConfigurableRegex with more debug output
     */
    public List<ProcedureBoundary> preprocessWithConfigurableRegex(String[] sourceToProcess) throws IOException {
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
    
    /**
     * Extract procedure name from line using configured patterns
     */
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
    
    /**
     * Validate procedure name
     */
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
     * Check if name is excluded by configuration
     */
    private boolean isExcludedByConfig(String name) {
        if (name == null || name.trim().isEmpty()) {
            return true;
        }
        
        String upperName = name.toUpperCase();
        
        // Check direct exclusions from config
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
     * Enhanced shouldUseHybridMode with debug output
     */
    public boolean shouldUseHybridMode(List<ProcedureBoundary> regexProcedures, int grammarProcedureCount) {
        if (!config.isHybridModeEnabled()) {
            System.out.println("🔍 DEBUG: Hybrid mode disabled in config");
            return false;
        }
        
        if (regexProcedures.isEmpty()) {
            System.out.println("🔍 DEBUG: No regex procedures found, skipping hybrid");
            return false;
        }
        
        double ratio = (double) grammarProcedureCount / regexProcedures.size();
        boolean useHybrid = ratio < config.getHybridThreshold();
        
        System.out.println("🔍 DEBUG: Hybrid decision:");
        System.out.println("  - Grammar procedures: " + grammarProcedureCount);
        System.out.println("  - Regex procedures: " + regexProcedures.size());
        System.out.println("  - Ratio: " + String.format("%.2f", ratio));
        System.out.println("  - Threshold: " + config.getHybridThreshold());
        System.out.println("  - Use hybrid: " + useHybrid);
        
        return useHybrid;
    }
    
    /**
     * Calculate configurable end line
     */
    public int calculateConfigurableEndLine(int startLine) {
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
    
    /**
     * Check if we're in PROCEDURE DIVISION context
     */
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
    public String determineProgramName(String currentProgramName) {
        // First try grammar-extracted name
        if (!currentProgramName.isEmpty() && !"UNKNOWN".equals(currentProgramName)) {
            return currentProgramName;
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
     * Create procedure from regex boundary using configurable analysis
     */
    public StructuralProcedureV2 createProcedureFromConfigurableRegex(ProcedureBoundary boundary) {
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
     * Extract statements from source with configurable patterns
     */
    public List<StructuralStatementV2> extractConfigurableStatementsFromSource(int startLine, int endLine) {
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
    
    /**
     * Process accumulated statement lines
     */
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
                    StructuralStatementV2 statement = StatementInitializer.createInitializedStatement(
                        statementType, stmt, startLine);
                    statements.add(statement);
                    
                    incrementStatementCount(statementType);
                    extractConfigurablePerformReferences(stmt);
                }
            }
        }
    }
    
    /**
     * Split compound statements
     */
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
    
    /**
     * Check if line is statement start
     */
    private boolean isStatementStart(String line) {
        String upper = line.toUpperCase().trim();
        
        // Enhanced statement start patterns
        return upper.matches("^(PERFORM|MOVE|IF|ELSE|EXEC|OPEN|CLOSE|READ|WRITE|" +
                            "DISPLAY|ACCEPT|ADD|SUBTRACT|MULTIPLY|DIVIDE|COMPUTE|" +
                            "SET|EVALUATE|SEARCH|CALL|STRING|UNSTRING|INSPECT|" +
                            "SORT|MERGE|GOBACK|EXIT|INITIALIZE|COPY|WHEN|UNTIL)\\s+.*") ||
               upper.matches("^\\d+\\s+(PERFORM|MOVE|IF|EXEC)\\s+.*"); // Line numbers
    }
    
    /**
     * Check if line is statement end
     */
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
    
    /**
     * Determine statement type using configuration
     */
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
        
        // Fallback to hardcoded patterns
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
    
    /**
     * Extract PERFORM references from statement
     */
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
    
    /**
     * Normalize identifier
     */
    private String normalizeIdentifier(String identifier) {
        // Remove punctuation and normalize spacing
        return identifier.replaceAll("[^A-Za-z0-9-_]", "").trim();
    }
    
    /**
     * Increment statement count
     */
    private void incrementStatementCount(String type) {
        statementCounts.put(type, statementCounts.getOrDefault(type, 0) + 1);
    }
}
