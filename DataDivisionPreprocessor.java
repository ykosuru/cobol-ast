/**
 * COBOL Data Division Preprocessor
 * Handles DATA DIVISION, WORKING-STORAGE, FILE SECTION, etc.
 * before grammar parsing to reduce parse warnings and improve accuracy
 * Author: Yekesa Kosuru
 */

import java.util.*;
import java.util.regex.Pattern;
import java.util.regex.Matcher;
import java.io.*;

public class DataDivisionPreprocessor {
    
    private ParserConfiguration config;
    private List<StructuralDataItemV2> dataItems = new ArrayList<>();
    private List<FileDescriptor> fileDescriptors = new ArrayList<>();
    private List<String> preprocessWarnings = new ArrayList<>();
    
    // Division boundaries
    private static final Pattern DATA_DIVISION = Pattern.compile("\\s*DATA\\s+DIVISION\\s*\\.", Pattern.CASE_INSENSITIVE);
    private static final Pattern PROCEDURE_DIVISION = Pattern.compile("\\s*PROCEDURE\\s+DIVISION", Pattern.CASE_INSENSITIVE);
    private static final Pattern WORKING_STORAGE = Pattern.compile("\\s*WORKING-STORAGE\\s+SECTION\\s*\\.", Pattern.CASE_INSENSITIVE);
    private static final Pattern FILE_SECTION = Pattern.compile("\\s*FILE\\s+SECTION\\s*\\.", Pattern.CASE_INSENSITIVE);
    private static final Pattern LINKAGE_SECTION = Pattern.compile("\\s*LINKAGE\\s+SECTION\\s*\\.", Pattern.CASE_INSENSITIVE);
    
    // Data item patterns
    private static final Pattern LEVEL_NUMBER = Pattern.compile("^\\s*(\\d{1,2})\\s+(.*)$");
    private static final Pattern FD_RECORD = Pattern.compile("^\\s*FD\\s+([A-Za-z][A-Za-z0-9-_]*)\\s*.*$", Pattern.CASE_INSENSITIVE);
    private static final Pattern CONDITION_NAME = Pattern.compile("^\\s*88\\s+([A-Za-z][A-Za-z0-9-_]*)\\s+.*$", Pattern.CASE_INSENSITIVE);
    
    public DataDivisionPreprocessor(ParserConfiguration config) {
        this.config = config;
    }
    
    /**
     * Main preprocessing method
     */
    public PreprocessingResult preprocessDataDivisions(String[] sourceLines) {
        List<String> cleanedLines = new ArrayList<>();
        DataDivisionContext context = new DataDivisionContext();
        
        for (int i = 0; i < sourceLines.length; i++) {
            String line = sourceLines[i];
            String trimmed = line.trim();
            
            // Update context based on current line
            updateContext(context, trimmed, i);
            
            if (context.isInDataDivision()) {
                // Process data division line
                processDataDivisionLine(line, i, context);
                
                // Replace with comment or empty line for grammar parser
                cleanedLines.add(createCleanedDataLine(line, context));
            } else {
                // Keep non-data division lines as-is
                cleanedLines.add(line);
            }
        }
        
        return new PreprocessingResult(
            cleanedLines.toArray(new String[0]),
            dataItems,
            fileDescriptors,
            preprocessWarnings
        );
    }
    
    /**
     * Update parsing context based on current line
     */
    private void updateContext(DataDivisionContext context, String trimmed, int lineNumber) {
        String upper = trimmed.toUpperCase();
        
        // Check for division boundaries
        if (DATA_DIVISION.matcher(upper).matches()) {
            context.enterDataDivision(lineNumber);
            if (config.isVerboseLogging()) {
                System.out.println("📊 Entering DATA DIVISION at line " + (lineNumber + 1));
            }
        } else if (PROCEDURE_DIVISION.matcher(upper).find()) {
            context.exitDataDivision(lineNumber);
            if (config.isVerboseLogging()) {
                System.out.println("📊 Exiting DATA DIVISION at line " + (lineNumber + 1));
            }
        }
        
        // Check for section boundaries within DATA DIVISION
        if (context.isInDataDivision()) {
            if (WORKING_STORAGE.matcher(upper).matches()) {
                context.enterSection("WORKING-STORAGE", lineNumber);
            } else if (FILE_SECTION.matcher(upper).matches()) {
                context.enterSection("FILE", lineNumber);
            } else if (LINKAGE_SECTION.matcher(upper).matches()) {
                context.enterSection("LINKAGE", lineNumber);
            }
        }
    }
    
