import java.util.*;


/**
 * Smart LLM Output Generator that provides complete code while managing context limits
 */
public class LLMOutputGenerator {
    
    private static final int MAX_LINES_PER_PROCEDURE = 50; // Configurable limit
    private static final int MAX_TOTAL_CODE_LINES = 500;   // Total code limit
    
    public String generateSmartLLMRepresentation(CobolStructure structure, String originalFile) {
        StringBuilder sb = new StringBuilder();
        
        sb.append("# COBOL to Java Translation Request\n\n");
        sb.append("**Source File:** ").append(originalFile).append("\n");
        sb.append("**Translation Target:** Java\n");
        sb.append("**Generated:** ").append(new Date()).append("\n");
        sb.append("**Analysis Mode:** Complete Code with Smart Chunking\n\n");
        
        // Program identification
        sb.append("## Program Structure Analysis\n\n");
        if (structure.getProgramId() != null) {
            sb.append("**Program ID:** ").append(structure.getProgramId()).append("\n");
        }
        if (structure.getAuthor() != null) {
            sb.append("**Author:** ").append(structure.getAuthor()).append("\n");
        }
        
        // Add data structures (existing logic)
        addDataStructures(sb, structure);
        
        // Smart procedure handling
        sb.append("## Complete Program Logic\n\n");
        addSmartProcedureAnalysis(sb, structure);
        
        // Translation guidance
        addTranslationGuidance(sb, structure);
        
        return sb.toString();
    }
    
    /**
     * Smart procedure analysis that balances completeness with context limits
     */
    private void addSmartProcedureAnalysis(StringBuilder sb, CobolStructure structure) {
        if (structure.getProcedures().isEmpty()) {
            sb.append("*No procedures detected.*\n");
            return;
        }
        
        // Calculate total code lines
        int totalCodeLines = structure.getProcedures().stream()
            .mapToInt(p -> p.getSourceCode().split("\n").length)
            .sum();
        
        sb.append("**Code Analysis Strategy:** ");
        if (totalCodeLines <= MAX_TOTAL_CODE_LINES) {
            sb.append("Complete code included (").append(totalCodeLines).append(" lines)\n\n");
            addCompleteProcedures(sb, structure);
        } else {
            sb.append("Intelligent chunking applied (").append(totalCodeLines).append(" total lines)\n\n");
            addChunkedProcedures(sb, structure);
        }
    }
    
    /**
     * Include complete procedures when total size is manageable
     */
    private void addCompleteProcedures(StringBuilder sb, CobolStructure structure) {
        sb.append("### Complete Procedure Definitions\n\n");
        
        for (CobolProcedure proc : structure.getProcedures()) {
            sb.append("#### ").append(proc.getName()).append("\n");
            sb.append("**Logic Summary:** ").append(proc.getLogicSummary()).append("\n\n");
            
            sb.append("```cobol\n");
            sb.append(proc.getSourceCode().trim()); // COMPLETE CODE
            sb.append("\n```\n\n");
        }
    }
    
    /**
     * Use intelligent chunking for large programs
     */
    private void addChunkedProcedures(StringBuilder sb, CobolStructure structure) {
        // Prioritize procedures by importance
        List<CobolProcedure> prioritizedProcedures = prioritizeProcedures(structure.getProcedures());
        
        sb.append("### High-Priority Procedures (Complete Code)\n\n");
        
        int codeLinesBudget = MAX_TOTAL_CODE_LINES;
        List<CobolProcedure> completeProcedures = new ArrayList<>();
        List<CobolProcedure> summarizedProcedures = new ArrayList<>();
        
        // Allocate budget to most important procedures
        for (CobolProcedure proc : prioritizedProcedures) {
            int procLines = proc.getSourceCode().split("\n").length;
            
            if (procLines <= codeLinesBudget && procLines <= MAX_LINES_PER_PROCEDURE) {
                completeProcedures.add(proc);
                codeLinesBudget -= procLines;
            } else {
                summarizedProcedures.add(proc);
            }
        }
        
        // Show complete code for priority procedures
        for (CobolProcedure proc : completeProcedures) {
            sb.append("#### ").append(proc.getName()).append(" ⭐\n");
            sb.append("**Logic Summary:** ").append(proc.getLogicSummary()).append("\n");
            sb.append("**Translation Priority:** HIGH - Complete code provided\n\n");
            
            sb.append("```cobol\n");
            sb.append(proc.getSourceCode().trim());
            sb.append("\n```\n\n");
        }
        
        // Show summaries for remaining procedures
        if (!summarizedProcedures.isEmpty()) {
            sb.append("### Supporting Procedures (Logic Summaries)\n\n");
            sb.append("*These procedures follow similar patterns to the high-priority ones above.*\n\n");
            
            for (CobolProcedure proc : summarizedProcedures) {
                sb.append("#### ").append(proc.getName()).append("\n");
                sb.append("**Logic Summary:** ").append(proc.getLogicSummary()).append("\n");
                sb.append("**Pattern:** ").append(identifyProcedurePattern(proc)).append("\n");
                
                // Show key business logic lines
                String[] lines = proc.getSourceCode().split("\n");
                List<String> keyLines = extractKeyBusinessLogic(lines);
                
                if (!keyLines.isEmpty()) {
                    sb.append("**Key Operations:**\n");
                    sb.append("```cobol\n");
                    for (String line : keyLines) {
                        sb.append(line).append("\n");
                    }
                    sb.append("```\n");
                }
                sb.append("\n");
            }
        }
    }
    
