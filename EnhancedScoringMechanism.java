/**
 * Enhanced Scoring Mechanism for COBOL Procedure Detection
 * This replaces the existing scoring methods in EnhancedASTParser.java
 */

import java.util.*;
import java.util.stream.Collectors;

public class EnhancedScoringMechanism {
    
    private final ParserConfiguration config;
    private final String[] sourceLines;
    private final Map<String, Integer> performReferences;
    
    // Enhanced minimum score threshold - more lenient but still filters noise
    private static final double ENHANCED_MINIMUM_SCORE = 35.0;
    
    public EnhancedScoringMechanism(ParserConfiguration config, String[] sourceLines, 
                                   Map<String, Integer> performReferences) {
        this.config = config;
        this.sourceLines = sourceLines;
        this.performReferences = performReferences;
    }
    
    /**
     * Enhanced scoring algorithm that considers multiple factors intelligently
     */
    public double calculateEnhancedScore(Object procObj) {
        double score = 0.0;
        
        String procName;
        List<?> statements;
        int lineNumber;
        
        if (procObj instanceof StructuralProcedureV2) {
            StructuralProcedureV2 proc = (StructuralProcedureV2) procObj;
            procName = proc.getName();
            statements = proc.getStatements();
            lineNumber = proc.getLineNumber();
        } else if (procObj instanceof CobolProcedure2) {
            CobolProcedure2 proc = (CobolProcedure2) procObj;
            procName = proc.getName();
            statements = proc.getStatements();
            lineNumber = proc.getLineNumber();
        } else {
            return 0.0;
        }
        
        // 1. BASE SCORE - Start with reasonable baseline
        score += 30.0;
        
        // 2. PROCEDURE DIVISION BONUS - Major boost for being in procedure division
        if (isProcedureDivisionProcedure(lineNumber)) {
            score += 25.0;
        }
        
        // 3. BUSINESS LOGIC NAMING PATTERNS - Recognize common COBOL procedure patterns
        score += calculateBusinessLogicNamingBonus(procName);
        
        // 4. STATEMENT ANALYSIS - Smarter statement evaluation
        score += calculateSmartStatementScore(statements);
        
        // 5. PERFORM REFERENCE ANALYSIS - Weighted but not overweighted
        score += calculateBalancedPerformScore(procName);
        
        // 6. SPECIAL STATEMENT BONUSES - Database, file operations, etc.
        score += calculateSpecialStatementBonuses(procObj);
        
        // 7. STATEMENT DIVERSITY - Reward varied statement types
        score += calculateStatementDiversityScore(statements);
        
        // 8. COBOL CONVENTION COMPLIANCE - Reward proper COBOL naming
        score += calculateCobolConventionScore(procName);
        
        // 9. CONTEXT PENALTIES - Penalize obvious false positives
        score -= calculateFalsePositivePenalties(procName, statements, lineNumber);
        
        return Math.max(score, 0.0); // Ensure non-negative score
    }
    
    /**
     * Check if procedure is actually in PROCEDURE DIVISION
     */
    private boolean isProcedureDivisionProcedure(int lineNumber) {
        // Look backwards to find PROCEDURE DIVISION
        for (int i = lineNumber - 1; i >= 0 && i < sourceLines.length; i--) {
            String line = sourceLines[i].toUpperCase().trim();
            if (line.contains("PROCEDURE DIVISION")) {
                return true;
            }
            // Stop if we hit another division
            if (line.contains("DATA DIVISION") || 
                line.contains("ENVIRONMENT DIVISION") ||
                line.contains("IDENTIFICATION DIVISION")) {
                return false;
            }
        }
        return false;
    }
    