    /**
     * Process a line within DATA DIVISION
     */
    private void processDataDivisionLine(String line, int lineNumber, DataDivisionContext context) {
        String trimmed = line.trim();
        
        if (trimmed.isEmpty() || isComment(trimmed)) {
            return;
        }
        
        try {
            // Handle FD records
            Matcher fdMatcher = FD_RECORD.matcher(trimmed);
            if (fdMatcher.matches()) {
                processFileDescriptor(fdMatcher.group(1), line, lineNumber);
                return;
            }
            
            // Handle level numbers (01, 05, 10, 88, etc.)
            Matcher levelMatcher = LEVEL_NUMBER.matcher(trimmed);
            if (levelMatcher.matches()) {
                int level = Integer.parseInt(levelMatcher.group(1));
                String remainder = levelMatcher.group(2).trim();
                
                processDataItem(level, remainder, line, lineNumber, context);
                return;
            }
            
            // Handle EXEC SQL INCLUDE statements in DATA DIVISION
            if (trimmed.toUpperCase().startsWith("EXEC SQL INCLUDE")) {
                processSqlInclude(trimmed, lineNumber);
                return;
            }
            
            // Handle continuation lines
            if (isDataContinuation(trimmed)) {
                processDataContinuation(trimmed, lineNumber, context);
                return;
            }
            
        } catch (Exception e) {
            preprocessWarnings.add("Failed to process DATA DIVISION line " + 
                                 (lineNumber + 1) + ": " + e.getMessage());
        }
    }
    
    /**
     * Process a data item (level 01-49)
     */
    private void processDataItem(int level, String remainder, String fullLine, 
                                int lineNumber, DataDivisionContext context) {
        
        if (level == 88) {
            // Condition name
            Matcher condMatcher = CONDITION_NAME.matcher(fullLine);
            if (condMatcher.matches()) {
                String conditionName = condMatcher.group(1);
                createConditionName(conditionName, fullLine, lineNumber, context);
            }
            return;
        }
        
        // Parse data item components
        DataItemParser parser = new DataItemParser(remainder);
        DataItemComponents components = parser.parse();
        
        if (components.name != null) {
            StructuralDataItemV2 dataItem = new StructuralDataItemV2();
            dataItem.setName(components.name);
            dataItem.setLevel(level);
            dataItem.setLineNumber(lineNumber + 1);
            dataItem.setSection(context.getCurrentSection());
            dataItem.setPicture(components.picture);
            dataItem.setUsage(components.usage);
            dataItem.setValue(components.value);
            dataItem.setOccurs(components.occurs);
            dataItem.setRedefines(components.redefines);
            
            dataItems.add(dataItem);
            
            if (config.isVerboseLogging()) {
                System.out.println("    📝 Data item: " + level + " " + components.name + 
                                 (components.picture != null ? " PIC " + components.picture : ""));
            }
        }
    }
    
    /**
     * Process file descriptor
     */
    private void processFileDescriptor(String fileName, String fullLine, int lineNumber) {
        FileDescriptor fd = new FileDescriptor();
        fd.setName(fileName);
        fd.setLineNumber(lineNumber + 1);
        fd.setDefinition(fullLine.trim());
        
        fileDescriptors.add(fd);
        
        if (config.isVerboseLogging()) {
            System.out.println("    📁 File descriptor: " + fileName);
        }
    }
    
    /**
     * Create cleaned line for grammar parser
     */
    private String createCleanedDataLine(String originalLine, DataDivisionContext context) {
        String trimmed = originalLine.trim();
        
        // Preserve section headers for grammar parser
        if (WORKING_STORAGE.matcher(trimmed.toUpperCase()).matches() ||
            FILE_SECTION.matcher(trimmed.toUpperCase()).matches() ||
            LINKAGE_SECTION.matcher(trimmed.toUpperCase()).matches() ||
            DATA_DIVISION.matcher(trimmed.toUpperCase()).matches()) {
            return originalLine;
        }
        
        // Replace data items with comments to preserve line numbers
        if (!trimmed.isEmpty() && !isComment(trimmed)) {
            // Preserve indentation and replace content with comment
            String indent = originalLine.substring(0, originalLine.indexOf(originalLine.trim()));
            return indent + "*> DATA-ITEM: " + trimmed.substring(0, Math.min(60, trimmed.length()));
        }
        
        return originalLine; // Keep empty lines and comments as-is
    }
    
