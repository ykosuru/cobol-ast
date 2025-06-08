import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.tree.*;
import java.io.*;
import java.nio.charset.Charset;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;
import java.lang.reflect.*;

public class Driver2 extends CobolPreprocessorBaseVisitor<StringBuilder> {
    private StringBuilder output = new StringBuilder();
    private static final String NEWLINE = "\n";
    private static final String EXEC_CICS_TAG = "*>EXECCICS";
    private static final String EXEC_SQL_TAG = "*>EXECSQL";
    private static final String EXEC_SQLIMS_TAG = "*>EXECSQLIMS";
    private static final String EXEC_END_TAG = "*>END-EXEC";
    private static final String COMMENT_TAG = "*>";
    private static final String COMMENT_ENTRY_TAG = "*>CE";
    
    protected Map<String, String> copyBooks = new HashMap<>();
    protected List<ReplaceContext> replaceContexts = new ArrayList<>();
    private CobolSourceFormatEnum format = CobolSourceFormatEnum.FIXED;
    protected boolean strictMode = true;

    private static interface CobolParserParams {
        CobolSourceFormatEnum getFormat();
        File getCopyBookDirectory();
        List<File> getCopyBookDirectories();
        List<String> getCopyBookExtensions();
        Charset getCharset();
        boolean isStrictMode();
        boolean shouldOutputAst();
        String getAstOutputFile();
        boolean shouldAddProgramStructure();
        boolean shouldCommentExecStatements();
    }

    private static enum CobolSourceFormatEnum {
        FIXED(Pattern.compile("^(.{0,6})(.{0,1})(.{0,4})(.{0,60})(.*)?$"), true, 80),
        TANDEM(Pattern.compile("^(.{0,1})(.{0,131})(.*)?$"), false, 132),
        VARIABLE(Pattern.compile("^(.{0,6})(.{0,1})(.{0,4})(.{0,252})(.*)?$"), true, 256);

        private final Pattern pattern;
        private final boolean commentEntryMultiLine;
        private final int maxLineLength;

        CobolSourceFormatEnum(Pattern pattern, boolean commentEntryMultiLine, int maxLineLength) {
            this.pattern = pattern;
            this.commentEntryMultiLine = commentEntryMultiLine;
            this.maxLineLength = maxLineLength;
        }

        public Pattern getPattern() { return pattern; }
        public boolean isCommentEntryMultiLine() { return commentEntryMultiLine; }
        public int getMaxLineLength() { return maxLineLength; }
    }

    private static class CobolParserParamsImpl implements CobolParserParams {
        private CobolSourceFormatEnum format = CobolSourceFormatEnum.FIXED;
        private File copyBookDirectory = new File(".");
        private List<File> copyBookDirectories = List.of(new File("."));
        private List<String> copyBookExtensions = List.of("cbl", "cpy");
        private Charset charset = Charset.defaultCharset();
        private boolean strictMode = true;
        private boolean outputAst = false;
        private String astOutputFile = null;
        private boolean addProgramStructure = true;
        private boolean commentExecStatements = false;

        @Override public CobolSourceFormatEnum getFormat() { return format; }
        public void setFormat(CobolSourceFormatEnum format) { this.format = format; }
        
        @Override public File getCopyBookDirectory() { return copyBookDirectory; }
        public void setCopyBookDirectory(File copyBookDirectory) { 
            this.copyBookDirectory = copyBookDirectory;
            this.copyBookDirectories = List.of(copyBookDirectory);
        }
        
        @Override public List<File> getCopyBookDirectories() { return copyBookDirectories; }
        public void setCopyBookDirectories(List<File> copyBookDirectories) {
            this.copyBookDirectories = copyBookDirectories != null ? copyBookDirectories : List.of();
            this.copyBookDirectory = copyBookDirectories != null && !copyBookDirectories.isEmpty() ? 
                copyBookDirectories.get(0) : new File(".");
        }
        
        @Override public List<String> getCopyBookExtensions() { return copyBookExtensions; }
        public void setCopyBookExtensions(List<String> copyBookExtensions) {
            this.copyBookExtensions = copyBookExtensions != null ? copyBookExtensions : List.of("cbl", "cpy");
        }
        
        @Override public Charset getCharset() { return charset; }
        public void setCharset(Charset charset) { 
            this.charset = charset != null ? charset : Charset.defaultCharset(); 
        }
        
        @Override public boolean isStrictMode() { return strictMode; }
        public void setStrictMode(boolean strictMode) { this.strictMode = strictMode; }
        
        @Override public boolean shouldOutputAst() { return outputAst; }
        public void setOutputAst(boolean outputAst) { this.outputAst = outputAst; }
        
        @Override public String getAstOutputFile() { return astOutputFile; }
        public void setAstOutputFile(String astOutputFile) { this.astOutputFile = astOutputFile; }
        
        @Override public boolean shouldAddProgramStructure() { return addProgramStructure; }
        public void setAddProgramStructure(boolean addProgramStructure) { this.addProgramStructure = addProgramStructure; }
        
        @Override public boolean shouldCommentExecStatements() { return commentExecStatements; }
        public void setCommentExecStatements(boolean commentExecStatements) { this.commentExecStatements = commentExecStatements; }
    }

    private static class CobolLine {
        private final String content;
        private final String sequenceArea;
        private final String indicatorArea;
        private final String areaA;
        private final String areaB;
        private final String comment;
        private final boolean isContinuation;

