/**
 * Enhanced TAL AST Parser with improved TAL syntax support
 * Fixes for bit fields, pointer operations, string moves, and SCAN statements
 * Author: Enhanced for Complete TAL Analysis
 */

 import org.antlr.v4.runtime.*;
 import org.antlr.v4.runtime.tree.*;
 import java.io.*;
 import java.nio.file.*;
 import java.util.*;
 import java.util.stream.Collectors;
 import java.util.regex.Pattern;
 import java.util.regex.Matcher;
 
 public class TALASTParser extends TALBaseListener {
     
     // Configuration and preprocessing components
     private TALParserConfiguration config;
     private TALDataPreprocessor dataPreprocessor;
     private List<TALStructuralDataItem> extractedDataItems = new ArrayList<>();
     private List<TALFileDescriptor> fileDescriptors = new ArrayList<>();
     private boolean dataItemsExtracted = false;
     private Map<String, List<TALStructuralDataItem>> dataItemsBySection = new HashMap<>();
     private List<TALFileDescriptor> preservedFileDescriptors = new ArrayList<>();
 
     // CRITICAL: Source lines for analysis
     private String[] sourceLines;
     
     // Enhanced scoring and filtering components
     private TALScoringMechanism scoringMechanism;
     private TALProcedureFilter procedureFilter;
     
     // Analysis results
     private TALStructuralAnalysisResult result;
     private List<TALStructuralProcedure> procedures = new ArrayList<>();
     private List<TALStructuralStatement> sqlStatements = new ArrayList<>();
     private List<TALStructuralStatement> copyStatements = new ArrayList<>();
     private List<TALStructuralStatement> callStatements = new ArrayList<>();
     private List<TALStructuralStatement> systemStatements = new ArrayList<>();
     private String programName = "UNKNOWN";
     private Map<String, Integer> callReferences = new HashMap<>();
     private Map<String, Integer> statementCounts = new HashMap<>();
     private List<String> parseWarnings = new ArrayList<>();
     private List<String> preprocessWarnings = new ArrayList<>();
     private CommonTokenStream tokenStream;
     private TALStructuralProcedure currentProcedure;
     private TALProcedureExtractor procedureExtractor;
 
     public static void main(String[] args) {
         if (args.length < 1) {
             System.err.println("Usage: java TALASTParser <tal-file> [config-file]");
             System.err.println("Examples:");
             System.err.println("  java TALASTParser myprogram.tal");
             System.err.println("  java TALASTParser myprogram.tal custom-config.properties");
             System.exit(1);
         }
         
         try {
             TALASTParser parser;
             if (args.length > 1) {
                 parser = new TALASTParser(args[1]);
             } else {
                 parser = new TALASTParser("tal-grammar.properties");
             }
             
             String talFile = args[0];
             System.out.println("🚀 Starting Enhanced TAL AST Parser analysis of: " + talFile);
             
             TALStructuralAnalysisResult result = parser.parseTALWithGrammar(talFile);
             
             parser.printEnhancedResults(result);
             
             String astFilename = talFile + ".ast";
             saveEnhancedAST(result, astFilename);
             
             System.out.println("✅ Analysis complete! AST saved to: " + astFilename);
             
         } catch (Exception e) {
             System.err.println("❌ Error analyzing TAL file: " + e.getMessage());
             if (e.getCause() != null) {
                 System.err.println("Caused by: " + e.getCause().getMessage());
             }
             e.printStackTrace();
             System.exit(1);
         }
     }
 
     // Constructor with configuration
     public TALASTParser(String configFile) {
         this.config = loadConfiguration(configFile);
         this.dataPreprocessor = new TALDataPreprocessor(config);
         this.procedureExtractor = new TALProcedureExtractor(config);
     }
     
     private void initializeEnhancedComponents() {
         this.scoringMechanism = new TALScoringMechanism(config, sourceLines, callReferences);
         this.procedureFilter = new TALProcedureFilter(config, scoringMechanism, callReferences);
     }
 
     private TALParserConfiguration loadConfiguration(String configFile) {
         TALParserConfiguration config = new TALParserConfiguration();
         config.loadDefaults();
         
         if (config.isVerboseLogging()) {
             System.out.println("📊 Using default TAL configuration");
         }
         
         List<String> issues = config.validate();
         if (!issues.isEmpty()) {
             System.err.println("⚠️ Configuration issues:");
             issues.forEach(issue -> System.err.println("  - " + issue));
         }
         
         return config;
     }

     public TALStructuralAnalysisResult parseTALWithGrammar(String filename) throws Exception {
        if (config.isVerboseLogging()) {
            System.out.println("🔍 Enhanced TAL grammar analysis of file: " + filename);
            System.out.println("📊 Configuration: " + config.toString());
        }
        
        sourceLines = readSourceLines(filename);
        System.out.println("📖 DEBUG: Read " + sourceLines.length + " source lines");
        
        initializeEnhancedComponents();
        
        TALDataPreprocessor.PreprocessingResult preprocessResult = null;
        if (config.isDataPreprocessingEnabled()) {
            if (config.isVerboseLogging()) {
                System.out.println("🔄 Preprocessing TAL DATA/TYPE sections...");
            }
            
            preprocessResult = dataPreprocessor.preprocessDataSections(sourceLines);
            preserveDataItems(preprocessResult);
            preprocessWarnings.addAll(preprocessResult.getWarnings());
            
            System.out.println("📖 DEBUG: After preprocessing and preservation:");
            System.out.println("  - Data items preserved: " + extractedDataItems.size());
            System.out.println("  - File descriptors preserved: " + preservedFileDescriptors.size());
            System.out.println("  - Data items by section: " + dataItemsBySection.size() + " sections");
        }
        
        List<TALProcedureBoundary> regexProcedures = new ArrayList<>();
        if (config.isRegexPreprocessingEnabled()) {
            String[] sourceToParse = sourceLines;
            if (preprocessResult != null && preprocessResult.getCleanedSource() != null) {
                sourceToParse = preprocessResult.getCleanedSource();
            }
            
            System.out.println("📖 DEBUG: Starting regex preprocessing with " + sourceToParse.length + " lines");
            regexProcedures = preprocessWithConfigurableRegex(sourceToParse);
            System.out.println("📖 DEBUG: Regex preprocessing found " + regexProcedures.size() + " procedure candidates");
        }
        
        boolean grammarSuccess = false;
        if (config.isGrammarParsingEnabled()) {
            System.out.println("📖 DEBUG: Starting enhanced grammar parsing...");
            String[] sourceToParse = sourceLines;
            if (preprocessResult != null && preprocessResult.getCleanedSource() != null) {
                sourceToParse = preprocessResult.getCleanedSource();
            }
            grammarSuccess = attemptEnhancedGrammarParsing(filename, sourceToParse);
            System.out.println("📖 DEBUG: Grammar parsing success: " + grammarSuccess);
            System.out.println("📖 DEBUG: Procedures found via grammar: " + procedures.size());
        }
        
        System.out.println("📖 DEBUG: Running enhanced TAL ProcedureExtractor...");
        TALBusinessLogicResult extractorResult = procedureExtractor.extractBusinessLogic(filename);
        List<TALStructuralProcedure> extractedProcedures = convertExtractorProcedures(extractorResult.getProcedures());
        
        System.out.println("📖 DEBUG: Merging procedures while preserving data items...");
        mergeProceduresWithDataPreservation(regexProcedures, extractedProcedures);
        
        if (config.isHybridModeEnabled() && shouldUseHybridMode(regexProcedures)) {
            if (config.isVerboseLogging()) {
                System.out.println("🔄 Applying hybrid enhancement...");
            }
            enhanceWithRegexResults(regexProcedures);
        }
        
        result = new TALStructuralAnalysisResult();
        result.setProgramName(determineProgramName(filename)); // Pass filename here
        List<TALStructuralProcedure> filteredProcedures = applyEnhancedFiltering();
        TALStatementInitializer.initializeAllProcedures(filteredProcedures);
        
        result.setProcedures(filteredProcedures);
        result.setSqlStatements(sqlStatements);
        result.setCopyStatements(copyStatements);
        result.setCallStatements(callStatements);
        result.setSystemStatements(systemStatements);
        result.setStatementCounts(statementCounts);
        result.setCallReferences(callReferences);
        result.setParseWarnings(parseWarnings);
        result.setDataItems(getPreservedDataItems());
        result.setFileDescriptors(getPreservedFileDescriptors());
        
        System.out.println("📖 DEBUG: Final result verification:");
        System.out.println("  - Procedures: " + result.getProcedures().size());
        System.out.println("  - Data items: " + result.getDataItems().size());
        System.out.println("  - File descriptors: " + result.getFileDescriptors().size());
        
        return result;
    }
 
 
     // ENHANCED: New method for improved grammar parsing with TAL-specific patterns
     private boolean attemptEnhancedGrammarParsing(String filename, String[] sourceToParse) {
         try {
             if (sourceToParse == null || sourceToParse.length == 0) {
                 System.out.println("📖 DEBUG: No source to parse");
                 return false;
             }
             
             // Enhanced TAL-specific parsing using direct line analysis
             boolean success = parseWithEnhancedTALPatterns(sourceToParse);
             
             // Fallback to ANTLR if available
             if (!success) {
                 System.out.println("📖 DEBUG: Falling back to ANTLR parsing...");
                 success = attemptGrammarParsing(filename, sourceToParse);
             }
             
             return success;
             
         } catch (Exception e) {
             if (config.getErrorRecoveryMode() == TALErrorRecoveryMode.STRICT) {
                 throw new RuntimeException("Enhanced grammar parsing failed in strict mode", e);
             }
             
             if (config.isVerboseLogging()) {
                 System.err.println("⚠️ Enhanced grammar parsing encountered issues: " + e.getMessage());
             }
             return false;
         }
     }
 
     // ENHANCED: New method for TAL-specific pattern parsing
     private boolean parseWithEnhancedTALPatterns(String[] sourceToParse) {
         try {
             // Enhanced patterns for TAL constructs
             Pattern procPattern = Pattern.compile("^\\s*(INT\\s+PROC|PROC|SUBPROC)\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*(?:\\([^)]*\\))?\\s*(?:MAIN)?\\s*;?", Pattern.CASE_INSENSITIVE);
             Pattern namePattern = Pattern.compile("^\\s*NAME\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*;", Pattern.CASE_INSENSITIVE);
             
             // Enhanced statement patterns
             Pattern bitFieldPattern = Pattern.compile("([A-Za-z_][A-Za-z0-9_.]*)\\.\\s*<(\\d+):(\\d+)>\\s*:=\\s*([^;]+);?", Pattern.CASE_INSENSITIVE);
             Pattern pointerDerefPattern = Pattern.compile("(\\.\\s*[A-Za-z_][A-Za-z0-9_]*)\\s*:=\\s*([^;]+);?", Pattern.CASE_INSENSITIVE);
             Pattern stringMovePattern = Pattern.compile("([A-Za-z_][A-Za-z0-9_.\\[\\]]*)'\\s*:='\\s*([^;]+);?", Pattern.CASE_INSENSITIVE);
             Pattern scanPattern = Pattern.compile("^\\s*SCAN\\s+([A-Za-z_][A-Za-z0-9_.]*)\\s+WHILE\\s+([^\\->]+)\\s*->\\s*([^;]+);?", Pattern.CASE_INSENSITIVE);
             Pattern rscanPattern = Pattern.compile("^\\s*RSCAN\\s+([A-Za-z_][A-Za-z0-9_.]*)\\s+WHILE\\s+([^\\->]+)\\s*->\\s*([^;]+);?", Pattern.CASE_INSENSITIVE);
             Pattern callPattern = Pattern.compile("^\\s*CALL\\s+(\\$?[A-Za-z_][A-Za-z0-9_]*)", Pattern.CASE_INSENSITIVE);
             Pattern assignmentPattern = Pattern.compile("^\\s*([A-Za-z_@][A-Za-z0-9_@.\\[\\]]*?)\\s*:=\\s*([^;]+);?", Pattern.CASE_INSENSITIVE);
             Pattern ifPattern = Pattern.compile("^\\s*IF\\s+([^\\sTHEN]+)(?:\\s+THEN)?", Pattern.CASE_INSENSITIVE);
             Pattern returnPattern = Pattern.compile("^\\s*RETURN\\s*([^;]*);?", Pattern.CASE_INSENSITIVE);
             
             TALStructuralProcedure currentProc = null;
             
             for (int i = 0; i < sourceToParse.length; i++) {
                 String line = sourceToParse[i].trim();
                 if (line.isEmpty() || line.startsWith("!")) continue;
                 
                 // Check for program name
                 Matcher nameMatcher = namePattern.matcher(line);
                 if (nameMatcher.find()) {
                     programName = nameMatcher.group(1);
                     if (config.isVerboseLogging()) {
                         System.out.println("📖 Found program name: " + programName);
                     }
                     continue;
                 }
                 
                 // Check for procedure start
                 Matcher procMatcher = procPattern.matcher(line);
                 if (procMatcher.find()) {
                     if (currentProc != null) {
                         procedures.add(currentProc);
                     }
                     
                     String procName = procMatcher.group(2);
                     currentProc = new TALStructuralProcedure();
                     currentProc.setName(procName);
                     currentProc.setLineNumber(i + 1);
                     currentProc.setStatements(new ArrayList<>());
                     
                     if (config.isVerboseLogging()) {
                         System.out.println("➕ Enhanced procedure: " + procName + " at line " + (i + 1));
                     }
                     continue;
                 }
                 
                 // Check for END (procedure end)
                 if (line.toUpperCase().equals("END;") && currentProc != null) {
                     currentProc.setEndLineNumber(i + 1);
                     TALStructuralStatement stmt = new TALStructuralStatement();
                     stmt.setType("END");
                     stmt.setContent(line);
                     stmt.setLineNumber(i + 1);
                     currentProc.getStatements().add(stmt);
                     incrementStatementCount("END");
                     continue;
                 }
                 
                 if (currentProc == null) continue;
                 
                 // ENHANCED: Parse bit field operations
                 Matcher bitFieldMatcher = bitFieldPattern.matcher(line);
                 if (bitFieldMatcher.find()) {
                     TALStructuralStatement stmt = new TALStructuralStatement();
                     stmt.setType("BIT_FIELD_ASSIGNMENT");
                     stmt.setContent(line);
                     stmt.setLineNumber(i + 1);
                     
                     String variable = bitFieldMatcher.group(1);
                     String startBit = bitFieldMatcher.group(2);
                     String endBit = bitFieldMatcher.group(3);
                     String value = bitFieldMatcher.group(4);
                     
                     stmt.setAccessedVariables(Arrays.asList(variable));
                     stmt.setBitFieldInfo(variable, startBit, endBit, value);
                     
                     currentProc.getStatements().add(stmt);
                     incrementStatementCount("BIT_FIELD_ASSIGNMENT");
                     
                     if (config.isVerboseLogging()) {
                         System.out.println("🔧 Found bit field assignment: " + variable + ".<" + startBit + ":" + endBit + ">");
                     }
                     continue;
                 }
                 
                 // ENHANCED: Parse pointer dereference operations
                 Matcher pointerDerefMatcher = pointerDerefPattern.matcher(line);
                 if (pointerDerefMatcher.find()) {
                     TALStructuralStatement stmt = new TALStructuralStatement();
                     stmt.setType("POINTER_DEREFERENCE");
                     stmt.setContent(line);
                     stmt.setLineNumber(i + 1);
                     
                     String pointer = pointerDerefMatcher.group(1);
                     String value = pointerDerefMatcher.group(2);
                     
                     stmt.setAccessedVariables(Arrays.asList(pointer.replace(".", "")));
                     stmt.setPointerTarget(pointer);
                     
                     currentProc.getStatements().add(stmt);
                     incrementStatementCount("POINTER_DEREFERENCE");
                     
                     if (config.isVerboseLogging()) {
                         System.out.println("👉 Found pointer dereference: " + pointer + " := " + value);
                     }
                     continue;
                 }
                 
                 // ENHANCED: Parse string move operations
                 Matcher stringMoveMatcher = stringMovePattern.matcher(line);
                 if (stringMoveMatcher.find()) {
                     TALStructuralStatement stmt = new TALStructuralStatement();
                     stmt.setType("STRING_MOVE");
                     stmt.setContent(line);
                     stmt.setLineNumber(i + 1);
                     
                     String target = stringMoveMatcher.group(1);
                     String source = stringMoveMatcher.group(2);
                     
                     stmt.setAccessedVariables(Arrays.asList(target));
                     stmt.setStringMoveInfo(target, source);
                     
                     currentProc.getStatements().add(stmt);
                     incrementStatementCount("STRING_MOVE");
                     
                     if (config.isVerboseLogging()) {
                         System.out.println("📝 Found string move: " + target + " ':=' " + source);
                     }
                     continue;
                 }
                 
                 // ENHANCED: Parse SCAN operations
                 Matcher scanMatcher = scanPattern.matcher(line);
                 if (scanMatcher.find()) {
                     TALStructuralStatement stmt = new TALStructuralStatement();
                     stmt.setType("SCAN");
                     stmt.setContent(line);
                     stmt.setLineNumber(i + 1);
                     
                     String source = scanMatcher.group(1);
                     String condition = scanMatcher.group(2).trim();
                     String target = scanMatcher.group(3).trim();
                     
                     stmt.setAccessedVariables(Arrays.asList(source, target.replace("@", "")));
                     stmt.setScanInfo(source, condition, target);
                     
                     currentProc.getStatements().add(stmt);
                     incrementStatementCount("SCAN");
                     
                     if (config.isVerboseLogging()) {
                         System.out.println("🔍 Found SCAN: " + source + " WHILE " + condition + " -> " + target);
                     }
                     continue;
                 }
                 
                 // Parse RSCAN operations
                 Matcher rscanMatcher = rscanPattern.matcher(line);
                 if (rscanMatcher.find()) {
                     TALStructuralStatement stmt = new TALStructuralStatement();
                     stmt.setType("RSCAN");
                     stmt.setContent(line);
                     stmt.setLineNumber(i + 1);
                     
                     String source = rscanMatcher.group(1);
                     String condition = rscanMatcher.group(2).trim();
                     String target = rscanMatcher.group(3).trim();
                     
                     stmt.setScanInfo(source, condition, target);
                     stmt.setAccessedVariables(Arrays.asList(source, target.replace("@", "")));
                     
                     currentProc.getStatements().add(stmt);
                     incrementStatementCount("RSCAN");
                     
                     if (config.isVerboseLogging()) {
                         System.out.println("🔍 Found RSCAN: " + source + " WHILE " + condition + " -> " + target);
                     }
                     continue;
                 }
                 
                 // ENHANCED: Parse CALL statements
                 Matcher callMatcher = callPattern.matcher(line);
                 if (callMatcher.find()) {
                     TALStructuralStatement stmt = new TALStructuralStatement();
                     stmt.setType("CALL");
                     stmt.setContent(line);
                     stmt.setLineNumber(i + 1);
                     
                     String callTarget = callMatcher.group(1);
                     
                     if (callTarget.startsWith("$")) {
                         stmt.setSystemFunction(callTarget);
                         systemStatements.add(stmt);
                         incrementStatementCount("SYSTEM");
                     } else {
                         stmt.setCallTarget(callTarget);
                         callStatements.add(stmt);
                     }
                     
                     callReferences.merge(callTarget.toUpperCase(), 1, Integer::sum);
                     currentProc.getStatements().add(stmt);
                     incrementStatementCount("CALL");
                     
                     if (config.isVerboseLogging()) {
                         System.out.println("📞 Found call to: " + callTarget);
                     }
                     continue;
                 }
                 
                 // Parse IF statements
                 Matcher ifMatcher = ifPattern.matcher(line);
                 if (ifMatcher.find()) {
                     TALStructuralStatement stmt = new TALStructuralStatement();
                     stmt.setType("IF");
                     stmt.setContent(line);
                     stmt.setLineNumber(i + 1);
                     
                     String condition = ifMatcher.group(1);
                     stmt.setCondition(condition);
                     
                     currentProc.getStatements().add(stmt);
                     incrementStatementCount("IF");
                     continue;
                 }
                 
                 // Parse ENDIF statements
                 if (line.toUpperCase().equals("ENDIF;")) {
                     TALStructuralStatement stmt = new TALStructuralStatement();
                     stmt.setType("ENDIF");
                     stmt.setContent(line);
                     stmt.setLineNumber(i + 1);
                     currentProc.getStatements().add(stmt);
                     incrementStatementCount("ENDIF");
                     continue;
                 }
                 
                 // Parse RETURN statements
                 Matcher returnMatcher = returnPattern.matcher(line);
                 if (returnMatcher.find()) {
                     TALStructuralStatement stmt = new TALStructuralStatement();
                     stmt.setType("RETURN");
                     stmt.setContent(line);
                     stmt.setLineNumber(i + 1);
                     
                     String returnValue = returnMatcher.group(1);
                     if (!returnValue.trim().isEmpty()) {
                         stmt.setReturnValue(returnValue);
                     }
                     
                     currentProc.getStatements().add(stmt);
                     incrementStatementCount("RETURN");
                     continue;
                 }
                 
                 // ENHANCED: Parse general assignments (including pointer assignments)
                 Matcher assignMatcher = assignmentPattern.matcher(line);
                 if (assignMatcher.find()) {
                     TALStructuralStatement stmt = new TALStructuralStatement();
                     
                     String target = assignMatcher.group(1);
                     String value = assignMatcher.group(2);
                     
                     // Detect pointer assignment
                     if (target.startsWith("@") || value.startsWith("@")) {
                         stmt.setType("POINTER_ASSIGNMENT");
                         stmt.setPointerTarget(target);
                         incrementStatementCount("POINTER_ASSIGNMENT");
                     } else {
                         stmt.setType("ASSIGNMENT");
                         incrementStatementCount("ASSIGNMENT");
                     }
                     
                     stmt.setContent(line);
                     stmt.setLineNumber(i + 1);
                     stmt.setAccessedVariables(Arrays.asList(target.replace("@", "")));
                     
                     currentProc.getStatements().add(stmt);
                     continue;
                 }
             }
             
             // Add the last procedure
             if (currentProc != null) {
                 procedures.add(currentProc);
             }
             
             // Set scores and reasoning for all procedures
             for (TALStructuralProcedure proc : procedures) {
                 proc.setContextScore(scoringMechanism.calculateScore(proc));
                 proc.setReasoningInfo("Found via enhanced TAL grammar parsing");
             }
             
             System.out.println("📖 DEBUG: Enhanced parsing found " + procedures.size() + " procedures");
             return true;
             
         } catch (Exception e) {
             System.err.println("⚠️ Error in enhanced TAL parsing: " + e.getMessage());
             e.printStackTrace();
             return false;
         }
     }
 
     // Original ANTLR-based parsing method (kept as fallback)
     private boolean attemptGrammarParsing(String filename, String[] sourceToParse) {
         try {
             if (sourceToParse == null || sourceToParse.length == 0) {
                 System.out.println("📖 DEBUG: No source to parse");
                 return false;
             }
             
             String sourceContent = String.join("\n", sourceToParse);
             ANTLRInputStream input = new ANTLRInputStream(sourceContent);
             
             TALLexer lexer = new TALLexer(input);
             this.tokenStream = new CommonTokenStream(lexer);
             TALParser parser = new TALParser(tokenStream);
             
             TALErrorListener errorListener = new TALErrorListener("Grammar", parseWarnings, config);
             parser.removeErrorListeners();
             parser.addErrorListener(errorListener);
             
             TALParser.ProgramContext tree = parser.program();
             
             if (tree == null) {
                 System.out.println("📖 DEBUG: Parse tree is null");
                 return false;
             }
             
             ParseTreeWalker walker = new ParseTreeWalker();
             walker.walk(this, tree);
             
             return true;
             
         } catch (Exception e) {
             if (config.getErrorRecoveryMode() == TALErrorRecoveryMode.STRICT) {
                 throw new RuntimeException("Grammar parsing failed in strict mode", e);
             }
             
             if (config.isVerboseLogging()) {
                 System.err.println("⚠️ Grammar parsing encountered issues: " + e.getMessage());
                 e.printStackTrace();
             }
             return false;
         }
     }
 
     // Rest of the class implementation remains largely the same but with enhanced statement handling
     
     static class TALStructuralAnalysisResult {
         private String programName;
         private List<TALStructuralProcedure> procedures = new ArrayList<>();
         private List<TALStructuralDataItem> dataItems = new ArrayList<>();
         private List<TALFileDescriptor> fileDescriptors = new ArrayList<>();
         private List<TALStructuralStatement> sqlStatements = new ArrayList<>();
         private List<TALStructuralStatement> copyStatements = new ArrayList<>();
         private List<TALStructuralStatement> callStatements = new ArrayList<>();
         private List<TALStructuralStatement> systemStatements = new ArrayList<>();
         private Map<String, Integer> statementCounts = new HashMap<>();
         private Map<String, Integer> callReferences = new HashMap<>();
         private List<String> parseWarnings = new ArrayList<>();
     
         public String getProgramName() { return programName; }
         public void setProgramName(String programName) { this.programName = programName; }
         public List<TALStructuralProcedure> getProcedures() { return procedures; }
         public void setProcedures(List<TALStructuralProcedure> procedures) { this.procedures = procedures; }
         public List<TALStructuralDataItem> getDataItems() { return dataItems; }
         public void setDataItems(List<TALStructuralDataItem> dataItems) { this.dataItems = dataItems; }
         public List<TALFileDescriptor> getFileDescriptors() { return fileDescriptors; }
         public void setFileDescriptors(List<TALFileDescriptor> fileDescriptors) { this.fileDescriptors = fileDescriptors; }
         public List<TALStructuralStatement> getSqlStatements() { return sqlStatements; }
         public void setSqlStatements(List<TALStructuralStatement> sqlStatements) { this.sqlStatements = sqlStatements; }
         public List<TALStructuralStatement> getCopyStatements() { return copyStatements; }
         public void setCopyStatements(List<TALStructuralStatement> copyStatements) { this.copyStatements = copyStatements; }
         public List<TALStructuralStatement> getCallStatements() { return callStatements; }
         public void setCallStatements(List<TALStructuralStatement> callStatements) { this.callStatements = callStatements; }
         public List<TALStructuralStatement> getSystemStatements() { return systemStatements; }
         public void setSystemStatements(List<TALStructuralStatement> systemStatements) { this.systemStatements = systemStatements; }
         public Map<String, Integer> getStatementCounts() { return statementCounts; }
         public void setStatementCounts(Map<String, Integer> statementCounts) { this.statementCounts = statementCounts; }
         public Map<String, Integer> getCallReferences() { return callReferences; }
         public void setCallReferences(Map<String, Integer> callReferences) { this.callReferences = callReferences; }
         public List<String> getParseWarnings() { return parseWarnings; }
         public void setParseWarnings(List<String> parseWarnings) { this.parseWarnings = parseWarnings; }
     }
 
     private void preserveDataItems(TALDataPreprocessor.PreprocessingResult preprocessResult) {
         if (preprocessResult == null) {
             System.out.println("📖 DEBUG: No preprocessing result to preserve");
             return;
         }
         
         extractedDataItems.clear();
         if (preprocessResult.getDataItems() != null) {
             extractedDataItems.addAll(preprocessResult.getDataItems());
         }
         
         preservedFileDescriptors.clear();
         if (preprocessResult.getFileDescriptors() != null) {
             preservedFileDescriptors.addAll(preprocessResult.getFileDescriptors());
         }
         
         dataItemsBySection.clear();
         dataItemsBySection = extractedDataItems.stream()
             .collect(Collectors.groupingBy(
                 item -> item.getSection() != null ? item.getSection() : "UNKNOWN"
             ));
         
         dataItemsExtracted = true;
         
         System.out.println("📖 DEBUG: Data items preserved successfully:");
         System.out.println("  - Total data items: " + extractedDataItems.size());
         System.out.println("  - Total file descriptors: " + preservedFileDescriptors.size());
     }
 
     private List<TALStructuralDataItem> getPreservedDataItems() {
         if (!dataItemsExtracted || extractedDataItems.isEmpty()) {
             return new ArrayList<>();
         }
         return new ArrayList<>(extractedDataItems);
     }
 
     private List<TALFileDescriptor> getPreservedFileDescriptors() {
         if (preservedFileDescriptors.isEmpty()) {
             return new ArrayList<>();
         }
         return new ArrayList<>(preservedFileDescriptors);
     }
 
     private List<TALStructuralProcedure> applyEnhancedFiltering() {
         return procedureFilter.applyEnhancedFiltering(procedures);
     }
 
     private List<TALStructuralProcedure> convertExtractorProcedures(List<TALProcedure> talProcedures) {
         List<TALStructuralProcedure> structuralProcedures = new ArrayList<>();
         for (TALProcedure talProc : talProcedures) {
             TALStructuralProcedure proc = new TALStructuralProcedure();
             proc.setName(talProc.getName());
             proc.setLineNumber(talProc.getLineNumber());
             proc.setEndLineNumber(calculateEndLine(talProc.getLineNumber()));
             proc.setContextScore(scoringMechanism.calculateScore(talProc));
             proc.setReasoningInfo(scoringMechanism.buildReasoning(talProc));
             
             List<TALStructuralStatement> statements = new ArrayList<>();
             for (TALStatement talStmt : talProc.getStatements()) {
                 TALStructuralStatement stmt = new TALStructuralStatement();
                 stmt.setType(talStmt.getType());
                 stmt.setContent(talStmt.getContent());
                 stmt.setLineNumber(talStmt.getLineNumber());
                 
                 stmt.setAccessedVariables(talStmt.getAccessedVariables() != null ? 
                     talStmt.getAccessedVariables() : new ArrayList<>());
                 stmt.setAccessedFiles(talStmt.getAccessedFiles() != null ? 
                     talStmt.getAccessedFiles() : new ArrayList<>());
                 stmt.setCallTarget(talStmt.getCallTarget());
                 stmt.setSystemFunction(talStmt.getSystemFunction());
                 
                 // Avoid duplicate RETURN statements
                 if ("RETURN".equals(talStmt.getType()) && !statements.stream()
                         .anyMatch(s -> s.getType().equals("RETURN") && s.getLineNumber() == talStmt.getLineNumber())) {
                     statements.add(stmt);
                 } else if (!"RETURN".equals(talStmt.getType())) {
                     statements.add(stmt);
                 }
                 
                 if ("SQL".equals(talStmt.getType())) {
                     sqlStatements.add(stmt);
                 } else if ("COPY".equals(talStmt.getType())) {
                     copyStatements.add(stmt);
                 } else if ("CALL".equals(talStmt.getType())) {
                     callStatements.add(stmt);
                 } else if (talStmt.getSystemFunction() != null) {
                     systemStatements.add(stmt);
                 }
                 
                 incrementStatementCount(talStmt.getType());
                 
                 if (talStmt.getCallTarget() != null) {
                     String normalizedTarget = normalizeIdentifier(talStmt.getCallTarget());
                     callReferences.merge(normalizedTarget.toUpperCase(), 1, Integer::sum);
                 }
             }
             proc.setStatements(statements);
             structuralProcedures.add(proc);
         }
         return structuralProcedures;
     }
 
     private void mergeProceduresWithDataPreservation(List<TALProcedureBoundary> regexProcedures, 
                                                     List<TALStructuralProcedure> extractedProcedures) {
         System.out.println("📖 DEBUG: Starting procedure merge with data preservation");
         
         Set<String> existingNames = procedures.stream()
             .map(TALStructuralProcedure::getName)
             .map(String::toUpperCase)
             .collect(Collectors.toSet());
 
         for (TALProcedureBoundary boundary : regexProcedures) {
             if (!existingNames.contains(boundary.getName().toUpperCase())) {
                 TALStructuralProcedure proc = createProcedureFromRegex(boundary);
                 if (proc != null) {
                     procedures.add(proc);
                     existingNames.add(boundary.getName().toUpperCase());
                 }
             }
         }
 
         for (TALStructuralProcedure extractedProc : extractedProcedures) {
             String normalizedName = extractedProc.getName().toUpperCase();
             Optional<TALStructuralProcedure> existingProc = procedures.stream()
                 .filter(p -> p.getName().toUpperCase().equals(normalizedName))
                 .findFirst();
 
             if (existingProc.isPresent()) {
                 TALStructuralProcedure existing = existingProc.get();
                 existing.setStatements(extractedProc.getStatements());
                 existing.setContextScore(Math.max(existing.getContextScore(), extractedProc.getContextScore()));
             } else {
                 procedures.add(extractedProc);
             }
         }
 
         procedures.sort(Comparator.comparingInt(TALStructuralProcedure::getLineNumber));
     }
 
     // ANTLR listener methods (kept for fallback compatibility)
     @Override
     public void enterNamePart(TALParser.NamePartContext ctx) {
         if (ctx.IDENTIFIER() != null) {
             String extractedName = ctx.IDENTIFIER().getText();
             if (extractedName != null && !extractedName.trim().isEmpty()) {
                 programName = extractedName;
                 if (config.isVerboseLogging()) {
                     System.out.println("📖 Found program name: " + programName);
                 }
             }
         }
     }

 
     @Override
     public void enterProgram(TALParser.ProgramContext ctx) {
         procedures.clear();
         extractedDataItems.clear();
         fileDescriptors.clear();
         sqlStatements.clear();
         copyStatements.clear();
         callStatements.clear();
         systemStatements.clear();
         callReferences.clear();
         statementCounts.clear();
         parseWarnings.clear();
         currentProcedure = null;
         
         if (config.isVerboseLogging()) {
             System.out.println("🌟 Entering program parsing");
         }
     }
 
     @Override
     public void exitProgram(TALParser.ProgramContext ctx) {
         if (config.isVerboseLogging()) {
             System.out.println("🏁 Exiting program parsing with " + procedures.size() + " procedures");
         }
     }
 
     @Override
     public void enterPragmaDirective(TALParser.PragmaDirectiveContext ctx) {
         TALStructuralStatement stmt = new TALStructuralStatement();
         stmt.setType("PRAGMA");
         stmt.setContent(getCleanStatementContent(ctx));
         stmt.setLineNumber(getLineNumberFromContext(ctx));
         
         if (currentProcedure != null) {
             currentProcedure.getStatements().add(stmt);
         }
         incrementStatementCount("PRAGMA");
     }
 
     @Override
     public void enterConstSection(TALParser.ConstSectionContext ctx) {
         extractVariableDeclaration(ctx, "CONST");
     }
     
     @Override
     public void enterTypeSection(TALParser.TypeSectionContext ctx) {
         extractVariableDeclaration(ctx, "TYPE");
     }
     
     @Override
     public void enterVarSection(TALParser.VarSectionContext ctx) {
         extractVariableDeclaration(ctx, "VAR");
     }
 
     @Override
     public void enterBlockDeclaration(TALParser.BlockDeclarationContext ctx) {
         TALStructuralProcedure block = new TALStructuralProcedure();
         
         String blockName = "BLOCK_PRIVATE";
         if (ctx.blockName() != null) {
             blockName = ctx.blockName().getText();
         }
         
         block.setName(blockName);
         block.setLineNumber(getLineNumberFromContext(ctx));
         block.setStatements(new ArrayList<>());
         currentProcedure = block;
         procedures.add(block);
         
         if (config.isVerboseLogging()) {
             System.out.println("➕ Block: " + block.getName() + " at line " + block.getLineNumber());
         }
     }
 
     @Override
     public void exitBlockDeclaration(TALParser.BlockDeclarationContext ctx) {
         if (currentProcedure != null) {
             currentProcedure.setEndLineNumber(getLineNumberFromContext(ctx));
             currentProcedure.setContextScore(scoringMechanism.calculateScore(currentProcedure));
             currentProcedure.setReasoningInfo("Found via TAL grammar block parsing");
             currentProcedure = null;
         }
     }
 
     @Override
     public void enterSimpleVariableDeclaration(TALParser.SimpleVariableDeclarationContext ctx) {
         extractVariableDeclaration(ctx, "VAR");
     }
 
     @Override
     public void enterArrayDeclaration(TALParser.ArrayDeclarationContext ctx) {
         extractVariableDeclaration(ctx, "ARRAY");
     }

     @Override
     public void enterStructPointerFieldDeclaration(TALParser.StructPointerFieldDeclarationContext ctx) {
         if (dataItemsExtracted) {
             return; // Skip if preprocessing already handled data items
         }
         
         String type = ctx.typeSpecification().getText();
         String name = ctx.IDENTIFIER().getText();
         String definition = ctx.getText();
         int lineNumber = ctx.start.getLine();
         
         TALStructuralDataItem item = new TALStructuralDataItem();
         item.setName("." + name); // Prefix with '.' to indicate pointer
         item.setDataType(type);
         item.setSection("STRUCT_MEMBER");
         item.setLineNumber(lineNumber);
         item.setDefinition(definition);
         
         extractedDataItems.add(item);
         dataItemsBySection.computeIfAbsent("STRUCT_MEMBER", k -> new ArrayList<>()).add(item);
         
         if (config.isVerboseLogging()) {
             System.out.println("📖 Added struct pointer field: " + name + " (type: " + type + ", line: " + lineNumber + ")");
         }
     }

    //@Override
     public void enterStatement(TALParser.StatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             // Get tokens in the statement's range
             List<Token> tokens = tokenStream.getTokens().subList(ctx.start.getTokenIndex(), ctx.stop.getTokenIndex() + 1);
             
             // Detect statement type
             boolean isStringMove = tokens.stream().anyMatch(t -> t.getType() == TALParser.STRINGMOVE);
             boolean isFunctionCall = false;
             String calledProc = null;
             
             // Detect function call (IDENTIFIER followed by LPAREN)
             for (int i = 0; i < tokens.size() - 1; i++) {
                 if (tokens.get(i).getType() == TALParser.IDENTIFIER && tokens.get(i + 1).getType() == TALParser.LPAREN) {
                     isFunctionCall = true;
                     calledProc = tokens.get(i).getText().toUpperCase();
                     break;
                 }
             }
             
             // Assign statement type
             if (isStringMove) {
                 stmt.setType("STRING_MOVE_ASSIGNMENT");
             } else if (tokens.stream().anyMatch(t -> t.getType() == TALParser.ASSIGN)) {
                 stmt.setType("ASSIGNMENT");
                 if (isFunctionCall) {
                     // Handle function call in assignment (e.g., extract_packet_type)
                     callReferences.merge(calledProc, 1, Integer::sum);
                     if (config.isVerboseLogging()) {
                         System.out.println("📞 Found call in assignment to: " + calledProc + " (line: " + stmt.getLineNumber() + ")");
                     }
                 }
             } else if (tokens.stream().anyMatch(t -> t.getType() == TALParser.CALL)) {
                 stmt.setType("CALL");
                 for (int i = 0; i < tokens.size() - 1; i++) {
                     if (tokens.get(i).getType() == TALParser.CALL && i + 1 < tokens.size()) {
                         if (tokens.get(i + 1).getType() == TALParser.IDENTIFIER) {
                             calledProc = tokens.get(i + 1).getText().toUpperCase();
                             callReferences.merge(calledProc, 1, Integer::sum);
                             if (config.isVerboseLogging()) {
                                 System.out.println("📞 Found call to: " + calledProc + " (line: " + stmt.getLineNumber() + ")");
                             }
                         }
                         break;
                     }
                 }
             } else if (tokens.stream().anyMatch(t -> t.getType() == TALParser.SCAN)) {
                 stmt.setType("SCAN");
             } else if (tokens.stream().anyMatch(t -> t.getType() == TALParser.IF)) {
                 stmt.setType("IF");
             } else if (tokens.stream().anyMatch(t -> t.getType() == TALParser.ENDIF)) {
                 stmt.setType("ENDIF");
             } else if (tokens.stream().anyMatch(t -> t.getType() == TALParser.RETURN)) {
                 stmt.setType("RETURN");
             } else if (tokens.stream().anyMatch(t -> t.getType() == TALParser.END)) {
                 stmt.setType("END");
             } else if (content.contains(".<")) {
                 stmt.setType("BIT_FIELD_ASSIGNMENT");
             } else if (content.contains("@")) {
                 stmt.setType("POINTER_ASSIGNMENT");
             } else if (content.contains(".")) {
                 stmt.setType("POINTER_DEREFERENCE");
             } else {
                 return; // Skip unrecognized statements
             }
             
             List<String> accessedVars = extractVariableNames(content);
             if (!accessedVars.isEmpty()) {
                 stmt.setAccessedVariables(accessedVars);
             }
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount(stmt.getType());
             
             if (config.isVerboseLogging()) {
                 System.out.println("📖 Added statement: " + stmt.getType() + " - " + content + " (line: " + stmt.getLineNumber() + ")");
             }
         }
     }
    
     @Override
     public void enterStructureDeclaration(TALParser.StructureDeclarationContext ctx) {
         if (ctx.IDENTIFIER() != null) {
             String structName = ctx.IDENTIFIER().getText();
             
             TALStructuralDataItem item = new TALStructuralDataItem();
             item.setName(structName);
             item.setSection("STRUCT");
             item.setLineNumber(getLineNumberFromContext(ctx));
             item.setDataType("STRUCT");
             item.setDefinition(getCleanStatementContent(ctx));
             
             extractedDataItems.add(item);
             
             if (config.isVerboseLogging()) {
                 System.out.println("📊 Found struct: " + structName);
             }
         }
     }
 
     @Override
     public void enterStructVariableDeclaration(TALParser.StructVariableDeclarationContext ctx) {
         extractVariableDeclaration(ctx, "STRUCT_VAR");
     }
 
     @Override
     public void enterTalPointerDeclaration(TALParser.TalPointerDeclarationContext ctx) {
         extractVariableDeclaration(ctx, "POINTER");
     }
 
     @Override
     public void enterPointerDeclaration(TALParser.PointerDeclarationContext ctx) {
         extractVariableDeclaration(ctx, "POINTER");
     }
 
     @Override
     public void enterStructurePointerDeclaration(TALParser.StructurePointerDeclarationContext ctx) {
         extractVariableDeclaration(ctx, "STRUCT_POINTER");
     }
 
     @Override
     public void enterSystemGlobalPointerDeclaration(TALParser.SystemGlobalPointerDeclarationContext ctx) {
         extractVariableDeclaration(ctx, "SYSTEM_GLOBAL_POINTER");
     }
 
     @Override
     public void enterReadOnlyArrayDeclaration(TALParser.ReadOnlyArrayDeclarationContext ctx) {
         extractVariableDeclaration(ctx, "READONLY_ARRAY");
     }
 
     @Override
     public void enterEquivalencedVarDeclaration(TALParser.EquivalencedVarDeclarationContext ctx) {
         extractVariableDeclaration(ctx, "EQUIVALENCED_VAR");
     }
 
     @Override
     public void enterLiteralDeclaration(TALParser.LiteralDeclarationContext ctx) {
         extractVariableDeclaration(ctx, "LITERAL");
     }
 
     @Override
     public void enterDefineDeclaration(TALParser.DefineDeclarationContext ctx) {
         extractVariableDeclaration(ctx, "DEFINE");
     }
 
     @Override
     public void enterSubprocedureDeclaration(TALParser.SubprocedureDeclarationContext ctx) {
         if (ctx.procName() != null) {
             String procName = ctx.procName().getText();
             currentProcedure = new TALStructuralProcedure();
             currentProcedure.setName(procName);
             currentProcedure.setLineNumber(getLineNumberFromContext(ctx));
             currentProcedure.setStatements(new ArrayList<>());
             
             if (config.isVerboseLogging()) {
                 System.out.println("➕ Subprocedure: " + procName + " at line " + getLineNumberFromContext(ctx));
             }
         }
     }
 
     @Override
     public void exitSubprocedureDeclaration(TALParser.SubprocedureDeclarationContext ctx) {
         if (currentProcedure != null) {
             currentProcedure.setEndLineNumber(getLineNumberFromContext(ctx));
             currentProcedure.setContextScore(scoringMechanism.calculateScore(currentProcedure));
             currentProcedure.setReasoningInfo("Found via TAL grammar subprocedure parsing");
             procedures.add(currentProcedure);
             currentProcedure = null;
         }
     }
 
     @Override
     public void enterForwardDeclaration(TALParser.ForwardDeclarationContext ctx) {
         String name = "UNKNOWN";
         if (ctx.procName() != null) {
             name = ctx.procName().getText();
         } else if (ctx.IDENTIFIER() != null) {
             name = ctx.IDENTIFIER().getText();
         }
         
         TALStructuralProcedure proc = new TALStructuralProcedure();
         proc.setName(name);
         proc.setLineNumber(getLineNumberFromContext(ctx));
         proc.setStatements(new ArrayList<>());
         proc.setReasoningInfo("Forward declaration");
         procedures.add(proc);
         
         if (config.isVerboseLogging()) {
             System.out.println("➕ Forward declaration: " + name);
         }
     }
 
     @Override
     public void enterExternalDeclaration(TALParser.ExternalDeclarationContext ctx) {
         extractVariableDeclaration(ctx, "EXTERNAL");
     }
 
     @Override
     public void enterModuleImport(TALParser.ModuleImportContext ctx) {
         TALStructuralStatement stmt = new TALStructuralStatement();
         stmt.setType("IMPORT");
         stmt.setContent(getCleanStatementContent(ctx));
         stmt.setLineNumber(getLineNumberFromContext(ctx));
         
         if (currentProcedure != null) {
             currentProcedure.getStatements().add(stmt);
         }
         incrementStatementCount("IMPORT");
     }
 

     @Override
     public void enterProcedureDeclaration(TALParser.ProcedureDeclarationContext ctx) {
         String procName = extractProcedureName(ctx);
         if (procName != null) {
             currentProcedure = new TALStructuralProcedure();
             currentProcedure.setName(procName);
             currentProcedure.setLineNumber(getLineNumberFromContext(ctx));
             currentProcedure.setStatements(new ArrayList<>());
             
             if (config.isVerboseLogging()) {
                 System.out.println("➕ Procedure: " + procName + " at line " + getLineNumberFromContext(ctx));
             }
         }
     }
 
     @Override
     public void exitProcedureDeclaration(TALParser.ProcedureDeclarationContext ctx) {
         if (currentProcedure != null) {
             currentProcedure.setEndLineNumber(getLineNumberFromContext(ctx));
             currentProcedure.setContextScore(scoringMechanism.calculateScore(currentProcedure));
             currentProcedure.setReasoningInfo("Found via TAL grammar parsing");
             procedures.add(currentProcedure);
             currentProcedure = null;
         }
     }
 

    
     @Override
     public void enterCallStatement(TALParser.CallStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("CALL");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             String callTarget = extractCallTarget(ctx);
             if (callTarget != null && isValidProcedureName(callTarget)) {
                 if (callTarget.startsWith("$")) {
                     stmt.setSystemFunction(callTarget);
                     systemStatements.add(stmt);
                     incrementStatementCount("SYSTEM");
                 } else {
                     stmt.setCallTarget(callTarget);
                     callStatements.add(stmt);
                 }
                 callReferences.merge(callTarget.toUpperCase(), 1, Integer::sum);
                 
                 if (config.isVerboseLogging()) {
                     System.out.println("📞 Found call to: " + callTarget);
                 }
             }
             
             if (!content.isEmpty()) {
                 currentProcedure.getStatements().add(stmt);
                 incrementStatementCount("CALL");
             }
         }
     }
 
     private boolean isValidProcedureName(String name) {
         if (name == null || name.isEmpty()) return false;
         return name.matches("[A-Za-z_$][A-Za-z0-9_]*") && !isKeyword(name);
     }
 
     @Override
     public void enterReturnStatement(TALParser.ReturnStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("RETURN");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             if (ctx.expression() != null) {
                 String returnValue = ctx.expression().getText();
                 if (returnValue != null && !returnValue.trim().isEmpty()) {
                     stmt.setReturnValue(returnValue);
                 }
             }
             
             if (!currentProcedure.getStatements().stream().anyMatch(s -> 
                 s.getType().equals("RETURN") && s.getLineNumber() == stmt.getLineNumber())) {
                 currentProcedure.getStatements().add(stmt);
                 incrementStatementCount("RETURN");
             }
         }
     }
 
    
 
     @Override
     public void enterIfStatement(TALParser.IfStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("IF");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             if (ctx.expression() != null) {
                 String condition = ctx.expression().getText();
                 if (condition != null && !condition.trim().isEmpty()) {
                     stmt.setCondition(condition);
                 }
             }
             
             if (!content.isEmpty()) {
                 currentProcedure.getStatements().add(stmt);
                 incrementStatementCount("IF");
             }
         }
     }
 
     @Override
     public void enterWhileStatement(TALParser.WhileStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("WHILE");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             if (ctx.expression() != null) {
                 String condition = ctx.expression().getText();
                 if (condition != null && !condition.trim().isEmpty()) {
                     stmt.setCondition(condition);
                 }
             }
             
             if (!content.isEmpty()) {
                 currentProcedure.getStatements().add(stmt);
                 incrementStatementCount("WHILE");
             }
         }
     }
 
     @Override
     public void enterCaseStatement(TALParser.CaseStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("CASE");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             if (!content.isEmpty()) {
                 currentProcedure.getStatements().add(stmt);
                 incrementStatementCount("CASE");
             }
         }
     }
 
     // Additional ANTLR listener methods for TAL-specific constructs
     @Override
     public void enterDoUntilStatement(TALParser.DoUntilStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("DO_UNTIL");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             if (ctx.expression() != null) {
                 String condition = ctx.expression().getText();
                 if (condition != null && !condition.trim().isEmpty()) {
                     stmt.setCondition(condition);
                 }
             }
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("DO_UNTIL");
             
             if (config.isVerboseLogging()) {
                 System.out.println("🔁 Found DO_UNTIL statement: " + content);
             }
         }
     }
 
     @Override
     public void enterForStatement(TALParser.ForStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("FOR");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("FOR");
             
             if (config.isVerboseLogging()) {
                 System.out.println("🔄 Found FOR statement: " + content);
             }
         }
     }
 
     @Override
     public void enterGotoStatement(TALParser.GotoStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("GOTO");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             if (ctx.IDENTIFIER() != null) {
                 String target = ctx.IDENTIFIER().getText();
                 if (target != null && !target.trim().isEmpty()) {
                     stmt.setCallTarget(target);
                 }
             }
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("GOTO");
             
             if (config.isVerboseLogging()) {
                 System.out.println("➡️ Found GOTO statement: " + content);
             }
         }
     }
 
     @Override
     public void enterAssertStatement(TALParser.AssertStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("ASSERT");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             if (ctx.expression() != null) {
                 String condition = ctx.expression().getText();
                 if (condition != null && !condition.trim().isEmpty()) {
                     stmt.setCondition(condition);
                 }
             }
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("ASSERT");
             
             if (config.isVerboseLogging()) {
                 System.out.println("✅ Found ASSERT statement: " + content);
             }
         }
     }
 
     @Override
     public void enterUseStatement(TALParser.UseStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("USE");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("USE");
             
             if (config.isVerboseLogging()) {
                 System.out.println("📚 Found USE statement: " + content);
             }
         }
     }
 
     @Override
     public void enterDropStatement(TALParser.DropStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("DROP");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("DROP");
             
             if (config.isVerboseLogging()) {
                 System.out.println("🗑️ Found DROP statement: " + content);
             }
         }
     }
 
     @Override
     public void enterStackStatement(TALParser.StackStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("STACK");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("STACK");
             
             if (config.isVerboseLogging()) {
                 System.out.println("📚 Found STACK statement: " + content);
             }
         }
     }
 
     @Override
     public void enterStoreStatement(TALParser.StoreStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("STORE");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("STORE");
             
             if (config.isVerboseLogging()) {
                 System.out.println("💾 Found STORE statement: " + content);
             }
         }
     }
 
     @Override
     public void enterCodeStatement(TALParser.CodeStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("CODE");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("CODE");
             
             if (config.isVerboseLogging()) {
                 System.out.println("💻 Found CODE statement: " + content);
             }
         }
     }
 
     @Override
     public void enterBitDepositStatement(TALParser.BitDepositStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("BIT_DEPOSIT");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("BIT_DEPOSIT");
             
             if (config.isVerboseLogging()) {
                 System.out.println("🔧 Found BIT_DEPOSIT statement: " + content);
             }
         }
     }
 
     @Override
     public void enterBitFieldAssignmentStatement(TALParser.BitFieldAssignmentStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("BIT_FIELD_ASSIGNMENT");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             try {
                 if (ctx.variableExpr() != null) {
                     String variable = ctx.variableExpr().getText();
                     String startBit = "0";
                     String endBit = null;
                     String value = "";
                     
                     if (ctx.bitPosition() != null && ctx.bitPosition().size() > 0) {
                         startBit = ctx.bitPosition(0).getText();
                         if (ctx.bitPosition().size() > 1) {
                             endBit = ctx.bitPosition(1).getText();
                         }
                     }
                     
                     if (ctx.expression() != null) {
                         value = ctx.expression().getText();
                     }
                     
                     stmt.setBitFieldInfo(variable, startBit, endBit, value);
                     stmt.setAccessedVariables(Arrays.asList(variable));
                 }
             } catch (Exception e) {
                 if (config.isVerboseLogging()) {
                     System.err.println("⚠️ Error processing bit field assignment: " + e.getMessage());
                 }
             }
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("BIT_FIELD_ASSIGNMENT");
             
             if (config.isVerboseLogging()) {
                 System.out.println("🔧 Found bit field assignment: " + content);
             }
         }
     }
 
     @Override
     public void enterPointerAssignmentStatement(TALParser.PointerAssignmentStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("POINTER_ASSIGNMENT");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             try {
                 List<String> accessedVars = new ArrayList<>();
                 if (ctx.variableExpr() != null && ctx.variableExpr().size() >= 1) {
                     String target = ctx.variableExpr(0).getText();
                     stmt.setPointerTarget(target);
                     accessedVars.add(target.replace("@", ""));
                     
                     if (ctx.variableExpr().size() >= 2) {
                         String source = ctx.variableExpr(1).getText();
                         accessedVars.add(source.replace("@", ""));
                     }
                 }
                 stmt.setAccessedVariables(accessedVars);
             } catch (Exception e) {
                 if (config.isVerboseLogging()) {
                     System.err.println("⚠️ Error processing pointer assignment: " + e.getMessage());
                 }
             }
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("POINTER_ASSIGNMENT");
             
             if (config.isVerboseLogging()) {
                 System.out.println("👉 Found pointer assignment: " + content);
             }
         }
     }
 
     @Override
     public void enterPointerDereferenceStatement(TALParser.PointerDereferenceStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("POINTER_DEREFERENCE");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             try {
                 if (ctx.variableExpr() != null) {
                     String pointer = ctx.variableExpr().getText();
                     stmt.setPointerTarget(pointer);
                     stmt.setAccessedVariables(Arrays.asList(pointer.replace(".", "")));
                 }
             } catch (Exception e) {
                 if (config.isVerboseLogging()) {
                     System.err.println("⚠️ Error processing pointer dereference: " + e.getMessage());
                 }
             }
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("POINTER_DEREFERENCE");
             
             if (config.isVerboseLogging()) {
                 System.out.println("👉 Found pointer dereference: " + content);
             }
         }
     }
 
     @Override
     public void enterStringMoveStatement(TALParser.StringMoveStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("STRING_MOVE");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             try {
                 if (ctx.variableExpr() != null && ctx.expression() != null) {
                     String target = ctx.variableExpr().getText();
                     String source = ctx.expression().getText();
                     stmt.setStringMoveInfo(target, source);
                     stmt.setAccessedVariables(Arrays.asList(target));
                 }
             } catch (Exception e) {
                 if (config.isVerboseLogging()) {
                     System.err.println("⚠️ Error processing string move: " + e.getMessage());
                 }
             }
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("STRING_MOVE");
             
             if (config.isVerboseLogging()) {
                 System.out.println("📝 Found string move: " + content);
             }
         }
     }
 
     @Override
     public void enterMoveStatement(TALParser.MoveStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("MOVE");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             try {
                 List<String> accessedVars = new ArrayList<>();
                 if (ctx.variableExpr() != null && ctx.variableExpr().size() >= 2) {
                     String source = ctx.variableExpr(0).getText();
                     String target = ctx.variableExpr(1).getText();
                     accessedVars.add(source);
                     accessedVars.add(target);
                 }
                 stmt.setAccessedVariables(accessedVars);
             } catch (Exception e) {
                 if (config.isVerboseLogging()) {
                     System.err.println("⚠️ Error processing move statement: " + e.getMessage());
                 }
             }
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("MOVE");
             
             if (config.isVerboseLogging()) {
                 System.out.println("📦 Found MOVE statement: " + content);
             }
         }
     }
 
     @Override
     public void enterScanStatement(TALParser.ScanStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("SCAN");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             List<String> accessedVars = extractVariableNames(content);
             if (!accessedVars.isEmpty()) {
                 stmt.setAccessedVariables(accessedVars);
             }
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("SCAN");
             
             if (config.isVerboseLogging()) {
                 System.out.println("🔍 Found SCAN statement: " + content + " (line: " + stmt.getLineNumber() + ")");
             }
         }
     }

     @Override
     public void enterRscanStatement(TALParser.RscanStatementContext ctx) {
         if (currentProcedure != null) {
             TALStructuralStatement stmt = new TALStructuralStatement();
             stmt.setType("RSCAN");
             String content = getCleanStatementContent(ctx);
             stmt.setContent(content);
             stmt.setLineNumber(getLineNumberFromContext(ctx));
             
             try {
                 String source = ctx.scanObject() != null ? ctx.scanObject().getText() : "";
                 String condition = ctx.scanTerminator() != null ? ctx.scanTerminator().getText() : "";
                 String target = ctx.nextAddr() != null ? ctx.nextAddr().getText() : "";
                 
                 List<String> accessedVars = new ArrayList<>();
                 if (!source.isEmpty()) {
                     accessedVars.add(source.replace(".", ""));
                 }
                 if (!target.isEmpty()) {
                     accessedVars.add(target.replace("@", "").replace(".", ""));
                 }
                 
                 stmt.setScanInfo(source, condition, target);
                 stmt.setAccessedVariables(accessedVars);
             } catch (Exception e) {
                 if (config.isVerboseLogging()) {
                     System.err.println("⚠️ Error processing RSCAN statement: " + e.getMessage());
                 }
             }
             
             currentProcedure.getStatements().add(stmt);
             incrementStatementCount("RSCAN");
             
             if (config.isVerboseLogging()) {
                 System.out.println("🔍 Found RSCAN statement: " + content);
             }
         }
     }
 
     // ============================================================================
     // Additional utility methods for enhanced statement processing
     // ============================================================================
 
     /**
      * Enhanced method to get line number from any ParserRuleContext
      */
     private int getLineNumberFromContext(ParserRuleContext ctx) {
         try {
             if (ctx != null && ctx.getStart() != null) {
                 return ctx.getStart().getLine();
             }
         } catch (Exception e) {
             if (config.isVerboseLogging()) {
                 System.err.println("⚠️ Error getting line number from context: " + e.getMessage());
             }
         }
         return 1; // Default line number if context is null or error occurs
     }
 
     /**
      * Safely extract text content from parser context
      */
     private String getCleanStatementContent(ParserRuleContext ctx) {
         if (ctx == null) return "";
         
         try {
             String content = ctx.getText();
             if (content == null) return "";
             
             // Clean up whitespace and limit length
             content = content.replaceAll("\\s+", " ").trim();
             if (content.length() > 200) {
                 content = content.substring(0, 197) + "...";
             }
             
             return content;
         } catch (Exception e) {
             if (config.isVerboseLogging()) {
                 System.err.println("⚠️ Error getting statement content: " + e.getMessage());
             }
             return "";
         }
     }
     
     /**
      * Extract variable names from declaration text
      */
     private void extractVariableDeclaration(ParserRuleContext ctx, String section) {
         try {
             String content = getCleanStatementContent(ctx);
             List<String> varNames = extractVariableNames(content);
             
             for (String varName : varNames) {
                 TALStructuralDataItem dataItem = new TALStructuralDataItem();
                 dataItem.setName(varName);
                 dataItem.setLineNumber(getLineNumberFromContext(ctx));
                 dataItem.setSection(section);
                 dataItem.setDefinition(content);
                 
                 String dataType = extractDataType(content);
                 if (dataType != null) {
                     dataItem.setDataType(dataType);
                 }
                 
                 extractedDataItems.add(dataItem);
                 
                 if (config.isVerboseLogging()) {
                     System.out.println("📊 Found variable: " + varName + " (" + section + ")");
                 }
             }
         } catch (Exception e) {
             if (config.isVerboseLogging()) {
                 System.err.println("⚠️ Error extracting variable declaration: " + e.getMessage());
             }
         }
     }
     
     /**
      * Extract variable names from a declaration string
      */
     private List<String> extractVariableNames(String declaration) {
         List<String> names = new ArrayList<>();
         try {
             if (declaration == null || declaration.trim().isEmpty()) {
                 return names;
             }
             
             String[] parts = declaration.split("[\\s,;.:()\\[\\]]+");
             
             for (String part : parts) {
                 if (isValidIdentifier(part) && !isKeyword(part)) {
                     names.add(part);
                 }
             }
         } catch (Exception e) {
             if (config.isVerboseLogging()) {
                 System.err.println("⚠️ Error extracting variable names: " + e.getMessage());
             }
         }
         
         return names;
     }
     
     /**
      * Extract data type from declaration content
      */
     private String extractDataType(String declaration) {
         if (declaration == null) return null;
         
         try {
             String upper = declaration.toUpperCase();
             if (upper.contains("DATA_PACKET_DEF")) return "data_packet_def";
             if (upper.contains("INT(32)")) return "INT(32)";
             if (upper.contains("INT(64)")) return "INT(64)";
             if (upper.contains("INT")) return "INT";
             if (upper.contains("STRING")) return "STRING";
             if (upper.contains("STRUCT")) return "STRUCT";
             if (upper.contains("CHAR")) return "CHAR";
             if (upper.contains("BYTE")) return "BYTE";
             if (upper.contains("BOOL")) return "BOOL";
             if (upper.contains("REAL(64)")) return "REAL(64)";
             if (upper.contains("REAL")) return "REAL";
             if (upper.contains("FIXED")) return "FIXED";
             if (upper.contains("UNSIGNED")) return "UNSIGNED";
             if (upper.contains("TIMESTAMP")) return "TIMESTAMP";
             if (upper.contains("EXTADDR")) return "EXTADDR";
             if (upper.contains("SGADDR")) return "SGADDR";
         } catch (Exception e) {
             if (config.isVerboseLogging()) {
                 System.err.println("⚠️ Error extracting data type: " + e.getMessage());
             }
         }
         
         return null;
     }
 
     /**
      * Extract procedure name from procedure declaration context
      */
     private String extractProcedureName(TALParser.ProcedureDeclarationContext ctx) {
         try {
             if (ctx == null) return null;
             
             if (ctx.procHeader() != null) {
                 // Try typed procedure header first
                 if (ctx.procHeader().typedProcHeader() != null && 
                     ctx.procHeader().typedProcHeader().procName() != null) {
                     return ctx.procHeader().typedProcHeader().procName().getText();
                 }
                 
                 // Try untyped procedure header
                 if (ctx.procHeader().untypedProcHeader() != null && 
                     ctx.procHeader().untypedProcHeader().procName() != null) {
                     return ctx.procHeader().untypedProcHeader().procName().getText();
                 }
                 
                 // Fallback: parse header text manually
                 String headerText = ctx.procHeader().getText();
                 if (headerText != null) {
                     String[] parts = headerText.split("\\s+");
                     for (int i = 0; i < parts.length - 1; i++) {
                         if ("PROC".equalsIgnoreCase(parts[i]) || 
                             "SUBPROC".equalsIgnoreCase(parts[i]) ||
                             parts[i].toUpperCase().endsWith("PROC")) {
                             String candidate = parts[i + 1];
                             candidate = candidate.replaceAll("[^A-Za-z0-9_]", "");
                             if (isValidIdentifier(candidate)) {
                                 return candidate;
                             }
                         }
                     }
                 }
             }
         } catch (Exception e) {
             if (config.isVerboseLogging()) {
                 System.err.println("⚠️ Error extracting procedure name: " + e.getMessage());
             }
         }
         return null;
     }
 
     /**
      * Extract call target from call statement
      */
     private String extractCallTarget(TALParser.CallStatementContext ctx) {
         try {
             if (ctx == null) return null;
             
             String callText = getCleanStatementContent(ctx);
             if (callText.isEmpty()) return null;
             
             // Remove CALL keyword and clean up
             String cleaned = callText.replaceAll("(?i)\\s*call\\s*", "").trim();
             
             // Handle system calls like $DISPLAY
             if (cleaned.startsWith("$")) {
                 int parenIndex = cleaned.indexOf('(');
                 if (parenIndex > 0) {
                     String target = cleaned.substring(0, parenIndex).trim();
                     if (isValidIdentifier(target)) {
                         return target;
                     }
                 } else {
                     String target = cleaned.split("\\s+")[0];
                     if (isValidIdentifier(target)) {
                         return target;
                     }
                 }
             }
             
             // Handle regular procedure calls
             int parenIndex = cleaned.indexOf('(');
             int semiIndex = cleaned.indexOf(';');
             int endIndex = -1;
             
             if (parenIndex > 0 && semiIndex > 0) {
                 endIndex = Math.min(parenIndex, semiIndex);
             } else if (parenIndex > 0) {
                 endIndex = parenIndex;
             } else if (semiIndex > 0) {
                 endIndex = semiIndex;
             }
             
             if (endIndex > 0) {
                 String target = cleaned.substring(0, endIndex).trim();
                 target = target.replaceAll("[^A-Za-z0-9_.$]", "");
                 if (isValidIdentifier(target)) {
                     return target;
                 }
             }
             
             // If no parentheses or semicolon, take the first word
             String[] words = cleaned.split("\\s+");
             if (words.length > 0) {
                 String target = words[0].replaceAll("[^A-Za-z0-9_.$]", "");
                 if (isValidIdentifier(target)) {
                     return target;
                 }
             }
             
         } catch (Exception e) {
             if (config.isVerboseLogging()) {
                 System.err.println("⚠️ Error extracting call target: " + e.getMessage());
             }
         }
         return null;
     }
 
     /**
      * Check if a string is a TAL keyword
      */
     private boolean isKeyword(String text) {
         if (text == null) return false;
         String upper = text.toUpperCase();
         
         // Core TAL keywords
         return upper.equals("VAR") || upper.equals("TYPE") || upper.equals("CONST") || 
                upper.equals("INT") || upper.equals("STRING") || upper.equals("STRUCT") ||
                upper.equals("RECORD") || upper.equals("BEGIN") || upper.equals("END") ||
                upper.equals("PROC") || upper.equals("SUBPROC") || upper.equals("CALL") ||
                upper.equals("IF") || upper.equals("THEN") || upper.equals("ELSE") ||
                upper.equals("WHILE") || upper.equals("DO") || upper.equals("FOR") ||
                upper.equals("RETURN") || upper.equals("CASE") || upper.equals("OF") ||
                upper.equals("MAIN") || upper.equals("CHAR") || upper.equals("BYTE") ||
                upper.equals("BOOL") || upper.equals("REAL") || upper.equals("FIXED") ||
                upper.equals("SCAN") || upper.equals("RSCAN") || upper.equals("MOVE") ||
                upper.equals("ASSERT") || upper.equals("USE") || upper.equals("DROP") ||
                upper.equals("STACK") || upper.equals("STORE") || upper.equals("CODE") ||
                upper.equals("GOTO") || upper.equals("UNTIL") || upper.equals("BITDEPOSIT") ||
                upper.equals("FORWARD") || upper.equals("EXTERNAL") || upper.equals("IMPORT") ||
                upper.equals("BLOCK") || upper.equals("PRIVATE") || upper.equals("ENTRY") ||
                upper.equals("LABEL") || upper.equals("LITERAL") || upper.equals("DEFINE") ||
                upper.equals("PRAGMA") || upper.equals("NAME") || upper.equals("DOWNTO") ||
                upper.equals("BY") || upper.equals("TO") || upper.equals("ENDFOR") ||
                upper.equals("ENDIF") || upper.equals("OTHERWISE") || upper.equals("NIL") ||
                upper.equals("TRUE") || upper.equals("FALSE") || upper.equals("UNSIGNED") ||
                upper.equals("TIMESTAMP") || upper.equals("EXTADDR") || upper.equals("SGADDR");
     }
     
     /**
      * Check if a string is a valid TAL identifier
      */
     private boolean isValidIdentifier(String text) {
         if (text == null || text.isEmpty()) return false;
         
         try {
             // TAL identifiers can start with letter, underscore, or dollar sign
             // and contain letters, digits, underscores, and sometimes periods for qualified names
             return text.matches("[$A-Za-z_][A-Za-z0-9_$.]*");
         } catch (Exception e) {
             return false;
         }
     }
 
     /**
      * Safely read source lines from file
      */
     private String[] readSourceLines(String filename) throws IOException {
         return TALParserUtilities.readSourceLines(filename);
     }
 
     /**
      * Preprocess source with configurable regex patterns
      */
     private List<TALProcedureBoundary> preprocessWithConfigurableRegex(String[] sourceToProcess) {
         TALParserUtilities utilities = new TALParserUtilities(config, sourceToProcess, callReferences, statementCounts);
         return utilities.preprocessWithRegex(sourceToProcess);
     }
 
     /**
      * Create procedure from regex boundary information
      */
     private TALStructuralProcedure createProcedureFromRegex(TALProcedureBoundary boundary) {
         TALParserUtilities utilities = new TALParserUtilities(config, sourceLines, callReferences, statementCounts);
         return utilities.createProcedureFromRegex(boundary);
     }
 
     /**
      * Determine if hybrid mode should be used
      */
     private boolean shouldUseHybridMode(List<TALProcedureBoundary> regexProcedures) {
         TALParserUtilities utilities = new TALParserUtilities(config, sourceLines, callReferences, statementCounts);
         return utilities.shouldUseHybridMode(regexProcedures, procedures.size());
     }
 
     /**
      * Enhance parsing results with regex-found procedures
      */
     private void enhanceWithRegexResults(List<TALProcedureBoundary> regexProcedures) {
         Set<String> grammarProcNames = procedures.stream()
             .map(TALStructuralProcedure::getName)
             .map(String::toUpperCase)
             .collect(Collectors.toSet());
         
         for (TALProcedureBoundary boundary : regexProcedures) {
             if (!grammarProcNames.contains(boundary.getName().toUpperCase())) {
                 TALStructuralProcedure proc = createProcedureFromRegex(boundary);
                 if (proc != null) {
                     procedures.add(proc);
                     if (config.isVerboseLogging()) {
                         System.out.println("🔍 Enhanced with regex procedure: " + proc.getName());
                     }
                 }
             }
         }
         
         procedures.sort(Comparator.comparingInt(TALStructuralProcedure::getLineNumber));
     }
 
     /**
      * Calculate end line for a procedure starting at given line
      */
     private int calculateEndLine(int startLine) {
         TALParserUtilities utilities = new TALParserUtilities(config, sourceLines, callReferences, statementCounts);
         return utilities.calculateEndLine(startLine);
     }
 

    /**
     * Determine program name from source
     */
    private String determineProgramName(String filename) {
        if (programName != null && !programName.equals("UNKNOWN")) {
            return programName;
        }
        
        try {
            for (String line : sourceLines) {
                String trimmed = line.trim();
                if (trimmed.toUpperCase().startsWith("NAME ")) {
                    String[] parts = trimmed.split("\\s+");
                    if (parts.length >= 2 && isValidIdentifier(parts[1])) {
                        programName = parts[1];
                        if (config.isVerboseLogging()) {
                            System.out.println("📖 Determined program name from NAME directive: " + programName);
                        }
                        return programName;
                    }
                }
            }
        } catch (Exception e) {
            if (config.isVerboseLogging()) {
                System.err.println("⚠️ Error determining program name: " + e.getMessage());
            }
        }
        
        // Fallback to using the filename or default if no NAME directive found
        if (programName == null || programName.equals("UNKNOWN")) {
            String fallbackName = extractProgramNameFromFilename(filename); // Pass filename here
            programName = fallbackName != null ? fallbackName : "UNKNOWN";
            if (config.isVerboseLogging()) {
                System.out.println("📖 Using fallback program name: " + programName);
            }
        }
        
        return programName;
    }

    /**
     * Extract program name from filename
     */

        private String extractProgramNameFromFilename(String filename) {
            try {
                if (filename != null && !filename.isEmpty()) {
                    String name = Paths.get(filename).getFileName().toString();
                    name = name.replaceFirst("[.][^.]+$", ""); // Remove file extension
                    if (isValidIdentifier(name)) {
                        return name;
                    }
                }
            } catch (Exception e) {
                if (config.isVerboseLogging()) {
                    System.err.println("⚠️ Error extracting program name from filename: " + e.getMessage());
                }
            }
            return null;
        }

    /**
     * Print enhanced analysis results
     */
    private void printEnhancedResults(TALStructuralAnalysisResult result) {
        System.out.println("=== TAL Analysis Results ===");
        System.out.println("Program Name: " + result.getProgramName());
        System.out.println("Procedures Found: " + result.getProcedures().size());
        System.out.println("Data Items: " + result.getDataItems().size());
        System.out.println("File Descriptors: " + result.getFileDescriptors().size());
        System.out.println("SQL Statements: " + result.getSqlStatements().size());
        System.out.println("Copy Statements: " + result.getCopyStatements().size());
        System.out.println("Call Statements: " + result.getCallStatements().size());
        System.out.println("System Statements: " + result.getSystemStatements().size());
        System.out.println("Statement Counts:");
        result.getStatementCounts().forEach((type, count) ->
            System.out.println("  - " + type + ": " + count));
        System.out.println("Call References:");
        result.getCallReferences().forEach((target, count) ->
            System.out.println("  - " + target + ": " + count));
        if (!result.getParseWarnings().isEmpty()) {
            System.out.println("Parse Warnings:");
            result.getParseWarnings().forEach(warning ->
                System.out.println("  - " + warning));
        }
        System.out.println("===========================");
    }

    /**
     * Save enhanced AST to file in S-Expression format matching COBOL ASTParser
     */
    private static void saveEnhancedAST(TALStructuralAnalysisResult result, String filename) {
        try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
            writer.println("(ENHANCED-TAL-ANALYSIS \"" + (result.getProgramName() != null ? result.getProgramName() : "UNKNOWN") + "\"");
            writer.println("  (METADATA");
            writer.println("    (ANALYSIS-TYPE \"ENHANCED-HYBRID-GRAMMAR\")");
            writer.println("    (TIMESTAMP \"" + new java.util.Date() + "\")");
            writer.println("    (PROCEDURES-COUNT " + (result.getProcedures() != null ? result.getProcedures().size() : 0) + ")");
            writer.println("    (DATA-ITEMS-COUNT " + (result.getDataItems() != null ? result.getDataItems().size() : 0) + ")");
            writer.println("    (FILE-DESCRIPTORS-COUNT " + (result.getFileDescriptors() != null ? result.getFileDescriptors().size() : 0) + ")");
            writer.println("    (CALL-STATEMENTS-COUNT " + (result.getCallStatements() != null ? result.getCallStatements().size() : 0) + ")");
            writer.println("    (SYSTEM-STATEMENTS-COUNT " + (result.getSystemStatements() != null ? result.getSystemStatements().size() : 0) + ")");
            writer.println("    (SQL-STATEMENTS-COUNT " + (result.getSqlStatements() != null ? result.getSqlStatements().size() : 0) + ")");
            
            int totalStatements = 0;
            if (result.getStatementCounts() != null) {
                totalStatements = result.getStatementCounts().values().stream().mapToInt(Integer::intValue).sum();
            }
            writer.println("    (TOTAL-STATEMENTS " + totalStatements + ")");
            writer.println("  )");
            
            if (result.getDataItems() != null && !result.getDataItems().isEmpty()) {
                writer.println("  (DATA-SECTION");
                Map<String, List<TALStructuralDataItem>> itemsBySection = result.getDataItems().stream()
                    .collect(Collectors.groupingBy(item -> item.getSection() != null ? item.getSection() : "UNKNOWN"));
                
                for (Map.Entry<String, List<TALStructuralDataItem>> entry : itemsBySection.entrySet()) {
                    String section = entry.getKey();
                    List<TALStructuralDataItem> items = entry.getValue();
                    writer.println("    (SECTION \"" + section + "\"");
                    for (TALStructuralDataItem item : items) {
                        writer.println("      (DATA-ITEM");
                        writer.println("        (NAME \"" + (item.getName() != null ? item.getName() : "UNKNOWN") + "\")");
                        writer.println("        (LINE " + item.getLineNumber() + ")");
                        if (item.getDataType() != null && !item.getDataType().trim().isEmpty()) {
                            writer.println("        (TYPE \"" + item.getDataType().replace("\"", "\\\"") + "\")");
                        }
                        if (item.getValue() != null && !item.getValue().trim().isEmpty()) {
                            writer.println("        (VALUE \"" + item.getValue().replace("\"", "\\\"") + "\")");
                        }
                        if (item.getDefinition() != null && !item.getDefinition().trim().isEmpty()) {
                            String definition = item.getDefinition().replace("\"", "\\\"").replace("\n", "\\n");
                            if (definition.length() > 200) {
                                definition = definition.substring(0, 197) + "...";
                            }
                            writer.println("        (DEFINITION \"" + definition + "\")");
                        }
                        writer.println("      )");
                    }
                    writer.println("    )");
                }
                writer.println("  )");
            }
            
            if (result.getFileDescriptors() != null && !result.getFileDescriptors().isEmpty()) {
                writer.println("  (FILE-DESCRIPTORS");
                for (TALFileDescriptor fd : result.getFileDescriptors()) {
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
            
            writer.println("  (PROCEDURES");
            if (result.getProcedures() != null) {
                for (TALStructuralProcedure proc : result.getProcedures()) {
                    writer.println("    (PROCEDURE \"" + (proc.getName() != null ? proc.getName() : "UNKNOWN") + "\"");
                    writer.println("      (SCORE " + proc.getContextScore() + ")");
                    writer.println("      (START-LINE " + proc.getLineNumber() + ")");
                    writer.println("      (END-LINE " + proc.getEndLineNumber() + ")");
                    writer.println("      (REASONING \"" + (proc.getReasoningInfo() != null ? proc.getReasoningInfo().replace("\"", "\\\"") : "") + "\")");
                    
                    int actualRefCount = getActualCallReferenceCount(proc.getName(), result.getCallReferences());
                    writer.println("      (CALL-REFERENCES " + actualRefCount + ")");
                    
                    if (proc.getStatements() != null) {
                        Map<String, Long> procStmtTypes = proc.getStatements().stream()
                            .filter(stmt -> stmt != null && stmt.getType() != null)
                            .collect(Collectors.groupingBy(TALStructuralStatement::getType, Collectors.counting()));
                        writer.println("      (STATEMENT-DISTRIBUTION");
                        procStmtTypes.entrySet().stream()
                            .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                            .forEach(entry -> writer.println("        (" + entry.getKey() + " " + entry.getValue() + ")"));
                        writer.println("      )");
                        
                        writer.println("      (STATEMENTS");
                        for (TALStructuralStatement stmt : proc.getStatements()) {
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
            
            writer.println("  (STATEMENT-ANALYSIS");
            writer.println("    (STATEMENT-DISTRIBUTION");
            if (result.getStatementCounts() != null) {
                result.getStatementCounts().entrySet().stream()
                    .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
                    .forEach(entry -> writer.println("      (" + entry.getKey() + " " + entry.getValue() + ")"));
            }
            writer.println("    )");
            writer.println("  )");
            
            writer.println("  (CALL-GRAPH");
            if (result.getCallReferences() != null) {
                result.getCallReferences().entrySet().stream()
                    .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
                    .forEach(entry -> writer.println("    (\"" + (entry.getKey() != null ? entry.getKey().replace("\"", "\\\"") : "") + "\" " + entry.getValue() + ")"));
            }
            writer.println("  )");
            
            writer.println(")");
            
            System.out.println("💾 Enhanced TAL AST saved to: " + filename);
            
        } catch (IOException e) {
            System.err.println("❌ Error saving enhanced AST: " + e.getMessage());
            e.printStackTrace();
        }
    }

    private static int getActualCallReferenceCount(String procName, Map<String, Integer> callReferences) {
        if (procName == null || procName.trim().isEmpty()) {
            return 0;
        }
        
        String upperProc = procName.toUpperCase();
        int count = callReferences.getOrDefault(upperProc, 0);
        count = Math.max(count, callReferences.getOrDefault(upperProc.replace("-", ""), 0));
        count = Math.max(count, callReferences.getOrDefault(upperProc.replace("_", ""), 0));
        
        return count;
    }

    /**
     * Escape special characters for S-Expression string literals
     */
    private static String escapeString(String input) {
        if (input == null) return "";
        return input.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n");
    }
   
    /**
     * Increment statement count for a given type
     */
    private void incrementStatementCount(String type) {
        if (type != null && !type.isEmpty()) {
            statementCounts.merge(type, 1, Integer::sum);
            if (config.isVerboseLogging()) {
                System.out.println("📊 Incremented count for statement type: " + type);
            }
        }
    }

    /**
     * Normalize identifier for consistent comparison
     */
    private String normalizeIdentifier(String identifier) {
        if (identifier == null) return "";
        return identifier.replaceAll("[^A-Za-z0-9_$]", "").toUpperCase();
    }

    /**
     * Inner class to handle TAL-specific error listening
     */
    private static class TALErrorListener extends BaseErrorListener {
        private final String phase;
        private final List<String> parseWarnings;
        private final TALParserConfiguration config;

        public TALErrorListener(String phase, List<String> parseWarnings, TALParserConfiguration config) {
            this.phase = phase;
            this.parseWarnings = parseWarnings;
            this.config = config;
        }

        @Override
        public void syntaxError(Recognizer<?, ?> recognizer, Object offendingSymbol,
                               int line, int charPositionInLine,
                               String msg, RecognitionException e) {
            String warning = String.format("%s phase - Line %d:%d - %s",
                phase, line, charPositionInLine, msg);
            parseWarnings.add(warning);
            if (config.isVerboseLogging()) {
                System.err.println("⚠️ " + warning);
            }
        }
    }
}

class TALBusinessLogicResult {
    private List<TALProcedure> procedures = new ArrayList<>();

    public List<TALProcedure> getProcedures() { return procedures; }
    public void setProcedures(List<TALProcedure> procedures) { this.procedures = procedures; }
}

class TALProcedure {
    String name;
    int lineNumber;
    List<TALStatement> statements = new ArrayList<>();

    public String getName() { return name; }
    public int getLineNumber() { return lineNumber; }
    public List<TALStatement> getStatements() { return statements; }
}

class TALStatement {
    String type;
    String content;
    int lineNumber;
    List<String> accessedVariables;
    List<String> accessedFiles;
    String callTarget;
    String systemFunction;

    public String getType() { return type; }
    public String getContent() { return content; }
    public int getLineNumber() { return lineNumber; }
    public List<String> getAccessedVariables() { return accessedVariables; }
    public List<String> getAccessedFiles() { return accessedFiles; }
    public String getCallTarget() { return callTarget; }
    public String getSystemFunction() { return systemFunction; }
}
class TALProcedureBoundary {
    private String name;
    private int startLine;
    private int endLine;

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public int getStartLine() { return startLine; }
    public void setStartLine(int startLine) { this.startLine = startLine; }
    public int getEndLine() { return endLine; }
    public void setEndLine(int endLine) { this.endLine = endLine; }
}

class TALScoringMechanism {
    private TALParserConfiguration config;
    private String[] sourceLines;
    private Map<String, Integer> callReferences;

    public TALScoringMechanism(TALParserConfiguration config, String[] sourceLines, Map<String, Integer> callReferences) {
        this.config = config;
        this.sourceLines = sourceLines;
        this.callReferences = callReferences;
    }

    // ENHANCED: Better scoring based on TAL-specific constructs
    public double calculateScore(TALProcedure proc) {
        double score = 50.0; // Base score

        if (proc.getStatements() != null) {
            // Boost score for TAL-specific constructs
            for (TALStatement stmt : proc.getStatements()) {
                switch (stmt.getType()) {
                    case "BIT_FIELD_ASSIGNMENT":
                        score += 15.0;
                        break;
                    case "POINTER_DEREFERENCE":
                    case "POINTER_ASSIGNMENT":
                        score += 10.0;
                        break;
                    case "STRING_MOVE":
                        score += 8.0;
                        break;
                    case "SCAN":
                        score += 12.0;
                        break;
                    case "CALL":
                        score += 5.0;
                        break;
                    default:
                        score += 1.0;
                }
            }

            // Bonus for procedure complexity
            if (proc.getStatements().size() > 10) {
                score += 10.0;
            }
        }
        // Check call references
        if (callReferences.containsKey(proc.getName().toUpperCase())) {
            score += callReferences.get(proc.getName().toUpperCase()) * 5.0;
        }

        return Math.min(score, 100.0); // Cap at 100
    }

    public double calculateScore(TALStructuralProcedure proc) 
    {
        double score = 50.0; // Base score

        if (proc.getStatements() != null) {
            // Count TAL-specific constructs
            Map<String, Long> stmtTypes = proc.getStatements().stream()
                .collect(Collectors.groupingBy(TALStructuralStatement::getType, Collectors.counting()));

            score += stmtTypes.getOrDefault("BIT_FIELD_ASSIGNMENT", 0L) * 15.0;
            score += stmtTypes.getOrDefault("POINTER_DEREFERENCE", 0L) * 10.0;
            score += stmtTypes.getOrDefault("POINTER_ASSIGNMENT", 0L) * 10.0;
            score += stmtTypes.getOrDefault("STRING_MOVE", 0L) * 8.0;
            score += stmtTypes.getOrDefault("SCAN", 0L) * 12.0;
            score += stmtTypes.getOrDefault("CALL", 0L) * 5.0;

            // Bonus for complexity
            if (proc.getStatements().size() > 10) {
                score += 10.0;
            }
        }

        // Check call references
        if (callReferences.containsKey(proc.getName().toUpperCase())) {
            score += callReferences.get(proc.getName().toUpperCase()) * 5.0;
        }

        return Math.min(score, 100.0); // Cap at 100
    }

    public double calculateScore(TALBusinessLogicResult result) {
        double totalScore = 0.0;
        for (TALProcedure proc : result.getProcedures()) {
            totalScore += calculateScore(proc);
        }
        return totalScore / result.getProcedures().size();
    }

    public String buildReasoning(TALProcedure proc) {
        StringBuilder reasoning = new StringBuilder("Enhanced TAL analysis: ");

        if (proc.getStatements() != null) {
            Map<String, Long> stmtTypes = proc.getStatements().stream()
                .collect(Collectors.groupingBy(TALStatement::getType, Collectors.counting()));

            List<String> features = new ArrayList<>();
            if (stmtTypes.containsKey("BIT_FIELD_ASSIGNMENT")) {
                features.add("bit field operations");
            }
            if (stmtTypes.containsKey("POINTER_DEREFERENCE") || stmtTypes.containsKey("POINTER_ASSIGNMENT")) {
                features.add("pointer operations");
            }
            if (stmtTypes.containsKey("STRING_MOVE")) {
                features.add("string moves");
            }
            if (stmtTypes.containsKey("SCAN")) {
                features.add("scan operations");
            }
            if (stmtTypes.containsKey("CALL")) {
                features.add("procedure calls");
            }

            if (!features.isEmpty()) {
                reasoning.append("contains ").append(String.join(", ", features));
            } else {
                reasoning.append("basic TAL constructs");
            }
        }

        return reasoning.toString();
    }
}




class TALProcedureFilter {
    private TALParserConfiguration config;
    private TALScoringMechanism scoringMechanism;
    private Map<String, Integer> callReferences;

    public TALProcedureFilter(TALParserConfiguration config, TALScoringMechanism scoringMechanism, Map<String, Integer> callReferences) {
        this.config = config;
        this.scoringMechanism = scoringMechanism;
        this.callReferences = callReferences;
    }

    public List<TALStructuralProcedure> applyEnhancedFiltering(List<TALStructuralProcedure> procedures) {
        // For now, return all procedures but could add filtering logic here
        return procedures.stream()
            .filter(proc -> proc.getContextScore() >= 25.0) // Minimum score threshold
            .sorted(Comparator.comparingInt(TALStructuralProcedure::getLineNumber))
            .collect(Collectors.toList());
    }
}
class TALParserUtilities {
    private TALParserConfiguration config;
    private String[] sourceLines;
    private Map<String, Integer> callReferences;
    private Map<String, Integer> statementCounts;

    public TALParserUtilities(TALParserConfiguration config, String[] sourceToProcess,
                             Map<String, Integer> callReferences, Map<String, Integer> statementCounts) {
        this.config = config;
        this.sourceLines = sourceToProcess;
        this.callReferences = callReferences;
        this.statementCounts = statementCounts;
    }

    public static String[] readSourceLines(String filename) throws IOException {
        return Files.readAllLines(Paths.get(filename)).toArray(new String[0]);
    }

    public List<TALProcedureBoundary> preprocessWithRegex(String[] sourceToProcess) {
        List<TALProcedureBoundary> boundaries = new ArrayList<>();
        Pattern procPattern = Pattern.compile("^\\s*(INT\\s+PROC|PROC|SUBPROC)\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*(?:\\([^)]*\\))?\\s*(?:MAIN)?\\s*;?", Pattern.CASE_INSENSITIVE);

        for (int i = 0; i < sourceToProcess.length; i++) {
            String line = sourceToProcess[i];
            Matcher matcher = procPattern.matcher(line);

            if (matcher.find()) {
                String procName = matcher.group(2);
                int endLine = findProcedureEnd(sourceToProcess, i);

                TALProcedureBoundary boundary = new TALProcedureBoundary();
                boundary.setName(procName);
                boundary.setStartLine(i + 1);
                boundary.setEndLine(endLine);

                boundaries.add(boundary);

                System.out.println("📖 DEBUG: Found procedure via enhanced regex: " + procName + " (lines " + boundary.getStartLine() + "-" + boundary.getEndLine() + ")");
            }
        }

        return boundaries;
    }

    private int findProcedureEnd(String[] sourceLines, int startLine) {
        int depth = 0;
        for (int i = startLine + 1; i < sourceLines.length; i++) {
            String line = sourceLines[i].trim().toUpperCase();

            if (line.startsWith("PROC ") || line.startsWith("SUBPROC ") || line.contains("INT PROC ")) {
                if (depth == 0) {
                    return i;
                }
            }

            if (line.startsWith("IF ") || line.startsWith("WHILE ") || line.startsWith("CASE ")) {
                depth++;
            } else if (line.startsWith("ENDIF") || line.startsWith("END;")) {
                if (depth > 0) {
                    depth--;
                } else if (line.startsWith("END;")) {
                    return i + 1;
                }
            }
        }
        return Math.min(startLine + 50, sourceLines.length);
    }

    public TALStructuralProcedure createProcedureFromRegex(TALProcedureBoundary boundary) {
        TALStructuralProcedure proc = new TALStructuralProcedure();
        proc.setName(boundary.getName());
        proc.setLineNumber(boundary.getStartLine());
        proc.setEndLineNumber(boundary.getEndLine());
        proc.setContextScore(75.0); // Higher score for regex-found procedures
        proc.setReasoningInfo("Found via enhanced regex preprocessing");
        return proc;
    }

    public boolean shouldUseHybridMode(List<TALProcedureBoundary> regexProcedures, int grammarProcedures) {
        return regexProcedures.size() > grammarProcedures;
    }

    public int calculateEndLine(int startLine) {
        for (int i = startLine; i < sourceLines.length && i < startLine + 100; i++) {
            String line = sourceLines[i].trim().toUpperCase();
            if (line.equals("END;")) {
                return i + 1;
            }
            if ((line.startsWith("PROC ") || line.startsWith("SUBPROC ")) && i > startLine) {
                return i;
            }
        }
        return Math.min(startLine + 50, sourceLines.length);
    }
}

class TALStatementInitializer {
    public static void initializeAllProcedures(List<TALStructuralProcedure> procedures) {
        for (TALStructuralProcedure proc : procedures) {
            if (proc.getStatements() == null) {
                proc.setStatements(new ArrayList<>());
            }
        }
    }
}

class TALParserConfiguration {
    private boolean verboseLogging = false;
    private boolean dataPreprocessingEnabled = true;
    private boolean regexPreprocessingEnabled = true;
    private boolean grammarParsingEnabled = true;
    private boolean hybridModeEnabled = true;
    private TALErrorRecoveryMode errorRecoveryMode = TALErrorRecoveryMode.LENIENT;
    private List<String> expectedProcedures = new ArrayList<>();

    public void loadDefaults() {
        verboseLogging = true;
        dataPreprocessingEnabled = true;
        regexPreprocessingEnabled = true;
        grammarParsingEnabled = true;
        hybridModeEnabled = true;
        errorRecoveryMode = TALErrorRecoveryMode.LENIENT;
    }
   
    public List<String> validate() {
        List<String> issues = new ArrayList<>();
        return issues;
    }
   
    public boolean isVerboseLogging() { return verboseLogging; }
    public boolean isDataPreprocessingEnabled() { return dataPreprocessingEnabled; }
    public boolean isRegexPreprocessingEnabled() { return regexPreprocessingEnabled; }
    public boolean isGrammarParsingEnabled() { return grammarParsingEnabled; }
    public boolean isHybridModeEnabled() { return hybridModeEnabled; }
    public TALErrorRecoveryMode getErrorRecoveryMode() { return errorRecoveryMode; }
    public List<String> getExpectedProcedures() { return expectedProcedures; }

    @Override
    public String toString() {
        return "TALParserConfiguration{" +
               "verbose=" + verboseLogging +
               ", dataPreprocessing=" + dataPreprocessingEnabled +
               ", grammarParsing=" + grammarParsingEnabled +
               ", hybrid=" + hybridModeEnabled +
               '}';
    }
}

enum TALErrorRecoveryMode {
    STRICT,
    LENIENT,
    IGNORE
}

class TALStructuralDataItem {
    private String name;
    private String dataType;
    private String value;
    private String definition;
    private String section;
    private int lineNumber;

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getDataType() { return dataType; }
    public void setDataType(String dataType) { this.dataType = dataType; }
    public String getValue() { return value; }
    public void setValue(String value) { this.value = value; }
    public String getDefinition() { return definition; }
    public void setDefinition(String definition) { this.definition = definition; }
    public String getSection() { return section; }
    public void setSection(String section) { this.section = section; }
    public int getLineNumber() { return lineNumber; }
    public void setLineNumber(int lineNumber) { this.lineNumber = lineNumber; }
}

class TALFileDescriptor {
    private String name;
    private String definition;
    private int lineNumber;

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getDefinition() { return definition; }
    public void setDefinition(String definition) { this.definition = definition; }
    public int getLineNumber() { return lineNumber; }
    public void setLineNumber(int lineNumber) { this.lineNumber = lineNumber; }
}

class TALStructuralProcedure {
    private String name;
    private int lineNumber;
    private int endLineNumber;
    private double contextScore;
    private String reasoningInfo;
    private List<TALStructuralStatement> statements = new ArrayList<>();

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public int getLineNumber() { return lineNumber; }
    public void setLineNumber(int lineNumber) { this.lineNumber = lineNumber; }
    public int getEndLineNumber() { return endLineNumber; }
    public void setEndLineNumber(int endLineNumber) { this.endLineNumber = endLineNumber; }
    public double getContextScore() { return contextScore; }
    public void setContextScore(double contextScore) { this.contextScore = contextScore; }
    public String getReasoningInfo() { return reasoningInfo; }
    public void setReasoningInfo(String reasoningInfo) { this.reasoningInfo = reasoningInfo; }
    public List<TALStructuralStatement> getStatements() { return statements; }
    public void setStatements(List<TALStructuralStatement> statements) { this.statements = statements; }
}

// ENHANCED: Extended TALStructuralStatement with TAL-specific fields
class TALStructuralStatement {
    private String type;
    private String content;
    private int lineNumber;
    private List<String> accessedVariables = new ArrayList<>();
    private List<String> accessedFiles = new ArrayList<>();
    private String callTarget;
    private String systemFunction;

    // ENHANCED: TAL-specific fields
    private String pointerTarget;
    private String condition;
    private String returnValue;
    private String bitFieldVariable;
    private String bitFieldStartBit;
    private String bitFieldEndBit;
    private String bitFieldValue;
    private String stringMoveTarget;
    private String stringMoveSource;
    private String scanSource;
    private String scanCondition;
    private String scanTarget;

    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }
    public int getLineNumber() { return lineNumber; }
    public void setLineNumber(int lineNumber) { this.lineNumber = lineNumber; }
    public List<String> getAccessedVariables() { return accessedVariables; }
    public void setAccessedVariables(List<String> accessedVariables) { this.accessedVariables = accessedVariables; }
    public List<String> getAccessedFiles() { return accessedFiles; }
    public void setAccessedFiles(List<String> accessedFiles) { this.accessedFiles = accessedFiles; }
    public String getCallTarget() { return callTarget; }
    public void setCallTarget(String callTarget) { this.callTarget = callTarget; }
    public String getSystemFunction() { return systemFunction; }
    public void setSystemFunction(String systemFunction) { this.systemFunction = systemFunction; }

    // ENHANCED: TAL-specific getters and setters
    public String getPointerTarget() { return pointerTarget; }
    public void setPointerTarget(String pointerTarget) { this.pointerTarget = pointerTarget; }
    public String getCondition() { return condition; }
    public void setCondition(String condition) { this.condition = condition; }
    public String getReturnValue() { return returnValue; }
    public void setReturnValue(String returnValue) { this.returnValue = returnValue; }
    public void setBitFieldInfo(String variable, String startBit, String endBit, String value) {
        this.bitFieldVariable = variable;
        this.bitFieldStartBit = startBit;
        this.bitFieldEndBit = endBit;
        this.bitFieldValue = value;
    }

    public void setStringMoveInfo(String target, String source) {
        this.stringMoveTarget = target;
        this.stringMoveSource = source;
    }

    public void setScanInfo(String source, String condition, String target) {
        this.scanSource = source;
        this.scanCondition = condition;
        this.scanTarget = target;
    }

    public String getBitFieldVariable() { return bitFieldVariable; }
    public String getBitFieldStartBit() { return bitFieldStartBit; }
    public String getBitFieldEndBit() { return bitFieldEndBit; }
    public String getBitFieldValue() { return bitFieldValue; }
    public String getStringMoveTarget() { return stringMoveTarget; }
    public String getStringMoveSource() { return stringMoveSource; }
    public String getScanSource() { return scanSource; }
    public String getScanCondition() { return scanCondition; }
    public String getScanTarget() { return scanTarget; }
}

class TALDataPreprocessor {
    private TALParserConfiguration config;

    public TALDataPreprocessor(TALParserConfiguration config) {
        this.config = config;
    }

    public PreprocessingResult preprocessDataSections(String[] sourceLines) {
        PreprocessingResult result = new PreprocessingResult();
        List<TALStructuralDataItem> dataItems = new ArrayList<>();

        // ENHANCED: Better patterns for TAL data structures
        Pattern structPattern = Pattern.compile("^\\s*STRUCT\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(\\*\\)\\s*;", Pattern.CASE_INSENSITIVE);
        Pattern varPattern = Pattern.compile("^\\s*(INT|STRING|CHAR|BYTE|BOOL|REAL|FIXED)(?:\\s*\\(\\d+\\))?\\s+([A-Za-z_][A-Za-z0-9_]*(?:\\.\\w+)?(?:\\[\\d+:\\d+\\])?)\\s*(?::=\\s*([^;]+))?\\s*;", Pattern.CASE_INSENSITIVE);
        Pattern pointerPattern = Pattern.compile("^\\s*([A-Za-z_][A-Za-z0-9_]*)\\s+(\\.\\w+(?:\\[\\d+:\\d+\\])?)\\s*;", Pattern.CASE_INSENSITIVE);
        Pattern namePattern = Pattern.compile("^\\s*NAME\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*;", Pattern.CASE_INSENSITIVE);

        Set<String> addedNames = new HashSet<>();
        boolean inStruct = false;
        String currentStructName = null;

        for (int i = 0; i < sourceLines.length; i++) {
            String line = sourceLines[i].trim();
            if (line.isEmpty() || line.startsWith("!")) continue;

            Matcher structMatcher = structPattern.matcher(line);
            Matcher varMatcher = varPattern.matcher(line);
            Matcher pointerMatcher = pointerPattern.matcher(line);
            Matcher nameMatcher = namePattern.matcher(line);

            if (structMatcher.find()) {
                String name = structMatcher.group(1);
                if (!addedNames.contains(name)) {
                    addedNames.add(name);
                    TALStructuralDataItem item = new TALStructuralDataItem();
                    item.setName(name);
                    item.setSection("STRUCT");
                    item.setLineNumber(i + 1);
                    item.setDataType("STRUCT");
                    item.setDefinition(line);
                    dataItems.add(item);
                    inStruct = true;
                    currentStructName = name;
                }
            } else if (inStruct && line.toUpperCase().startsWith("END")) {
                inStruct = false;
                currentStructName = null;
            } else if (inStruct && !nameMatcher.find()) {
                // Parse struct members
                if (varMatcher.find()) {
                    String type = varMatcher.group(1);
                    String name = varMatcher.group(2);
                    String value = varMatcher.groupCount() >= 3 ? varMatcher.group(3) : null;

                    if (!addedNames.contains(name)) {
                        addedNames.add(name);
                        TALStructuralDataItem item = new TALStructuralDataItem();
                        item.setName(name);
                        item.setSection("STRUCT_MEMBER");
                        item.setLineNumber(i + 1);
                        item.setDataType(type.toUpperCase());
                        item.setDefinition(line);
                        if (value != null) {
                            item.setValue(value.trim());
                        }
                        dataItems.add(item);
                    }
                }
            } else if (!inStruct && !nameMatcher.find()) {
                if (varMatcher.find()) {
                    String type = varMatcher.group(1);
                    String name = varMatcher.group(2);
                    String value = varMatcher.groupCount() >= 3 ? varMatcher.group(3) : null;

                    if (!addedNames.contains(name)) {
                        addedNames.add(name);
                        TALStructuralDataItem item = new TALStructuralDataItem();
                        item.setName(name);
                        item.setSection(name.contains("[") ? "ARRAY" : "VAR");
                        item.setLineNumber(i + 1);
                        item.setDataType(type.toUpperCase());
                        item.setDefinition(line);
                        if (value != null) {
                            item.setValue(value.trim());
                        }
                        dataItems.add(item);
                    }
                } else if (pointerMatcher.find()) {
                    String type = pointerMatcher.group(1);
                    String name = pointerMatcher.group(2);

                    if (!addedNames.contains(name)) {
                        addedNames.add(name);
                        TALStructuralDataItem item = new TALStructuralDataItem();
                        item.setName(name);
                        item.setSection("POINTER");
                        item.setLineNumber(i + 1);
                        item.setDataType(type);
                        item.setDefinition(line);
                        dataItems.add(item);
                    }
                }
            }
        }

        result.setDataItems(dataItems);
        result.setCleanedSource(sourceLines);
        return result;
    }

    static class PreprocessingResult {
        private List<TALStructuralDataItem> dataItems = new ArrayList<>();
        private List<TALFileDescriptor> fileDescriptors = new ArrayList<>();
        private String[] cleanedSource;
        private List<String> warnings = new ArrayList<>();

        public List<TALStructuralDataItem> getDataItems() { return dataItems; }
        public void setDataItems(List<TALStructuralDataItem> dataItems) { this.dataItems = dataItems; }
        public List<TALFileDescriptor> getFileDescriptors() { return fileDescriptors; }
        public void setFileDescriptors(List<TALFileDescriptor> fileDescriptors) { this.fileDescriptors = fileDescriptors; }
        public String[] getCleanedSource() { return cleanedSource; }
        public void setCleanedSource(String[] cleanedSource) { this.cleanedSource = cleanedSource; }
        public List<String> getWarnings() { return warnings; }
        public void setWarnings(List<String> warnings) { this.warnings = warnings; }
    }
}

class TALProcedureExtractor {
    private TALParserConfiguration config;

    public TALProcedureExtractor(TALParserConfiguration config) {
        this.config = config;
    }

    public TALBusinessLogicResult extractBusinessLogic(String filename) {
        TALBusinessLogicResult result = new TALBusinessLogicResult();
        List<TALProcedure> procedures = new ArrayList<>();

        try {
            String[] sourceLines = TALParserUtilities.readSourceLines(filename);

            // ENHANCED: Better patterns for TAL constructs
            Pattern procPattern = Pattern.compile("^\\s*(INT\\s+PROC|PROC|SUBPROC)\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*(?:\\([^)]*\\))?\\s*(?:MAIN)?\\s*;?", Pattern.CASE_INSENSITIVE);
            Pattern callPattern = Pattern.compile("^\\s*CALL\\s+(\\$?[A-Za-z_][A-Za-z0-9_]*)", Pattern.CASE_INSENSITIVE);
            Pattern returnPattern = Pattern.compile("^\\s*RETURN\\s*([^;]*);?", Pattern.CASE_INSENSITIVE);
            Pattern ifPattern = Pattern.compile("^\\s*IF\\s+([^\\sTHEN]+)(?:\\s+THEN)?", Pattern.CASE_INSENSITIVE);
            Pattern assignmentPattern = Pattern.compile("^\\s*([A-Za-z_@][A-Za-z0-9_@.\\[\\]]*?)\\s*:=\\s*([^;]+);?", Pattern.CASE_INSENSITIVE);
            Pattern bitFieldPattern = Pattern.compile("([A-Za-z_][A-Za-z0-9_.]*)\\.\\s*<(\\d+):(\\d+)>\\s*:=\\s*([^;]+);?", Pattern.CASE_INSENSITIVE);
            Pattern stringMovePattern = Pattern.compile("([A-Za-z_][A-Za-z0-9_.\\[\\]]*)'\\s*:='\\s*([^;]+);?", Pattern.CASE_INSENSITIVE);
            Pattern scanPattern = Pattern.compile("^\\s*SCAN\\s+([A-Za-z_][A-Za-z0-9_.]*)\\s+WHILE\\s+([^\\->]+)\\s*->\\s*([^;]+);?", Pattern.CASE_INSENSITIVE);
            Pattern controlPattern = Pattern.compile("^\\s*(IF|ENDIF|END)\\s*", Pattern.CASE_INSENSITIVE);
            Pattern dataPattern = Pattern.compile("^\\s*(INT|STRING|STRUCT|data_packet_def)\\s+.*", Pattern.CASE_INSENSITIVE);

            TALProcedure currentProc = null;
            for (int i = 0; i < sourceLines.length; i++) {
                String line = sourceLines[i].trim();
                if (line.isEmpty() || line.startsWith("!")) continue;

                Matcher procMatcher = procPattern.matcher(line);

                if (procMatcher.find()) {
                    if (currentProc != null) {
                        procedures.add(currentProc);
                    }
                    currentProc = new TALProcedure();
                    currentProc.name = procMatcher.group(2);
                    currentProc.lineNumber = i + 1;
                    currentProc.statements = new ArrayList<>();
                } else if (currentProc != null && !dataPattern.matcher(line).find()) {
                  // Check for bit field operations
                  Matcher bitFieldMatcher = bitFieldPattern.matcher(line);
                  if (bitFieldMatcher.find()) {
                      TALStatement stmt = new TALStatement();
                      stmt.type = "BIT_FIELD_ASSIGNMENT";
                      stmt.content = line;
                      stmt.lineNumber = i + 1;
                      currentProc.statements.add(stmt);
                      continue;
                  }

                  // Check for string move operations
                  Matcher stringMoveMatcher = stringMovePattern.matcher(line);
                  if (stringMoveMatcher.find()) {
                      TALStatement stmt = new TALStatement();
                      stmt.type = "STRING_MOVE";
                      stmt.content = line;
                      stmt.lineNumber = i + 1;
                      currentProc.statements.add(stmt);
                      continue;
                  }

                  // Check for SCAN operations
                  Matcher scanMatcher = scanPattern.matcher(line);
                  if (scanMatcher.find()) {
                      TALStatement stmt = new TALStatement();
                      stmt.type = "SCAN";
                      stmt.content = line;
                      stmt.lineNumber = i + 1;
                      currentProc.statements.add(stmt);
                      continue;
                  }

                  // Check for CALL statements
                  Matcher callMatcher = callPattern.matcher(line);
                  if (callMatcher.find()) {
                      TALStatement stmt = new TALStatement();
                      stmt.type = "CALL";
                      String callTarget = callMatcher.group(1);
                      if (callTarget.startsWith("$")) {
                          stmt.systemFunction = callTarget;
                      } else {
                          stmt.callTarget = callTarget;
                      }
                      stmt.content = line;
                      stmt.lineNumber = i + 1;
                      currentProc.statements.add(stmt);
                      continue;
                  }
                  // Check for RETURN statements
                  Matcher returnMatcher = returnPattern.matcher(line);
                  if (returnMatcher.find()) {
                      TALStatement stmt = new TALStatement();
                      stmt.type = "RETURN";
                      stmt.content = line;
                      stmt.lineNumber = i + 1;
                      currentProc.statements.add(stmt);
                      continue;
                  }

                  // Check for IF statements
                  Matcher ifMatcher = ifPattern.matcher(line);
                  if (ifMatcher.find()) {
                      TALStatement stmt = new TALStatement();
                      stmt.type = "IF";
                      stmt.content = line;
                      stmt.lineNumber = i + 1;
                      currentProc.statements.add(stmt);
                      continue;
                  }

                  // Check for control statements
                  Matcher controlMatcher = controlPattern.matcher(line);
                  if (controlMatcher.find()) {
                      String keyword = controlMatcher.group(1).toUpperCase();
                      TALStatement stmt = new TALStatement();
                      stmt.type = keyword;
                      stmt.content = line;
                      stmt.lineNumber = i + 1;
                      currentProc.statements.add(stmt);
                      continue;
                  }

         // Check for assignments (including pointer assignments)
         Matcher assignMatcher = assignmentPattern.matcher(line);
         if (assignMatcher.find()) {
             TALStatement stmt = new TALStatement();
             String target = assignMatcher.group(1);
             String value = assignMatcher.group(2);

             // Detect pointer assignment
             if (target.startsWith("@") || value.startsWith("@")) {
                 stmt.type = "POINTER_ASSIGNMENT";
             } else if (target.startsWith(".")) {
                 stmt.type = "POINTER_DEREFERENCE";
             } else {
                 stmt.type = "ASSIGNMENT";
             }

             stmt.content = line;
             stmt.lineNumber = i + 1;
             currentProc.statements.add(stmt);
         }
     }
 }
 if (currentProc != null) {
     procedures.add(currentProc);
 }

 result.setProcedures(procedures);
 if (config.isVerboseLogging()) {
     System.out.println("📖 DEBUG: Enhanced extractor found " + procedures.size() + " procedures");
 }

} catch (Exception e) {
 System.err.println("⚠️ Error in enhanced TAL procedure extraction: " + e.getMessage());
}

return result;
}
}


