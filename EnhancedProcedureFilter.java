/**
 * Enhanced Procedure Filtering Logic
 * This handles false positive detection and filtering for COBOL procedures
 */

import java.util.*;
import java.util.stream.Collectors;

public class EnhancedProcedureFilter {
    
    private final ParserConfiguration config;
    private final EnhancedScoringMechanism scoringMechanism;
    private final Map<String, Integer> performReferences;
    
    public EnhancedProcedureFilter(ParserConfiguration config, 
                                   EnhancedScoringMechanism scoringMechanism,
                                   Map<String, Integer> performReferences) {
        this.config = config;
        this.scoringMechanism = scoringMechanism;
        this.performReferences = performReferences;
    }
    
    /**
     * Enhanced filtering logic
     */
    public List<StructuralProcedureV2> applyEnhancedFiltering(List<StructuralProcedureV2> procedures) {
        if (config.isVerboseLogging()) {
            System.out.println("📊 Enhanced analysis of " + procedures.size() + " procedures");
        }
        
        // Apply enhanced scoring
        for (StructuralProcedureV2 proc : procedures) {
            double score = scoringMechanism.calculateEnhancedScore(proc);
            proc.setContextScore(score);
            
            String reasoning = scoringMechanism.buildEnhancedReasoning(proc);
            proc.setReasoningInfo(reasoning);
            
            if (config.isVerboseLogging()) {
                System.out.println("🔍 ENHANCED: Procedure '" + proc.getName() + "' scored " + 
                                  String.format("%.1f", score) + " (threshold: " + scoringMechanism.getMinimumScore() + ")");
            }
        }
        
        // Apply enhanced filtering
        List<StructuralProcedureV2> filtered = procedures.stream()
                .filter(p -> {
                    boolean passesScore = p.getContextScore() >= scoringMechanism.getMinimumScore();
                    boolean notFalsePositive = !isEnhancedFalsePositive(p);
                    
                    if (!passesScore && config.isVerboseLogging()) {
                        System.out.println("🔍 ENHANCED: '" + p.getName() + "' filtered out - low score (" + 
                                         String.format("%.1f", p.getContextScore()) + ")");
                    }
                    if (!notFalsePositive && config.isVerboseLogging()) {
                        System.out.println("🔍 ENHANCED: '" + p.getName() + "' filtered out - false positive");
                    }
                    
                    return passesScore && notFalsePositive;
                })
                .sorted((a, b) -> Double.compare(b.getContextScore(), a.getContextScore()))
                .collect(Collectors.toList());
        
        if (config.isVerboseLogging()) {
            System.out.println("📊 Enhanced result: " + filtered.size() + " confirmed procedures");
        }
        
        return filtered;
    }
    
    /**
     * Enhanced false positive detection
     */
    public boolean isEnhancedFalsePositive(StructuralProcedureV2 proc) {
        String name = proc.getName();
        String upperName = name.toUpperCase();
        
        // Absolute exclusions - these are never procedures
        String[] absoluteExclusions = {
            "IDENTIFICATION", "ENVIRONMENT", "DATA", "PROCEDURE",
            "FILE-CONTROL", "WORKING-STORAGE", "LINKAGE-SECTION", 
            "FILE-SECTION", "CONFIGURATION", "INPUT-OUTPUT"
        };
        
        for (String exclusion : absoluteExclusions) {
            if (upperName.equals(exclusion)) {
                return true;
            }
        }
        
        // Variable patterns (but allow some exceptions for business names)
        if (upperName.matches("^(WS|LS|FD|SD)[A-Z0-9]+$") && name.length() > 15) {
            return true;
        }
        
        // Very short single-character or two-character names
        if (name.length() <= 2 && !scoringMechanism.isEnhancedMainProcedure(name)) {
            return true;
        }
        
        // Empty procedures with no references and non-business names
        if (proc.getStatements().isEmpty() && 
            getPerformReferenceCount(name) == 0 && 
            calculateBusinessLogicNamingBonus(name) == 0.0) {
            return true;
        }
        
        return false;
    }
    
    /**
     * Helper method to get perform reference count
     */
    private int getPerformReferenceCount(String procName) {
        if (procName == null) return 0;
        
        // Check multiple naming conventions
        String[] variations = {
            procName.toUpperCase(),
            procName.toLowerCase(),
            procName.replaceAll("([a-z])([A-Z])", "$1$2").toUpperCase(),
            procName.replace("-", "").toUpperCase(),
            procName.replace("_", "").toUpperCase()
        };
        
        return Arrays.stream(variations)
            .mapToInt(variant -> performReferences.getOrDefault(variant, 0))
            .max()
            .orElse(0);
    }
    
    /**
     * Helper method to calculate business logic naming bonus (simplified version)
     */
    private double calculateBusinessLogicNamingBonus(String procName) {
        String lowerName = procName.toLowerCase();
        
        // Business logic patterns
        String[] businessPatterns = {
            "process", "validate", "calculate", "transform", "convert",
            "initialize", "read", "write", "open", "close", "file",
            "main", "start", "begin", "end", "finish", "complete"
        };
        
        for (String pattern : businessPatterns) {
            if (lowerName.contains(pattern)) {
                return 10.0; // Simple bonus for any business pattern
            }
        }
        
        return 0.0;
    }
    
    /**
     * Check if procedure name matches exclusion patterns
     */
    public boolean isExcludedByConfig(String name) {
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
     * Enhanced false positive procedure detection (legacy support)
     */
    public boolean isFalsePositiveProcedure(StructuralProcedureV2 proc) {
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
            !scoringMechanism.isEnhancedMainProcedure(name)) {
            return true;
        }
        
        return false;
    }
}