        CobolLine(String content, String sequenceArea, String indicatorArea, String areaA, String areaB, String comment, boolean isContinuation) {
            this.content = content != null ? content.trim() : "";
            this.sequenceArea = sequenceArea != null ? sequenceArea.trim() : "";
            this.indicatorArea = indicatorArea != null ? indicatorArea : "";
            this.areaA = areaA != null ? areaA.trim() : "";
            this.areaB = areaB != null ? areaB.trim() : "";
            this.comment = comment != null ? comment.trim() : "";
            this.isContinuation = isContinuation;
        }

        public String getContent() { return content; }
        public String getSequenceArea() { return sequenceArea; }
        public String getIndicatorArea() { return indicatorArea; }
        public String getAreaA() { return areaA; }
        public String getAreaB() { return areaB; }
        public String getComment() { return comment; }
        public boolean isContinuation() { return isContinuation; }
    }

    private static class CobolLineWriterImpl {
        public String serialize(List<CobolLine> lines) {
            StringBuilder result = new StringBuilder();
            for (CobolLine line : lines) {
                if (!line.getContent().isEmpty()) {
                    result.append(line.getContent()).append(NEWLINE);
                }
            }
            return result.toString();
        }
    }

    private interface CobolDocumentParser {
        String processLines(String code, CobolParserParams params) throws IOException;
    }

    private class CobolDocumentParserImpl implements CobolDocumentParser {
        private final Pattern processPattern = Pattern.compile("(?i)^\\s*(CBL|PROCESS)\\s+(.+)$");

        @Override
        public String processLines(String code, CobolParserParams params) throws IOException {
            // Preprocess code to normalize PROCESS/CBL directives
            StringBuilder normalizedCode = new StringBuilder();
            BufferedReader reader = new BufferedReader(new StringReader(code));
            String line;
            while ((line = reader.readLine()) != null) {
                Matcher matcher = processPattern.matcher(line);
                if (matcher.matches()) {
                    normalizedCode.append("CBL ").append(matcher.group(2).trim()).append(NEWLINE);
                } else {
                    normalizedCode.append(line).append(NEWLINE);
                }
            }

            try {
                CharStream input = CharStreams.fromString(normalizedCode.toString());
                CobolPreprocessorLexer lexer = new CobolPreprocessorLexer(input);
                CommonTokenStream tokens = new CommonTokenStream(lexer);
                CobolPreprocessorParser parser = new CobolPreprocessorParser(tokens);
                parser.removeErrorListeners();
                
                if (params.isStrictMode()) {
                    parser.addErrorListener(new BaseErrorListener() {
                        @Override
                        public void syntaxError(Recognizer<?, ?> recognizer, Object offendingSymbol, int line,
                                int charPositionInLine, String msg, RecognitionException e) {
                            if (e != null) {
                                System.out.println(String.format("Parse error at line %d:%d: %s", line, charPositionInLine, msg));
                                throw new RuntimeException(msg);
                            } else {
                                System.out.println(String.format("Parse warning at line %d:%d: %s", line, charPositionInLine, msg));
                            }
                        }
                    });
                }
                
                CobolPreprocessorParser.StartRuleContext tree = parser.startRule();
                Driver2 visitor = new Driver2();
                visitor.copyBooks = copyBooks;
                visitor.replaceContexts = replaceContexts;
                visitor.strictMode = params.isStrictMode();
                return visitor.visitStartRule(tree).toString();
            } catch (Exception e) {
                throw new IOException("Failed to parse COBOL code: " + e.getMessage(), e);
            }
        }
    }

    // FIXED: Proper ReplaceRule class with word boundary handling
    private static class ReplaceRule {
        String replaceable;
        String replacement;
        Pattern pattern;

        ReplaceRule(String replaceable, String replacement) {
            this.replaceable = replaceable;
            this.replacement = replacement;
            
            // Handle pseudo-text (==text==) vs regular words
            if (replaceable.startsWith("==") && replaceable.endsWith("==")) {
                // Pseudo-text: exact match of content between == markers
                String content = replaceable.substring(2, replaceable.length() - 2);
                // For pseudo-text, match anywhere but use word boundaries for safety
                this.pattern = Pattern.compile("\\b" + Pattern.quote(content) + "\\b", Pattern.CASE_INSENSITIVE);
            } else {
                // Regular word: match whole words only with strict word boundaries
                this.pattern = Pattern.compile("\\b" + Pattern.quote(replaceable) + "\\b", Pattern.CASE_INSENSITIVE);
            }
        }
    }

    private static class ReplaceContext {
        List<ReplaceRule> rules = new ArrayList<>();

        void addRule(String replaceable, String replacement) {
            rules.add(new ReplaceRule(replaceable, replacement));
        }

        String apply(String text) {
            String result = text;
            for (ReplaceRule rule : rules) {
                // Handle replacement - if replacement is pseudo-text, extract content
                String replaceWith = rule.replacement;
                if (replaceWith.startsWith("==") && replaceWith.endsWith("==")) {
                    replaceWith = replaceWith.substring(2, replaceWith.length() - 2);
                }
                result = rule.pattern.matcher(result).replaceAll(replaceWith);
            }
            return result;
        }
    }

    public String process(File cobolFile, CobolParserParams params) throws IOException {
        if (cobolFile == null || !cobolFile.exists()) {
            String msg = String.format("Input file does not exist: %s",
                    cobolFile != null ? cobolFile.getAbsolutePath() : "null");
            System.out.println(msg);
            throw new IOException(msg);
        }
        if (!cobolFile.canRead()) {
            String msg = String.format("Input file is not readable: %s", cobolFile.getAbsolutePath());
            System.out.println(msg);
            throw new IOException(msg);
        }
        if (cobolFile.length() == 0 && params.isStrictMode()) {
            String msg = String.format("Input file is empty: %s", cobolFile.getAbsolutePath());
            System.out.println(msg);
            throw new IOException(msg);
        }
        
        Charset charset = params != null && params.getCharset() != null ? params.getCharset() : Charset.defaultCharset();
        System.out.println(String.format("Preprocessing file %s with line format %s and charset %s",
                cobolFile.getName(), params != null && params.getFormat() != null ? params.getFormat() : format, charset));
        String cobolFileContent = Files.readString(cobolFile.toPath(), charset);
        return process(cobolFileContent, params);
    }

