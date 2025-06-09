import java.util.*;
import java.util.regex.Pattern;
import java.util.regex.Matcher;
import java.util.stream.Collectors;
import java.io.*;
import java.nio.file.Files;
import java.nio.file.Paths;

/**
 * Fixed Complete COBOL Call Graph Analyzer with all dependencies and errors resolved
 */
public class CallGraphAnalyzer {
    
    /**
     * Main analysis method - enhanced COBOL analysis with proper call graph tracking
     */
    public CobolStructure analyzeCobolWithCallGraph(String source, String fileName) {
        System.out.println("🔍 Starting Call Graph Analysis for: " + fileName);
        
        CobolStructure structure = new CobolStructure();
        
        // Phase 1: Extract all paragraph/section definitions first
        System.out.println("📍 Phase 1: Extracting paragraph definitions...");
        Map<String, ParagraphDefinition> definedParagraphs = extractAllParagraphDefinitions(source);
        
        // Phase 2: Parse the program structure
        System.out.println("📊 Phase 2: Parsing basic program structure...");
        parseBasicStructure(source, structure);
        
        // Phase 3: Build call graph
        System.out.println("🕸️  Phase 3: Building call graph...");
        CallGraph callGraph = buildCallGraph(source, definedParagraphs, structure); // Fixed: pass structure
        
        // Phase 4: Resolve PERFORM calls with call graph context
        System.out.println("🔗 Phase 4: Resolving PERFORM calls...");
        resolvePerformCallsWithGraph(source, structure, callGraph, definedParagraphs);
        
        // Phase 5: Detect truly external calls
        System.out.println("🎯 Phase 5: Identifying external calls...");
        identifyExternalCalls(structure, callGraph);
        
        System.out.println("✅ Call Graph Analysis completed successfully!");
        return structure;
    }
    
    /**
     * Phase 1: Extract all paragraph and section definitions
     */
    private Map<String, ParagraphDefinition> extractAllParagraphDefinitions(String source) {
        Map<String, ParagraphDefinition> paragraphs = new HashMap<>();
        String[] lines = source.split("\n");
        
        boolean inProcedureDivision = false;
        int currentLineNumber = 0;
        
        for (String line : lines) {
            currentLineNumber++;
            String cobolSource = extractCobolSource(line);
            if (cobolSource == null || cobolSource.trim().isEmpty()) {
                continue;
            }
            
            String upperSource = cobolSource.toUpperCase().trim();
            
            // Track when we enter procedure division
            if (upperSource.contains("PROCEDURE") && upperSource.contains("DIVISION")) {
                inProcedureDivision = true;
                continue;
            }
            
            if (inProcedureDivision) {
                // Look for section definitions
                if (upperSource.matches(".*SECTION\\s*\\.$")) {
                    String sectionName = extractSectionName(upperSource);
                    paragraphs.put(sectionName, new ParagraphDefinition(
                        sectionName, currentLineNumber, ParagraphType.SECTION));
                    System.out.println("📍 Found section: " + sectionName + " at line " + currentLineNumber);
                }
                // Look for paragraph definitions (more precise regex)
                else if (upperSource.matches("^[A-Z0-9][A-Z0-9\\-]*\\s*\\.$") && 
                         !upperSource.contains("SECTION")) {
                    String paragraphName = upperSource.replace(".", "").trim();
                    
                    // Filter out common false positives
                    if (!isLikelyFalsePositive(paragraphName, upperSource)) {
                        paragraphs.put(paragraphName, new ParagraphDefinition(
                            paragraphName, currentLineNumber, ParagraphType.PARAGRAPH));
                        System.out.println("📍 Found paragraph: " + paragraphName + " at line " + currentLineNumber);
                    }
                }
            }
        }
        
        System.out.println("✅ Total paragraphs/sections found: " + paragraphs.size());
        return paragraphs;
    }
    
    /**
     * Check if a potential paragraph name is likely a false positive
     */
    private boolean isLikelyFalsePositive(String name, String context) {
        // Common false positives
        String[] falsePositives = {
            "XXXXX\\d+", "CM\\d+", "\\d+", // Line numbers or IDs
            "VALUE", "PICTURE", "PIC",     // COBOL keywords
            "SPACES", "ZERO", "ZEROS",     // COBOL literals
            "END-.*"                       // End markers
        };
        
        for (String pattern : falsePositives) {
            if (name.matches(pattern)) {
                return true;
            }
        }
        
        // Check if it's part of a data definition
        if (context.contains("PIC") || context.contains("VALUE") || 
            context.matches(".*\\d\\d.*")) {
            return true;
        }
        
        return false;
    }
    