    /**
     * Check if line is a comment
     */
    private boolean isComment(String line) {
        return line.startsWith("*") || line.startsWith("*>") || 
               line.startsWith("//") || line.startsWith("/*");
    }
    
    /**
     * Check if line is a data item continuation
     */
    private boolean isDataContinuation(String line) {
        // Common continuation patterns in COBOL data items
        String upper = line.toUpperCase();
        return upper.matches("\\s*(PIC|PICTURE|VALUE|OCCURS|REDEFINES|USAGE|COMP|BINARY|PACKED-DECIMAL).*") ||
               upper.matches("\\s*(DISPLAY|COMPUTATIONAL|COMP-[0-9]|SYNCHRONIZED|SYNC).*") ||
               line.matches("\\s*['\"].*['\"].*"); // String literals
    }
    
    /**
     * Data item parser for complex data definitions
     */
    private static class DataItemParser {
        private String input;
        private int position;
        
        public DataItemParser(String input) {
            this.input = input.trim();
            this.position = 0;
        }
        
        public DataItemComponents parse() {
            DataItemComponents components = new DataItemComponents();
            
            // Extract name (first word that's not a keyword)
            components.name = extractName();
            
            // Extract clauses
            while (position < input.length()) {
                skipWhitespace();
                if (position >= input.length()) break;
                
                String remaining = input.substring(position).toUpperCase();
                
                if (remaining.startsWith("PIC ") || remaining.startsWith("PICTURE ")) {
                    components.picture = extractPicture();
                } else if (remaining.startsWith("VALUE ")) {
                    components.value = extractValue();
                } else if (remaining.startsWith("OCCURS ")) {
                    components.occurs = extractOccurs();
                } else if (remaining.startsWith("REDEFINES ")) {
                    components.redefines = extractRedefines();
                } else if (remaining.startsWith("USAGE ") || remaining.matches("(COMP|BINARY|DISPLAY|PACKED-DECIMAL).*")) {
                    components.usage = extractUsage();
                } else {
                    // Skip unknown clause
                    skipToNextClause();
                }
            }
            
            return components;
        }
        
        private String extractName() {
            skipWhitespace();
            int start = position;
            while (position < input.length() && 
                   (Character.isLetterOrDigit(input.charAt(position)) || 
                    input.charAt(position) == '-' || input.charAt(position) == '_')) {
                position++;
            }
            return position > start ? input.substring(start, position) : null;
        }
        
        private String extractPicture() {
            skipKeyword("PIC");
            if (!skipKeyword("PICTURE")) {
                skipKeyword("PIC");
            }
            skipWhitespace();
            
            int start = position;
            // Picture can be complex: X(10), S9(5)V99, etc.
            while (position < input.length() && input.charAt(position) != ' ') {
                if (input.charAt(position) == '(') {
                    // Skip parentheses content
                    int parenCount = 1;
                    position++;
                    while (position < input.length() && parenCount > 0) {
                        if (input.charAt(position) == '(') parenCount++;
                        else if (input.charAt(position) == ')') parenCount--;
                        position++;
                    }
                } else {
                    position++;
                }
            }
            
            return position > start ? input.substring(start, position).trim() : null;
        }
        
        private String extractValue() {
            skipKeyword("VALUE");
            skipWhitespace();
            
            int start = position;
            if (position < input.length() && 
                (input.charAt(position) == '\'' || input.charAt(position) == '"')) {
                // Quoted string
                char quote = input.charAt(position++);
                while (position < input.length() && input.charAt(position) != quote) {
                    position++;
                }
                if (position < input.length()) position++; // Skip closing quote
            } else {
                // Unquoted value
                while (position < input.length() && input.charAt(position) != ' ' && input.charAt(position) != '.') {
                    position++;
                }
            }
            
            return position > start ? input.substring(start, position).trim() : null;
        }
        
        private String extractOccurs() {
            skipKeyword("OCCURS");
            skipWhitespace();
            
            int start = position;
            while (position < input.length() && Character.isDigit(input.charAt(position))) {
                position++;
            }
            
            return position > start ? input.substring(start, position) : null;
        }
        
        private String extractRedefines() {
            skipKeyword("REDEFINES");
            skipWhitespace();
            return extractName();
        }
        