    /**
     * Prioritize procedures by business importance
     */
    private List<CobolProcedure> prioritizeProcedures(List<CobolProcedure> procedures) {
        return procedures.stream()
            .sorted((p1, p2) -> {
                int score1 = calculateProcedureImportance(p1);
                int score2 = calculateProcedureImportance(p2);
                return Integer.compare(score2, score1); // Descending order
            })
            .collect(java.util.stream.Collectors.toList());
    }
    
    /**
     * Calculate procedure importance score
     */
    private int calculateProcedureImportance(CobolProcedure proc) {
        int score = 0;
        String name = proc.getName().toUpperCase();
        String code = proc.getSourceCode().toUpperCase();
        
        // Main/entry points get highest priority
        if (name.contains("MAIN") || name.contains("INIT") || name.contains("START")) {
            score += 100;
        }
        
        // Business logic procedures
        if (code.contains("CALCULATE") || code.contains("COMPUTE") || code.contains("VALIDATE")) {
            score += 50;
        }
        
        // File I/O operations
        if (code.contains("READ") || code.contains("WRITE") || code.contains("OPEN")) {
            score += 30;
        }
        
        // Decision logic
        if (code.contains("IF") || code.contains("EVALUATE")) {
            score += 20;
        }
        
        // Longer procedures likely have more business logic
        score += Math.min(proc.getSourceCode().split("\n").length, 50);
        
        return score;
    }
    
    /**
     * Identify common procedure patterns for translation guidance
     */
    private String identifyProcedurePattern(CobolProcedure proc) {
        String code = proc.getSourceCode().toUpperCase();
        
        if (code.contains("VALIDATE") || code.contains("CHECK")) {
            return "Input Validation Pattern";
        } else if (code.contains("CALCULATE") || code.contains("COMPUTE")) {
            return "Business Calculation Pattern";
        } else if (code.contains("READ") && code.contains("WRITE")) {
            return "Data Processing Pattern";
        } else if (code.contains("DISPLAY") || code.contains("WRITE")) {
            return "Output Generation Pattern";
        } else if (code.contains("PERFORM")) {
            return "Control Flow Pattern";
        } else {
            return "Utility Pattern";
        }
    }
    
    /**
     * Extract key business logic lines from procedure
     */
    private List<String> extractKeyBusinessLogic(String[] lines) {
        List<String> keyLines = new ArrayList<>();
        
        for (String line : lines) {
            String upperLine = line.trim().toUpperCase();
            
            // Skip comments and empty lines
            if (upperLine.isEmpty() || upperLine.startsWith("*")) {
                continue;
            }
            
            // Include important business operations
            if (upperLine.contains("COMPUTE") || 
                upperLine.contains("CALCULATE") ||
                upperLine.contains("IF") ||
                upperLine.contains("EVALUATE") ||
                upperLine.contains("CALL") ||
                upperLine.contains("PERFORM") ||
                (upperLine.contains("MOVE") && !upperLine.contains("SPACES")) ||
                upperLine.contains("ADD") ||
                upperLine.contains("SUBTRACT") ||
                upperLine.contains("MULTIPLY") ||
                upperLine.contains("DIVIDE")) {
                
                keyLines.add(line.trim());
                
                // Limit to avoid overwhelming output
                if (keyLines.size() >= 10) {
                    break;
                }
            }
        }
        
        return keyLines;
    }
    
    /**
     * Add data structures section
     */
    private void addDataStructures(StringBuilder sb, CobolStructure structure) {
        sb.append("\n## Data Structures\n\n");
        
        if (!structure.getWorkingStorageVariables().isEmpty()) {
            sb.append("### Working Storage Variables\n");
            for (CobolVariable var : structure.getWorkingStorageVariables()) {
                sb.append("- **").append(var.getName()).append("**");
                sb.append(" (Level ").append(var.getLevel()).append(")");
                sb.append(" - Type: ").append(var.getDataType());
                if (var.getPictureClause() != null) {
                    sb.append(", Picture: ").append(var.getPictureClause());
                }
                if (var.getInitialValue() != null) {
                    sb.append(", Initial: ").append(var.getInitialValue());
                }
                sb.append("\n");
            }
            sb.append("\n");
        }
    }
    