    /**
     * Enhanced business logic naming pattern recognition
     */
    private double calculateBusinessLogicNamingBonus(String procName) {
        double bonus = 0.0;
        String lowerName = procName.toLowerCase();
        
        // High-value business logic patterns (20 points)
        String[] highValuePatterns = {
            "process", "validate", "calculate", "transform", "convert",
            "initialize", "termination", "cleanup", "setup", "mainline"
        };
        for (String pattern : highValuePatterns) {
            if (lowerName.contains(pattern)) {
                bonus += 20.0;
                break;
            }
        }
        
        // Medium-value I/O patterns (15 points)
        String[] ioPatterns = {
            "read", "write", "open", "close", "file", "input", "output",
            "load", "save", "fetch", "get", "put"
        };
        for (String pattern : ioPatterns) {
            if (lowerName.contains(pattern)) {
                bonus += 15.0;
                break;
            }
        }
        
        // Database/data patterns (15 points)
        String[] dataPatterns = {
            "sql", "select", "insert", "update", "delete", "database",
            "table", "record", "data", "entity"
        };
        for (String pattern : dataPatterns) {
            if (lowerName.contains(pattern)) {
                bonus += 15.0;
                break;
            }
        }
        
        // Business domain patterns (10 points)
        String[] domainPatterns = {
            "customer", "order", "product", "account", "transaction",
            "header", "detail", "trailer", "summary", "report"
        };
        for (String pattern : domainPatterns) {
            if (lowerName.contains(pattern)) {
                bonus += 10.0;
                break;
            }
        }
        
        // Control flow patterns (15 points)
        String[] controlPatterns = {
            "main", "start", "begin", "end", "finish", "complete",
            "check", "verify", "control", "manage"
        };
        for (String pattern : controlPatterns) {
            if (lowerName.contains(pattern)) {
                bonus += 15.0;
                break;
            }
        }
        
        return bonus;
    }
    
    /**
     * Smarter statement scoring that considers quality, not just quantity
     */
    private double calculateSmartStatementScore(List<?> statements) {
        double score = 0.0;
        int stmtCount = statements.size();
        
        // Base score for having statements
        if (stmtCount > 0) {
            score += 10.0;
        }
        
        // Progressive scoring - diminishing returns for very large procedures
        if (stmtCount >= 1) score += 5.0;   // 1+ statements
        if (stmtCount >= 3) score += 5.0;   // 3+ statements  
        if (stmtCount >= 5) score += 5.0;   // 5+ statements
        if (stmtCount >= 10) score += 5.0;  // 10+ statements
        if (stmtCount >= 20) score += 5.0;  // 20+ statements
        if (stmtCount >= 50) score += 5.0;  // 50+ statements
        
        // Penalty for extremely short procedures (likely false positives)
        if (stmtCount == 1) {
            score -= 5.0;
        }
        
        // Bonus for moderate-sized procedures (sweet spot)
        if (stmtCount >= 5 && stmtCount <= 30) {
            score += 10.0;
        }
        
        return score;
    }
    