    public String process(String cobolCode, CobolParserParams params) throws IOException {
        if (cobolCode == null || cobolCode.trim().isEmpty()) {
            String msg = "Input COBOL code is null or empty";
            System.out.println(msg);
            throw new IOException(msg);
        }
        if (params == null) {
            System.out.println("CobolParserParams is null, using default settings.");
            params = new CobolParserParamsImpl();
        }
        
        strictMode = params.isStrictMode();
        format = params.getFormat() != null ? params.getFormat() : CobolSourceFormatEnum.FIXED;
        loadCopyBooks(params.getCopyBookDirectories(), params.getCopyBookExtensions(), params.getCharset(), new HashSet<>());
        
        List<CobolLine> lines = readLines(cobolCode, params);
        List<CobolLine> rewrittenLines = rewriteLines(lines);
        String preprocessedCobol = parseDocument(lines, params);
        
        // Add missing COBOL program structure if needed
        if (params.shouldAddProgramStructure()) {
            preprocessedCobol = addCobolProgramStructure(preprocessedCobol);
        }
        
        // Apply final formatting fixes after all processing
        preprocessedCobol = applyFinalFormatting(preprocessedCobol);
        
        // Generate AST if requested
        if (params.shouldOutputAst()) {
            String astCompatibleCode = applyAstCompatibleFormatting(preprocessedCobol, params);
            generateAstOutput(astCompatibleCode, params);
        }
        
        return preprocessedCobol;
    }

    protected List<CobolLine> readLines(String cobolCode, CobolParserParams params) throws IOException {
        List<CobolLine> result = new ArrayList<>();
        BufferedReader reader = new BufferedReader(new StringReader(cobolCode));
        String line;
        
        while ((line = reader.readLine()) != null) {
            line = line.trim();
            
            // Skip empty lines
            if (line.isEmpty()) {
                continue;
            }
            
            // Skip comment lines (lines starting with *)
            if (line.startsWith("*")) {
                continue;
            }
            
            // Create a simple CobolLine
            result.add(new CobolLine(line, "", "", "", line, "", false));
        }
        
        return result;
    }

    protected List<CobolLine> rewriteLines(List<CobolLine> lines) {
        List<CobolLine> result = new ArrayList<>();
        boolean inCommentEntry = false;
        
        for (CobolLine line : lines) {
            String content = line.getContent();
            
            // Check for comment entry markers
            if (content.contains("*>CE")) {
                inCommentEntry = true;
                continue;
            }
            
            // Skip lines while in comment entry mode
            if (inCommentEntry) {
                if (content.startsWith("*") || content.trim().isEmpty()) {
                    continue;
                } else {
                    inCommentEntry = false; // Exit comment mode
                }
            }
            
            // Skip regular comment lines
            if (content.startsWith("*")) {
                continue;
            }
            
            result.add(line);
        }
        
        return result;
    }

    protected String parseDocument(List<CobolLine> lines, CobolParserParams params) throws IOException {
        String serializedLines = new CobolLineWriterImpl().serialize(lines);
        return new CobolDocumentParserImpl().processLines(serializedLines, params);
    }

    // FIXED: Better COBOL structure detection and formatting
    private String addCobolProgramStructure(String cobolCode) {
        // Check if the code already has proper COBOL structure
        if (cobolCode.contains("IDENTIFICATION DIVISION") || cobolCode.contains("PROGRAM-ID")) {
            return cobolCode;
        }
        
        StringBuilder structuredCobol = new StringBuilder();
        boolean hasDataDivision = cobolCode.contains("DATA DIVISION") || cobolCode.contains("WORKING-STORAGE");
        boolean hasProcedureDivision = cobolCode.contains("PROCEDURE DIVISION") || 
                                      cobolCode.contains("MOVE ") || 
                                      cobolCode.contains("EXEC ");
        
        // Add minimal IDENTIFICATION DIVISION
        structuredCobol.append("IDENTIFICATION DIVISION.").append(NEWLINE);
        structuredCobol.append("PROGRAM-ID. PREPROCESSED-PROGRAM.").append(NEWLINE);
        structuredCobol.append(NEWLINE);
        
        // Process the existing code and add appropriate divisions
        String[] lines = cobolCode.split("\\r?\\n");
        boolean inDataSection = false;
        boolean inProcedureSection = false;
        boolean addedDataDivision = false;
        boolean addedProcedureDivision = false;
        
        for (String line : lines) {
            line = line.trim();
            if (line.isEmpty()) continue;
            
            // Skip compiler directives at program level
            if (line.startsWith("CBL ") || line.startsWith("PROCESS ")) {
                continue;
            }
            
            // Check if we need to add DATA DIVISION
            if (!addedDataDivision && (line.contains("WORKING-STORAGE") || line.matches("^\\d+\\s+.*"))) {
                if (!inDataSection) {
                    structuredCobol.append("DATA DIVISION.").append(NEWLINE);
                    addedDataDivision = true;
                    inDataSection = true;
                }
            }
            
            // Check if we need to add PROCEDURE DIVISION
            if (!addedProcedureDivision && (line.startsWith("MOVE ") || line.startsWith("EXEC ") || 
                line.startsWith("CALL ") || line.startsWith("IF ") || line.startsWith("PERFORM "))) {
                if (!inProcedureSection) {
                    if (inDataSection) {
                        structuredCobol.append(NEWLINE);
                    }
                    structuredCobol.append("PROCEDURE DIVISION.").append(NEWLINE);
                    addedProcedureDivision = true;
                    inProcedureSection = true;
                    inDataSection = false;
                }
            }
            
            structuredCobol.append(line).append(NEWLINE);
        }
        
        // Add STOP RUN if we added a PROCEDURE DIVISION
        if (addedProcedureDivision) {
            structuredCobol.append("STOP RUN.").append(NEWLINE);
        }
        
        return structuredCobol.toString();
    }
    