        private String extractUsage() {
            int start = position;
            String remaining = input.substring(position).toUpperCase();
            
            if (remaining.startsWith("USAGE ")) {
                skipKeyword("USAGE");
                skipWhitespace();
                start = position;
            }
            
            // Extract usage type
            String[] usageTypes = {"COMPUTATIONAL", "COMP", "COMP-1", "COMP-2", "COMP-3", 
                                 "BINARY", "DISPLAY", "PACKED-DECIMAL"};
            
            for (String usage : usageTypes) {
                if (remaining.startsWith(usage)) {
                    position += usage.length();
                    return usage;
                }
            }
            
            return null;
        }
        
        private void skipWhitespace() {
            while (position < input.length() && Character.isWhitespace(input.charAt(position))) {
                position++;
            }
        }
        
        private boolean skipKeyword(String keyword) {
            skipWhitespace();
            if (position + keyword.length() <= input.length() &&
                input.substring(position, position + keyword.length()).equalsIgnoreCase(keyword)) {
                position += keyword.length();
                return true;
            }
            return false;
        }
        
        private void skipToNextClause() {
            while (position < input.length() && input.charAt(position) != ' ') {
                position++;
            }
        }
    }
    
    /**
     * Process SQL INCLUDE statements
     */
    private void processSqlInclude(String line, int lineNumber) {
        String include = line.trim();
        if (config.isVerboseLogging()) {
            System.out.println("    🗄️  SQL Include: " + include);
        }
        // Could expand copybook analysis here
    }
    
    /**
     * Process data continuation lines
     */
    private void processDataContinuation(String line, int lineNumber, DataDivisionContext context) {
        // Handle continuation of previous data item
        if (config.isVerboseLogging()) {
            System.out.println("    ↳ Continuation: " + line.trim());
        }
    }
    
    /**
     * Create condition name (88 level)
     */
    private void createConditionName(String name, String fullLine, int lineNumber, DataDivisionContext context) {
        StructuralDataItemV2 conditionName = new StructuralDataItemV2();
        conditionName.setName(name);
        conditionName.setLevel(88);
        conditionName.setLineNumber(lineNumber + 1);
        conditionName.setSection(context.getCurrentSection());
        conditionName.setType("CONDITION");
        
        dataItems.add(conditionName);
        
        if (config.isVerboseLogging()) {
            System.out.println("    🎯 Condition: 88 " + name);
        }
    }
    
    // Supporting classes
    
    /**
     * Context tracker for DATA DIVISION parsing
     */
    private static class DataDivisionContext {
        private boolean inDataDivision = false;
        private String currentSection = null;
        private int dataDivisionStartLine = -1;
        
        public void enterDataDivision(int lineNumber) {
            this.inDataDivision = true;
            this.dataDivisionStartLine = lineNumber;
        }
        
        public void exitDataDivision(int lineNumber) {
            this.inDataDivision = false;
            this.currentSection = null;
        }
        
        public void enterSection(String sectionName, int lineNumber) {
            this.currentSection = sectionName;
        }
        
        public boolean isInDataDivision() { return inDataDivision; }
        public String getCurrentSection() { return currentSection; }
        public int getDataDivisionStartLine() { return dataDivisionStartLine; }
    }
    
    /**
     * Data item components
     */
    private static class DataItemComponents {
        String name;
        String picture;
        String value;
        String occurs;
        String redefines;
        String usage;
    }
    
    /**
     * File descriptor
     */
    public static class FileDescriptor {
        private String name;
        private int lineNumber;
        private String definition;
        
        // Getters and setters
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public int getLineNumber() { return lineNumber; }
        public void setLineNumber(int lineNumber) { this.lineNumber = lineNumber; }
        public String getDefinition() { return definition; }
        public void setDefinition(String definition) { this.definition = definition; }
    }
    
    /**
     * Preprocessing result
     */
    public static class PreprocessingResult {
        private final String[] cleanedSource;
        private final List<StructuralDataItemV2> dataItems;
        private final List<FileDescriptor> fileDescriptors;
        private final List<String> warnings;
        
        public PreprocessingResult(String[] cleanedSource, 
                                 List<StructuralDataItemV2> dataItems,
                                 List<FileDescriptor> fileDescriptors,
                                 List<String> warnings) {
            this.cleanedSource = cleanedSource;
            this.dataItems = dataItems;
            this.fileDescriptors = fileDescriptors;
            this.warnings = warnings;
        }
        
        // Getters
        public String[] getCleanedSource() { return cleanedSource; }
        public List<StructuralDataItemV2> getDataItems() { return dataItems; }
        public List<FileDescriptor> getFileDescriptors() { return fileDescriptors; }
        public List<String> getWarnings() { return warnings; }
    }
}
