/**
 * EnhancedASTParser based on Cobol.g4 leveraging Visitor and Listener pattern
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
    private boolean dataItemsExtracted = false;
    private Map<String, List<StructuralDataItemV2>> dataItemsBySection = new HashMap<>();
    private List<DataDivisionPreprocessor.FileDescriptor> preservedFileDescriptors = new ArrayList<>();


    // CRITICAL: Make sure this is declared
    private String[] sourceLines;  // THIS MUST BE DECLARED AS A FIELD
    
    // Enhanced scoring and filtering components
    private EnhancedScoringMechanism scoringMechanism;
    private EnhancedProcedureFilter procedureFilter;
    
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
    private ProcedureExtractor procedureExtractor;

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: java ASTParser <cobol-file> [config-file]");
            System.err.println("Examples:");
            System.err.println("  java EnhancedASTParser myprogram.cbl");
            System.err.println("  java EnhancedASTParser myprogram.cbl custom-config.properties");
            System.exit(1);
        }
        
        try {
            ASTParser parser;
            if (args.length > 1) {
                parser = new EnhancedASTParser(args[1]);
            } else {
                parser = new EnhancedASTParser("cobol-grammar.properties");
            }
            
            String cobolFile = args[0];
            System.out.println("🚀 Starting EnhancedASTParser analysis of: " + cobolFile);
            
            StructuralAnalysisResultV2 result = parser.parseCobolWithGrammar(cobolFile);
            
            parser.printEnhancedResults(result);
            
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

    // Updated constructor to initialize enhanced components
    public ASTParser(String configFile) {
        this.config = loadConfiguration(configFile);
        this.dataPreprocessor = new DataDivisionPreprocessor(config);
        this.procedureExtractor = new ProcedureExtractor(config);
        // Enhanced scoring and filtering will be initialized after sourceLines are available
    }
    
    /**
     * Initialize enhanced components after sourceLines are available
     */
    private void initializeEnhancedComponents() {
        this.scoringMechanism = new EnhancedScoringMechanism(config, sourceLines, performReferences);
        this.procedureFilter = new EnhancedProcedureFilter(config, scoringMechanism, performReferences);
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
    
    /*
     * Added ProcedureExtractor in case grammar missed anything
     */

     public StructuralAnalysisResultV2 parseCobolWithGrammar(String filename) throws Exception {
        if (config.isVerboseLogging()) {
            System.out.println("🔍 EnhancedASTParser grammar-enhanced analysis of COBOL file: " + filename);
            System.out.println("📊 Configuration: " + config.toString());
        }
        
        // Read source for line-based analysis
        sourceLines = readSourceLines(filename);
        System.out.println("🔍 DEBUG: Read " + sourceLines.length + " source lines");
        
        // Initialize enhanced components now that sourceLines are available
        initializeEnhancedComponents();
        
        // STEP 1: Preprocess DATA DIVISION - PRESERVE IMMEDIATELY
        DataDivisionPreprocessor.PreprocessingResult preprocessResult = null;
        if (config.isDataDivisionPreprocessingEnabled()) {
            if (config.isVerboseLogging()) {
                System.out.println("🔄 Preprocessing DATA DIVISION sections...");
            }
            
            preprocessResult = dataPreprocessor.preprocessDataDivisions(sourceLines);
            
            // PRESERVE DATA ITEMS IMMEDIATELY AFTER EXTRACTION
            preserveDataItems(preprocessResult);
            
            preprocessWarnings.addAll(preprocessResult.getWarnings());
            
            System.out.println("🔍 DEBUG: After preprocessing and preservation:");
            System.out.println("  - Data items preserved: " + extractedDataItems.size());
            System.out.println("  - File descriptors preserved: " + preservedFileDescriptors.size());
            System.out.println("  - Data items by section: " + dataItemsBySection.size() + " sections");
            
            if (config.isVerboseLogging()) {
                System.out.println("📊 Extracted " + extractedDataItems.size() + " data items");
                System.out.println("📊 Extracted " + preservedFileDescriptors.size() + " file descriptors");
                if (!preprocessResult.getWarnings().isEmpty()) {
                    System.out.println("⚠️ Preprocessing warns: " + preprocessResult.getWarnings().size());
                }
            }
        }
        
        // STEP 2: Apply regex preprocessing if enabled
        List<ProcedureBoundary> regexProcedures = new ArrayList<>();
        if (config.isRegexPreprocessingEnabled()) {
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
            
            String[] sourceToParse = (preprocessResult != null) ? 
                preprocessResult.getCleanedSource() : sourceLines;
            grammarSuccess = attemptConfigurableGrammarParsingWithCleanedSource(filename, sourceToParse);
            
            System.out.println("🔍 DEBUG: Grammar parsing success: " + grammarSuccess);
            System.out.println("🔍 DEBUG: Procedures found via grammar: " + procedures.size());
            for (StructuralProcedureV2 proc : procedures) {
                System.out.println("  - " + proc.getName() + " (lines " + proc.getLineNumber() + "-" + proc.getEndLineNumber() + ")");
            }
        }
        
        // STEP 4: Integrate ProcedureExtractor for comprehensive procedure detection
        System.out.println("🔍 DEBUG: Running ProcedureExtractor for enhanced procedure detection...");
        BusinessLogicResult extractorResult = procedureExtractor.extractBusinessLogic(filename);
        List<StructuralProcedureV2> extractedProcedures = convertExtractorProcedures(extractorResult.getProcedures());
        
        // STEP 5: Merge procedures from grammar, regex, and ProcedureExtractor WITH DATA PRESERVATION
        System.out.println("🔍 DEBUG: Merging procedures while preserving data items...");
        mergeProceduresWithDataPreservation(regexProcedures, extractedProcedures);
        System.out.println("🔍 DEBUG: Total procedures after merge: " + procedures.size());
        System.out.println("🔍 DEBUG: Data items still preserved: " + extractedDataItems.size());
        
        // STEP 6: Hybrid approach based on configuration
        System.out.println("🔍 DEBUG: Checking hybrid mode...");
        System.out.println("  - Hybrid enabled: " + config.isHybridModeEnabled());
        System.out.println("  - Should use hybrid: " + shouldUseHybridMode(regexProcedures));
        System.out.println("  - Grammar procedures: " + procedures.size());
        System.out.println("  - Regex procedures: " + regexProcedures.size());
        System.out.println("  - Extractor procedures: " + extractedProcedures.size());
        
        if (config.isHybridModeEnabled() && shouldUseHybridMode(regexProcedures)) {
            if (config.isVerboseLogging()) {
                System.out.println("🔄 Applying configurable hybrid enhancement...");
            }
            int beforeCount = procedures.size();
            enhanceWithConfigurableRegexResults(regexProcedures);
            int afterCount = procedures.size();
            System.out.println("🔍 DEBUG: Hybrid enhancement added " + (afterCount - beforeCount) + " procedures");
        }
        
        // Build result with enhanced data items and procedures
        result = new StructuralAnalysisResultV2();
        result.setProgramName(determineProgramName());
        
        // Apply enhanced filtering and ensure all statements are properly initialized
        List<StructuralProcedureV2> filteredProcedures = applyEnhancedFiltering();
        StatementInitializer.initializeAllProcedures(filteredProcedures);
        
        result.setProcedures(filteredProcedures);
        result.setSqlStatements(sqlStatements);
        result.setCopyStatements(copyStatements);
        result.setStatementCounts(statementCounts);
        result.setPerformReferences(performReferences);
        result.setParseWarnings(parseWarnings);
        
        // ENSURE DATA ITEMS ARE PRESERVED IN FINAL RESULT
        result.setDataItems(getPreservedDataItems());
        result.setFileDescriptors(getPreservedFileDescriptors());
        
        System.out.println("🔍 DEBUG: Final result verification:");
        System.out.println("  - Procedures: " + result.getProcedures().size());
        System.out.println("  - Data items: " + result.getDataItems().size());
        System.out.println("  - File descriptors: " + result.getFileDescriptors().size());
        
        return result;
    }
    

    private void preserveDataItems(DataDivisionPreprocessor.PreprocessingResult preprocessResult) {
        if (preprocessResult == null) {
            System.out.println("🔍 DEBUG: No preprocessing result to preserve");
            return;
        }
        
        // SIMPLE preservation - just keep references
        extractedDataItems.clear();
        if (preprocessResult.getDataItems() != null) {
            extractedDataItems.addAll(preprocessResult.getDataItems());
        }
        
        preservedFileDescriptors.clear();
        if (preprocessResult.getFileDescriptors() != null) {
            preservedFileDescriptors.addAll(preprocessResult.getFileDescriptors());
        }
        
        // Group data items by section
        dataItemsBySection.clear();
        dataItemsBySection = extractedDataItems.stream()
            .collect(Collectors.groupingBy(
                item -> item.getSection() != null ? item.getSection() : "UNKNOWN"
            ));
        
        dataItemsExtracted = true;
        
        System.out.println("🔍 DEBUG: Data items preserved successfully:");
        System.out.println("  - Total data items: " + extractedDataItems.size());
        System.out.println("  - Total file descriptors: " + preservedFileDescriptors.size());
        System.out.println("  - Sections: " + dataItemsBySection.keySet());
    }

   

    /**
     * NEW: Get preserved data items
     */
    private List<StructuralDataItemV2> getPreservedDataItems() {
        if (!dataItemsExtracted || extractedDataItems.isEmpty()) {
            System.out.println("🔍 DEBUG: No preserved data items available");
            return new ArrayList<>();
        }
        
        System.out.println("🔍 DEBUG: Returning " + extractedDataItems.size() + " preserved data items");
        return new ArrayList<>(extractedDataItems); // Return copy to prevent modification
    }

    /**
     * NEW: Get preserved file descriptors
     */
    private List<DataDivisionPreprocessor.FileDescriptor> getPreservedFileDescriptors() {
        if (preservedFileDescriptors.isEmpty()) {
            System.out.println("🔍 DEBUG: No preserved file descriptors available");
            return new ArrayList<>();
        }
        
        System.out.println("🔍 DEBUG: Returning " + preservedFileDescriptors.size() + " preserved file descriptors");
        return new ArrayList<>(preservedFileDescriptors); // Return copy to prevent modification
    }

    
    /**
     * Apply enhanced filtering using the new components
     */
    private List<StructuralProcedureV2> applyEnhancedFiltering() {
        return procedureFilter.applyEnhancedFiltering(procedures);
    }

    // New method to convert ProcedureExtractor's CobolProcedure to StructuralProcedureV2
    private List<StructuralProcedureV2> convertExtractorProcedures(List<CobolProcedure2> cobolProcedures) {
        List<StructuralProcedureV2> structuralProcedures = new ArrayList<>();
        for (CobolProcedure2 cobolProc : cobolProcedures) {
            StructuralProcedureV2 proc = new StructuralProcedureV2();
            proc.setName(cobolProc.getName());
            proc.setLineNumber(cobolProc.getLineNumber());
            proc.setEndLineNumber(calculateConfigurableEndLine(cobolProc.getLineNumber()));
            proc.setContextScore(scoringMechanism.calculateEnhancedScore(cobolProc));
            proc.setReasoningInfo(scoringMechanism.buildEnhancedReasoning(cobolProc));
            
            List<StructuralStatementV2> statements = new ArrayList<>();
            for (CobolStatement2 cobolStmt : cobolProc.getStatements()) {
                StructuralStatementV2 stmt = new StructuralStatementV2();
                stmt.setType(cobolStmt.getType());
                stmt.setContent(cobolStmt.getContent());
                stmt.setLineNumber(cobolStmt.getLineNumber());
                
                // Add business logic details - safely handle null values
                stmt.setAccessedDataItems(cobolStmt.getAccessedDataItems() != null ? 
                    cobolStmt.getAccessedDataItems() : new ArrayList<>());
                stmt.setAccessedFiles(cobolStmt.getAccessedFiles() != null ? 
                    cobolStmt.getAccessedFiles() : new ArrayList<>());
                stmt.setSqlTable(cobolStmt.getSqlTable());
                stmt.setPerformTarget(cobolStmt.getPerformTarget());
                
                statements.add(stmt);
                
                // Update global sqlStatements and statementCounts
                if ("EXEC_SQL".equals(cobolStmt.getType())) {
                    sqlStatements.add(stmt);
                }
                incrementStatementCount(cobolStmt.getType());
                if (cobolStmt.getPerformTarget() != null) {
                    String normalizedTarget = normalizeIdentifier(cobolStmt.getPerformTarget());
                    performReferences.merge(normalizedTarget.toUpperCase(), 1, Integer::sum);
                }
            }
            proc.setStatements(statements);
            structuralProcedures.add(proc);
        }
        return structuralProcedures;
    }

    /**
     * FIXED: Merge procedures with data preservation
     */
    private void mergeProceduresWithDataPreservation(List<ProcedureBoundary> regexProcedures, 
    List<StructuralProcedureV2> extractedProcedures) {
        System.out.println("🔍 DEBUG: Starting procedure merge with data preservation");
        System.out.println("  - Data items before merge: " + extractedDataItems.size());
        System.out.println("  - File descriptors before merge: " + preservedFileDescriptors.size());

        Set<String> existingNames = procedures.stream()
        .map(StructuralProcedureV2::getName)
        .map(String::toUpperCase)
        .collect(Collectors.toSet());

        // Add regex procedures not already present
        for (ProcedureBoundary boundary : regexProcedures) 
        {
            if (!existingNames.contains(boundary.getName().toUpperCase())) {
            StructuralProcedureV2 proc = createProcedureFromConfigurableRegex(boundary);
                if (proc != null) {
                    procedures.add(proc);
                    existingNames.add(boundary.getName().toUpperCase());
                }
            }
        }

        // Add ProcedureExtractor procedures, updating existing ones if needed
        for (StructuralProcedureV2 extractedProc : extractedProcedures) 
        {
            String normalizedName = extractedProc.getName().toUpperCase();
            Optional<StructuralProcedureV2> existingProc = procedures.stream()
            .filter(p -> p.getName().toUpperCase().equals(normalizedName))
            .findFirst();

            if (existingProc.isPresent()) {
                // Update existing procedure with richer details
                StructuralProcedureV2 existing = existingProc.get();
                existing.setStatements(extractedProc.getStatements()); // Use richer statements
                existing.setContextScore(Math.max(existing.getContextScore(), extractedProc.getContextScore()));
                existing.setReasoningInfo(existing.getReasoningInfo() + ", enhanced by ProcedureExtractor");
            } 
            else {
                procedures.add(extractedProc);
                existingNames.add(normalizedName);
            }
        }

        // Sort by line number
        procedures.sort(Comparator.comparingInt(StructuralProcedureV2::getLineNumber));

        System.out.println("🔍 DEBUG: Procedure merge completed with data preservation");
        System.out.println("  - Data items after merge: " + extractedDataItems.size());
        System.out.println("  - File descriptors after merge: " + preservedFileDescriptors.size());
        System.out.println("  - Total procedures: " + procedures.size());

        // VERIFY DATA PRESERVATION
        if (dataItemsExtracted && extractedDataItems.isEmpty()) 
        {
            System.err.println("⚠️ WARNING: Data items were lost during procedure merge!");
            // Attempt recovery if possible
            if (!dataItemsBySection.isEmpty()) 
            {
                System.out.println("🔄 Attempting data recovery from preserved sections...");
                extractedDataItems.clear();
                for (List<StructuralDataItemV2> sectionItems : dataItemsBySection.values()) 
                {
                    extractedDataItems.addAll(sectionItems);
                }
                System.out.println("✅ Recovered " + extractedDataItems.size() + " data items");
            }
        }
    }

    /**
     * Enhanced shouldUseHybridMode using utilities
     */
    private boolean shouldUseHybridMode(List<ProcedureBoundary> regexProcedures) {
        EnhancedParserUtilities utilities = new EnhancedParserUtilities(config, sourceLines, performReferences, statementCounts);
        return utilities.shouldUseHybridMode(regexProcedures, procedures.size());
    }
    
    /**
     * Enhance with regex results using configurable logic
     */
    private void enhanceWithConfigurableRegexResults(List<ProcedureBoundary> regexProcedures) {
        Set<String> grammarProcNames = procedures.stream()
            .map(StructuralProcedureV2::getName)
            .collect(Collectors.toSet());
        
        EnhancedParserUtilities utilities = new EnhancedParserUtilities(config, sourceLines, performReferences, statementCounts);
        
        for (ProcedureBoundary boundary : regexProcedures) {
            if (!grammarProcNames.contains(boundary.getName())) {
                StructuralProcedureV2 proc = utilities.createProcedureFromConfigurableRegex(boundary);
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
     * Enhanced preprocessWithConfigurableRegex using utilities
     */
    private List<ProcedureBoundary> preprocessWithConfigurableRegex(String[] sourceToProcess) throws IOException {
        EnhancedParserUtilities utilities = new EnhancedParserUtilities(config, sourceToProcess, performReferences, statementCounts);
        return utilities.preprocessWithConfigurableRegex(sourceToProcess);
    }
    
    /**
     * Create procedure from regex boundary using configurable analysis
     */
    private StructuralProcedureV2 createProcedureFromConfigurableRegex(ProcedureBoundary boundary) {
        EnhancedParserUtilities utilities = new EnhancedParserUtilities(config, sourceLines, performReferences, statementCounts);
        return utilities.createProcedureFromConfigurableRegex(boundary);
    }
    
    /**
     * Calculate configurable end line using utilities
     */
    private int calculateConfigurableEndLine(int startLine) {
        EnhancedParserUtilities utilities = new EnhancedParserUtilities(config, sourceLines, performReferences, statementCounts);
        return utilities.calculateConfigurableEndLine(startLine);
    }
    
    /**
     * Determine program name using utilities
     */
    private String determineProgramName() {
        EnhancedParserUtilities utilities = new EnhancedParserUtilities(config, sourceLines, performReferences, statementCounts);
        return utilities.determineProgramName(programName);
    }
    
    /**
     * Read source lines from file
     */
    private String[] readSourceLines(String filename) throws IOException {
        return EnhancedParserUtilities.readSourceLines(filename);
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
     * Attempt grammar parsing with cleaned source
     */
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

    // ADD THIS METHOD - printEnhancedResults
    public void printEnhancedResults(StructuralAnalysisResultV2 result) {
        System.out.println("\n=== ENHANCED COBOL ANALYSIS RESULTS ===");
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
            .filter(p -> p.getContextScore() >= scoringMechanism.getMinimumScore() + 30.0)
            .count();
        System.out.println("High confidence procedures (≥" + (scoringMechanism.getMinimumScore() + 30.0) + "): " + highConfidenceProcs);
        
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
    
    
    private static void saveEnhancedAST(StructuralAnalysisResultV2 result, String filename) {
        try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
            writer.println("(ENHANCED-COBOL-ANALYSIS \"" + (result.getProgramName() != null ? result.getProgramName() : "UNKNOWN") + "\"");
            writer.println("  (METADATA");
            writer.println("    (ANALYSIS-TYPE \"ENHANCED-HYBRID-GRAMMAR\")");
            writer.println("    (TIMESTAMP \"" + new java.util.Date() + "\")");
            writer.println("    (PROCEDURES-COUNT " + (result.getProcedures() != null ? result.getProcedures().size() : 0) + ")");
            writer.println("    (DATA-ITEMS-COUNT " + (result.getDataItems() != null ? result.getDataItems().size() : 0) + ")");
            writer.println("    (FILE-DESCRIPTORS-COUNT " + (result.getFileDescriptors() != null ? result.getFileDescriptors().size() : 0) + ")");
            writer.println("    (SQL-STATEMENTS-COUNT " + (result.getSqlStatements() != null ? result.getSqlStatements().size() : 0) + ")");
            writer.println("    (COPY-STATEMENTS-COUNT " + (result.getCopyStatements() != null ? result.getCopyStatements().size() : 0) + ")");
            writer.println("    (STATEMENT-TYPES-COUNT " + (result.getStatementCounts() != null ? result.getStatementCounts().size() : 0) + ")");
            
            int totalStatements = 0;
            if (result.getStatementCounts() != null) {
                totalStatements = result.getStatementCounts().values().stream()
                    .mapToInt(Integer::intValue).sum();
            }
            writer.println("    (TOTAL-STATEMENTS " + totalStatements + ")");
            writer.println("  )");
            
            // ENHANCED: DATA DIVISION section with preservation info
            if (result.getDataItems() != null && !result.getDataItems().isEmpty()) {
                writer.println("  (DATA-DIVISION");
                
                // Group data items by section
                Map<String, List<StructuralDataItemV2>> itemsBySection = result.getDataItems().stream()
                    .collect(Collectors.groupingBy(
                        item -> item.getSection() != null ? item.getSection() : "UNKNOWN"
                    ));
                
                for (Map.Entry<String, List<StructuralDataItemV2>> entry : itemsBySection.entrySet()) {
                    String section = entry.getKey();
                    List<StructuralDataItemV2> items = entry.getValue();
                    
                    writer.println("    (SECTION \"" + section + "\"");
                    
                    for (StructuralDataItemV2 item : items) {
                        writer.println("      (DATA-ITEM");
                        writer.println("        (NAME \"" + (item.getName() != null ? item.getName() : "UNKNOWN") + "\")");
                        writer.println("        (LEVEL " + item.getLevel() + ")");
                        writer.println("        (LINE " + item.getLineNumber() + ")");
                        
                        if (item.getPicture() != null && !item.getPicture().trim().isEmpty()) {
                            writer.println("        (PICTURE \"" + item.getPicture().replace("\"", "\\\"") + "\")");
                        }
                        
                        if (item.getValue() != null && !item.getValue().trim().isEmpty()) {
                            writer.println("        (VALUE \"" + item.getValue().replace("\"", "\\\"") + "\")");
                        }
                        
                        if (item.getRedefines() != null && !item.getRedefines().trim().isEmpty()) {
                            writer.println("        (REDEFINES \"" + item.getRedefines().replace("\"", "\\\"") + "\")");
                        }
                        
                        if (item.getOccurs() != null && !item.getOccurs().trim().isEmpty()) {
                            writer.println("        (OCCURS \"" + item.getOccurs().replace("\"", "\\\"") + "\")");
                        }
                        
                        if (item.getUsage() != null && !item.getUsage().trim().isEmpty()) {
                            writer.println("        (USAGE \"" + item.getUsage().replace("\"", "\\\"") + "\")");
                        }
                        
                        writer.println("      )");
                    }
                    
                    writer.println("    )");
                }
                
                writer.println("  )");
            }
            
            // File descriptors section
            if (result.getFileDescriptors() != null && !result.getFileDescriptors().isEmpty()) {
                writer.println("  (FILE-DESCRIPTORS");
                for (DataDivisionPreprocessor.FileDescriptor fd : result.getFileDescriptors()) {
                    writer.println("    (FILE-DESCRIPTOR");
                    writer.println("      (NAME \"" + (fd.getName() != null ? fd.getName() : "UNKNOWN") + "\")");
                    writer.println("      (LINE " + fd.getLineNumber() + ")");
                    if (fd.getDefinition() != null) {
                        String definition = fd.getDefinition().replace("\"", "\\\"").replace("\n", "\\n");
                        if (definition.length() > 200) {
                            definition = definition.substring(0, 197) + "...";
                        }
                        writer.println("      (DEFINITION \"" + definition + "\")");
                    }
                    writer.println("    )");
                }
                writer.println("  )");
            }
            
            // Enhanced procedures with null safety
            writer.println("  (PROCEDURES");
            if (result.getProcedures() != null) {
                for (StructuralProcedureV2 proc : result.getProcedures()) {
                    writer.println("    (PROCEDURE \"" + (proc.getName() != null ? proc.getName() : "UNKNOWN") + "\"");
                    writer.println("      (SCORE " + proc.getContextScore() + ")");
                    writer.println("      (START-LINE " + proc.getLineNumber() + ")");
                    writer.println("      (END-LINE " + proc.getEndLineNumber() + ")");
                    writer.println("      (REASONING \"" + (proc.getReasoningInfo() != null ? proc.getReasoningInfo().replace("\"", "\\\"") : "") + "\")");
                    
                    int actualRefCount = getActualPerformReferenceCount(proc.getName(), result.getPerformReferences());
                    writer.println("      (PERFORM-REFERENCES " + actualRefCount + ")");
                    
                    // Statement distribution with null safety
                    if (proc.getStatements() != null) {
                        Map<String, Long> procStmtTypes = proc.getStatements().stream()
                            .filter(stmt -> stmt != null && stmt.getType() != null)
                            .collect(Collectors.groupingBy(StructuralStatementV2::getType, Collectors.counting()));
                        writer.println("      (STATEMENT-DISTRIBUTION");
                        procStmtTypes.entrySet().stream()
                            .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                            .forEach(entry -> writer.println("        (" + entry.getKey() + " " + entry.getValue() + ")"));
                        writer.println("      )");
                        
                        // Statements with null safety
                        writer.println("      (STATEMENTS");
                        for (StructuralStatementV2 stmt : proc.getStatements()) {
                            if (stmt != null) {
                                String content = stmt.getContent() != null ? stmt.getContent() : "";
                                content = content.replace("\"", "\\\"").replace("\n", "\\n");
                                if (content.length() > 150) {
                                    content = content.substring(0, 147) + "...";
                                }
                                String type = stmt.getType() != null ? stmt.getType() : "UNKNOWN";
                                writer.println("        (" + type + " \"" + content + "\" " + stmt.getLineNumber() + ")");
                            }
                        }
                        writer.println("      )");
                    } else {
                        writer.println("      (STATEMENT-DISTRIBUTION)");
                        writer.println("      (STATEMENTS)");
                    }
                    writer.println("    )");
                }
            }
            writer.println("  )");
            
            // Statement analysis with null safety
            writer.println("  (STATEMENT-ANALYSIS");
            writer.println("    (STATEMENT-DISTRIBUTION");
            if (result.getStatementCounts() != null) {
                result.getStatementCounts().entrySet().stream()
                    .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
                    .forEach(entry -> writer.println("      (" + entry.getKey() + " " + entry.getValue() + ")"));
            }
            writer.println("    )");
            writer.println("  )");
            
            // PERFORM reference graph with null safety
            writer.println("  (PERFORM-GRAPH");
            if (result.getPerformReferences() != null) {
                result.getPerformReferences().entrySet().stream()
                    .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
                    .forEach(entry -> writer.println("    (\"" + (entry.getKey() != null ? entry.getKey().replace("\"", "\\\"") : "") + "\" " + entry.getValue() + ")"));
            }
            writer.println("  )");
            
            writer.println(")");
            
            System.out.println("📄 Enhanced AST saved with DATA DIVISION preservation to: " + filename);
            
        } catch (IOException e) {
            System.err.println("❌ Error saving enhanced AST: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
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
}