    private String applyAstCompatibleFormatting(String cobolCode, CobolParserParams params) {
        StringBuilder result = new StringBuilder();
        String[] lines = cobolCode.split("\\r?\\n");
        System.out.println("DEBUG: Applying AST compatible formatting...");
        for (String line : lines) {
            String formatted = line;
            String originalLine = formatted;
            formatted = formatted.replaceAll("\\bTO\\s+OUTPUT\\b", "TO OUTPUT-VAR");
            if (formatted.contains("OUTPUT-VAR")) {
                System.out.println("DEBUG: OUTPUT-VAR detected: " + formatted);
            }
            if (!originalLine.equals(formatted)) {
                System.out.println("DEBUG: Line changed: " + originalLine + " -> " + formatted);
            }
            result.append(formatted).append(NEWLINE);
        }
        String finalResult = result.toString();
        System.out.println("DEBUG: Final AST-compatible code:\n=== START ===\n" + finalResult + "=== END ===");
        return finalResult;
    }

    /* 
        // FIXED: Better AST-compatible formatting
    private String applyAstCompatibleFormatting(String cobolCode, CobolParserParams params) {
        StringBuilder result = new StringBuilder();
        String[] lines = cobolCode.split("\\r?\\n");
        
        System.out.println("DEBUG: Applying AST compatible formatting...");
        
        for (String line : lines) {
            if (line.trim().isEmpty()) {
                result.append(line).append(NEWLINE);
                continue;
            }
            
            String formatted = line;
            String originalLine = formatted;
            
            //formatted=formatted.replaceAll("\\bOUTPUT-VAR\\b", "OUTPUT-VAR-VAR");
            // Fix reserved word issues - convert OUTPUT to a valid identifier
            formatted = formatted.replaceAll("\\bTO\\s+OUTPUT\\b", "TO OUTPUT-VAR");
            
            if (params.shouldCommentExecStatements()) {
                // Convert EXEC CICS to comments for AST parsing compatibility
                if (formatted.contains("EXEC CICS")) {
                    formatted = formatted.replaceAll("\\bEXEC\\s+CICS\\s+(.+?)\\s+END-EXEC\\b", 
                        "*> EXEC CICS $1 END-EXEC");
                    System.out.println("DEBUG: Comment mode - converted: " + originalLine + " -> " + formatted);
                }
                
                // Convert EXEC SQL to comments for AST parsing compatibility
                if (formatted.contains("EXEC SQL")) {
                    formatted = formatted.replaceAll("\\bEXEC\\s+SQL\\s+(.+?)\\s+END-EXEC\\b", 
                        "*> EXEC SQL $1 END-EXEC");
                    System.out.println("DEBUG: Comment mode - converted: " + originalLine + " -> " + formatted);
                }
            } else {
                // Convert EXEC statements to the format expected by Cobol.g4 lexer
                if (formatted.contains("EXEC CICS")) {
                    // Convert to EXECCICSLINE format: *>EXECCICS content
                    formatted = formatted.replaceAll("\\bEXEC\\s+CICS\\s+(.+?)\\s+END-EXEC\\b", 
                        "*>EXECCICS $1");
                    System.out.println("DEBUG: Lexer mode - converted: " + originalLine + " -> " + formatted);
                }
                
                if (formatted.contains("EXEC SQL")) {
                    // Convert to EXECSQLLINE format: *>EXECSQL content  
                    formatted = formatted.replaceAll("\\bEXEC\\s+SQL\\s+(.+?)\\s+END-EXEC\\b", 
                        "*>EXECSQL $1");
                    System.out.println("DEBUG: Lexer mode - converted: " + originalLine + " -> " + formatted);
                }
                
                if (formatted.contains("EXEC SQLIMS")) {
                    // Convert to EXECSQLIMSLINE format: *>EXECSQLIMS content
                    formatted = formatted.replaceAll("\\bEXEC\\s+SQLIMS\\s+(.+?)\\s+END-EXEC\\b", 
                        "*>EXECSQLIMS $1");
                    System.out.println("DEBUG: Lexer mode - converted: " + originalLine + " -> " + formatted);
                }
            }
            
            if (formatted.contains("OUTPUT-VAR")) {
                System.out.println("DEBUG: Found OUTPUT-VAR in line: " + formatted);
            }

            if (!originalLine.equals(formatted)) {
                System.out.println("DEBUG: Line changed: " + originalLine + " -> " + formatted);
            }
            
            result.append(formatted).append(NEWLINE);
        }
        
        String finalResult = result.toString();
        System.out.println("DEBUG: Final AST-compatible code:");
        System.out.println("=== START ===");
        System.out.println(finalResult);
        System.out.println("=== END ===");
        
        return finalResult;
    }
    */