    /**
     * Phase 2: Parse basic program structure
     */
    private void parseBasicStructure(String source, CobolStructure structure) {
        String[] lines = source.split("\n");
        
        boolean inDataDivision = false;
        boolean inProcedureDivision = false;
        boolean inWorkingStorage = false;
        boolean inFileSection = false;
        
        StringBuilder currentProcedure = new StringBuilder();
        String currentProcedureName = "MAIN";
        
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i];
            String cobolSource = extractCobolSource(line);
            if (cobolSource == null || cobolSource.trim().isEmpty()) continue;
            
            String upperSource = cobolSource.toUpperCase();
            
            // Extract program identification with continuation support
            if (upperSource.contains("PROGRAM-ID")) {
                String programId = extractProgramId(upperSource);
                if (programId != null) {
                    structure.setProgramId(programId);
                } else if (i + 1 < lines.length) {
                    String nextLine = extractCobolSource(lines[i + 1]);
                    if (nextLine != null && !nextLine.trim().isEmpty()) {
                        programId = nextLine.trim().replace(".", "");
                        structure.setProgramId(programId);
                    }
                }
            }
            
            if (upperSource.contains("AUTHOR")) {
                String author = extractAuthor(cobolSource);
                if (author != null) {
                    structure.setAuthor(author);
                } else if (i + 1 < lines.length) {
                    String nextLine = extractCobolSource(lines[i + 1]);
                    if (nextLine != null && !nextLine.trim().isEmpty()) {
                        author = nextLine.trim().replace(".", "");
                        structure.setAuthor(author);
                    }
                }
            }
            
            // Track divisions and sections
            if (upperSource.contains("DATA DIVISION")) {
                inDataDivision = true;
                inProcedureDivision = false;
            } else if (upperSource.contains("PROCEDURE") && upperSource.contains("DIVISION")) {
                inDataDivision = false;
                inProcedureDivision = true;
            }
            
            if (upperSource.contains("WORKING-STORAGE SECTION")) {
                inWorkingStorage = true;
                inFileSection = false;
            } else if (upperSource.contains("FILE SECTION")) {
                inWorkingStorage = false;
                inFileSection = true;
            }
            
            // Extract working storage variables
            if (inDataDivision && inWorkingStorage) {
                CobolVariable var = parseVariableLineFixed(cobolSource);
                if (var != null) {
                    structure.getWorkingStorageVariables().add(var);
                }
            }
            
            // Extract file descriptions
            if (inDataDivision && inFileSection) {
                CobolFile file = parseFileDescription(cobolSource);
                if (file != null) {
                    structure.getFileDescriptions().add(file);
                }
            }
            
