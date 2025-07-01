/**
 * Enhanced PERFORM Graph-Ordered COBOL to Modern Java Conversion Prompt Generator
 * Uses AST PERFORM GRAPH + Configurable Pattern Rules to send procedures with transformation guidance
 */

import java.io.*;
import java.util.*;
import java.util.stream.Collectors;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.regex.Pattern;
import java.util.regex.Matcher;

public class PerformGraphPromptGenerator {
    
    private PatternRuleEngine patternRuleEngine;
    
    public static void main(String[] args) {
        if (args.length < 2) {
            System.err.println("Usage: java PerformGraphPromptGenerator <cobol-file> <ast-file> [pattern-rules-file] [output-dir]");
            System.err.println("  pattern-rules-file: JSON file with COBOL->Java transformation patterns (optional)");
            System.exit(1);
        }
        
        try {
            PerformGraphPromptGenerator generator = new PerformGraphPromptGenerator();
            
            System.out.println("🔄 Enhanced PERFORM Graph-Ordered COBOL->Java Conversion");
            System.out.println("📊 Analyzing execution flow from AST...");
            
            // Load pattern rules if provided
            String patternRulesFile = args.length > 2 ? args[2] : null;
            String outputDir = args.length > 3 ? args[3] : "execution_order_prompts/";
            
            if (patternRulesFile != null && !patternRulesFile.equals(outputDir)) {
                System.out.println("📋 Loading pattern transformation rules from: " + patternRulesFile);
                generator.loadPatternRules(patternRulesFile);
            } else {
                System.out.println("📋 Using default pattern transformation rules");
                generator.loadDefaultPatternRules();
            }
            
            ExecutionOrderResult result = generator.generateExecutionOrderPrompts(args[0], args[1], outputDir);
            generator.printResults(result);
            
        } catch (Exception e) {
            System.err.println("❌ Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    /**
     * Load pattern transformation rules from file or use defaults
     */
    public void loadPatternRules(String patternRulesFile) throws IOException {
        if (patternRulesFile != null && Files.exists(Paths.get(patternRulesFile))) {
            String rulesContent = Files.readString(Paths.get(patternRulesFile));
            this.patternRuleEngine = PatternRuleEngine.fromJson(rulesContent);
        } else {
            loadDefaultPatternRules();
        }
    }
    
    /**
     * Load default pattern transformation rules
     */
    public void loadDefaultPatternRules() {
        this.patternRuleEngine = PatternRuleEngine.createDefault();
    }
    
    public ExecutionOrderResult generateExecutionOrderPrompts(String cobolFile, String astFile, String outputDir) 
            throws IOException {
        
        Files.createDirectories(Paths.get(outputDir));
        EnhancedASTData astData = parseAST(astFile);
        String cobolSource = Files.readString(Paths.get(cobolFile));
        ExecutionOrderResult result = new ExecutionOrderResult();
        
        // Initialize pattern rules if not already loaded
        if (patternRuleEngine == null) {
            loadDefaultPatternRules();
        }
        
        // 1. Extract PERFORM GRAPH from AST
        PerformGraph performGraph = extractPerformGraph(astData);
        System.out.println("📈 Found PERFORM GRAPH with " + performGraph.getNodes().size() + " procedures");
        
        // 2. Determine execution order based on call frequency and dependencies
        List<String> executionOrder = determineExecutionOrder(performGraph);
        System.out.println("🔄 Execution order: " + String.join(" → ", executionOrder));
        
        // 3. Analyze architectural patterns for each procedure
        Map<String, ArchitecturalPattern> procedurePatterns = analyzeProcedurePatterns(astData, cobolSource);
        
        // 4. Apply pattern rules to enhance architectural patterns
        enhancePatternsWithRules(procedurePatterns, cobolSource);
        
        // 5. Generate individual procedure prompts in execution order
        int sequenceNumber = 1;
        for (String procedureName : executionOrder) {
            if (procedurePatterns.containsKey(procedureName)) {
                generateSequentialProcedurePrompt(
                    procedureName, 
                    sequenceNumber++, 
                    procedurePatterns.get(procedureName),
                    cobolSource, 
                    astData,
                    outputDir, 
                    result
                );
            }
        }
        
        // 6. Generate pattern rules summary
        generatePatternRulesSummary(outputDir, result);
        
        // 7. Generate final integration prompt
        generateIntegrationPrompt(executionOrder, procedurePatterns, outputDir, result);
        
        return result;
    }
    
    /**
     * Enhance architectural patterns with custom transformation rules
     */
    private void enhancePatternsWithRules(Map<String, ArchitecturalPattern> procedurePatterns, String cobolSource) {
        System.out.println("🎯 Applying pattern transformation rules...");
        
        for (Map.Entry<String, ArchitecturalPattern> entry : procedurePatterns.entrySet()) {
            String procedureName = entry.getKey();
            ArchitecturalPattern pattern = entry.getValue();
            String procedureCode = extractProcedureCode(cobolSource, procedureName);
            
            // Apply pattern rules to enhance the architectural pattern
            List<TransformationRule> applicableRules = patternRuleEngine.findApplicableRules(
                procedureName, procedureCode, pattern.getPrimaryPattern()
            );
            
            // Add transformation guidance from rules
            for (TransformationRule rule : applicableRules) {
                pattern.addTransformationRule(rule);
                
                // Override or enhance Java patterns based on rules
                if (rule.isOverrideMode()) {
                    pattern.clearRecommendedJavaPatterns();
                }
                
                for (String javaPattern : rule.getTargetJavaPatterns()) {
                    pattern.addRecommendedJavaPattern(javaPattern);
                }
                
                // Add specific implementation guidance
                pattern.addImplementationGuidance(rule.getImplementationGuidance());
                
                // Update return type if specified
                if (rule.getTargetReturnType() != null && !rule.getTargetReturnType().isEmpty()) {
                    pattern.setTargetReturnType(rule.getTargetReturnType());
                }
            }
            
            if (!applicableRules.isEmpty()) {
                System.out.println("  ✅ Applied " + applicableRules.size() + " rules to " + procedureName);
            }
        }
    }
    
    /**
     * Generate a summary of all pattern transformation rules for reference
     */
    private void generatePatternRulesSummary(String outputDir, ExecutionOrderResult result) throws IOException {
        StringBuilder summary = new StringBuilder();
        
        summary.append("# Pattern Transformation Rules Reference\n\n");
        summary.append("This document contains all the pattern transformation rules being applied during the COBOL to Java conversion.\n\n");
        
        summary.append("## Active Transformation Rules\n\n");
        
        List<TransformationRule> allRules = patternRuleEngine.getAllRules();
        for (int i = 0; i < allRules.size(); i++) {
            TransformationRule rule = allRules.get(i);
            summary.append("### Rule ").append(i + 1).append(": ").append(rule.getName()).append("\n\n");
            
            summary.append("**Description:** ").append(rule.getDescription()).append("\n\n");
            
            summary.append("**Triggers when:**\n");
            if (!rule.getCobolPatterns().isEmpty()) {
                summary.append("- COBOL patterns: `").append(String.join("`, `", rule.getCobolPatterns())).append("`\n");
            }
            if (!rule.getProcedureNamePatterns().isEmpty()) {
                summary.append("- Procedure names matching: `").append(String.join("`, `", rule.getProcedureNamePatterns())).append("`\n");
            }
            if (!rule.getArchitecturalPatterns().isEmpty()) {
                summary.append("- Architectural patterns: ").append(String.join(", ", rule.getArchitecturalPatterns())).append("\n");
            }
            summary.append("\n");
            
            summary.append("**Recommended Java Patterns:**\n");
            for (String pattern : rule.getTargetJavaPatterns()) {
                summary.append("- ").append(pattern).append("\n");
            }
            summary.append("\n");
            
            if (rule.getTargetReturnType() != null && !rule.getTargetReturnType().isEmpty()) {
                summary.append("**Target Return Type:** `").append(rule.getTargetReturnType()).append("`\n\n");
            }
            
            summary.append("**Implementation Guidance:**\n");
            summary.append(rule.getImplementationGuidance()).append("\n\n");
            
            if (!rule.getCodeExamples().isEmpty()) {
                summary.append("**Code Examples:**\n");
                for (Map.Entry<String, String> example : rule.getCodeExamples().entrySet()) {
                    summary.append("**").append(example.getKey()).append(":**\n");
                    summary.append("```java\n").append(example.getValue()).append("\n```\n\n");
                }
            }
            
            summary.append("---\n\n");
        }
        
        String filename = "00_pattern_rules_reference.md";
        Files.write(Paths.get(outputDir + filename), summary.toString().getBytes());
        result.addPrompt("Pattern Rules Reference", filename);
    }
    
    /**
     * Extract PERFORM GRAPH from AST data
     */
    private PerformGraph extractPerformGraph(EnhancedASTData astData) {
        PerformGraph graph = new PerformGraph();
        
        // Get PERFORM references from AST
        Map<String, Integer> performRefs = astData.getPerformReferences();
        
        for (Map.Entry<String, Integer> entry : performRefs.entrySet()) {
            String procedureName = entry.getKey();
            int callCount = entry.getValue();
            
            graph.addNode(procedureName, callCount);
        }
        
        // Add procedures without explicit PERFORM calls (like mainline)
        for (String procName : astData.getAllProcedureNames()) {
            if (!graph.hasNode(procName)) {
                graph.addNode(procName, 0); // Entry points or called procedures
            }
        }
        
        return graph;
    }
    
    /**
     * Determine logical execution order based on PERFORM frequency and AST analysis
     */
    private List<String> determineExecutionOrder(PerformGraph graph) {
        List<String> executionOrder = new ArrayList<>();
        Set<String> processed = new HashSet<>();
        
        // 1. Identify procedure categories based on call patterns and complexity
        ProcedureClassification classification = classifyProcedures(graph);
        
        // 2. Start with entry points (procedures never called by others or called least)
        List<String> entryPoints = classification.getEntryPoints();
        for (String entryPoint : entryPoints) {
            if (!processed.contains(entryPoint)) {
                executionOrder.add(entryPoint);
                processed.add(entryPoint);
            }
        }
        
        // 3. Add initialization procedures (called early, setup-oriented)
        List<String> initProcedures = classification.getInitializationProcedures();
        for (String proc : initProcedures) {
            if (!processed.contains(proc)) {
                executionOrder.add(proc);
                processed.add(proc);
            }
        }
        
        // 4. Add high-frequency core procedures (most business logic)
        List<String> coreProcedures = classification.getCoreProcedures();
        for (String proc : coreProcedures) {
            if (!processed.contains(proc)) {
                executionOrder.add(proc);
                processed.add(proc);
            }
        }
        
        // 5. Add supporting procedures (moderate frequency)
        List<String> supportProcedures = classification.getSupportProcedures();
        for (String proc : supportProcedures) {
            if (!processed.contains(proc)) {
                executionOrder.add(proc);
                processed.add(proc);
            }
        }
        
        // 6. Add cleanup procedures (called late in process)
        List<String> cleanupProcedures = classification.getCleanupProcedures();
        for (String proc : cleanupProcedures) {
            if (!processed.contains(proc)) {
                executionOrder.add(proc);
                processed.add(proc);
            }
        }
        
        // 7. Add any remaining procedures by call frequency
        List<String> remaining = graph.getNodes().stream()
            .filter(name -> !processed.contains(name))
            .sorted((a, b) -> graph.getCallCount(b) - graph.getCallCount(a))
            .collect(Collectors.toList());
        
        executionOrder.addAll(remaining);
        
        return executionOrder;
    }
    
    /**
     * Classify procedures based on call patterns and characteristics
     */
    private ProcedureClassification classifyProcedures(PerformGraph graph) {
        ProcedureClassification classification = new ProcedureClassification();
        
        // Calculate statistics for intelligent classification
        List<Integer> callCounts = graph.getNodes().stream()
            .map(graph::getCallCount)
            .sorted()
            .collect(Collectors.toList());
        
        if (callCounts.isEmpty()) {
            return classification;
        }
        
        // Statistical thresholds
        int minCalls = callCounts.get(0);
        int maxCalls = callCounts.get(callCounts.size() - 1);
        double avgCalls = callCounts.stream().mapToInt(Integer::intValue).average().orElse(0.0);
        int highFreqThreshold = (int) Math.max(avgCalls, maxCalls * 0.6);
        int mediumFreqThreshold = (int) Math.max(1, avgCalls * 0.5);
        
        // Classify each procedure
        for (String procName : graph.getNodes()) {
            int callCount = graph.getCallCount(procName);
            String nameLower = procName.toLowerCase();
            
            // Entry points: never called or called very rarely
            if (callCount == minCalls && minCalls <= 1) {
                // Additional heuristics for entry points
                if (nameLower.contains("main") || 
                    nameLower.contains("start") ||
                    nameLower.contains("begin") ||
                    callCount == 0) {
                    classification.addEntryPoint(procName);
                    continue;
                }
            }
            
            // Initialization: called early, setup patterns
            if (isInitializationProcedure(procName, callCount, avgCalls)) {
                classification.addInitializationProcedure(procName);
                continue;
            }
            
            // Cleanup: called late, cleanup patterns  
            if (isCleanupProcedure(procName, callCount, avgCalls)) {
                classification.addCleanupProcedure(procName);
                continue;
            }
            
            // Core business logic: high call frequency
            if (callCount >= highFreqThreshold) {
                classification.addCoreProcedure(procName);
                continue;
            }
            
            // Supporting procedures: medium frequency
            if (callCount >= mediumFreqThreshold) {
                classification.addSupportProcedure(procName);
                continue;
            }
            
            // Default: treat as support procedure
            classification.addSupportProcedure(procName);
        }
        
        return classification;
    }
    
    /**
     * Determine if procedure is initialization-oriented
     */
    private boolean isInitializationProcedure(String procName, int callCount, double avgCalls) {
        String nameLower = procName.toLowerCase();
        
        // Semantic indicators
        boolean hasInitSemantics = nameLower.contains("init") ||
                                 nameLower.contains("setup") ||
                                 nameLower.contains("open") ||
                                 nameLower.contains("start") ||
                                 nameLower.contains("begin") ||
                                 nameLower.contains("load") ||
                                 nameLower.contains("read") && nameLower.contains("parm");
        
        // Call pattern: typically called once or few times
        boolean hasInitCallPattern = callCount <= Math.max(2, avgCalls * 0.3);
        
        return hasInitSemantics || (hasInitCallPattern && nameLower.length() > 4);
    }
    
    /**
     * Determine if procedure is cleanup-oriented  
     */
    private boolean isCleanupProcedure(String procName, int callCount, double avgCalls) {
        String nameLower = procName.toLowerCase();
        
        // Semantic indicators
        boolean hasCleanupSemantics = nameLower.contains("term") ||
                                    nameLower.contains("cleanup") ||
                                    nameLower.contains("close") ||
                                    nameLower.contains("end") ||
                                    nameLower.contains("finish") ||
                                    nameLower.contains("stop") ||
                                    nameLower.contains("exit");
        
        // Call pattern: typically called once or few times
        boolean hasCleanupCallPattern = callCount <= Math.max(2, avgCalls * 0.3);
        
        return hasCleanupSemantics || (hasCleanupCallPattern && nameLower.contains("final"));
    }
    
    /**
     * Analyze architectural patterns for each procedure
     */
    private Map<String, ArchitecturalPattern> analyzeProcedurePatterns(EnhancedASTData astData, String cobolSource) {
        Map<String, ArchitecturalPattern> patterns = new HashMap<>();
        
        for (String procName : astData.getAllProcedureNames()) {
            ProcedureInfo procInfo = astData.getProcedureInfo(procName);
            String procCode = extractProcedureCode(cobolSource, procName);
            
            ArchitecturalPattern pattern = identifyPattern(procName, procInfo, procCode);
            patterns.put(procName, pattern);
        }
        
        return patterns;
    }
    
    /**
     * Identify architectural pattern for a procedure
     */
    private ArchitecturalPattern identifyPattern(String procName, ProcedureInfo procInfo, String procCode) {
        ArchitecturalPattern pattern = new ArchitecturalPattern();
        pattern.setProcedureName(procName);
        
        String nameLower = procName.toLowerCase();
        String codeLower = procCode.toLowerCase();
        
        // Analyze primary pattern
        if (nameLower.contains("valid") || codeLower.contains("if ") && codeLower.contains("set ")) {
            pattern.setPrimaryPattern("VALIDATION");
            pattern.addRecommendedJavaPattern("Functional Validation with Predicates");
            pattern.addRecommendedJavaPattern("Chain of Responsibility for complex rules");
            pattern.setTargetReturnType("Mono<ValidationResult>");
        } else if (nameLower.contains("read") || nameLower.contains("file") || codeLower.contains("read ")) {
            pattern.setPrimaryPattern("FILE_PROCESSING");
            pattern.addRecommendedJavaPattern("Reactive Streams with Flux<T>");
            pattern.addRecommendedJavaPattern("Resource management with Flux.using()");
            pattern.setTargetReturnType("Flux<FileRecord>");
        } else if (codeLower.contains("exec sql") || codeLower.contains("select ")) {
            pattern.setPrimaryPattern("DATABASE_ACCESS");
            pattern.addRecommendedJavaPattern("R2DBC reactive database operations");
            pattern.addRecommendedJavaPattern("Repository pattern with reactive types");
            pattern.setTargetReturnType("Mono<DatabaseResult>");
        } else if (nameLower.contains("process") && (codeLower.contains("move ") || codeLower.contains("initialize"))) {
            pattern.setPrimaryPattern("DATA_TRANSFORMATION");
            pattern.addRecommendedJavaPattern("Builder pattern for object construction");
            pattern.addRecommendedJavaPattern("Functional mapping with Stream API");
            pattern.setTargetReturnType("Mono<ProcessedRecord>");
        } else if (nameLower.contains("init") || nameLower.contains("open")) {
            pattern.setPrimaryPattern("INITIALIZATION");
            pattern.addRecommendedJavaPattern("Spring configuration and dependency injection");
            pattern.addRecommendedJavaPattern("Resource initialization with @PostConstruct");
            pattern.setTargetReturnType("Mono<Void>");
        } else if (nameLower.contains("term") || nameLower.contains("close")) {
            pattern.setPrimaryPattern("CLEANUP");
            pattern.addRecommendedJavaPattern("Resource cleanup with @PreDestroy");
            pattern.addRecommendedJavaPattern("Reactive cleanup with doFinally()");
            pattern.setTargetReturnType("Mono<Void>");
        } else {
            pattern.setPrimaryPattern("BUSINESS_LOGIC");
            pattern.addRecommendedJavaPattern("Service layer with business methods");
            pattern.addRecommendedJavaPattern("Command pattern for complex operations");
            pattern.setTargetReturnType("Mono<BusinessResult>");
        }
        
        // Analyze secondary patterns
        if (codeLower.contains("if ") || codeLower.contains("evaluate")) {
            pattern.addSecondaryPattern("ERROR_HANDLING");
            pattern.addRecommendedJavaPattern("Reactive error operators (onErrorReturn, onErrorMap)");
        }
        
        if (codeLower.contains("perform ")) {
            pattern.addSecondaryPattern("ORCHESTRATION");
            pattern.addRecommendedJavaPattern("Service composition with flatMap()");
        }
        
        return pattern;
    }
    
    /**
     * Generate individual procedure conversion prompt with rich context and pattern rules
     */
    private void generateSequentialProcedurePrompt(String procedureName, int sequenceNumber, 
                                                 ArchitecturalPattern pattern, String cobolSource, 
                                                 EnhancedASTData astData, String outputDir, 
                                                 ExecutionOrderResult result) throws IOException {
        
        StringBuilder prompt = new StringBuilder();
        
        prompt.append("# Procedure ").append(sequenceNumber).append(": Convert `").append(procedureName).append("`\n\n");
        
        prompt.append("## Execution Context\n");
        prompt.append("**Sequence:** ").append(sequenceNumber).append(" in execution order\n");
        prompt.append("**PERFORM Count:** ").append(astData.getPerformReferences().getOrDefault(procedureName, 0)).append(" times\n");
        prompt.append("**Primary Pattern:** ").append(pattern.getPrimaryPattern()).append("\n");
        if (!pattern.getSecondaryPatterns().isEmpty()) {
            prompt.append("**Secondary Patterns:** ").append(String.join(", ", pattern.getSecondaryPatterns())).append("\n");
        }
        prompt.append("\n");
        
        // Add applied transformation rules section
        if (!pattern.getTransformationRules().isEmpty()) {
            prompt.append("## Applied Transformation Rules\n");
            prompt.append("The following pattern transformation rules apply to this procedure:\n\n");
            
            for (TransformationRule rule : pattern.getTransformationRules()) {
                prompt.append("### ").append(rule.getName()).append("\n");
                prompt.append("**Why it applies:** ").append(rule.getDescription()).append("\n\n");
                
                prompt.append("**Required Java Patterns:**\n");
                for (String javaPattern : rule.getTargetJavaPatterns()) {
                    prompt.append("- ").append(javaPattern).append("\n");
                }
                prompt.append("\n");
                
                if (rule.getTargetReturnType() != null && !rule.getTargetReturnType().isEmpty()) {
                    prompt.append("**Target Return Type:** `").append(rule.getTargetReturnType()).append("`\n\n");
                }
                
                prompt.append("**Implementation Guidance:**\n");
                prompt.append(rule.getImplementationGuidance()).append("\n\n");
                
                if (!rule.getCodeExamples().isEmpty()) {
                    prompt.append("**Code Examples:**\n");
                    for (Map.Entry<String, String> example : rule.getCodeExamples().entrySet()) {
                        prompt.append("**").append(example.getKey()).append(":**\n");
                        prompt.append("```java\n").append(example.getValue()).append("\n```\n\n");
                    }
                }
                
                prompt.append("---\n\n");
            }
        }
        
        // Include relevant AST analysis for this procedure
        prompt.append("## AST Analysis for `").append(procedureName).append("`\n");
        ProcedureInfo procInfo = astData.getProcedureInfo(procedureName);
        prompt.append("```json\n");
        prompt.append("{\n");
        prompt.append("  \"procedure\": \"").append(procedureName).append("\",\n");
        prompt.append("  \"complexityScore\": ").append(String.format("%.1f", procInfo.getScore())).append(",\n");
        prompt.append("  \"lineRange\": \"").append(procInfo.getStartLine()).append("-").append(procInfo.getEndLine()).append("\",\n");
        prompt.append("  \"performReferences\": ").append(astData.getPerformReferences().getOrDefault(procedureName, 0)).append(",\n");
        
        // Add statement distribution if available
        if (procInfo.getStatementDistribution() != null && !procInfo.getStatementDistribution().isEmpty()) {
            prompt.append("  \"statementTypes\": {\n");
            List<Map.Entry<String, Integer>> sortedStatements = procInfo.getStatementDistribution().entrySet()
                .stream()
                .sorted((a, b) -> b.getValue().compareTo(a.getValue()))
                .collect(Collectors.toList());
            
            for (int i = 0; i < sortedStatements.size(); i++) {
                Map.Entry<String, Integer> entry = sortedStatements.get(i);
                prompt.append("    \"").append(entry.getKey()).append("\": ").append(entry.getValue());
                if (i < sortedStatements.size() - 1) prompt.append(",");
                prompt.append("\n");
            }
            prompt.append("  },\n");
        }
        
        // Add reasoning from AST if available
        if (procInfo.getReasoning() != null && !procInfo.getReasoning().isEmpty()) {
            prompt.append("  \"astReasoning\": \"").append(procInfo.getReasoning().replace("\"", "\\\"")).append("\",\n");
        }
        
        prompt.append("  \"identifiedPattern\": \"").append(pattern.getPrimaryPattern()).append("\",\n");
        prompt.append("  \"appliedRulesCount\": ").append(pattern.getTransformationRules().size()).append("\n");
        prompt.append("}\n");
        prompt.append("```\n\n");
        
        prompt.append("## Complete COBOL Source Code\n");
        prompt.append("```cobol\n");
        prompt.append(extractProcedureCode(cobolSource, procedureName));
        prompt.append("```\n\n");
        
        // Add context from related procedures if this procedure calls others
        String relatedProcedures = findRelatedProcedures(procedureName, cobolSource);
        if (!relatedProcedures.isEmpty()) {
            prompt.append("## Related Procedure Calls\n");
            prompt.append("This procedure calls the following procedures:\n");
            prompt.append("```cobol\n");
            prompt.append(relatedProcedures);
            prompt.append("```\n\n");
        }
        
        prompt.append("## Recommended Java Patterns\n");
        prompt.append("Based on the AST analysis and applied transformation rules:\n\n");
        
        for (String javaPattern : pattern.getRecommendedJavaPatterns()) {
            prompt.append("- **").append(javaPattern).append("**\n");
        }
        prompt.append("\n");
        
        // Add custom implementation guidance
        if (!pattern.getImplementationGuidance().isEmpty()) {
            prompt.append("## Custom Implementation Guidance\n");
            for (String guidance : pattern.getImplementationGuidance()) {
                prompt.append(guidance).append("\n\n");
            }
        }
        
        prompt.append("## Implementation Guidance\n");
        prompt.append("Create a Spring Boot service method that:\n\n");
        prompt.append("- **Service Class:** Fits the `").append(pattern.getPrimaryPattern()).append("` pattern\n");
        prompt.append("- **Return Type:** Use reactive types (").append(pattern.getTargetReturnType()).append(" or similar)\n");
        prompt.append("- **Method Name:** Choose an appropriate business-focused name\n");
        prompt.append("- **Parameters:** Analyze the COBOL code to determine what inputs are needed\n");
        prompt.append("- **Annotations:** Apply appropriate Spring annotations (@Service, @Transactional, etc.)\n\n");
        
        prompt.append("## Conversion Guidelines\n");
        prompt.append("1. **Primary Focus:** ").append(getConversionFocus(pattern.getPrimaryPattern())).append("\n");
        prompt.append("2. **Architecture:** Design the service class and method signature that best fits the business logic\n");
        prompt.append("3. **Pattern Rules:** Follow the specific transformation rules outlined above\n");
        prompt.append("4. **Reactive Programming:** Use appropriate reactive types (Mono/Flux) based on the data flow\n");
        prompt.append("5. **Error Handling:** Apply reactive error operators for robustness\n");
        prompt.append("6. **Dependencies:** Inject required repositories/services via constructor\n");
        prompt.append("7. **Business Logic:** Focus on the actual business rules, not just syntax conversion\n\n");
        
        prompt.append("## Key Implementation Notes\n");
        prompt.append("- **AST shows:** ").append(generateASTInsights(procInfo, pattern)).append("\n");
        prompt.append("- **Business Context:** Analyze variable names and logic flow in the COBOL code\n");
        prompt.append("- **Integration:** This procedure is called ").append(astData.getPerformReferences().getOrDefault(procedureName, 0)).append(" times - design for reusability\n");
        prompt.append("- **Pattern Rules:** ").append(pattern.getTransformationRules().size()).append(" transformation rules applied\n\n");
        
        prompt.append("**Convert this procedure to a modern Spring Boot service method, following the specified transformation rules and designing the optimal method signature and implementation for the ").append(pattern.getPrimaryPattern()).append(" pattern.**\n");
        
        String filename = String.format("%02d_%s_conversion.md", sequenceNumber, procedureName.toLowerCase());
        Files.write(Paths.get(outputDir + filename), prompt.toString().getBytes());
        result.addPrompt(sequenceNumber + ". " + procedureName, filename);
    }
    
    /**
     * Generate final integration prompt
     */
    private void generateIntegrationPrompt(List<String> executionOrder, 
                                         Map<String, ArchitecturalPattern> patterns,
                                         String outputDir, ExecutionOrderResult result) throws IOException {
        
        StringBuilder prompt = new StringBuilder();
        
        prompt.append("# Final Integration: Complete Service Orchestration\n\n");
        
        prompt.append("## Execution Flow Summary\n");
        prompt.append("You have converted individual procedures in this order:\n\n");
        
        for (int i = 0; i < executionOrder.size(); i++) {
            String procName = executionOrder.get(i);
            ArchitecturalPattern pattern = patterns.get(procName);
            prompt.append(String.format("%d. `%s` → %s (%s)\n", 
                i + 1, procName, pattern.getPrimaryPattern(), pattern.getTargetReturnType()));
        }
        prompt.append("\n");
        
        prompt.append("## Integration Strategy\n");
        prompt.append("Now create the main orchestration service that coordinates all converted procedures:\n\n");
        
        prompt.append("```java\n");
        prompt.append("@Service\n");
        prompt.append("@Slf4j\n");
        prompt.append("public class VehicleExportOrchestrationService {\n");
        prompt.append("    \n");
        prompt.append("    // Inject all converted services\n");
        
        Set<String> serviceClasses = patterns.values().stream()
            .map(this::determineServiceClass)
            .collect(Collectors.toSet());
        
        for (String serviceClass : serviceClasses) {
            prompt.append("    private final ").append(serviceClass).append(" ").append(toCamelCase(serviceClass)).append(";\n");
        }
        
        prompt.append("    \n");
        prompt.append("    public Mono<ProcessingResult> processVehicleExportFile(String filePath) {\n");
        prompt.append("        return ").append(toCamelCase(executionOrder.get(0))).append("()\n");
        
        for (int i = 1; i < Math.min(5, executionOrder.size()); i++) {
            prompt.append("            .flatMap(result -> ").append(toCamelCase(executionOrder.get(i))).append("(result))\n");
        }
        
        prompt.append("            .doOnSuccess(result -> log.info(\"Processing completed successfully\"))\n");
        prompt.append("            .doOnError(error -> log.error(\"Processing failed: {}\", error.getMessage()));\n");
        prompt.append("    }\n");
        prompt.append("}\n");
        prompt.append("```\n\n");
        
        prompt.append("## Integration Requirements\n");
        prompt.append("1. **Chain procedures** in the correct execution order\n");
        prompt.append("2. **Handle errors** at the orchestration level\n");
        prompt.append("3. **Pass data** between procedures using reactive operators\n");
        prompt.append("4. **Add logging** for observability\n");
        prompt.append("5. **Implement circuit breakers** for resilience\n\n");
        
        prompt.append("**Create the complete orchestration service that integrates all converted procedures.**\n");
        
        String filename = String.format("%02d_integration_orchestration.md", executionOrder.size() + 1);
        Files.write(Paths.get(outputDir + filename), prompt.toString().getBytes());
        result.addPrompt("Integration", filename);
    }
    
    // Helper methods
    
    private EnhancedASTData parseAST(String astFile) throws IOException {
        String astContent = Files.readString(Paths.get(astFile));
        return ASTTreeParser.parseASTContent(astContent);
    }
    
    private String extractProcedureCode(String cobolSource, String procedureName) {
        String[] lines = cobolSource.split("\n");
        StringBuilder extracted = new StringBuilder();
        boolean inProcedure = false;
        int emptyLineCount = 0;
        
        for (String line : lines) {
            if (line.trim().toLowerCase().startsWith(procedureName.toLowerCase() + ".")) {
                inProcedure = true;
                extracted.append(line).append("\n");
                continue;
            }
            
            if (inProcedure) {
                if (line.trim().isEmpty()) {
                    emptyLineCount++;
                    if (emptyLineCount >= 2) break; // End of procedure
                } else {
                    emptyLineCount = 0;
                    // Check if we've hit another procedure
                    if (line.trim().endsWith(".") && 
                        Character.isLetter(line.trim().charAt(0)) && 
                        !line.trim().startsWith("*")) {
                        break; // Next procedure started
                    }
                }
                extracted.append(line).append("\n");
            }
        }
        
        return extracted.toString();
    }
    
    private String determineServiceClass(ArchitecturalPattern pattern) {
        switch (pattern.getPrimaryPattern()) {
            case "VALIDATION": return "ValidationService";
            case "FILE_PROCESSING": return "FileProcessingService"; 
            case "DATABASE_ACCESS": return "DatabaseService";
            case "DATA_TRANSFORMATION": return "TransformationService";
            case "INITIALIZATION": return "InitializationService";
            case "CLEANUP": return "CleanupService";
            default: return "BusinessLogicService";
        }
    }
    
    private String getConversionFocus(String primaryPattern) {
        switch (primaryPattern) {
            case "VALIDATION": return "Convert IF-THEN chains to functional validation rules";
            case "FILE_PROCESSING": return "Replace sequential file I/O with reactive streams";
            case "DATABASE_ACCESS": return "Convert EXEC SQL to reactive R2DBC operations";
            case "DATA_TRANSFORMATION": return "Replace MOVE statements with builder patterns";
            case "INITIALIZATION": return "Use Spring configuration and dependency injection";
            case "CLEANUP": return "Implement proper resource cleanup with reactive patterns";
            default: return "Apply appropriate service layer patterns";
        }
    }
    
    private String toCamelCase(String input) {
        if (input == null || input.isEmpty()) return input;
        String[] parts = input.split("(?=[A-Z])|[-_\\s]+");
        StringBuilder result = new StringBuilder(parts[0].toLowerCase());
        for (int i = 1; i < parts.length; i++) {
            if (!parts[i].isEmpty()) {
                result.append(Character.toUpperCase(parts[i].charAt(0)))
                      .append(parts[i].substring(1).toLowerCase());
            }
        }
        return result.toString();
    }
    
    /**
     * Find related procedures called by this procedure
     */
    private String findRelatedProcedures(String procedureName, String cobolSource) {
        String procedureCode = extractProcedureCode(cobolSource, procedureName);
        StringBuilder related = new StringBuilder();
        
        String[] lines = procedureCode.split("\n");
        for (String line : lines) {
            String trimmed = line.trim().toUpperCase();
            if (trimmed.startsWith("PERFORM ") && !trimmed.contains("UNTIL")) {
                // Extract the performed procedure name
                String performLine = trimmed.substring(8).trim(); // Remove "PERFORM "
                if (performLine.length() > 0) {
                    related.append(line.trim()).append("\n");
                }
            }
        }
        
        return related.toString();
    }
    
    /**
     * Generate insights from AST analysis
     */
    private String generateASTInsights(ProcedureInfo procInfo, ArchitecturalPattern pattern) {
        StringBuilder insights = new StringBuilder();
        
        insights.append("Complexity score ").append(String.format("%.1f", procInfo.getScore()));
        
        if (procInfo.getStatementDistribution() != null && !procInfo.getStatementDistribution().isEmpty()) {
            // Find the most common statement type
            String mostCommon = procInfo.getStatementDistribution().entrySet().stream()
                .max(Map.Entry.comparingByValue())
                .map(Map.Entry::getKey)
                .orElse("UNKNOWN");
            
            int totalStatements = procInfo.getStatementDistribution().values().stream()
                .mapToInt(Integer::intValue).sum();
            
            insights.append(", ").append(totalStatements).append(" statements dominated by ").append(mostCommon);
        }
        
        if (procInfo.getReasoning() != null && procInfo.getReasoning().contains("SQL")) {
            insights.append(", contains database operations");
        }
        
        return insights.toString();
    }
    
    private void printResults(ExecutionOrderResult result) {
        System.out.println("\n✅ Enhanced PERFORM Graph-Ordered Prompt Generation Complete!");
        System.out.println("🔄 Generated " + result.getPrompts().size() + " sequential prompts");
        System.out.println("🎯 Applied " + patternRuleEngine.getAllRules().size() + " transformation rules");
        System.out.println("\n📋 Execution Order Prompts:");
        
        for (Map.Entry<String, String> prompt : result.getPrompts().entrySet()) {
            System.out.println("  📄 " + prompt.getKey() + ": " + prompt.getValue());
        }
        
        System.out.println("\n🎯 Benefits of this enhanced approach:");
        System.out.println("   • Follows natural COBOL execution flow");
        System.out.println("   • Respects procedure dependencies");
        System.out.println("   • Applies configurable transformation rules");
        System.out.println("   • One focused prompt per procedure with custom patterns");
        System.out.println("   • Pattern rules reference for consistent conversion");
        System.out.println("   • Final integration prompt ties everything together");
    }
}

// Supporting classes

class ExecutionOrderResult {
    private final Map<String, String> prompts = new LinkedHashMap<>();
    
    public void addPrompt(String name, String filename) {
        prompts.put(name, filename);
    }
    
    public Map<String, String> getPrompts() { return prompts; }
}

class PerformGraph {
    private final Map<String, Integer> nodes = new HashMap<>();
    
    public void addNode(String procedureName, int callCount) {
        nodes.put(procedureName, callCount);
    }
    
    public boolean hasNode(String procedureName) {
        return nodes.containsKey(procedureName);
    }
    
    public int getCallCount(String procedureName) {
        return nodes.getOrDefault(procedureName, 0);
    }
    
    public Set<String> getNodes() {
        return nodes.keySet();
    }
}

class ProcedureClassification {
    private final List<String> entryPoints = new ArrayList<>();
    private final List<String> initializationProcedures = new ArrayList<>();
    private final List<String> coreProcedures = new ArrayList<>();
    private final List<String> supportProcedures = new ArrayList<>(); 
    private final List<String> cleanupProcedures = new ArrayList<>();
    
    public void addEntryPoint(String procedure) {
        entryPoints.add(procedure);
    }
    
    public void addInitializationProcedure(String procedure) {
        initializationProcedures.add(procedure);
    }
    
    public void addCoreProcedure(String procedure) {
        coreProcedures.add(procedure);
    }
    
    public void addSupportProcedure(String procedure) {
        supportProcedures.add(procedure);
    }
    
    public void addCleanupProcedure(String procedure) {
        cleanupProcedures.add(procedure);
    }
    
    public List<String> getEntryPoints() {
        return entryPoints.stream()
            .sorted() // Deterministic ordering
            .collect(Collectors.toList());
    }
    
    public List<String> getInitializationProcedures() {
        return initializationProcedures.stream()
            .sorted()
            .collect(Collectors.toList());
    }
    
    public List<String> getCoreProcedures() {
        return coreProcedures.stream()
            .sorted()
            .collect(Collectors.toList());
    }
    
    public List<String> getSupportProcedures() {
        return supportProcedures.stream()
            .sorted()
            .collect(Collectors.toList());
    }
    
    public List<String> getCleanupProcedures() {
        return cleanupProcedures.stream()
            .sorted()
            .collect(Collectors.toList());
    }
}

// Enhanced ArchitecturalPattern class with transformation rules support
class ArchitecturalPattern {
    private String procedureName;
    private String primaryPattern;
    private List<String> secondaryPatterns = new ArrayList<>();
    private List<String> recommendedJavaPatterns = new ArrayList<>();
    private String targetReturnType;
    private List<TransformationRule> transformationRules = new ArrayList<>();
    private List<String> implementationGuidance = new ArrayList<>();
    
    // Getters and setters
    public String getProcedureName() { return procedureName; }
    public void setProcedureName(String procedureName) { this.procedureName = procedureName; }
    
    public String getPrimaryPattern() { return primaryPattern; }
    public void setPrimaryPattern(String primaryPattern) { this.primaryPattern = primaryPattern; }
    
    public List<String> getSecondaryPatterns() { return secondaryPatterns; }
    public void addSecondaryPattern(String pattern) { this.secondaryPatterns.add(pattern); }
    
    public List<String> getRecommendedJavaPatterns() { return recommendedJavaPatterns; }
    public void addRecommendedJavaPattern(String pattern) { this.recommendedJavaPatterns.add(pattern); }
    public void clearRecommendedJavaPatterns() { this.recommendedJavaPatterns.clear(); }
    
    public String getTargetReturnType() { return targetReturnType; }
    public void setTargetReturnType(String targetReturnType) { this.targetReturnType = targetReturnType; }
    
    public List<TransformationRule> getTransformationRules() { return transformationRules; }
    public void addTransformationRule(TransformationRule rule) { this.transformationRules.add(rule); }
    
    public List<String> getImplementationGuidance() { return implementationGuidance; }
    public void addImplementationGuidance(String guidance) { this.implementationGuidance.add(guidance); }
}

// Pattern Rule Engine for managing transformation rules
class PatternRuleEngine {
    private List<TransformationRule> rules = new ArrayList<>();
    
    public static PatternRuleEngine fromJson(String jsonContent) {
        // Simplified JSON parsing - in practice, use Jackson or Gson
        PatternRuleEngine engine = new PatternRuleEngine();
        // Parse JSON and populate rules
        // For now, return default rules
        return createDefault();
    }
    
    public static PatternRuleEngine createDefault() {
        PatternRuleEngine engine = new PatternRuleEngine();
        
        // COBOL FILE I/O to Reactive Streams
        TransformationRule fileRule = new TransformationRule();
        fileRule.setName("COBOL File I/O to Reactive Streams");
        fileRule.setDescription("Convert sequential file operations to reactive stream processing");
        fileRule.addCobolPattern("READ.*");
        fileRule.addCobolPattern("WRITE.*");
        fileRule.addCobolPattern("OPEN.*");
        fileRule.addCobolPattern("CLOSE.*");
        fileRule.addArchitecturalPattern("FILE_PROCESSING");
        fileRule.addTargetJavaPattern("Use Flux<T> for streaming file data");
        fileRule.addTargetJavaPattern("Resource management with Flux.using()");
        fileRule.addTargetJavaPattern("Non-blocking I/O with Spring WebFlux");
        fileRule.setTargetReturnType("Flux<FileRecord>");
        fileRule.setImplementationGuidance(
            "Replace sequential file operations with reactive streams:\n" +
            "- Use Flux.fromIterable() for reading file lines\n" +
            "- Implement backpressure handling for large files\n" +
            "- Use Flux.using() for automatic resource cleanup\n" +
            "- Apply .publishOn() for I/O operations on separate thread pool"
        );
        fileRule.addCodeExample("File Reading", 
            "@Service\n" +
            "public class FileProcessingService {\n" +
            "    public Flux<FileRecord> processFile(Path filePath) {\n" +
            "        return Flux.using(\n" +
            "            () -> Files.lines(filePath),\n" +
            "            lines -> lines.map(this::parseRecord)\n" +
            "                          .map(FileRecord::new),\n" +
            "            Stream::close\n" +
            "        ).publishOn(Schedulers.boundedElastic());\n" +
            "    }\n" +
            "}"
        );
        engine.addRule(fileRule);
        
        // COBOL EVALUATE to Strategy Pattern
        TransformationRule evaluateRule = new TransformationRule();
        evaluateRule.setName("COBOL EVALUATE to Strategy Pattern");
        evaluateRule.setDescription("Convert EVALUATE statements to Strategy pattern with functional interfaces");
        evaluateRule.addCobolPattern("EVALUATE.*");
        evaluateRule.addCobolPattern("WHEN.*");
        evaluateRule.addTargetJavaPattern("Strategy Pattern with Function interfaces");
        evaluateRule.addTargetJavaPattern("Map-based dispatch for performance");
        evaluateRule.addTargetJavaPattern("Optional.ofNullable() for null safety");
        evaluateRule.setTargetReturnType("Mono<ProcessingResult>");
        evaluateRule.setImplementationGuidance(
            "Convert EVALUATE logic to functional strategy pattern:\n" +
            "- Create Map<Condition, Function> for dispatch\n" +
            "- Use Optional.ofNullable() for safe navigation\n" +
            "- Apply reactive error handling with onErrorReturn()\n" +
            "- Consider caching strategies for frequently used conditions"
        );
        evaluateRule.addCodeExample("Strategy Pattern",
            "private final Map<String, Function<Input, ProcessingResult>> strategies = Map.of(\n" +
            "    \"TYPE_A\", this::processTypeA,\n" +
            "    \"TYPE_B\", this::processTypeB,\n" +
            "    \"DEFAULT\", this::processDefault\n" +
            ");\n" +
            "\n" +
            "public Mono<ProcessingResult> processEvaluate(String type, Input input) {\n" +
            "    return Mono.fromCallable(() -> \n" +
            "        Optional.ofNullable(strategies.get(type))\n" +
            "                .orElse(strategies.get(\"DEFAULT\"))\n" +
            "                .apply(input)\n" +
            "    ).onErrorReturn(ProcessingResult.failed());\n" +
            "}"
        );
        engine.addRule(evaluateRule);
        
        // COBOL SQL to R2DBC
        TransformationRule sqlRule = new TransformationRule();
        sqlRule.setName("COBOL EXEC SQL to R2DBC");
        sqlRule.setDescription("Convert embedded SQL to reactive R2DBC operations");
        sqlRule.addCobolPattern("EXEC SQL.*");
        sqlRule.addCobolPattern("SELECT.*");
        sqlRule.addCobolPattern("INSERT.*");
        sqlRule.addCobolPattern("UPDATE.*");
        sqlRule.addCobolPattern("DELETE.*");
        sqlRule.addArchitecturalPattern("DATABASE_ACCESS");
        sqlRule.addTargetJavaPattern("R2DBC reactive database operations");
        sqlRule.addTargetJavaPattern("Repository pattern with reactive types");
        sqlRule.addTargetJavaPattern("Connection pooling with ConnectionFactory");
        sqlRule.setTargetReturnType("Mono<DatabaseResult>");
        sqlRule.setImplementationGuidance(
            "Replace EXEC SQL with reactive R2DBC:\n" +
            "- Use DatabaseClient for complex queries\n" +
            "- Implement proper connection management\n" +
            "- Apply @Transactional for transactional boundaries\n" +
            "- Use Mono.defer() for lazy evaluation of database operations"
        );
        sqlRule.addCodeExample("R2DBC Repository",
            "@Repository\n" +
            "public class VehicleRepository {\n" +
            "    private final DatabaseClient client;\n" +
            "    \n" +
            "    public Mono<Vehicle> findById(Long id) {\n" +
            "        return client.sql(\"SELECT * FROM vehicles WHERE id = :id\")\n" +
            "                    .bind(\"id\", id)\n" +
            "                    .map(row -> mapToVehicle(row))\n" +
            "                    .one()\n" +
            "                    .onErrorResume(DataAccessException.class,\n" +
            "                                 ex -> Mono.empty());\n" +
            "    }\n" +
            "}"
        );
        engine.addRule(sqlRule);
        
        // COBOL Data Validation to Bean Validation
        TransformationRule validationRule = new TransformationRule();
        validationRule.setName("COBOL Data Validation to Bean Validation");
        validationRule.setDescription("Convert IF-based validation to declarative Bean Validation");
        validationRule.addCobolPattern("IF.*INVALID.*");
        validationRule.addCobolPattern("IF.*NOT NUMERIC.*");
        validationRule.addCobolPattern("IF.*SPACES.*");
        validationRule.addProcedureNamePattern(".*VALID.*");
        validationRule.addProcedureNamePattern(".*CHECK.*");
        validationRule.addArchitecturalPattern("VALIDATION");
        validationRule.addTargetJavaPattern("Bean Validation with annotations");
        validationRule.addTargetJavaPattern("Custom validators for business rules");
        validationRule.addTargetJavaPattern("Functional validation with Predicates");
        validationRule.setTargetReturnType("Mono<ValidationResult>");
        validationRule.setImplementationGuidance(
            "Convert procedural validation to declarative approach:\n" +
            "- Use @Valid, @NotNull, @Pattern annotations\n" +
            "- Create custom validators for complex business rules\n" +
            "- Implement Validator<T> interface for functional validation\n" +
            "- Collect all validation errors before returning result"
        );
        validationRule.addCodeExample("Bean Validation",
            "public class VehicleData {\n" +
            "    @NotBlank(message = \"VIN cannot be blank\")\n" +
            "    @Pattern(regexp = \"[A-Z0-9]{17}\", message = \"Invalid VIN format\")\n" +
            "    private String vin;\n" +
            "    \n" +
            "    @NotNull\n" +
            "    @Min(value = 1900, message = \"Year must be after 1900\")\n" +
            "    private Integer year;\n" +
            "}\n" +
            "\n" +
            "@Service\n" +
            "public class ValidationService {\n" +
            "    public Mono<ValidationResult> validate(VehicleData data) {\n" +
            "        return Mono.fromCallable(() -> validator.validate(data))\n" +
            "                  .map(violations -> ValidationResult.from(violations));\n" +
            "    }\n" +
            "}"
        );
        engine.addRule(validationRule);
        
        return engine;
    }
    
    public void addRule(TransformationRule rule) {
        rules.add(rule);
    }
    
    public List<TransformationRule> getAllRules() {
        return new ArrayList<>(rules);
    }
    
    public List<TransformationRule> findApplicableRules(String procedureName, String procedureCode, String architecturalPattern) {
        List<TransformationRule> applicable = new ArrayList<>();
        
        for (TransformationRule rule : rules) {
            if (rule.appliesTo(procedureName, procedureCode, architecturalPattern)) {
                applicable.add(rule);
            }
        }
        
        return applicable;
    }
}

// Transformation Rule class
class TransformationRule {
    private String name;
    private String description;
    private List<String> cobolPatterns = new ArrayList<>();
    private List<String> procedureNamePatterns = new ArrayList<>();
    private List<String> architecturalPatterns = new ArrayList<>();
    private List<String> targetJavaPatterns = new ArrayList<>();
    private String targetReturnType;
    private String implementationGuidance;
    private Map<String, String> codeExamples = new HashMap<>();
    private boolean overrideMode = false;
    
    public boolean appliesTo(String procedureName, String procedureCode, String architecturalPattern) {
        // Check architectural pattern match
        if (!architecturalPatterns.isEmpty() && !architecturalPatterns.contains(architecturalPattern)) {
            return false;
        }
        
        // Check procedure name patterns
        for (String namePattern : procedureNamePatterns) {
            if (Pattern.matches(namePattern.toUpperCase(), procedureName.toUpperCase())) {
                return true;
            }
        }
        
        // Check COBOL code patterns
        String codeUpper = procedureCode.toUpperCase();
        for (String cobolPattern : cobolPatterns) {
            if (Pattern.compile(cobolPattern.toUpperCase()).matcher(codeUpper).find()) {
                return true;
            }
        }
        
        // If no specific patterns, match on architectural pattern only
        return !architecturalPatterns.isEmpty() && architecturalPatterns.contains(architecturalPattern);
    }
    
    // Getters and setters
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    
    public List<String> getCobolPatterns() { return cobolPatterns; }
    public void addCobolPattern(String pattern) { this.cobolPatterns.add(pattern); }
    
    public List<String> getProcedureNamePatterns() { return procedureNamePatterns; }
    public void addProcedureNamePattern(String pattern) { this.procedureNamePatterns.add(pattern); }
    
    public List<String> getArchitecturalPatterns() { return architecturalPatterns; }
    public void addArchitecturalPattern(String pattern) { this.architecturalPatterns.add(pattern); }
    
    public List<String> getTargetJavaPatterns() { return targetJavaPatterns; }
    public void addTargetJavaPattern(String pattern) { this.targetJavaPatterns.add(pattern); }
    
    public String getTargetReturnType() { return targetReturnType; }
    public void setTargetReturnType(String targetReturnType) { this.targetReturnType = targetReturnType; }
    
    public String getImplementationGuidance() { return implementationGuidance; }
    public void setImplementationGuidance(String implementationGuidance) { this.implementationGuidance = implementationGuidance; }
    
    public Map<String, String> getCodeExamples() { return codeExamples; }
    public void addCodeExample(String title, String code) { this.codeExamples.put(title, code); }
    
    public boolean isOverrideMode() { return overrideMode; }
    public void setOverrideMode(boolean overrideMode) { this.overrideMode = overrideMode; }
}

// Reuse existing classes with minor modifications
class EnhancedASTData {
    private Map<String, Integer> performReferences = new HashMap<>();
    private List<String> allProcedureNames = new ArrayList<>();
    private Map<String, ProcedureInfo> procedureDetails = new HashMap<>();
    
    public Map<String, Integer> getPerformReferences() { return performReferences; }
    public List<String> getAllProcedureNames() { return allProcedureNames; }
    
    public ProcedureInfo getProcedureInfo(String name) {
        return procedureDetails.computeIfAbsent(name, ProcedureInfo::new);
    }
    
    public void addProcedureInfo(String name, ProcedureInfo info) {
        procedureDetails.put(name, info);
        if (!allProcedureNames.contains(name)) {
            allProcedureNames.add(name);
        }
    }
}

class ProcedureInfo {
    private String name;
    private double score;
    private int startLine;
    private int endLine;
    private Map<String, Integer> statementDistribution = new HashMap<>();
    private String reasoning;
    
    public ProcedureInfo(String name) {
        this.name = name;
        this.score = 100.0;
        this.startLine = 1;
        this.endLine = 10;
    }
    
    // Getters and setters
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public double getScore() { return score; }
    public void setScore(double score) { this.score = score; }
    
    public int getStartLine() { return startLine; }
    public void setStartLine(int startLine) { this.startLine = startLine; }
    
    public int getEndLine() { return endLine; }
    public void setEndLine(int endLine) { this.endLine = endLine; }
    
    public Map<String, Integer> getStatementDistribution() { return statementDistribution; }
    public void setStatementDistribution(Map<String, Integer> statementDistribution) { 
        this.statementDistribution = statementDistribution; 
    }
    
    public String getReasoning() { return reasoning; }
    public void setReasoning(String reasoning) { this.reasoning = reasoning; }
}

class ASTTreeParser {
    public static EnhancedASTData parseASTContent(String astContent) {
        EnhancedASTData data = new EnhancedASTData();
        
        String[] lines = astContent.split("\n");
        boolean inPerformGraph = false;
        boolean inProcedures = false;
        ProcedureInfo currentProcedure = null;
        
        for (String line : lines) {
            line = line.trim();
            
            // Look for PROCEDURES section
            if (line.startsWith("(PROCEDURES")) {
                inProcedures = true;
                continue;
            }
            
            // Parse procedure definition
            if (inProcedures && line.startsWith("(PROCEDURE")) {
                String procName = extractProcedureName(line);
                if (procName != null) {
                    currentProcedure = new ProcedureInfo(procName);
                    data.addProcedureInfo(procName, currentProcedure);
                }
                continue;
            }
            
            // Parse procedure details
            if (currentProcedure != null && inProcedures) {
                if (line.startsWith("(SCORE")) {
                    double score = extractScore(line);
                    currentProcedure.setScore(score);
                } else if (line.startsWith("(START-LINE")) {
                    int startLine = extractNumber(line);
                    currentProcedure.setStartLine(startLine);
                } else if (line.startsWith("(END-LINE")) {
                    int endLine = extractNumber(line);
                    currentProcedure.setEndLine(endLine);
                } else if (line.startsWith("(REASONING")) {
                    String reasoning = extractQuotedString(line);
                    currentProcedure.setReasoning(reasoning);
                } else if (line.startsWith("(STATEMENT-DISTRIBUTION")) {
                    parseStatementDistribution(lines, currentProcedure);
                }
                
                // End of current procedure
                if (line.equals(")") && !line.startsWith("(")) {
                    currentProcedure = null;
                }
            }
            
            // Look for PERFORM-GRAPH section
            if (line.startsWith("(PERFORM-GRAPH")) {
                inPerformGraph = true;
                inProcedures = false;
                continue;
            }
            
            if (inPerformGraph) {
                if (line.startsWith(")")) {
                    break; // End of PERFORM-GRAPH
                }
                
                // Parse perform references: ("PROCEDURE_NAME" count)
                if (line.startsWith("(\"") && line.contains("\"")) {
                    String[] parts = line.split("\"");
                    if (parts.length >= 3) {
                        String procedureName = parts[1];
                        String countPart = parts[2].trim();
                        if (countPart.endsWith(")")) {
                            countPart = countPart.substring(0, countPart.length() - 1).trim();
                            try {
                                int count = Integer.parseInt(countPart);
                                data.getPerformReferences().put(procedureName, count);
                                if (!data.getAllProcedureNames().contains(procedureName)) {
                                    data.getAllProcedureNames().add(procedureName);
                                }
                            } catch (NumberFormatException e) {
                                // Ignore malformed entries
                            }
                        }
                    }
                }
            }
        }
        
        return data;
    }
    
    private static String extractProcedureName(String line) {
        int start = line.indexOf('"');
        int end = line.lastIndexOf('"');
        if (start != -1 && end != -1 && start < end) {
            return line.substring(start + 1, end);
        }
        return null;
    }
    
    private static double extractScore(String line) {
        try {
            String scoreStr = line.replaceAll("[^0-9.]", "");
            return Double.parseDouble(scoreStr);
        } catch (NumberFormatException e) {
            return 100.0;
        }
    }
    
    private static int extractNumber(String line) {
        try {
            String numberStr = line.replaceAll("[^0-9]", "");
            return Integer.parseInt(numberStr);
        } catch (NumberFormatException e) {
            return 0;
        }
    }
    
    private static String extractQuotedString(String line) {
        int start = line.indexOf('"');
        int end = line.lastIndexOf('"');
        if (start != -1 && end != -1 && start < end) {
            return line.substring(start + 1, end);
        }
        return "";
    }
    
    private static void parseStatementDistribution(String[] lines, ProcedureInfo procedure) {
        Map<String, Integer> distribution = new HashMap<>();
        
        // This is a simplified parser - in practice you'd need to parse the nested structure
        // For now, we'll just extract some common statement types
        for (String line : lines) {
            line = line.trim();
            if (line.startsWith("(") && line.contains(" ") && !line.startsWith("(STATEMENT-DISTRIBUTION")) {
                String[] parts = line.split("\\s+");
                if (parts.length >= 2) {
                    String stmtType = parts[0].substring(1); // Remove opening paren
                    try {
                        String countStr = parts[parts.length - 1].replaceAll("[^0-9]", "");
                        if (!countStr.isEmpty()) {
                            int count = Integer.parseInt(countStr);
                            distribution.put(stmtType, count);
                        }
                    } catch (NumberFormatException e) {
                        // Ignore malformed entries
                    }
                }
            }
        }
        
        procedure.setStatementDistribution(distribution);
    }
}