    /**
     * Balanced PERFORM reference scoring - important but not dominating
     */
    private double calculateBalancedPerformScore(String procName) {
        int refCount = getPerformReferenceCount(procName);
        
        if (refCount == 0) {
            // Not all procedures are called via PERFORM - don't penalize heavily
            return 0.0;
        } else if (refCount == 1) {
            return 8.0;  // Single reference is still valuable
        } else if (refCount <= 3) {
            return 15.0; // Multiple references are very good
        } else {
            return 20.0; // Many references are excellent
        }
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
     * Enhanced special statement bonuses
     */
    private double calculateSpecialStatementBonuses(Object procObj) {
        double bonus = 0.0;
        Map<String, Long> stmtTypeCount;
        
        if (procObj instanceof StructuralProcedureV2) {
            StructuralProcedureV2 proc = (StructuralProcedureV2) procObj;
            stmtTypeCount = proc.getStatements().stream()
                .collect(Collectors.groupingBy(StructuralStatementV2::getType, Collectors.counting()));
        } else if (procObj instanceof CobolProcedure2) {
            CobolProcedure2 proc = (CobolProcedure2) procObj;
            stmtTypeCount = proc.getStatements().stream()
                .collect(Collectors.groupingBy(CobolStatement2::getType, Collectors.counting()));
        } else {
            return 0.0;
        }
        
        // Database operations (high value)
        if (stmtTypeCount.containsKey("EXEC_SQL")) bonus += 15.0;
        
        // File operations (high value)
        if (stmtTypeCount.containsKey("OPEN")) bonus += 10.0;
        if (stmtTypeCount.containsKey("CLOSE")) bonus += 10.0;
        if (stmtTypeCount.containsKey("READ")) bonus += 10.0;
        if (stmtTypeCount.containsKey("WRITE")) bonus += 10.0;
        
        // Control structures (medium value)
        if (stmtTypeCount.containsKey("IF")) bonus += 5.0;
        if (stmtTypeCount.containsKey("EVALUATE")) bonus += 8.0;
        if (stmtTypeCount.containsKey("PERFORM")) bonus += 5.0;
        
        // Data manipulation (medium value)
        if (stmtTypeCount.containsKey("MOVE")) bonus += 3.0;
        if (stmtTypeCount.containsKey("COMPUTE")) bonus += 5.0;
        if (stmtTypeCount.containsKey("ADD")) bonus += 3.0;
        if (stmtTypeCount.containsKey("SUBTRACT")) bonus += 3.0;
        if (stmtTypeCount.containsKey("MULTIPLY")) bonus += 3.0;
        if (stmtTypeCount.containsKey("DIVIDE")) bonus += 3.0;
        
        // String operations (lower value but still relevant)
        if (stmtTypeCount.containsKey("STRING")) bonus += 3.0;
        if (stmtTypeCount.containsKey("UNSTRING")) bonus += 3.0;
        if (stmtTypeCount.containsKey("INSPECT")) bonus += 3.0;
        
        // Initialization and setup
        if (stmtTypeCount.containsKey("INITIALIZE")) bonus += 5.0;
        if (stmtTypeCount.containsKey("ACCEPT")) bonus += 3.0;
        if (stmtTypeCount.containsKey("DISPLAY")) bonus += 2.0;
        
        return bonus;
    }
    
    /**
     * Statement diversity scoring - reward procedures with varied operations
     */
    private double calculateStatementDiversityScore(List<?> statements) {
        Set<String> stmtTypes = statements.stream()
            .map(s -> (s instanceof StructuralStatementV2) ? 
                ((StructuralStatementV2) s).getType() : 
                ((CobolStatement2) s).getType())
            .collect(Collectors.toSet());
        
        int uniqueTypes = stmtTypes.size();
        
        if (uniqueTypes >= 1) return 2.0;
        if (uniqueTypes >= 3) return 4.0;
        if (uniqueTypes >= 5) return 8.0;
        if (uniqueTypes >= 8) return 12.0;
        
        return 0.0;
    }
    
    /**
     * COBOL naming convention compliance scoring
     */
    private double calculateCobolConventionScore(String procName) {
        double score = 0.0;
        
        // Proper length (3-30 characters is typical)
        if (procName.length() >= 3 && procName.length() <= 30) {
            score += 5.0;
        }
        
        // Starts with letter
        if (Character.isLetter(procName.charAt(0))) {
            score += 5.0;
        }
        
        // Uses proper COBOL characters (letters, numbers, hyphens)
        if (procName.matches("[A-Za-z][A-Za-z0-9-]*")) {
            score += 5.0;
        }
        
        // CamelCase or kebab-case (modern COBOL style)
        if (procName.matches(".*[a-z][A-Z].*") || procName.contains("-")) {
            score += 3.0;
        }
        
        // Not all uppercase (unless very short)
        if (procName.length() > 5 && !procName.equals(procName.toUpperCase())) {
            score += 2.0;
        }
        
        return score;
    }
    
    /**
     * False positive penalties to reduce noise
     */
    private double calculateFalsePositivePenalties(String procName, List<?> statements, int lineNumber) {
        double penalty = 0.0;
        String upperName = procName.toUpperCase();
        
        // Division/Section headers (major penalty)
        String[] divisionHeaders = {
            "IDENTIFICATION", "ENVIRONMENT", "DATA", "PROCEDURE",
            "FILE-CONTROL", "WORKING-STORAGE", "LINKAGE-SECTION", 
            "FILE-SECTION", "CONFIGURATION", "INPUT-OUTPUT"
        };
        for (String header : divisionHeaders) {
            if (upperName.equals(header) || upperName.contains(header)) {
                penalty += 30.0;
            }
        }
        
        // Variable-like names (medium penalty)
        if (upperName.matches("^(WS|LS|FD|SD)[A-Z].*")) {
            penalty += 20.0;
        }
        
        // Very short names (small penalty)
        if (procName.length() <= 2) {
            penalty += 10.0;
        }
        
        // Empty or nearly empty procedures (medium penalty)
        if (statements.isEmpty()) {
            penalty += 15.0;
        } else if (statements.size() == 1) {
            // Check if the single statement is just a comment or label
            Object stmt = statements.get(0);
            String content = (stmt instanceof StructuralStatementV2) ? 
                ((StructuralStatementV2) stmt).getContent() : 
                ((CobolStatement2) stmt).getContent();
            
            if (content.trim().isEmpty() || content.trim().startsWith("*")) {
                penalty += 10.0;
            }
        }
        
        // END-* patterns (these are usually clause endings, not procedures)
        if (upperName.startsWith("END-")) {
            penalty += 25.0;
        }
        
        // Single word, all caps, common COBOL keywords
        String[] keywords = {
            "FILE", "SECTION", "DIVISION", "WHEN", "ELSE", "THEN",
            "CONTINUE", "EXIT", "STOP", "GOBACK"
        };
        for (String keyword : keywords) {
            if (upperName.equals(keyword)) {
                penalty += 20.0;
            }
        }
        
        return penalty;
    }
    
    /**
     * Enhanced main procedure detection
     */
    public boolean isEnhancedMainProcedure(String name) {
        String lower = name.toLowerCase();
        
        // Main procedure patterns
        String[] mainPatterns = {
            "main", "mainline", "start", "begin", "initialization", 
            "init", "setup", "control", "driver", "master"
        };
        
        for (String pattern : mainPatterns) {
            if (lower.contains(pattern)) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * Enhanced reasoning builder with detailed explanations
     */
    public String buildEnhancedReasoning(Object procObj) {
        List<String> reasons = new ArrayList<>();
        
        String procName;
        List<?> statements;
        int lineNumber;
        
        if (procObj instanceof StructuralProcedureV2) {
            StructuralProcedureV2 proc = (StructuralProcedureV2) procObj;
            procName = proc.getName();
            statements = proc.getStatements();
            lineNumber = proc.getLineNumber();
        } else if (procObj instanceof CobolProcedure2) {
            CobolProcedure2 proc = (CobolProcedure2) procObj;
            procName = proc.getName();
            statements = proc.getStatements();
            lineNumber = proc.getLineNumber();
        } else {
            return "enhanced analysis";
        }
        
        reasons.add("enhanced scoring v2.0");
        
        // Procedure division context
        if (isProcedureDivisionProcedure(lineNumber)) {
            reasons.add("in PROCEDURE DIVISION");
        }
        
        // Business logic naming
        double namingBonus = calculateBusinessLogicNamingBonus(procName);
        if (namingBonus > 0) {
            reasons.add("business logic naming (+" + namingBonus + ")");
        }
        
        // PERFORM references
        int refCount = getPerformReferenceCount(procName);
        if (refCount > 0) {
            reasons.add(refCount + " PERFORM refs");
        }
        
        // Statement analysis
        int stmtCount = statements.size();
        if (stmtCount > 0) {
            Set<String> stmtTypes = statements.stream()
                .map(s -> (s instanceof StructuralStatementV2) ? 
                    ((StructuralStatementV2) s).getType() : 
                    ((CobolStatement2) s).getType())
                .collect(Collectors.toSet());
            
            reasons.add(stmtCount + " stmts, " + stmtTypes.size() + " types");
        }
        
        // Special statements
        Map<String, Long> stmtTypeCount = statements.stream()
            .collect(Collectors.groupingBy(
                s -> (s instanceof StructuralStatementV2) ? 
                    ((StructuralStatementV2) s).getType() : 
                    ((CobolStatement2) s).getType(), 
                Collectors.counting()));
        
        if (stmtTypeCount.containsKey("EXEC_SQL")) {
            reasons.add("SQL operations");
        }
        if (stmtTypeCount.containsKey("READ") || stmtTypeCount.containsKey("WRITE")) {
            reasons.add("file I/O");
        }
        if (stmtTypeCount.containsKey("IF") || stmtTypeCount.containsKey("EVALUATE")) {
            reasons.add("control logic");
        }
        
        // Main procedure detection
        if (isEnhancedMainProcedure(procName)) {
            reasons.add("main procedure pattern");
        }
        
        // Enhancement source
        if (procObj instanceof CobolProcedure2) {
            reasons.add("ProcedureExtractor enhanced");
        }
        
        return String.join(", ", reasons);
    }
    
    /**
     * Get minimum score threshold
     */
    public double getMinimumScore() {
        return ENHANCED_MINIMUM_SCORE;
    }
}