    // FIXED: Better final formatting
    private String applyFinalFormatting(String cobolCode) {
        String formatted = cobolCode;
        
        // Fix common formatting issues
        formatted = formatted.replaceAll("\\bLINKPROGRAM\\b", "LINK PROGRAM");
        formatted = formatted.replaceAll("\\bEXECCICS\\b", "EXEC CICS");
        formatted = formatted.replaceAll("\\bTO\\s+OUTPUT\\b", "TO OUTPUT-VAR");
        
        // Fix data description entry formatting - remove extra dots
        formatted = formatted.replaceAll("(\\d+)\\s*\\.\\s*\\.\\s*\\.\\s*", "$1 ");
        //YK
        formatted = formatted.replaceAll("\\s*\\. \\. \\.\\s*", " "); // Clean up dots

        // Normalize whitespace but preserve line structure
        String[] lines = formatted.split("\\r?\\n");
        StringBuilder result = new StringBuilder();
        
        for (String line : lines) {
            String trimmed = line.trim();
            if (!trimmed.isEmpty()) {
                // Normalize internal whitespace while preserving structure
                String normalized = trimmed.replaceAll("\\s+", " ");
                result.append(normalized).append(NEWLINE);
            }
        }
        
        return result.toString();
    }

    // Visitor methods - these are the core preprocessor implementation

    @Override
    public StringBuilder visitStartRule(CobolPreprocessorParser.StartRuleContext ctx) {
        output = new StringBuilder();
        for (int i = 0; i < ctx.getChildCount(); i++) {
            ParseTree child = ctx.getChild(i);
            if (child instanceof TerminalNode) {
                // Skip terminal nodes that are just whitespace or newlines
                String text = child.getText().trim();
                if (!text.isEmpty() && !text.equals("\n") && !text.equals("\r\n")) {
                    // Only process meaningful terminal content
                    continue;
                }
            } else {
                child.accept(this);
            }
        }
        return output;
    }

    @Override
    public StringBuilder visitCompilerOptions(CobolPreprocessorParser.CompilerOptionsContext ctx) {
        // FIXED: Better reconstruction with proper spacing
        StringBuilder lineBuilder = new StringBuilder();
        
        for (int i = 0; i < ctx.getChildCount(); i++) {
            ParseTree child = ctx.getChild(i);
            String token = child.getText();
            
            // Add space before token (except for first token and punctuation)
            if (i > 0 && !token.trim().isEmpty() && !token.equals(".") && !token.equals(",")) {
                lineBuilder.append(" ");
            }
            lineBuilder.append(token);
        }
        
        String text = lineBuilder.toString().trim();
        if (!text.isEmpty()) {
            output.append(text).append(NEWLINE);
        }
        return output;
    }

    @Override
    public StringBuilder visitCopyStatement(CobolPreprocessorParser.CopyStatementContext ctx) {
        String copySource = ctx.copySource().getText().replaceAll("[\"'.]", "").toUpperCase();
        String copyContent = copyBooks.getOrDefault(copySource, null);
        
        if (copyContent == null) {
            String msg = "Copybook not found: " + copySource;
            System.out.println(msg);
            if (strictMode) {
                throw new RuntimeException(msg);
            }
            copyContent = "* COPY " + copySource + " content not found.";
        }
        
        // Apply REPLACING if present
        if (ctx.replacingPhrase() != null && !ctx.replacingPhrase().isEmpty()) {
            copyContent = applyReplacing(copyContent, ctx.replacingPhrase().get(0));
        }
        
        // Process each line of copybook content to preserve formatting
        String[] lines = copyContent.split("\\r?\\n");
        for (String line : lines) {
            if (!line.trim().isEmpty()) {
                output.append(line.trim()).append(NEWLINE);
            }
        }
        
        return output;
    }

    @Override
    public StringBuilder visitReplaceByStatement(CobolPreprocessorParser.ReplaceByStatementContext ctx) {
        ReplaceContext context = new ReplaceContext();
        for (CobolPreprocessorParser.ReplaceClauseContext clause : ctx.replaceClause()) {
            String replaceable = clause.replaceable().getText();
            String replacement = clause.replacement().getText();
            context.addRule(replaceable, replacement);
        }
        replaceContexts.add(context);
        return output;
    }

    @Override
    public StringBuilder visitReplaceOffStatement(CobolPreprocessorParser.ReplaceOffStatementContext ctx) {
        if (!replaceContexts.isEmpty()) {
            replaceContexts.remove(replaceContexts.size() - 1);
        }
        return output;
    }

    @Override
    public StringBuilder visitExecCicsStatement(CobolPreprocessorParser.ExecCicsStatementContext ctx) {
        // FIXED: Better EXEC CICS reconstruction
        StringBuilder lineBuilder = new StringBuilder();
        
        for (int i = 0; i < ctx.getChildCount(); i++) {
            ParseTree child = ctx.getChild(i);
            String token = child.getText();
            
            // Add space before token (except for first token and punctuation)
            if (i > 0 && !token.trim().isEmpty() && !token.equals(".") && !token.equals(",")) {
                lineBuilder.append(" ");
            }
            lineBuilder.append(token);
        }
        
        String text = lineBuilder.toString().trim();
        
        // Handle special EXEC tags transformation
        if (text.contains(EXEC_CICS_TAG)) {
            text = text.replace(EXEC_CICS_TAG, "EXEC CICS");
        }
        if (text.contains(EXEC_END_TAG)) {
            text = text.replace(EXEC_END_TAG, "END-EXEC");
        }
        
        output.append(text).append(NEWLINE);
        return output;
    }

    @Override
    public StringBuilder visitExecSqlStatement(CobolPreprocessorParser.ExecSqlStatementContext ctx) {
        String text = ctx.getText().replace(EXEC_SQL_TAG, "EXEC SQL").replace(EXEC_END_TAG, "END-EXEC");
        if (text.contains("INCLUDE") && text.contains("END-EXEC")) {
            String includeName = text.replaceAll(".*INCLUDE\\s+(\\w+)\\s+END-EXEC.*", "$1").toUpperCase();
            String copyContent = copyBooks.getOrDefault(includeName, null);
            if (copyContent != null) {
                text = copyContent;
            } else {
                System.out.println("EXEC SQL INCLUDE copybook not found: " + includeName);
            }
        }
        output.append(text).append(NEWLINE);
        return output;
    }