            // Extract procedure code
            if (inProcedureDivision) {
                // Check for section headers
                if (upperSource.matches(".*SECTION\\s*\\.$")) {
                    if (currentProcedure.length() > 0) {
                        addProcedure(structure, currentProcedureName, currentProcedure.toString());
                    }
                    currentProcedureName = extractSectionName(upperSource);
                    currentProcedure = new StringBuilder();
                }
                // Check for paragraph names
                else if (upperSource.trim().matches("^[A-Z0-9][A-Z0-9\\-]*\\s*\\.$") &&
                         !isLikelyFalsePositive(upperSource.replace(".", "").trim(), upperSource)) {
                    if (currentProcedure.length() > 0) {
                        addProcedure(structure, currentProcedureName, currentProcedure.toString());
                    }
                    currentProcedureName = upperSource.replace(".", "").trim();
                    currentProcedure = new StringBuilder();
                } 
                // Regular procedure statements
                else if (!upperSource.trim().isEmpty() && 
                         !upperSource.contains("PROCEDURE DIVISION")) {
                    currentProcedure.append(cobolSource).append("\n");
                }
            }
        }
        
        // Add final procedure
        if (currentProcedure.length() > 0) {
            addProcedure(structure, currentProcedureName, currentProcedure.toString());
        }
    }
    
    /**
     * Phase 3: Build comprehensive call graph - FIXED with structure parameter
     */
    private CallGraph buildCallGraph(String source, Map<String, ParagraphDefinition> definedParagraphs, CobolStructure structure) {
        CallGraph callGraph = new CallGraph();
        String[] lines = source.split("\n");
        
        boolean inProcedureDivision = false;
        String currentParagraph = "MAIN";
        
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i];
            String cobolSource = extractCobolSource(line);
            if (cobolSource == null || cobolSource.trim().isEmpty()) continue;
            
            String upperSource = cobolSource.toUpperCase();
            
            if (upperSource.contains("PROCEDURE") && upperSource.contains("DIVISION")) {
                inProcedureDivision = true;
                continue;
            }
            
            if (inProcedureDivision) {
                // Update current paragraph context
                if (upperSource.trim().matches("^[A-Z0-9][A-Z0-9\\-]*\\s*\\.$") &&
                    !isLikelyFalsePositive(upperSource.replace(".", "").trim(), upperSource)) {
                    currentParagraph = upperSource.replace(".", "").trim();
                }
                
                // Extract PERFORM calls with enhanced parsing
                List<PerformCall> performCalls = extractEnhancedPerformCalls(upperSource, i + 1);
                for (PerformCall call : performCalls) {
                    callGraph.addCall(currentParagraph, call);
                }
                
                // Extract external program calls
                CobolExternalCall externalCall = parseCallStatement(upperSource, String.valueOf(i + 1));
                if (externalCall != null) {
                    callGraph.addExternalCall(currentParagraph, externalCall);
                    structure.getExternalCalls().add(externalCall); // FIXED: now structure is available
                }
                
                // Extract copybook statements
                CobolCopybook copybook = parseCopyStatement(upperSource, String.valueOf(i + 1));
                if (copybook != null) {
                    structure.getCopybooks().add(copybook); // FIXED: now structure is available
                }
            }
        }
        
        return callGraph;
    }
    
    /**
     * Enhanced PERFORM call extraction with better parsing
     */
    private List<PerformCall> extractEnhancedPerformCalls(String line, int lineNumber) {
        List<PerformCall> calls = new ArrayList<>();
        
        // More comprehensive PERFORM patterns
        String[] patterns = {
            "PERFORM\\s+([A-Z0-9\\-]+)\\s+THRU\\s+([A-Z0-9\\-]+)",          // PERFORM X THRU Y
            "PERFORM\\s+([A-Z0-9\\-]+)\\s+(\\d+)\\s+TIMES",                // PERFORM X N TIMES
            "PERFORM\\s+([A-Z0-9\\-]+)\\s+UNTIL\\s+",                      // PERFORM X UNTIL
            "PERFORM\\s+([A-Z0-9\\-]+)\\s+VARYING\\s+",                    // PERFORM X VARYING
            "PERFORM\\s+([A-Z0-9\\-]+)(?:\\s|$|\\.)"                       // PERFORM X (simple)
        };
        
        PerformType[] types = {
            PerformType.THROUGH,
            PerformType.TIMES,
            PerformType.UNTIL,
            PerformType.VARYING,
            PerformType.SIMPLE
        };
        
        for (int i = 0; i < patterns.length; i++) {
            Pattern pattern = Pattern.compile(patterns[i]);
            Matcher matcher = pattern.matcher(line);
            
            if (matcher.find()) {
                String targetName = matcher.group(1);
                PerformCall call = new PerformCall(targetName, types[i], lineNumber);
                
                // Handle THRU case
                if (i == 0 && matcher.groupCount() > 1) {
                    call.setThroughTarget(matcher.group(2));
                }
                
                calls.add(call);
                break; // Only match first pattern to avoid duplicates
            }
        }
        
        return calls;
    }
    
    /**
     * Phase 4: Resolve PERFORM calls using call graph context
     */
    private void resolvePerformCallsWithGraph(String source, CobolStructure structure, 
            CallGraph callGraph, Map<String, ParagraphDefinition> definedParagraphs) {
        
        // Convert internal call graph to CobolPerformCall objects
        for (Map.Entry<String, List<PerformCall>> entry : callGraph.getCalls().entrySet()) {
            String caller = entry.getKey();
            
            for (PerformCall call : entry.getValue()) {
                CobolPerformCall performCall = new CobolPerformCall(call.getTargetName());
                performCall.setPerformType(convertPerformType(call.getType()));
                performCall.setSourceLocation("Line " + call.getLineNumber() + " (called from " + caller + ")");
                performCall.setThroughTarget(call.getThroughTarget());
                
                // Check if target exists in defined paragraphs
                boolean isExternal = !definedParagraphs.containsKey(call.getTargetName());
                
                // Additional checks for potential copybook references
                if (isExternal) {
                    isExternal = !isPotentialCopybookParagraph(call.getTargetName(), structure);
                }
                
                performCall.setExternal(isExternal);
                structure.getPerformCalls().add(performCall);
            }
        }
    }
    
    /**
     * Phase 5: Identify truly external calls vs. copybook references
     */
    private void identifyExternalCalls(CobolStructure structure, CallGraph callGraph) {
        List<CobolPerformCall> externalPerforms = structure.getPerformCalls().stream()
            .filter(CobolPerformCall::isExternal)
            .collect(Collectors.toList());
        
        System.out.println("🔍 Analyzing " + externalPerforms.size() + " potentially external PERFORM calls:");
        
        for (CobolPerformCall perform : externalPerforms) {
            String targetName = perform.getTargetName();
            
            // Categorize the external call
            ExternalCallCategory category = categorizeExternalCall(targetName, structure);
            
            switch (category) {
                case LIKELY_COPYBOOK:
                    System.out.println("📚 " + targetName + " - Likely in copybook");
                    perform.setExternal(false); // Mark as resolved
                    break;
                case LIKELY_EXTERNAL_PROGRAM:
                    System.out.println("🔗 " + targetName + " - Likely external program");
                    break;
                case LIKELY_ERROR:
                    System.out.println("❌ " + targetName + " - Likely parsing error");
                    break;
                case UNKNOWN:
                    System.out.println("❓ " + targetName + " - Unknown target");
                    break;
            }
        }
    }
    
    // Helper methods (all implementations included)
    
    private String extractCobolSource(String line) {
        if (line.length() < 7) return null;
        if (line.length() > 6 && line.charAt(6) == '*') return null;
        
        int startCol = 7;
        int endCol = Math.min(72, line.length());
        if (startCol >= line.length()) return null;
        
        return line.substring(startCol, endCol);
    }
    
    private String extractSectionName(String line) {
        return line.replace("SECTION", "").replace(".", "").trim();
    }
    
    private String extractProgramId(String line) {
        Pattern pattern = Pattern.compile("PROGRAM-ID\\.?\\s*([A-Z0-9\\-]+)");
        Matcher matcher = pattern.matcher(line);
        return matcher.find() ? matcher.group(1).trim() : null;
    }
    
    private String extractAuthor(String line) {
        if (!line.toUpperCase().contains("AUTHOR")) return null;
        
        String afterAuthor = line.substring(line.toUpperCase().indexOf("AUTHOR") + 6).trim();
        if (afterAuthor.startsWith(".")) afterAuthor = afterAuthor.substring(1).trim();
        if (afterAuthor.endsWith(".")) afterAuthor = afterAuthor.substring(0, afterAuthor.length() - 1);
        
        return afterAuthor.isEmpty() ? null : afterAuthor;
    }
    
    private void addProcedure(CobolStructure structure, String name, String code) {
        if (code.trim().isEmpty()) return;
        
        CobolProcedure proc = new CobolProcedure(name, code.trim());
        proc.setLogicSummary(summarizeProcedureLogic(code));
        structure.getProcedures().add(proc);
    }
    
    private String summarizeProcedureLogic(String procedureCode) {
        String upperCode = procedureCode.toUpperCase();
        List<String> operations = new ArrayList<>();
        
        if (upperCode.contains("MOVE")) operations.add("Data Movement");
        if (upperCode.contains("ADD") || upperCode.contains("SUBTRACT") || 
            upperCode.contains("MULTIPLY") || upperCode.contains("DIVIDE") ||
            upperCode.contains("COMPUTE")) {
            operations.add("Arithmetic Operations");
        }
        if (upperCode.contains("IF")) operations.add("Conditional Logic");
        if (upperCode.contains("PERFORM")) operations.add("Loop/Iteration");
        if (upperCode.contains("READ") || upperCode.contains("WRITE") || 
            upperCode.contains("OPEN") || upperCode.contains("CLOSE")) {
            operations.add("File I/O");
        }
        if (upperCode.contains("DISPLAY")) operations.add("Output");
        if (upperCode.contains("ACCEPT")) operations.add("Input");
        if (upperCode.contains("CALL")) operations.add("Subprogram Call");
        
        return operations.isEmpty() ? "General Processing" : String.join(", ", operations);
    }
    
    private CobolVariable parseVariableLineFixed(String line) {
        String trimmed = line.trim();
        Pattern levelPattern = Pattern.compile("^(\\d{1,2})\\s+([A-Z0-9\\-]+)(.*)");
        Matcher levelMatcher = levelPattern.matcher(trimmed);
        
        if (levelMatcher.matches()) {
            try {
                int level = Integer.parseInt(levelMatcher.group(1));
                String name = levelMatcher.group(2);
                String remainder = levelMatcher.group(3);
                
                if ("FILLER".equals(name) && !remainder.contains("VALUE")) {
                    return null;
                }
                
                CobolVariable var = new CobolVariable(name, level, "UNKNOWN");
                
                // Extract PICTURE clause
                Pattern picPattern = Pattern.compile("(?:PIC|PICTURE)\\s+(?:IS\\s+)?([A-Z0-9\\(\\)\\.,V\\-\\+]+)");
                Matcher picMatcher = picPattern.matcher(remainder.toUpperCase());
                if (picMatcher.find()) {
                    String picture = picMatcher.group(1);
                    var.setPictureClause(picture);
                    var = new CobolVariable(name, level, deriveDataType(picture));
                    var.setPictureClause(picture);
                }
                
                // Extract VALUE clause
                Pattern valuePattern = Pattern.compile("VALUE\\s+(?:IS\\s+)?([^.]+)");
                Matcher valueMatcher = valuePattern.matcher(remainder.toUpperCase());
                if (valueMatcher.find()) {
                    String value = valueMatcher.group(1).trim();
                    var.setInitialValue(value);
                }
                
                return var;
                
            } catch (NumberFormatException e) {
                // Not a valid level number
            }
        }
        
        return null;
    }
    
    private CobolFile parseFileDescription(String line) {
        String trimmed = line.trim().toUpperCase();
        
        if (trimmed.startsWith("FD ") || trimmed.startsWith("FD\t")) {
            String remaining = trimmed.substring(2).trim();
            String fileName = remaining.split("\\s+")[0];
            CobolFile file = new CobolFile(fileName);
            
            if (remaining.contains("LABEL")) {
                file.setRecordFormat("LABEL RECORDS");
            }
            
            return file;
        }
        
        if (trimmed.startsWith("SELECT ")) {
            String remaining = trimmed.substring(6).trim();
            String fileName = remaining.split("\\s+")[0];
            CobolFile file = new CobolFile(fileName);
            file.setAccessMode("SEQUENTIAL");
            return file;
        }
        
        return null;
    }
    
    private String deriveDataType(String pictureClause) {
        if (pictureClause == null) return "UNKNOWN";
        
        pictureClause = pictureClause.toUpperCase();
        
        if (pictureClause.contains("X")) {
            return "ALPHANUMERIC";
        } else if (pictureClause.contains("9")) {
            return pictureClause.contains("V") ? "NUMERIC_DECIMAL" : "NUMERIC_INTEGER";
        } else if (pictureClause.contains("A")) {
            return "ALPHABETIC";
        }
        
        return "UNKNOWN";
    }
    
    private CobolExternalCall parseCallStatement(String line, String lineNumber) {
        String[] patterns = {
            "CALL\\s+'([^']+)'",
            "CALL\\s+([A-Z0-9\\-]+)",
            "EXEC\\s+CICS\\s+LINK\\s+PROGRAM\\s*\\(\\s*'([^']+)'\\s*\\)"
        };
        
        CobolExternalCall.CallType[] callTypes = {
            CobolExternalCall.CallType.STATIC_CALL,
            CobolExternalCall.CallType.DYNAMIC_CALL,
            CobolExternalCall.CallType.CICS_CALL
        };
        
        for (int i = 0; i < patterns.length; i++) {
            Pattern pattern = Pattern.compile(patterns[i]);
            Matcher matcher = pattern.matcher(line);
            if (matcher.find()) {
                String programName = matcher.group(1);
                CobolExternalCall call = new CobolExternalCall(programName);
                call.setCallType(callTypes[i]);
                call.setSourceLocation("Line " + lineNumber);
                call.setDynamic(i == 1);
                
                if (line.contains("USING")) {
                    call.getParameters().addAll(extractUsingParameters(line));
                }
                
                return call;
            }
        }
        return null;
    }
    
    private CobolCopybook parseCopyStatement(String line, String lineNumber) {
        String[] patterns = {
            "COPY\\s+([A-Z0-9\\-\\.]+)",
            "COPY\\s+'([^']+)'",
            "COPY\\s+([A-Z0-9\\-\\.]+)\\s+OF\\s+([A-Z0-9\\-\\.]+)"
        };
        
        for (int i = 0; i < patterns.length; i++) {
            Pattern pattern = Pattern.compile(patterns[i]);
            Matcher matcher = pattern.matcher(line);
            if (matcher.find()) {
                String copybookName = matcher.group(1);
                CobolCopybook copybook = new CobolCopybook(copybookName);
                copybook.setSourceLocation("Line " + lineNumber);
                
                if (matcher.groupCount() > 1 && matcher.group(2) != null) {
                    copybook.setLibrary(matcher.group(2));
                }
                
                if (line.contains("REPLACING")) {
                    int replacingIndex = line.indexOf("REPLACING");
                    copybook.setReplacingClause(line.substring(replacingIndex));
                }
                
                copybook.setType(determineCopybookType(copybookName, line));
                return copybook;
            }
        }
        return null;
    }
    
    private List<String> extractUsingParameters(String line) {
        List<String> parameters = new ArrayList<>();
        
        int usingIndex = line.toUpperCase().indexOf("USING");
        if (usingIndex >= 0) {
            String usingClause = line.substring(usingIndex + 5).trim();
            
            usingClause = usingClause.replaceAll("(?i)\\bBY\\s+REFERENCE\\b", "")
                                     .replaceAll("(?i)\\bBY\\s+CONTENT\\b", "")
                                     .replaceAll("(?i)\\bBY\\s+VALUE\\b", "");
            
            String[] parts = usingClause.split("\\s+");
            for (String part : parts) {
                part = part.trim().replaceAll("[,.]", "");
                if (!part.isEmpty() && part.matches("[A-Z0-9\\-]+")) {
                    parameters.add(part);
                }
            }
        }
        
        return parameters;
    }
    
    private CobolCopybook.CopybookType determineCopybookType(String name, String context) {
        name = name.toUpperCase();
        context = context.toUpperCase();
        
        if (name.contains("REC") || name.contains("RECORD") || name.contains("LAYOUT")) {
            return CobolCopybook.CopybookType.DATA_STRUCTURE;
        } else if (name.contains("PROC") || name.contains("ROUTINE") || context.contains("PROCEDURE")) {
            return CobolCopybook.CopybookType.PROCEDURE_CODE;
        } else if (name.contains("CONST") || name.contains("CODE") || name.contains("MSG")) {
            return CobolCopybook.CopybookType.CONSTANTS;
        }
        
        return CobolCopybook.CopybookType.UNKNOWN;
    }
    
    private boolean isPotentialCopybookParagraph(String paragraphName, CobolStructure structure) {
        // Check if there are copybooks that might contain this paragraph
        for (CobolCopybook copybook : structure.getCopybooks()) {
            if (copybook.getType() == CobolCopybook.CopybookType.PROCEDURE_CODE) {
                return true;
            }
        }
        
        // Check naming patterns that suggest copybook origin
        String[] copybookPatterns = {
            ".*-RTN$", ".*-ROUTINE$", ".*-PROC$", ".*-PROCESS$",
            "COMMON-.*", "UTIL-.*", "STD-.*", "STANDARD-.*"
        };
        
        for (String pattern : copybookPatterns) {
            if (paragraphName.matches(pattern)) {
                return true;
            }
        }
        
        return false;
    }
    
    private ExternalCallCategory categorizeExternalCall(String targetName, CobolStructure structure) {
        if (targetName.matches("\\d+") || targetName.length() < 3) {
            return ExternalCallCategory.LIKELY_ERROR;
        }
        
        if (isPotentialCopybookParagraph(targetName, structure)) {
            return ExternalCallCategory.LIKELY_COPYBOOK;
        }
        
        String[] externalPatterns = {
            "CALL-.*", "EXEC-.*", "RUN-.*", "START-.*",
            ".*-PGM$", ".*-PROGRAM$", ".*-MODULE$"
        };
        
        for (String pattern : externalPatterns) {
            if (targetName.matches(pattern)) {
                return ExternalCallCategory.LIKELY_EXTERNAL_PROGRAM;
            }
        }
        
        return ExternalCallCategory.UNKNOWN;
    }
    
    private CobolPerformCall.PerformType convertPerformType(PerformType type) {
        switch (type) {
            case SIMPLE: return CobolPerformCall.PerformType.SIMPLE;
            case THROUGH: return CobolPerformCall.PerformType.THROUGH;
            case TIMES: return CobolPerformCall.PerformType.TIMES;
            case UNTIL: return CobolPerformCall.PerformType.UNTIL;
            case VARYING: return CobolPerformCall.PerformType.VARYING;
            default: return CobolPerformCall.PerformType.SIMPLE;
        }
    }
    
    // Static main method for testing
    public static void main(String[] args) {
        if (args.length < 1) {
            System.out.println("Usage: java CallGraphAnalyzer <cobol-file>");
            return;
        }
        
        try {
            String cobolSource = new String(Files.readAllBytes(Paths.get(args[0])));
            
            CallGraphAnalyzer analyzer = new CallGraphAnalyzer();
            CobolStructure structure = analyzer.analyzeCobolWithCallGraph(cobolSource, args[0]);
            
            // Print summary
            System.out.println("\n📊 ANALYSIS SUMMARY:");
            System.out.println("Program: " + (structure.getProgramId() != null ? structure.getProgramId() : "Unknown"));
            System.out.println("Author: " + (structure.getAuthor() != null ? structure.getAuthor() : "Unknown"));
            System.out.println("Working Storage Variables: " + structure.getWorkingStorageVariables().size());
            System.out.println("File Descriptions: " + structure.getFileDescriptions().size());
            System.out.println("Procedures: " + structure.getProcedures().size());
            System.out.println("Copybooks: " + structure.getCopybooks().size());
            System.out.println("External Calls: " + structure.getExternalCalls().size());
            System.out.println("Total PERFORM calls: " + structure.getPerformCalls().size());
            
            long externalPerforms = structure.getPerformCalls().stream()
                .filter(CobolPerformCall::isExternal).count();
            System.out.println("External PERFORM calls: " + externalPerforms);
            
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
}

// ===== SUPPORTING DATA STRUCTURES =====

class ParagraphDefinition {
    private String name;
    private int lineNumber;
    private ParagraphType type;
    
    public ParagraphDefinition(String name, int lineNumber, ParagraphType type) {
        this.name = name;
        this.lineNumber = lineNumber;
        this.type = type;
    }
    
    public String getName() { return name; }
    public int getLineNumber() { return lineNumber; }
    public ParagraphType getType() { return type; }
}

enum ParagraphType {
    PARAGRAPH, SECTION
}

class CallGraph {
    private Map<String, List<PerformCall>> calls = new HashMap<>();
    private Map<String, List<CobolExternalCall>> externalCalls = new HashMap<>();
    
    public void addCall(String from, PerformCall to) {
        calls.computeIfAbsent(from, k -> new ArrayList<>()).add(to);
    }
    
    public void addExternalCall(String from, CobolExternalCall to) {
        externalCalls.computeIfAbsent(from, k -> new ArrayList<>()).add(to);
    }
    
    public Map<String, List<PerformCall>> getCalls() { return calls; }
    public Map<String, List<CobolExternalCall>> getExternalCalls() { return externalCalls; }
    
    public void printCallGraph() {
        System.out.println("\n📊 Call Graph Analysis:");
        for (Map.Entry<String, List<PerformCall>> entry : calls.entrySet()) {
            System.out.println("📍 " + entry.getKey() + " calls:");
            for (PerformCall call : entry.getValue()) {
                System.out.println("  → " + call.getTargetName() + " (" + call.getType() + ")");
            }
        }
    }
}

class PerformCall {
    private String targetName;
    private String throughTarget;
    private PerformType type;
    private int lineNumber;
    
    public PerformCall(String targetName, PerformType type, int lineNumber) {
        this.targetName = targetName;
        this.type = type;
        this.lineNumber = lineNumber;
    }
    
    public String getTargetName() { return targetName; }
    public String getThroughTarget() { return throughTarget; }
    public void setThroughTarget(String throughTarget) { this.throughTarget = throughTarget; }
    public PerformType getType() { return type; }
    public int getLineNumber() { return lineNumber; }
}

enum PerformType {
    SIMPLE, THROUGH, TIMES, UNTIL, VARYING
}

enum ExternalCallCategory {
    LIKELY_COPYBOOK,
    LIKELY_EXTERNAL_PROGRAM, 
    LIKELY_ERROR,
    UNKNOWN
}












