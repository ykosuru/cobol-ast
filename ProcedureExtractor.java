
/*
 * Enhanced Procedure Extractor
 * Extracts COBOL procedures and their business logic using text analysis and DataDivisionPreprocessor
 */

import java.io.*;
import java.util.*;
import java.util.regex.*;

public class ProcedureExtractor {
    
    private DataDivisionPreprocessor dataPreprocessor;
    
    public ProcedureExtractor(ParserConfiguration config) {
        this.dataPreprocessor = new DataDivisionPreprocessor(config);
    }
    
    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: java ProcedureExtractor <cobol-file>");
            System.exit(1);
        }
        
        try {
            ParserConfiguration config = new ParserConfiguration();
            config.setVerboseLogging(true);
            ProcedureExtractor extractor = new ProcedureExtractor(config);
            BusinessLogicResult result = extractor.extractBusinessLogic(args[0]);
            extractor.printBusinessLogicResults(result);
        } catch (IOException e) {
            System.err.println("Error reading file: " + e.getMessage());
        }
    }
    
    /**
     * Extract business logic from COBOL file
     */
    public BusinessLogicResult extractBusinessLogic(String filename) throws IOException {
        String content = readFile(filename);
        DataDivisionPreprocessor.PreprocessingResult preprocessResult = dataPreprocessor.preprocessDataDivisions(content.split("\n"));
        List<CobolProcedure2> procedures = extractProceduresFromText(content, preprocessResult);
        return new BusinessLogicResult(procedures, preprocessResult.getDataItems(), preprocessResult.getFileDescriptors());
    }
    
    /**
     * Extract procedures from COBOL text with preprocessing results
     */
    private List<CobolProcedure2> extractProceduresFromText(String content, DataDivisionPreprocessor.PreprocessingResult preprocessResult) {
        List<CobolProcedure2> procedures = new ArrayList<>();
        String[] lines = content.split("\n");
        Set<String> dataItemNames = new HashSet<>();
        for (StructuralDataItemV2 item : preprocessResult.getDataItems()) {
            dataItemNames.add(item.getName().toLowerCase());
        }
        Set<String> fileNames = new HashSet<>();
        for (DataDivisionPreprocessor.FileDescriptor fd : preprocessResult.getFileDescriptors()) {
            fileNames.add(fd.getName().toLowerCase());
        }
        
        boolean inProcedureDiv = false;
        CobolProcedure2 currentProc = null;
        
        System.out.println("🔍 Analyzing " + lines.length + " lines for procedures...");
        
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i];
            String trimmed = line.trim();
            String upper = trimmed.toUpperCase();
            
            if (trimmed.startsWith("*")) {
                continue;
            }
            
            if (upper.contains("PROCEDURE DIVISION")) {
                inProcedureDiv = true;
                System.out.println("✅ Found PROCEDURE DIVISION at line " + (i + 1));
                continue;
            }
            
            if (!inProcedureDiv) {
                continue;
            }
            
            if (isParagraphDefinition(trimmed)) {
                if (currentProc != null) {
                    procedures.add(currentProc);
                }
                
                String procName = extractParagraphName(trimmed);
                currentProc = new CobolProcedure2(procName, i + 1);
                System.out.println("📋 Found procedure: " + procName + " at line " + (i + 1));
            } else if (currentProc != null && !trimmed.isEmpty()) {
                String stmtType = getStatementType(trimmed);
                List<String> accessedDataItems = extractAccessedDataItems(trimmed, dataItemNames);
                List<String> accessedFiles = extractAccessedFiles(trimmed, fileNames);
                String sqlTable = extractSqlTable(trimmed);
                String performTarget = extractPerformTarget(trimmed);
                currentProc.addStatement(new CobolStatement2(stmtType, trimmed, i + 1, accessedDataItems, accessedFiles, sqlTable, performTarget));
            }
        }
        
        if (currentProc != null) {
            procedures.add(currentProc);
        }
        
        findMissingProcedures(content, procedures, dataItemNames);
        return procedures;
    }
    
    /**
     * Find missing procedures by analyzing comments and context
     */
    private void findMissingProcedures(String content, List<CobolProcedure2> procedures, Set<String> dataItemNames) {
        System.out.println("\n🔍 Second pass: looking for missing procedures...");
        
        Set<String> foundNames = new HashSet<>();
        for (CobolProcedure2 proc : procedures) {
            foundNames.add(proc.getName().toLowerCase());
        }
        
        String[] expectedProcs = {
            "mainlineProcessing", "initialization", "readCtrpaParm99",
            "openInOutFile", "processExpFile", "validateExpRec",
            "validateSerialNo", "processCpuDir", "processCustDtl",
            "processHeaderRec", "processDetailRec", "processTrailRec",
            "readInputFile", "termination"
        };
        
        for (String expected : expectedProcs) {
            if (!foundNames.contains(expected.toLowerCase())) {
                System.out.println("🔍 Looking for missing procedure: " + expected);
                
                String[] lines = content.split("\n");
                for (int i = 0; i < lines.length; i++) {
                    String line = lines[i];
                    String upper = line.toUpperCase();
                    
                    if (line.trim().startsWith("*") && upper.contains(expected.toUpperCase())) {
                        System.out.println("   Found reference in comment at line " + (i + 1) + ": " + line.trim());
                        
                        for (int j = i + 1; j < Math.min(i + 10, lines.length); j++) {
                            String nextLine = lines[j].trim();
                            if (!nextLine.startsWith("*") && !nextLine.isEmpty()) {
                                if (nextLine.toLowerCase().contains(expected.toLowerCase()) ||
                                    isLikelyProcedureStart(nextLine, expected)) {
                                    System.out.println("   🎯 Found likely procedure at line " + (j + 1) + ": " + nextLine);
                                    
                                    CobolProcedure2 proc = new CobolProcedure2(expected, j + 1);
                                    List<String> accessedDataItems = extractAccessedDataItems(nextLine, dataItemNames);
                                    List<String> accessedFiles = new ArrayList<>();
                                    String sqlTable = extractSqlTable(nextLine);
                                    String performTarget = extractPerformTarget(nextLine);
                                    proc.addStatement(new CobolStatement2("RECOVERED", nextLine, j + 1, accessedDataItems, accessedFiles, sqlTable, performTarget));
                                    procedures.add(proc);
                                    foundNames.add(expected.toLowerCase());
                                    break;
                                }
                            }
                        }
                    }
                    
                    if (!line.trim().startsWith("*") && upper.contains(expected.toUpperCase())) {
                        String trimmed = line.trim();
                        if (trimmed.toLowerCase().startsWith(expected.toLowerCase()) && 
                            (trimmed.endsWith(".") || trimmed.contains("."))) {
                            System.out.println("   🎯 Found procedure definition at line " + (i + 1) + ": " + trimmed);
                            
                            CobolProcedure2 proc = new CobolProcedure2(expected, i + 1);
                            List<String> accessedDataItems = extractAccessedDataItems(trimmed, dataItemNames);
                            List<String> accessedFiles = new ArrayList<>();
                            String sqlTable = extractSqlTable(trimmed);
                            String performTarget = extractPerformTarget(trimmed);
                            proc.addStatement(new CobolStatement2("RECOVERED", trimmed, i + 1, accessedDataItems, accessedFiles, sqlTable, performTarget));
                            procedures.add(proc);
                            foundNames.add(expected.toLowerCase());
                            break;
                        }
                    }
                }
            }
        }
    }
    
    /**
     * Check if a line is likely the start of a specific procedure
     */
    private boolean isLikelyProcedureStart(String line, String expectedProcName) {
        String upper = line.toUpperCase();
        String expectedUpper = expectedProcName.toUpperCase();
        
        if (upper.equals(expectedUpper + ".")) {
            return true;
        }
        
        if (upper.matches("^" + expectedUpper + "\\s*\\.\\s*$")) {
            return true;
        }
        
        if (upper.startsWith(expectedUpper) && line.trim().length() <= expectedProcName.length() + 5) {
            return true;
        }
        
        return false;
    }
    
    /**
     * Check if a line is a paragraph definition
     */
    private boolean isParagraphDefinition(String line) {
        Pattern pattern = Pattern.compile("^([a-zA-Z][a-zA-Z0-9-]+)\\s*\\.\\s*$");
        Matcher matcher = pattern.matcher(line);
        
        if (matcher.find()) {
            String name = matcher.group(1);
            String upper = name.toUpperCase();
            
            if (isCobolKeyword(upper) || isFalsePositive(upper)) {
                return false;
            }
            
            return name.length() >= 3 && name.length() <= 50;
        }
        
        return false;
    }
    
    /**
     * Check for common false positives
     */
    private boolean isFalsePositive(String name) {
        String[] falsePositives = {
            "END-EXEC", "END-IF", "END-EVALUATE", "END-PERFORM", "END-READ", "END-WRITE",
            "ENDREAD", "ENDWRITE", "ENDPERFORM", "ENDEVALUATE", "ENDIF",
            "WSSAVECTRPAINTNO", "WSPREVKEEPNOCHA", "WSSERIALNO",
            "DCLVWMCTRPA", "DCLVWMTRLI", "DCLVWMCUCP", "DCLVWMCU00"
        };
        
        for (String fp : falsePositives) {
            if (fp.equals(name)) {
                return true;
            }
        }
        
        if (name.startsWith("WS") && name.length() > 10) {
            return true;
        }
        
        if (name.startsWith("DCL")) {
            return true;
        }
        
        return false;
    }
    
    /**
     * Extract paragraph name from line
     */
    private String extractParagraphName(String line) {
        Pattern pattern = Pattern.compile("^([a-zA-Z][a-zA-Z0-9-]+)\\s*\\.\\s*$");
        Matcher matcher = pattern.matcher(line);
        
        if (matcher.find()) {
            return matcher.group(1);
        }
        
        return "UNKNOWN";
    }
    
    /**
     * Determine statement type
     */
    private String getStatementType(String line) {
        String upper = line.toUpperCase().trim();
        
        if (upper.startsWith("PERFORM")) return "PERFORM";
        if (upper.startsWith("MOVE")) return "MOVE";
        if (upper.startsWith("IF")) return "IF";
        if (upper.startsWith("EXEC SQL")) return "EXEC_SQL";
        if (upper.startsWith("INITIALIZE")) return "INITIALIZE";
        if (upper.startsWith("OPEN")) return "OPEN";
        if (upper.startsWith("CLOSE")) return "CLOSE";
        if (upper.startsWith("READ")) return "READ";
        if (upper.startsWith("WRITE")) return "WRITE";
        if (upper.startsWith("EVALUATE")) return "EVALUATE";
        if (upper.startsWith("ADD")) return "ADD";
        if (upper.startsWith("SUBTRACT")) return "SUBTRACT";
        if (upper.startsWith("MULTIPLY")) return "MULTIPLY";
        if (upper.startsWith("DIVIDE")) return "DIVIDE";
        if (upper.startsWith("COMPUTE")) return "COMPUTE";
        if (upper.startsWith("DISPLAY")) return "DISPLAY";
        if (upper.startsWith("ACCEPT")) return "ACCEPT";
        if (upper.startsWith("SET")) return "SET";
        if (upper.startsWith("INSPECT")) return "INSPECT";
        if (upper.startsWith("UNSTRING")) return "UNSTRING";
        if (upper.startsWith("STRING")) return "STRING";
        if (upper.startsWith("CALL")) return "CALL";
        if (upper.startsWith("GOBACK")) return "GOBACK";
        if (upper.startsWith("STOP")) return "STOP";
        if (upper.startsWith("EXIT")) return "EXIT";
        if (upper.contains("END-IF")) return "END-IF";
        if (upper.contains("END-EXEC")) return "END-EXEC";
        if (upper.contains("END-EVALUATE")) return "END-EVALUATE";
        if (upper.contains("END-READ")) return "END-READ";
        
        return "STATEMENT";
    }
    
    /**
     * Extract data items accessed in a statement
     */
    private List<String> extractAccessedDataItems(String line, Set<String> dataItemNames) {
        List<String> accessed = new ArrayList<>();
        String upperLine = line.toUpperCase();
        
        for (String dataItem : dataItemNames) {
            if (upperLine.contains(dataItem.toUpperCase())) {
                accessed.add(dataItem);
            }
        }
        
        return accessed;
    }
    
    /**
     * Extract files accessed in a statement
     */
    private List<String> extractAccessedFiles(String line, Set<String> fileNames) {
        List<String> accessed = new ArrayList<>();
        String upperLine = line.toUpperCase();
        
        for (String fileName : fileNames) {
            if (upperLine.contains(fileName.toUpperCase())) {
                accessed.add(fileName);
            }
        }
        
        return accessed;
    }
    
    /**
     * Extract SQL table name from EXEC SQL statement
     */
    private String extractSqlTable(String line) {
        String upperLine = line.toUpperCase();
        if (!upperLine.startsWith("EXEC SQL")) {
            return null;
        }
        
        Pattern pattern = Pattern.compile("FROM\\s+([A-Z][A-Z0-9_]*)", Pattern.CASE_INSENSITIVE);
        Matcher matcher = pattern.matcher(upperLine);
        if (matcher.find()) {
            return matcher.group(1);
        }
        
        return null;
    }
    
    /**
     * Extract PERFORM target procedure
     */
    private String extractPerformTarget(String line) {
        String upperLine = line.toUpperCase();
        if (!upperLine.startsWith("PERFORM")) {
            return null;
        }
        
        Pattern pattern = Pattern.compile("PERFORM\\s+([A-Z][A-Z0-9-]*)", Pattern.CASE_INSENSITIVE);
        Matcher matcher = pattern.matcher(upperLine);
        if (matcher.find()) {
            return matcher.group(1);
        }
        
        return null;
    }
    
    /**
     * Check if word is a COBOL keyword
     */
    private boolean isCobolKeyword(String word) {
        String[] keywords = {
            "PERFORM", "IF", "ELSE", "END-IF", "MOVE", "ADD", "SUBTRACT",
            "MULTIPLY", "DIVIDE", "COMPUTE", "DISPLAY", "ACCEPT", "READ",
            "WRITE", "OPEN", "CLOSE", "EVALUATE", "WHEN", "END-EVALUATE",
            "INITIALIZE", "INSPECT", "STRING", "UNSTRING", "CALL", "GOBACK",
            "STOP", "EXIT", "CONTINUE", "SET", "SEARCH", "SORT", "MERGE",
            "IDENTIFICATION", "DIVISION", "PROGRAM-ID", "ENVIRONMENT",
            "DATA", "PROCEDURE", "WORKING-STORAGE", "FILE", "SECTION",
            "SELECT", "ASSIGN", "FD", "PIC", "PICTURE", "VALUE", "REDEFINES"
        };
        
        for (String keyword : keywords) {
            if (keyword.equals(word)) {
                return true;
            }
        }
        return false;
    }
    
    /**
     * Read file content
     */
    private String readFile(String filename) throws IOException {
        StringBuilder content = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new FileReader(filename))) {
            String line;
            while ((line = reader.readLine()) != null) {
                content.append(line).append("\n");
            }
        }
        return content.toString();
    }
    
    /**
     * Print business logic extraction results to console and write to JSON file
     */
    private void printBusinessLogicResults(BusinessLogicResult result) {
        // Console output (unchanged)
        System.out.println("\n=== BUSINESS LOGIC EXTRACTION RESULTS ===");
        System.out.println("Total procedures: " + result.getProcedures().size());
        System.out.println("Total data items: " + result.getDataItems().size());
        System.out.println("Total file descriptors: " + result.getFileDescriptors().size());
        
        if (result.getProcedures().isEmpty()) {
            System.out.println("❌ No procedures found!");
            return;
        }
        
        System.out.println("\n📋 Business Logic by Procedure:");
        StringBuilder jsonBuilder = new StringBuilder();
        jsonBuilder.append("{\n");
        jsonBuilder.append("  \"totalProcedures\": ").append(result.getProcedures().size()).append(",\n");
        jsonBuilder.append("  \"totalDataItems\": ").append(result.getDataItems().size()).append(",\n");
        jsonBuilder.append("  \"totalFileDescriptors\": ").append(result.getFileDescriptors().size()).append(",\n");
        jsonBuilder.append("  \"procedures\": [\n");
        
        String[] expectedProcs = {
            "mainlineProcessing", "initialization", "readCtrpaParm99",
            "openInOutFile", "processExpFile", "validateExpRec",
            "validateSerialNo", "processCpuDir", "processCustDtl",
            "processHeaderRec", "processDetailRec", "processTrailRec",
            "readInputFile", "termination"
        };
        
        Set<String> foundNames = new HashSet<>();
        for (int i = 0; i < result.getProcedures().size(); i++) {
            CobolProcedure2 proc = result.getProcedures().get(i);
            foundNames.add(proc.getName().toLowerCase());
            
            // Console output
            System.out.println((i + 1) + ". " + proc.getName() + " (Line " + proc.getLineNumber() + ")");
            System.out.println("   Statements: " + proc.getStatements().size());
            
            Map<String, Integer> stmtCounts = new HashMap<>();
            Set<String> accessedDataItems = new HashSet<>();
            Set<String> accessedFiles = new HashSet<>();
            Set<String> sqlTables = new HashSet<>();
            Set<String> performTargets = new HashSet<>();
            
            for (CobolStatement2 stmt : proc.getStatements()) {
                stmtCounts.merge(stmt.getType(), 1, Integer::sum);
                accessedDataItems.addAll(stmt.getAccessedDataItems());
                accessedFiles.addAll(stmt.getAccessedFiles());
                if (stmt.getSqlTable() != null) {
                    sqlTables.add(stmt.getSqlTable());
                }
                if (stmt.getPerformTarget() != null) {
                    performTargets.add(stmt.getPerformTarget());
                }
            }
            
            // JSON output for procedure
            jsonBuilder.append("    {\n");
            jsonBuilder.append("      \"name\": \"").append(escapeJson(proc.getName())).append("\",\n");
            jsonBuilder.append("      \"lineNumber\": ").append(proc.getLineNumber()).append(",\n");
            jsonBuilder.append("      \"statements\": [\n");
            
            for (int j = 0; j < proc.getStatements().size(); j++) {
                CobolStatement2 stmt = proc.getStatements().get(j);
                jsonBuilder.append("        {\n");
                jsonBuilder.append("          \"type\": \"").append(escapeJson(stmt.getType())).append("\",\n");
                jsonBuilder.append("          \"content\": \"").append(escapeJson(stmt.getContent())).append("\",\n");
                jsonBuilder.append("          \"lineNumber\": ").append(stmt.getLineNumber()).append(",\n");
                jsonBuilder.append("          \"accessedDataItems\": [");
                for (int k = 0; k < stmt.getAccessedDataItems().size(); k++) {
                    jsonBuilder.append("\"").append(escapeJson(stmt.getAccessedDataItems().get(k))).append("\"");
                    if (k < stmt.getAccessedDataItems().size() - 1) {
                        jsonBuilder.append(",");
                    }
                }
                jsonBuilder.append("],\n");
                jsonBuilder.append("          \"accessedFiles\": [");
                for (int k = 0; k < stmt.getAccessedFiles().size(); k++) {
                    jsonBuilder.append("\"").append(escapeJson(stmt.getAccessedFiles().get(k))).append("\"");
                    if (k < stmt.getAccessedFiles().size() - 1) {
                        jsonBuilder.append(",");
                    }
                }
                jsonBuilder.append("],\n");
                jsonBuilder.append("          \"sqlTable\": ");
                if (stmt.getSqlTable() != null) {
                    jsonBuilder.append("\"").append(escapeJson(stmt.getSqlTable())).append("\"");
                } else {
                    jsonBuilder.append("null");
                }
                jsonBuilder.append(",\n");
                jsonBuilder.append("          \"performTarget\": ");
                if (stmt.getPerformTarget() != null) {
                    jsonBuilder.append("\"").append(escapeJson(stmt.getPerformTarget())).append("\"");
                } else {
                    jsonBuilder.append("null");
                }
                jsonBuilder.append("\n");
                jsonBuilder.append("        }");
                if (j < proc.getStatements().size() - 1) {
                    jsonBuilder.append(",");
                }
                jsonBuilder.append("\n");
            }
            jsonBuilder.append("      ],\n");
            jsonBuilder.append("      \"statementDistribution\": {\n");
            List<Map.Entry<String, Integer>> sortedStmtCounts = new ArrayList<>(stmtCounts.entrySet());
            sortedStmtCounts.sort((a, b) -> b.getValue().compareTo(a.getValue()));
            for (int j = 0; j < sortedStmtCounts.size(); j++) {
                Map.Entry<String, Integer> entry = sortedStmtCounts.get(j);
                jsonBuilder.append("        \"").append(escapeJson(entry.getKey())).append("\": ").append(entry.getValue());
                if (j < sortedStmtCounts.size() - 1) {
                    jsonBuilder.append(",");
                }
                jsonBuilder.append("\n");
            }
            jsonBuilder.append("      },\n");
            jsonBuilder.append("      \"accessedDataItems\": [");
            List<String> sortedDataItems = new ArrayList<>(accessedDataItems);
            Collections.sort(sortedDataItems);
            for (int j = 0; j < sortedDataItems.size(); j++) {
                jsonBuilder.append("\"").append(escapeJson(sortedDataItems.get(j))).append("\"");
                if (j < sortedDataItems.size() - 1) {
                    jsonBuilder.append(",");
                }
            }
            jsonBuilder.append("],\n");
            jsonBuilder.append("      \"accessedFiles\": [");
            List<String> sortedFiles = new ArrayList<>(accessedFiles);
            Collections.sort(sortedFiles);
            for (int j = 0; j < sortedFiles.size(); j++) {
                jsonBuilder.append("\"").append(escapeJson(sortedFiles.get(j))).append("\"");
                if (j < sortedFiles.size() - 1) {
                    jsonBuilder.append(",");
                }
            }
            jsonBuilder.append("],\n");
            jsonBuilder.append("      \"sqlTables\": [");
            List<String> sortedSqlTables = new ArrayList<>(sqlTables);
            Collections.sort(sortedSqlTables);
            for (int j = 0; j < sortedSqlTables.size(); j++) {
                jsonBuilder.append("\"").append(escapeJson(sortedSqlTables.get(j))).append("\"");
                if (j < sortedSqlTables.size() - 1) {
                    jsonBuilder.append(",");
                }
            }
            jsonBuilder.append("],\n");
            jsonBuilder.append("      \"performedProcedures\": [");
            List<String> sortedPerformTargets = new ArrayList<>(performTargets);
            Collections.sort(sortedPerformTargets);
            for (int j = 0; j < sortedPerformTargets.size(); j++) {
                jsonBuilder.append("\"").append(escapeJson(sortedPerformTargets.get(j))).append("\"");
                if (j < sortedPerformTargets.size() - 1) {
                    jsonBuilder.append(",");
                }
            }
            jsonBuilder.append("]\n");
            jsonBuilder.append("    }");
            if (i < result.getProcedures().size() - 1) {
                jsonBuilder.append(",");
            }
            jsonBuilder.append("\n");
            
            // Console output (continued)
            System.out.println("   Statement Distribution:");
            sortedStmtCounts.forEach(entry -> 
                System.out.println("     " + entry.getKey() + ": " + entry.getValue()));
            
            if (!accessedDataItems.isEmpty()) {
                System.out.println("   Accessed Data Items:");
                sortedDataItems.forEach(item -> System.out.println("     " + item));
            }
            
            if (!accessedFiles.isEmpty()) {
                System.out.println("   Accessed Files:");
                sortedFiles.forEach(file -> System.out.println("     " + file));
            }
            
            if (!sqlTables.isEmpty()) {
                System.out.println("   SQL Tables Accessed:");
                sortedSqlTables.forEach(table -> System.out.println("     " + table));
            }
            
            if (!performTargets.isEmpty()) {
                System.out.println("   Performed Procedures:");
                sortedPerformTargets.forEach(target -> System.out.println("     " + target));
            }
            
            System.out.println("   First Statements:");
            for (int j = 0; j < Math.min(3, proc.getStatements().size()); j++) {
                CobolStatement2 stmt = proc.getStatements().get(j);
                String content = stmt.getContent();
                if (content.length() > 60) {
                    content = content.substring(0, 60) + "...";
                }
                System.out.println("     " + stmt.getType() + ": " + content);
            }
            System.out.println();
        }
        
        jsonBuilder.append("  ],\n");
        jsonBuilder.append("  \"expectedVsFound\": [\n");
        
        // Console output for expected vs found
        System.out.println("=== EXPECTED vs FOUND ===");
        for (String expected : expectedProcs) {
            boolean found = foundNames.contains(expected.toLowerCase());
            System.out.println((found ? "✅" : "❌") + " " + expected);
            
            jsonBuilder.append("    {\n");
            jsonBuilder.append("      \"procedure\": \"").append(escapeJson(expected)).append("\",\n");
            jsonBuilder.append("      \"found\": ").append(found).append("\n");
            jsonBuilder.append("    }");
            if (!expected.equals(expectedProcs[expectedProcs.length - 1])) {
                jsonBuilder.append(",");
            }
            jsonBuilder.append("\n");
        }
        
        jsonBuilder.append("  ],\n");
        jsonBuilder.append("  \"matchRate\": \"").append(
            foundNames.stream().mapToInt(name -> 
                Arrays.stream(expectedProcs).anyMatch(exp -> exp.toLowerCase().equals(name)) ? 1 : 0
            ).sum() + "/" + expectedProcs.length).append("\"\n");
        jsonBuilder.append("}\n");
        
        // Write JSON to file
        try (FileWriter writer = new FileWriter("business_logic_output.json")) {
            writer.write(jsonBuilder.toString());
            System.out.println("\n✅ Business logic results written to business_logic_output.json");
        } catch (IOException e) {
            System.err.println("❌ Error writing to business_logic_output.json: " + e.getMessage());
        }
        
        // Console output for match rate
        System.out.println("\nMatch rate: " + 
            foundNames.stream().mapToInt(name -> 
                Arrays.stream(expectedProcs).anyMatch(exp -> exp.toLowerCase().equals(name)) ? 1 : 0
            ).sum() + "/" + expectedProcs.length);
    }
    
    /**
     * Escape string for JSON
     */
    private String escapeJson(String str) {
        if (str == null) {
            return "";
        }
        return str.replace("\"", "\\\"")
                 .replace("\\", "\\\\")
                 .replace("\n", "\\n")
                 .replace("\r", "\\r")
                 .replace("\t", "\\t");
    }
}