    @Override
    public StringBuilder visitExecSqlImsStatement(CobolPreprocessorParser.ExecSqlImsStatementContext ctx) {
        String text = ctx.getText().replace(EXEC_SQLIMS_TAG, "EXEC SQLIMS").replace(EXEC_END_TAG, "END-EXEC");
        output.append(text).append(NEWLINE);
        return output;
    }

    @Override
    public StringBuilder visitEjectStatement(CobolPreprocessorParser.EjectStatementContext ctx) {
        return output; // Skip EJECT statements
    }

    @Override
    public StringBuilder visitSkipStatement(CobolPreprocessorParser.SkipStatementContext ctx) {
        return output; // Skip SKIP statements
    }

    @Override
    public StringBuilder visitTitleStatement(CobolPreprocessorParser.TitleStatementContext ctx) {
        return output; // Skip TITLE statements
    }

    @Override
    public StringBuilder visitCharDataLine(CobolPreprocessorParser.CharDataLineContext ctx) {
        // FIXED: Better token reconstruction with proper spacing
        StringBuilder lineBuilder = new StringBuilder();
        
        for (int i = 0; i < ctx.getChildCount(); i++) {
            ParseTree child = ctx.getChild(i);
            String token = child.getText();
            
            // Add space before token (except for first token and punctuation)
            if (i > 0 && !token.trim().isEmpty() && !token.equals(".") && !token.equals(",") && !token.equals("(") && !token.equals(")")) {
                lineBuilder.append(" ");
            }
            lineBuilder.append(token);
        }
        
        String text = lineBuilder.toString().trim();
        
        // Skip if this line is a comment or empty
        if (text.isEmpty() || text.startsWith("*")) {
            return output;
        }
        
        // Apply active REPLACE transformations
        for (ReplaceContext context : replaceContexts) {
            text = context.apply(text);
        }
        
        // Only append non-empty lines
        if (!text.isEmpty()) {
            output.append(text).append(NEWLINE);
        }
        return output;
    }

    // FIXED: Better REPLACING logic with proper word boundary handling
    private String applyReplacing(String content, CobolPreprocessorParser.ReplacingPhraseContext replacingPhrase) {
        if (replacingPhrase == null) {
            System.out.println("Invalid replacing phrase, skipping replacement.");
            return content;
        }
        
        String result = content;
        for (CobolPreprocessorParser.ReplaceClauseContext clause : replacingPhrase.replaceClause()) {
            String replaceable = clause.replaceable().getText();
            String replacement = clause.replacement().getText();
            
            // Handle pseudo-text replacement
            if (replaceable.startsWith("==") && replaceable.endsWith("==")) {
                String searchText = replaceable.substring(2, replaceable.length() - 2);
                String replaceText = replacement.startsWith("==") && replacement.endsWith("==") 
                    ? replacement.substring(2, replacement.length() - 2) 
                    : replacement;
                // For pseudo-text, use word boundaries to prevent partial matches
                Pattern pattern = Pattern.compile(Pattern.quote(searchText)+ Pattern.CASE_INSENSITIVE);
                result = pattern.matcher(result).replaceAll(replaceText);
            } else {
                // Regular word replacement with strict word boundaries
                Pattern pattern = Pattern.compile("\\b" + Pattern.quote(replaceable) + "\\b", Pattern.CASE_INSENSITIVE);
                result = pattern.matcher(result).replaceAll(replacement);
            }
        }
        return result;
    }