    /**
     * Add comprehensive translation guidance
     */
    private void addTranslationGuidance(StringBuilder sb, CobolStructure structure) {
        sb.append("## Java Translation Strategy\n\n");
        
        String className = structure.getProgramId() != null ? 
                toPascalCase(structure.getProgramId()) : "CobolProgram";
        
        sb.append("### Recommended Architecture\n");
        sb.append("```java\n");
        sb.append("public class ").append(className).append(" {\n");
        sb.append("    // Field declarations based on working storage\n");
        
        // Generate field declarations
        int fieldCount = 0;
        for (CobolVariable var : structure.getWorkingStorageVariables()) {
            if (fieldCount >= 5) {
                sb.append("    // ... ").append(structure.getWorkingStorageVariables().size() - 5)
                  .append(" more fields\n");
                break;
            }
            
            String javaType = mapCobolToJavaType(var);
            String fieldName = toCamelCase(var.getName());
            sb.append("    private ").append(javaType).append(" ").append(fieldName);
            
            if (var.getInitialValue() != null && !var.getInitialValue().equals("SPACES")) {
                sb.append(" = ").append(formatJavaInitialValue(var.getInitialValue(), javaType));
            }
            sb.append(";\n");
            fieldCount++;
        }
        
        sb.append("\n    // Method declarations based on procedures\n");
        
        // Generate method signatures
        int methodCount = 0;
        for (CobolProcedure proc : structure.getProcedures()) {
            if (methodCount >= 3) {
                sb.append("    // ... ").append(structure.getProcedures().size() - 3)
                  .append(" more methods\n");
                break;
            }
            
            String methodName = toCamelCase(proc.getName());
            sb.append("    public void ").append(methodName).append("() {\n");
            sb.append("        // TODO: Implement ").append(proc.getName()).append("\n");
            sb.append("        // Logic: ").append(proc.getLogicSummary()).append("\n");
            sb.append("    }\n\n");
            methodCount++;
        }
        
        sb.append("}\n");
        sb.append("```\n\n");
        
        sb.append("### Translation Notes\n");
        sb.append("- **Complete business logic preserved** in high-priority procedures\n");
        sb.append("- **Pattern-based translation** for supporting procedures\n");
        sb.append("- **Data type mappings** provided for all COBOL PICTURE clauses\n");
        sb.append("- **Control flow maintained** through method call structure\n\n");
    }
    
    // Helper methods
    private String toPascalCase(String input) {
        if (input == null || input.isEmpty()) return "CobolProgram";
        String[] parts = input.replace("-", " ").split("\\s+");
        StringBuilder result = new StringBuilder();
        for (String part : parts) {
            if (!part.isEmpty()) {
                result.append(part.substring(0, 1).toUpperCase());
                if (part.length() > 1) {
                    result.append(part.substring(1).toLowerCase());
                }
            }
        }
        return result.toString();
    }
    
    private String toCamelCase(String input) {
        if (input == null || input.isEmpty()) return "unknown";
        String[] parts = input.toLowerCase().replace("-", " ").split("\\s+");
        StringBuilder result = new StringBuilder(parts[0]);
        for (int i = 1; i < parts.length; i++) {
            if (!parts[i].isEmpty()) {
                result.append(parts[i].substring(0, 1).toUpperCase());
                if (parts[i].length() > 1) {
                    result.append(parts[i].substring(1));
                }
            }
        }
        return result.toString();
    }
    
    private String mapCobolToJavaType(CobolVariable var) {
        String dataType = var.getDataType();
        String picture = var.getPictureClause();
        
        if ("ALPHANUMERIC".equals(dataType)) {
            return "String";
        } else if ("NUMERIC_DECIMAL".equals(dataType)) {
            return "BigDecimal";
        } else if ("NUMERIC_INTEGER".equals(dataType)) {
            if (picture != null && picture.length() > 4) {
                return "long";
            } else {
                return "int";
            }
        } else {
            return "String"; // Default
        }
    }
    
    private String formatJavaInitialValue(String cobolValue, String javaType) {
        if (cobolValue == null) return "null";
        
        cobolValue = cobolValue.trim();
        
        if ("String".equals(javaType)) {
            if (cobolValue.startsWith("\"") && cobolValue.endsWith("\"")) {
                return cobolValue;
            } else {
                return "\"" + cobolValue.replace("\"", "\\\"") + "\"";
            }
        } else if ("BigDecimal".equals(javaType)) {
            return "new BigDecimal(\"" + cobolValue.replace("\"", "") + "\")";
        } else {
            return cobolValue.replace("\"", "");
        }
    }
}