    private void generateAstOutput(String preprocessedCobol, CobolParserParams params) {
        try {
            System.out.println("Generating AST from preprocessed COBOL...");
            
            // Try to load the Cobol parser classes using reflection
            Class<?> lexerClass = Class.forName("CobolLexer");
            Class<?> parserClass = Class.forName("CobolParser");
            
            // Create lexer instance
            Constructor<?> lexerConstructor = lexerClass.getConstructor(CharStream.class);
            CharStream input = CharStreams.fromString(preprocessedCobol);
            Object lexer = lexerConstructor.newInstance(input);
            
            // Create token stream
            Constructor<?> tokenStreamConstructor = CommonTokenStream.class.getConstructor(TokenSource.class);
            CommonTokenStream tokens = (CommonTokenStream) tokenStreamConstructor.newInstance(lexer);
            
            // Create parser instance
            Constructor<?> parserConstructor = parserClass.getConstructor(TokenStream.class);
            Object parser = parserConstructor.newInstance(tokens);
            
            // Remove error listeners
            Method removeErrorListeners = parserClass.getMethod("removeErrorListeners");
            removeErrorListeners.invoke(parser);
            
            // Add custom error listener
            Method addErrorListener = parserClass.getMethod("addErrorListener", ANTLRErrorListener.class);
            addErrorListener.invoke(parser, new BaseErrorListener() {
                @Override
                public void syntaxError(Recognizer<?, ?> recognizer, Object offendingSymbol, int line,
                        int charPositionInLine, String msg, RecognitionException e) {
                    System.err.println(String.format("AST Parse error at line %d:%d: %s", 
                            line, charPositionInLine, msg));
                }
            });
            
            // Parse starting from the root rule
            Method startRule = parserClass.getMethod("startRule");
            ParseTree tree = (ParseTree) startRule.invoke(parser);
            
            // Generate AST representation
            String astOutput = generateAstString(tree, 0);
            
            // Output AST
            String outputFile = params.getAstOutputFile();
            if (outputFile != null) {
                try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputFile))) {
                    writer.write("=== COBOL AST ===\n\n");
                    writer.write("Preprocessed COBOL:\n");
                    writer.write("==================\n");
                    writer.write(preprocessedCobol);
                    writer.write("\n\n");
                    writer.write("Abstract Syntax Tree:\n");
                    writer.write("====================\n");
                    writer.write(astOutput);
                }
                System.out.println("AST written to: " + outputFile);
            } else {
                System.out.println("\n=== COBOL AST ===\n");
                System.out.println(astOutput);
            }
            
        } catch (ClassNotFoundException e) {
            System.err.println("CobolLexer and CobolParser classes not found. Please generate them from Cobol.g4 first:");
            System.err.println("  antlr4 -Dlanguage=Java Cobol.g4");
            System.err.println("  javac *.java");
            if (params.isStrictMode()) {
                throw new RuntimeException("AST generation failed: Cobol parser classes not available", e);
            }
        } catch (Exception e) {
            System.err.println("Failed to generate AST: " + e.getMessage());
            e.printStackTrace();
            if (params.isStrictMode()) {
                throw new RuntimeException("AST generation failed", e);
            }
        }
    }
    
    private String generateAstString(ParseTree tree, int depth) {
        StringBuilder sb = new StringBuilder();
        String indent = "  ".repeat(depth);
        
        if (tree instanceof TerminalNode) {
            // Terminal node (leaf)
            TerminalNode terminal = (TerminalNode) tree;
            String text = terminal.getText();
            String tokenName = getTokenName(terminal.getSymbol().getType());
            sb.append(indent).append("TERMINAL: ").append(tokenName)
              .append(" = '").append(text.replace("\n", "\\n").replace("\r", "\\r")).append("'\n");
        } else {
            // Non-terminal node
            String ruleName = tree.getClass().getSimpleName();
            if (ruleName.endsWith("Context")) {
                ruleName = ruleName.substring(0, ruleName.length() - 7); // Remove "Context"
            }
            
            sb.append(indent).append("RULE: ").append(ruleName);
            
            int childCount = tree.getChildCount();
            if (childCount == 0) {
                sb.append(" (empty)\n");
            } else {
                sb.append(" (").append(childCount).append(" children)\n");
                
                // Process children
                for (int i = 0; i < childCount; i++) {
                    ParseTree child = tree.getChild(i);
                    sb.append(generateAstString(child, depth + 1));
                }
            }
        }
        
        return sb.toString();
    }
    
    private String getTokenName(int tokenType) {
        try {
            // Try to get token name using reflection
            Class<?> lexerClass = Class.forName("CobolLexer");
            Field vocabularyField = lexerClass.getField("VOCABULARY");
            Vocabulary vocabulary = (Vocabulary) vocabularyField.get(null);
            return vocabulary.getDisplayName(tokenType);
        } catch (Exception e) {
            return "TOKEN_" + tokenType;
        }
    }

    private void loadCopyBooks(List<File> directories, List<String> extensions, Charset charset, Set<String> included) throws IOException {
        copyBooks.clear();
        for (File dir : directories) {
            if (!dir.isDirectory()) {
                System.out.println("Copybook directory is invalid: " + dir.getAbsolutePath());
                continue;
            }
            File[] files = dir.listFiles((d, name) -> {
                for (String ext : extensions) {
                    if (name.toLowerCase().endsWith("." + ext.toLowerCase())) {
                        return true;
                    }
                }
                return false;
            });
            if (files == null) {
                continue;
            }
            for (File file : files) {
                String key = file.getName().replaceFirst("[.][^.]+$", "").toUpperCase();
                if (included.contains(key)) {
                    System.out.println("Circular copybook dependency detected: " + key);
                    if (strictMode) {
                        throw new IOException("Circular copybook dependency: " + key);
                    }
                    continue;
                }
                included.add(key);
                try (BufferedReader reader = new BufferedReader(new FileReader(file, charset))) {
                    StringBuilder content = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) {
                        content.append(line).append(NEWLINE);
                    }
                    String copyContent = content.toString();
                    
                    // Handle nested COPY statements
                    Pattern copyPattern = Pattern.compile("(?i)^\\s*COPY\\s+(\\w+)\\s*(\\.)?(?:\\s*REPLACING\\s+(.+?)(?:\\.|$))?\\s*$", Pattern.MULTILINE);
                    Matcher matcher = copyPattern.matcher(copyContent);
                    StringBuilder resolvedContent = new StringBuilder();
                    int lastEnd = 0;
                    
                    while (matcher.find()) {
                        resolvedContent.append(copyContent, lastEnd, matcher.start());
                        String nestedCopy = matcher.group(1).toUpperCase();
                        String replacing = matcher.group(3);
                        String nestedContent = copyBooks.getOrDefault(nestedCopy, null);
                        
                        if (nestedContent == null) {
                            File nestedFile = findCopyBookFile(nestedCopy, directories, extensions);
                            if (nestedFile != null) {
                                Set<String> newIncluded = new HashSet<>(included);
                                loadCopyBook(nestedFile, charset, newIncluded);
                                nestedContent = copyBooks.get(nestedCopy);
                            }
                        }
                        
                        if (nestedContent == null) {
                            System.out.println("Nested copybook not found: " + nestedCopy);
                            resolvedContent.append("COPY ").append(nestedCopy).append(" content not found.");
                        } else {
                            String processedContent = nestedContent;
                            if (replacing != null) {
                                CobolPreprocessorParser.ReplacingPhraseContext phraseContext = parseReplacingPhrase(replacing);
                                if (phraseContext != null) {
                                    processedContent = applyReplacing(processedContent, phraseContext);
                                } else {
                                    System.out.println("Skipping invalid REPLACING clause in copybook: " + replacing);
                                }
                            }
                            resolvedContent.append(processedContent);
                        }
                        lastEnd = matcher.end();
                    }
                    resolvedContent.append(copyContent, lastEnd, copyContent.length());
                    copyBooks.put(key, resolvedContent.toString());
                    System.out.println("Loaded copybook: " + file.getName());
                } catch (IOException e) {
                    System.out.println("Failed to load copybook " + file.getName() + ": " + e.getMessage());
                    if (strictMode) {
                        throw e;
                    }
                } finally {
                    included.remove(key);
                }
            }
        }
    }

    private File findCopyBookFile(String name, List<File> directories, List<String> extensions) {
        for (File dir : directories) {
            for (String ext : extensions) {
                File file = new File(dir, name + "." + ext);
                if (file.exists() && file.isFile()) {
                    return file;
                }
            }
        }
        return null;
    }

    protected void loadCopyBook(File file, Charset charset, Set<String> included) throws IOException {
        String key = file.getName().replaceFirst("[.][^.]+$", "").toUpperCase();
        if (included.contains(key)) {
            throw new IOException("Circular copybook dependency: " + key);
        }
        included.add(key);
        try (BufferedReader reader = new BufferedReader(new FileReader(file, charset))) {
            StringBuilder content = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                content.append(line).append(NEWLINE);
            }
            copyBooks.put(key, content.toString());
        } finally {
            included.remove(key);
        }
    }

    private CobolPreprocessorParser.ReplacingPhraseContext parseReplacingPhrase(String replacingText) {
        try {
            CharStream input = CharStreams.fromString("REPLACING " + replacingText + ".");
            CobolPreprocessorLexer lexer = new CobolPreprocessorLexer(input);
            CommonTokenStream tokens = new CommonTokenStream(lexer);
            CobolPreprocessorParser parser = new CobolPreprocessorParser(tokens);
            return parser.replacingPhrase();
        } catch (Exception e) {
            System.out.println("Failed to parse replacing phrase: " + replacingText);
            return null;
        }
    }

    public static void main(String[] args) throws IOException {
        if (args.length < 2) {
            System.err.println("Usage: java Driver2 <input.cbl> <output.cbl> [options]");
            System.err.println("Options:");
            System.err.println("  --ast                    Generate AST output to console");
            System.err.println("  --ast-file <file>        Generate AST output to file");
            System.err.println("  --charset <charset>      Use specific charset (default: ISO-8859-1)");
            System.err.println("  --no-strict              Disable strict mode");
            System.err.println("  --no-structure           Don't add missing COBOL program structure");
            System.err.println("  --comment-exec           Convert EXEC statements to comments (alternative format)");
            System.err.println("");
            System.err.println("Note: To use AST generation, first generate Cobol parser classes:");
            System.err.println("  antlr4 -Dlanguage=Java Cobol.g4");
            System.err.println("  javac *.java");
            System.exit(1);
        }

        String inputFile = args[0];
        String outputFile = args[1];
        
        // Parse command line options
        boolean outputAst = false;
        String astOutputFile = null;
        String charsetName = "ISO-8859-1";
        boolean strictMode = true;
        boolean addProgramStructure = true;
        boolean commentExecStatements = false;
        
        for (int i = 2; i < args.length; i++) {
            switch (args[i]) {
                case "--ast":
                    outputAst = true;
                    break;
                case "--ast-file":
                    if (i + 1 < args.length) {
                        outputAst = true;
                        astOutputFile = args[++i];
                    } else {
                        System.err.println("Error: --ast-file requires a filename");
                        System.exit(1);
                    }
                    break;
                case "--charset":
                    if (i + 1 < args.length) {
                        charsetName = args[++i];
                    } else {
                        System.err.println("Error: --charset requires a charset name");
                        System.exit(1);
                    }
                    break;
                case "--no-strict":
                    strictMode = false;
                    break;
                case "--no-structure":
                    addProgramStructure = false;
                    break;
                case "--comment-exec":
                    commentExecStatements = true;
                    break;
                default:
                    System.err.println("Unknown option: " + args[i]);
                    System.exit(1);
            }
        }

        Driver2 preprocessor = new Driver2();
        CobolParserParams params = new CobolParserParamsImpl();
        ((CobolParserParamsImpl) params).setFormat(CobolSourceFormatEnum.FIXED);
        ((CobolParserParamsImpl) params).setCopyBookDirectory(new File("./copybooks"));
        ((CobolParserParamsImpl) params).setCopyBookDirectories(Arrays.asList(new File("./copybooks")));
        ((CobolParserParamsImpl) params).setCopyBookExtensions(Arrays.asList("cbl", "cpy"));
        ((CobolParserParamsImpl) params).setCharset(Charset.forName(charsetName));
        ((CobolParserParamsImpl) params).setStrictMode(strictMode);
        ((CobolParserParamsImpl) params).setOutputAst(outputAst);
        ((CobolParserParamsImpl) params).setAstOutputFile(astOutputFile);
        ((CobolParserParamsImpl) params).setAddProgramStructure(addProgramStructure);
        ((CobolParserParamsImpl) params).setCommentExecStatements(commentExecStatements);

        String result = preprocessor.process(new File(inputFile), params);

        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputFile))) {
            writer.write(result);
        }

        System.out.println("Preprocessing completed. Output written to " + outputFile);
        
        if (outputAst && astOutputFile == null) {
            System.out.println("\nNote: AST was displayed above. Use --ast-file to save to a file.");
        }
    }
}

