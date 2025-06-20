import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.tree.*;
import java.util.*;
import java.io.*;


/**
 * Enhanced COBOL AST Parser that generates LISP-style AST from COBOL programs
 * using comprehensive ANTLR grammar for accurate parsing and data structure extraction
 */
public class EnhancedCobolASTParser extends CobolBaseVisitor<ASTNode> {
    
    // Program metadata
    private String programName = "UNKNOWN";
    private List<DataStructureInfo> dataStructures = new ArrayList<>();
    private List<ProcedureInfo> procedures = new ArrayList<>();
    private List<FileOperationInfo> fileOperations = new ArrayList<>();
    private List<CommunicationInfo> communicationDescriptions = new ArrayList<>();
    private String currentSection = "UNKNOWN";

    private int linkageItemCount = 0;
    private List<String> linkageParameters = new ArrayList<>();

    // Parse tree root for LISP output
    private ASTNode rootNode;
    private int nodeCounter = 0;
    
    // Debug flags
    private boolean debugMode = false;
    
    public static void main(String[] args) {
        if (args.length == 0) {
            System.out.println("Usage: java EnhancedCobolASTParser <cobol-file> [--debug]");
            return;
        }
        
        try {
            EnhancedCobolASTParser parser = new EnhancedCobolASTParser();
            
            // Check for debug flag
            if (args.length > 1 && "--debug".equals(args[1])) {
                parser.debugMode = true;
            }
            
            ASTNode ast = parser.parseCobolFile(args[0]);
            
            // Output LISP-style AST
            System.out.println("\n=== LISP-Style AST ===");
            System.out.println(ast.toLisp());
            
            // Save to file
           // If executed after ManualLineSplitter, this writes to the output directory,
            // which is already included in the first argument.
            String outputPath = args[0] ;
            
            String outputFile = outputPath + ".ast";
            System.out.println("Saving AST to: " + outputFile);
            // Ensure output directory exists
            File outputDir = new File(outputPath);
            if (!outputDir.exists()) {
                outputDir.mkdirs();
            }
            // Write AST to file
            System.out.println("Writing AST to file: " + outputFile);
            try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile))) {
                writer.println(ast.toLisp());
                System.out.println("AST saved to: " + outputFile);
            }
            
            // Output extracted data structures as JSON
            System.out.println("\n=== Data Structures ===");

            parser.generateDataStructuresJSON(outputPath + ".json");
            
            // Generate Java class suggestions
            parser.generateJavaClassSuggestions(outputPath + ".java");
            
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    public ASTNode parseCobolFile(String filePath) throws Exception {
        System.out.println("🔍 Parsing COBOL file: " + filePath);
        
        // Preprocess the COBOL file
        String cobolSource = preprocessCobolFile(filePath);
        System.out.println("📄 Preprocessed source (" + cobolSource.length() + " chars)");
        
        if (debugMode) {
            System.out.println("📄 Preprocessed content:");
            String[] lines = cobolSource.split("\n");
            for (int i = 0; i < lines.length; i++) {
                System.out.println(String.format("%3d: %s", i + 1, lines[i]));
            }
        }
        
        // Create ANTLR input stream
        ANTLRInputStream input = new ANTLRInputStream(cobolSource);
        
        // Create lexer and parser
        CobolLexer lexer = new CobolLexer(input);
        CommonTokenStream tokens = new CommonTokenStream(lexer);
        CobolParser parser = new CobolParser(tokens);
        
        // Add error listeners
        addErrorListeners(lexer, parser);
        
        // Parse starting from compilation unit
        ParseTree tree = parser.startRule(); // Use startRule instead of compilationUnit
        System.out.println("🌳 Parse tree created successfully");
        
        if (debugMode) {
            System.out.println("🌳 Parse tree structure:");
            printParseTree(tree, 0);
        }
        
        // Visit the tree to build AST
        rootNode = new ASTNode("COBOL-PROGRAM", programName, 1);
        visit(tree);
        
        System.out.println("✅ AST generation complete!");
        System.out.println("📊 Found " + dataStructures.size() + " data structures");
        System.out.println("📊 Found " + procedures.size() + " procedures");
        System.out.println("📊 Found " + fileOperations.size() + " file operations");
        System.out.println("📊 Found " + communicationDescriptions.size() + " communication descriptions");
        
        return rootNode;
    }
    
    private void printParseTree(ParseTree tree, int depth) {
        if (depth > 10) return; // Prevent too deep recursion
        
        String indent = "  ".repeat(depth);
        String className = tree.getClass().getSimpleName();
        String text = tree.getText();
        if (text.length() > 50) text = text.substring(0, 50) + "...";
        
        System.out.println(indent + className + ": " + text);
        
        for (int i = 0; i < tree.getChildCount(); i++) {
            printParseTree(tree.getChild(i), depth + 1);
        }
    }
    
    private String preprocessCobolFile(String filePath) throws IOException {
        List<String> lines = new ArrayList<>();
        
        try (BufferedReader reader = new BufferedReader(new FileReader(filePath))) {
            String line;
            int lineNum = 0;
            while ((line = reader.readLine()) != null) {
                lineNum++;
                String cleaned = preprocessLine(line, lineNum);
                
                if (cleaned != null && !cleaned.trim().isEmpty()) {
                    lines.add(cleaned);
                }
            }
        }
        
        return String.join("\n", lines);
    }
    
    private String preprocessLine(String line, int lineNum) {
        if (debugMode) {
            System.out.println("Line " + lineNum + " (len=" + line.length() + "): '" + line + "'");
        }
        
        // Handle empty lines
        if (line.trim().isEmpty()) {
            return null;
        }
        
        String cleaned = line;
        
        // Better sequence number detection
        if (cleaned.length() >= 6) {
            String firstSix = cleaned.substring(0, 6);
            
            // More robust sequence number detection
            if (firstSix.matches("\\d{6}|\\s{6}|\\d+\\s*")) {
                cleaned = cleaned.substring(6); // Remove sequence numbers
                
                // Handle indicator area (column 7)
                if (cleaned.length() > 0) {
                    char indicator = cleaned.charAt(0);
                    
                    // Skip comment lines
                    if (indicator == '*' || indicator == '/' || indicator == 'C' || indicator == 'c') {
                        return null;
                    }
                    
                    // Handle continuation lines
                    if (indicator == '-') {
                        cleaned = "     " + cleaned.substring(1);
                    } else if (indicator == ' ' || Character.isWhitespace(indicator)) {
                        cleaned = cleaned.substring(1);
                    } else if (indicator == 'D' || indicator == 'd') {
                        cleaned = cleaned.substring(1); // Debug line
                    }
                }
            }
        }
        
        // Skip header lines and metadata
        String upperCleaned = cleaned.trim().toUpperCase();
        if (isMetadataLine(upperCleaned)) {
            return null;
        }
        
        // Handle COBOL line continuation (literal continuation)
        if (cleaned.endsWith("-")) {
            // This is a continuation marker - handle in calling code
            cleaned = cleaned.substring(0, cleaned.length() - 1);
        }
        
        return cleaned.trim().isEmpty() ? null : cleaned;
    }
    
    private boolean isMetadataLine(String upperLine) {
        return upperLine.startsWith("*HEADER") ||
               upperLine.startsWith("*END-OF") ||
               upperLine.matches("\\*.*") || // Any comment line starting with *
               upperLine.startsWith("FEDERAL COMPILER") ||
               upperLine.startsWith("GENERAL SERVICES") ||
               upperLine.startsWith("AUTOMATED DATA") ||
               upperLine.startsWith("SOFTWARE DEVELOPMENT") ||
               upperLine.contains("LEESBURG PIKE") ||
               upperLine.contains("FALLS CHURCH") ||
               upperLine.contains("PHONE") ||
               upperLine.contains("VERSION") && upperLine.contains("JULY") ||
               upperLine.matches("\"[0-9.]+\".*") ||
               upperLine.matches("\\d{2}/\\d{2}/\\d{2,4}.*");
    }

    private boolean isInIdentificationDivision(String upperLine) {
        // Skip obvious metadata lines that appear in IDENTIFICATION DIVISION
        return upperLine.startsWith("FEDERAL COMPILER") ||
               upperLine.startsWith("GENERAL SERVICES") ||
               upperLine.startsWith("AUTOMATED DATA") ||
               upperLine.startsWith("SOFTWARE DEVELOPMENT") ||
               upperLine.startsWith("LEESBURG PIKE") ||
               upperLine.startsWith("FALLS CHURCH") ||
               upperLine.startsWith("PHONE") ||
               upperLine.startsWith("CCVS-") ||
               upperLine.startsWith("CREATION DATE") ||
               upperLine.startsWith("VALIDATION DATE") ||
               upperLine.matches("\"[0-9.]+\".*") || // Version numbers like "4.2"
               upperLine.matches("\\d{2}/\\d{2}/\\d{2,4}.*") || // Date patterns
               upperLine.matches("\".*\"\\s*\\.?") || // Quoted literals
               (upperLine.contains("VERSION") && upperLine.contains("JULY")) ||
               (upperLine.contains("CREATION") && upperLine.contains("VALIDATION")) ||
               upperLine.equals("HIGH") ||
               upperLine.startsWith("\"") && upperLine.length() < 20; // Short quoted strings
    }
    
    private void addErrorListeners(CobolLexer lexer, CobolParser parser) {
        BaseErrorListener errorListener = new BaseErrorListener() {
            @Override
            public void syntaxError(Recognizer<?, ?> recognizer, Object offendingSymbol,
                                  int line, int charPositionInLine, String msg, RecognitionException e) {
                String sourceName = recognizer.getInputStream().getSourceName();
                System.err.println("❌ " + sourceName + " line " + line + ":" + charPositionInLine + " " + msg);
                
                if (offendingSymbol instanceof Token) {
                    Token token = (Token) offendingSymbol;
                    System.err.println("   Offending token: '" + token.getText() + "'");
                }
            }
        };
        
        lexer.removeErrorListeners();
        parser.removeErrorListeners();
        lexer.addErrorListener(errorListener);
        parser.addErrorListener(errorListener);
    }
    
    // ===========================================
    // VISITOR METHODS FOR AST GENERATION
    // ===========================================
    
    @Override
    public ASTNode visitStartRule(CobolParser.StartRuleContext ctx) {
        log("🔍 Visiting start rule");
        
        if (ctx.compilationUnit() != null) {
            ASTNode compilationNode = visit(ctx.compilationUnit());
            if (compilationNode != null) {
                rootNode.addChild(compilationNode);
            }
        }
        
        return rootNode;
    }
    
    @Override
    public ASTNode visitCompilationUnit(CobolParser.CompilationUnitContext ctx) {
        log("🔍 Visiting compilation unit");
        
        ASTNode compilationNode = new ASTNode("COMPILATION-UNIT", null, getLineNumber(ctx));
        
        // Process program units
        for (CobolParser.ProgramUnitContext programCtx : ctx.programUnit()) {
            ASTNode programNode = visit(programCtx);
            if (programNode != null) {
                compilationNode.addChild(programNode);
            }
        }
        
        // Process copy statements
        for (CobolParser.CopyStatementContext copyCtx : ctx.copyStatement()) {
            ASTNode copyNode = visit(copyCtx);
            if (copyNode != null) {
                compilationNode.addChild(copyNode);
            }
        }
        
        return compilationNode;
    }
    
    @Override
    public ASTNode visitProgramUnit(CobolParser.ProgramUnitContext ctx) {
        log("🔍 Visiting program unit");
        
        ASTNode programNode = new ASTNode("PROGRAM-UNIT", null, getLineNumber(ctx));
        
        // Visit identification division
        if (ctx.identificationDivision() != null) {
            ASTNode idDiv = visit(ctx.identificationDivision());
            if (idDiv != null) programNode.addChild(idDiv);
        }
        
        // Visit environment division
        if (ctx.environmentDivision() != null) {
            ASTNode envDiv = visit(ctx.environmentDivision());
            if (envDiv != null) programNode.addChild(envDiv);
        }
        
        // Visit data division
        if (ctx.dataDivision() != null) {
            ASTNode dataDiv = visit(ctx.dataDivision());
            if (dataDiv != null) programNode.addChild(dataDiv);
        }
        
        // Visit procedure division
        if (ctx.procedureDivision() != null) {
            ASTNode procDiv = visit(ctx.procedureDivision());
            if (procDiv != null) programNode.addChild(procDiv);
        }
        
        // Visit nested program units
        for (CobolParser.ProgramUnitContext nestedCtx : ctx.programUnit()) {
            ASTNode nestedNode = visit(nestedCtx);
            if (nestedNode != null) programNode.addChild(nestedNode);
        }
        
        // Visit end program statement
        if (ctx.endProgramStatement() != null) {
            ASTNode endNode = visit(ctx.endProgramStatement());
            if (endNode != null) programNode.addChild(endNode);
        }
        
        return programNode;
    }

    @Override
    public ASTNode visitErrorNode(ErrorNode node) {
        log("❌ Error node encountered: " + node.getText());
        return new ASTNode("ERROR-NODE", node.getText(), 
                        node.getSymbol() != null ? node.getSymbol().getLine() : 1);
    }
    
    @Override
    public ASTNode visitEnvironmentDivision(CobolParser.EnvironmentDivisionContext ctx) {
        log("🔍 Visiting ENVIRONMENT DIVISION");
        
        ASTNode envDiv = new ASTNode("ENVIRONMENT-DIVISION", null, getLineNumber(ctx));
        
        // Process environment division body elements
        for (CobolParser.EnvironmentDivisionBodyContext bodyCtx : ctx.environmentDivisionBody()) {
            ASTNode bodyNode = visit(bodyCtx);
            if (bodyNode != null) {
                envDiv.addChild(bodyNode);
            }
        }
        
        return envDiv;
    }

    @Override
    public ASTNode visitEnvironmentDivisionBody(CobolParser.EnvironmentDivisionBodyContext ctx) {
        log("🔍 Visiting environment division body");
        
        // Handle different types of environment division body elements
        if (ctx.configurationSection() != null) {
            return visit(ctx.configurationSection());
        } else if (ctx.specialNamesParagraph() != null) {
            return visit(ctx.specialNamesParagraph());
        } else if (ctx.inputOutputSection() != null) {
            return visit(ctx.inputOutputSection());
        }
        
        return null;
    }

    @Override
    public ASTNode visitConfigurationSection(CobolParser.ConfigurationSectionContext ctx) {
        log("🔍 Visiting CONFIGURATION SECTION");
        
        ASTNode configSection = new ASTNode("CONFIGURATION-SECTION", null, getLineNumber(ctx));
        
        // Process configuration section paragraphs
        for (CobolParser.ConfigurationSectionParagraphContext paragraphCtx : ctx.configurationSectionParagraph()) {
            ASTNode paragraphNode = visit(paragraphCtx);
            if (paragraphNode != null) {
                configSection.addChild(paragraphNode);
            }
        }
        
        return configSection;
    }
    
    @Override
    public ASTNode visitConfigurationSectionParagraph(CobolParser.ConfigurationSectionParagraphContext ctx) {
        log("🔍 Visiting configuration section paragraph");
        
        // Handle different types of configuration paragraphs
        if (ctx.sourceComputerParagraph() != null) {
            return visit(ctx.sourceComputerParagraph());
        } else if (ctx.objectComputerParagraph() != null) {
            return visit(ctx.objectComputerParagraph());
        } else if (ctx.specialNamesParagraph() != null) {
            return visit(ctx.specialNamesParagraph());
        } else if (ctx.repositoryParagraph() != null) {
            return visit(ctx.repositoryParagraph());
        }
        
        return null;
    }

    @Override
    public ASTNode visitObjectComputerParagraph(CobolParser.ObjectComputerParagraphContext ctx) {
        log("🔍 Visiting OBJECT-COMPUTER paragraph");
        
        ASTNode objectNode = new ASTNode("OBJECT-COMPUTER", null, getLineNumber(ctx));
        
        // Extract computer name if present
        if (ctx.computerName() != null) {
            String computerName = ctx.computerName().getText();
            ASTNode nameNode = new ASTNode("COMPUTER-NAME", computerName, getLineNumber(ctx));
            objectNode.addChild(nameNode);
        }
        
        // Process object computer clauses
        for (CobolParser.ObjectComputerClauseContext clauseCtx : ctx.objectComputerClause()) {
            ASTNode clauseNode = visit(clauseCtx);
            if (clauseNode != null) {
                objectNode.addChild(clauseNode);
            }
        }
        
        return objectNode;
    }

    @Override
    public ASTNode visitSourceComputerParagraph(CobolParser.SourceComputerParagraphContext ctx) {
        log("🔍 Visiting SOURCE-COMPUTER paragraph");
        
        ASTNode sourceNode = new ASTNode("SOURCE-COMPUTER", null, getLineNumber(ctx));
        
        // Extract computer name if present
        if (ctx.computerName() != null) {
            String computerName = ctx.computerName().getText();
            ASTNode nameNode = new ASTNode("COMPUTER-NAME", computerName, getLineNumber(ctx));
            sourceNode.addChild(nameNode);
        }
        
        // Check for DEBUGGING MODE
        if (ctx.getText().toUpperCase().contains("DEBUGGING")) {
            ASTNode debugNode = new ASTNode("DEBUGGING-MODE", "true", getLineNumber(ctx));
            sourceNode.addChild(debugNode);
        }
        
        return sourceNode;
    }
    
    @Override
    public ASTNode visitInputOutputSection(CobolParser.InputOutputSectionContext ctx) {
        log("🔍 Visiting INPUT-OUTPUT SECTION");
        
        ASTNode ioSection = new ASTNode("INPUT-OUTPUT-SECTION", null, getLineNumber(ctx));
        
        // Process input-output section paragraphs
        for (CobolParser.InputOutputSectionParagraphContext paragraphCtx : ctx.inputOutputSectionParagraph()) {
            ASTNode paragraphNode = visit(paragraphCtx);
            if (paragraphNode != null) {
                ioSection.addChild(paragraphNode);
            }
        }
        
        return ioSection;
    }

    @Override
    public ASTNode visitInputOutputSectionParagraph(CobolParser.InputOutputSectionParagraphContext ctx) {
        log("🔍 Visiting input-output section paragraph");
        
        // Handle different types of I-O paragraphs
        if (ctx.fileControlParagraph() != null) {
            return visit(ctx.fileControlParagraph());
        } else if (ctx.ioControlParagraph() != null) {
            return visit(ctx.ioControlParagraph());
        }
        
        return null;
    }

    @Override
    public ASTNode visitFileControlParagraph(CobolParser.FileControlParagraphContext ctx) {
        log("🔍 Visiting FILE-CONTROL paragraph");
        
        ASTNode fileControlNode = new ASTNode("FILE-CONTROL", null, getLineNumber(ctx));
        
        // Process file control entries
        for (CobolParser.FileControlEntryContext entryCtx : ctx.fileControlEntry()) {
            ASTNode entryNode = visit(entryCtx);
            if (entryNode != null) {
                fileControlNode.addChild(entryNode);
            }
        }
        
        return fileControlNode;
    }

    @Override
    public ASTNode visitFileControlEntry(CobolParser.FileControlEntryContext ctx) {
        log("🔍 Visiting file control entry");
        
        ASTNode entryNode = new ASTNode("FILE-CONTROL-ENTRY", null, getLineNumber(ctx));
        
        // Process SELECT clause
        if (ctx.selectClause() != null) {
            ASTNode selectNode = visit(ctx.selectClause());
            if (selectNode != null) {
                entryNode.addChild(selectNode);
            }
        }
        
        // Process file control clauses
        for (CobolParser.FileControlClauseContext clauseCtx : ctx.fileControlClause()) {
            ASTNode clauseNode = visit(clauseCtx);
            if (clauseNode != null) {
                entryNode.addChild(clauseNode);
            }
        }
        
        return entryNode;
    }

    @Override
    public ASTNode visitSelectClause(CobolParser.SelectClauseContext ctx) {
        log("🔍 Visiting SELECT clause");
        
        ASTNode selectNode = new ASTNode("SELECT-CLAUSE", null, getLineNumber(ctx));
        
        // Check for OPTIONAL
        if (ctx.OPTIONAL() != null) {
            ASTNode optionalNode = new ASTNode("OPTIONAL", "true", getLineNumber(ctx));
            selectNode.addChild(optionalNode);
        }
        
        // Get file name
        if (ctx.fileName() != null) {
            String fileName = ctx.fileName().getText();
            ASTNode fileNameNode = new ASTNode("FILE-NAME", fileName, getLineNumber(ctx));
            selectNode.addChild(fileNameNode);
        }
        
        return selectNode;
    }
    
    @Override
    public ASTNode visitLocalStorageSection(CobolParser.LocalStorageSectionContext ctx) {
        log("🔍 Visiting LOCAL-STORAGE SECTION");
        
        setCurrentSection("LOCAL-STORAGE");
        
        ASTNode localSection = new ASTNode("LOCAL-STORAGE-SECTION", null, getLineNumber(ctx));
        
        // Process data description groups
        for (CobolParser.DataDescriptionGroupContext groupCtx : ctx.dataDescriptionGroup()) {
            ASTNode groupNode = visit(groupCtx);
            if (groupNode != null) {
                localSection.addChild(groupNode);
            }
        }
        
        log("✅ Processed LOCAL-STORAGE SECTION with " + localSection.children.size() + " items");
        
        return localSection;
    }

    public List<String> getLinkageParameters() {
        return new ArrayList<>(linkageParameters);
    }
    
    public int getLinkageItemCount() {
        return linkageItemCount;
    }

    private boolean shouldIncludeDataStructure(String dataName, String level, DataStructureInfo dataInfo) {
        if (dataName == null || dataName.equals("FILLER") || dataName.equals("UNNAMED")) {
            return false;
        }
        
        // Include based on level and section
        switch (currentSection) {
            case "LINKAGE-SECTION":
                // Include all meaningful linkage items (they're parameters)
                linkageItemCount++;
                if (level.equals("01") || level.equals("77")) {
                    linkageParameters.add(dataName);
                    return true;
                }
                // Also include subordinate items in linkage for completeness
                return !level.equals("88"); // Exclude condition names in linkage
                
            case "WORKING-STORAGE":
            case "FILE-SECTION":
            case "LOCAL-STORAGE":
                // Standard filtering for other sections
                return level.equals("01") || level.equals("77") || 
                       (level.equals("88") && dataInfo.hasValue) ||
                       level.equals("66"); // Include RENAMES items
                       
            default:
                return level.equals("01") || level.equals("77");
        }
    }
    

    @Override
    public ASTNode visitFileSection(CobolParser.FileSectionContext ctx) {
        log("🔍 Visiting FILE SECTION");
        
        String previousSection = currentSection;
        currentSection = "FILE-SECTION";
        
        ASTNode fileSection = new ASTNode("FILE-SECTION", null, getLineNumber(ctx));
        
        try {
            // Process file description entries
            for (CobolParser.FileDescriptionEntryContext fdCtx : ctx.fileDescriptionEntry()) {
                ASTNode fdNode = visit(fdCtx);
                if (fdNode != null) {
                    fileSection.addChild(fdNode);
                }
            }
            
            log("✅ Processed FILE SECTION with " + fileSection.children.size() + " entries");
            
        } finally {
            currentSection = previousSection;
        }
        
        return fileSection;
    }

    @Override
    public ASTNode visitFileDescriptionEntry(CobolParser.FileDescriptionEntryContext ctx) {
        log("🔍 Visiting file description entry");
        
        ASTNode fdNode = new ASTNode("FILE-DESCRIPTION-ENTRY", null, getLineNumber(ctx));
        
        // Check for FD or SD
        String fdType = "FD";
        if (ctx.getText().toUpperCase().startsWith("SD")) {
            fdType = "SD";
        }
        ASTNode typeNode = new ASTNode("FD-TYPE", fdType, getLineNumber(ctx));
        fdNode.addChild(typeNode);
        
        // Get file name
        if (ctx.fileName() != null) {
            String fileName = ctx.fileName().getText();
            ASTNode nameNode = new ASTNode("FILE-NAME", fileName, getLineNumber(ctx));
            fdNode.addChild(nameNode);
        }
        
        // Process file description entry clauses
        for (CobolParser.FileDescriptionEntryClauseContext clauseCtx : ctx.fileDescriptionEntryClause()) {
            ASTNode clauseNode = visit(clauseCtx);
            if (clauseNode != null) {
                fdNode.addChild(clauseNode);
            }
        }
        
        // Process data description groups
        for (CobolParser.DataDescriptionGroupContext groupCtx : ctx.dataDescriptionGroup()) {
            ASTNode groupNode = visit(groupCtx);
            if (groupNode != null) {
                fdNode.addChild(groupNode);
            }
        }
        
        return fdNode;
    }

    @Override
    public ASTNode visitFileDescriptionEntryClause(CobolParser.FileDescriptionEntryClauseContext ctx) {
        log("🔍 Visiting file description entry clause");
        
        // Handle different types of FD clauses
        if (ctx.externalClause() != null) {
            return new ASTNode("EXTERNAL-CLAUSE", ctx.externalClause().getText(), getLineNumber(ctx));
        } else if (ctx.globalClause() != null) {
            return new ASTNode("GLOBAL-CLAUSE", ctx.globalClause().getText(), getLineNumber(ctx));
        } else if (ctx.blockContainsClause() != null) {
            return new ASTNode("BLOCK-CONTAINS-CLAUSE", ctx.blockContainsClause().getText(), getLineNumber(ctx));
        } else if (ctx.recordContainsClause() != null) {
            return new ASTNode("RECORD-CONTAINS-CLAUSE", ctx.recordContainsClause().getText(), getLineNumber(ctx));
        } else if (ctx.labelRecordsClause() != null) {
            return new ASTNode("LABEL-RECORDS-CLAUSE", ctx.labelRecordsClause().getText(), getLineNumber(ctx));
        } else if (ctx.valueOfClause() != null) {
            return new ASTNode("VALUE-OF-CLAUSE", ctx.valueOfClause().getText(), getLineNumber(ctx));
        } else if (ctx.dataRecordsClause() != null) {
            return new ASTNode("DATA-RECORDS-CLAUSE", ctx.dataRecordsClause().getText(), getLineNumber(ctx));
        } else if (ctx.linageClause() != null) {
            return new ASTNode("LINAGE-CLAUSE", ctx.linageClause().getText(), getLineNumber(ctx));
        } else if (ctx.codeSetClause() != null) {
            return new ASTNode("CODE-SET-CLAUSE", ctx.codeSetClause().getText(), getLineNumber(ctx));
        } else if (ctx.reportClause() != null) {
            return new ASTNode("REPORT-CLAUSE", ctx.reportClause().getText(), getLineNumber(ctx));
        } else if (ctx.recordingModeClause() != null) {
            return new ASTNode("RECORDING-MODE-CLAUSE", ctx.recordingModeClause().getText(), getLineNumber(ctx));
        }
        
        return new ASTNode("UNKNOWN-FD-CLAUSE", ctx.getText(), getLineNumber(ctx));
    }

    @Override
    public ASTNode visitDataDescriptionEntry(CobolParser.DataDescriptionEntryContext ctx) {
        log("🔍 Visiting data description entry (generic)");
        
        // Handle different formats of data description entries
        if (ctx.dataDescriptionEntryFormat1() != null) {
            return visit(ctx.dataDescriptionEntryFormat1());
        } else if (ctx.dataDescriptionEntryFormat2() != null) {
            return visit(ctx.dataDescriptionEntryFormat2());
        } else if (ctx.dataDescriptionEntryFormat3() != null) {
            return visit(ctx.dataDescriptionEntryFormat3());
        } else if (ctx.dataDescriptionEntryFormat4() != null) {
            return visit(ctx.dataDescriptionEntryFormat4());
        } else if (ctx.dataDescriptionEntryExecSql() != null) {
            return visit(ctx.dataDescriptionEntryExecSql());
        } else if (ctx.copyStatement() != null) {
            return visit(ctx.copyStatement());
        }
        
        // Fallback for unhandled formats
        ASTNode genericEntry = new ASTNode("DATA-DESCRIPTION-ENTRY", ctx.getText(), getLineNumber(ctx));
        return genericEntry;
    }


    @Override
    public ASTNode visitIdentificationDivision(CobolParser.IdentificationDivisionContext ctx) {
        log("🔍 Visiting IDENTIFICATION DIVISION");
        
        ASTNode idDiv = new ASTNode("IDENTIFICATION-DIVISION", null, getLineNumber(ctx));
        
        // Visit program ID paragraph
        if (ctx.programIdParagraph() != null) {
            ASTNode progId = visit(ctx.programIdParagraph());
            if (progId != null) idDiv.addChild(progId);
        }
        
        // Visit other identification paragraphs
        for (CobolParser.IdentificationDivisionBodyContext bodyCtx : ctx.identificationDivisionBody()) {
            ASTNode bodyNode = visit(bodyCtx);
            if (bodyNode != null) idDiv.addChild(bodyNode);
        }
        
        return idDiv;
    }
    
    @Override
    public ASTNode visitProgramIdParagraph(CobolParser.ProgramIdParagraphContext ctx) {
        log("🔍 Visiting PROGRAM-ID paragraph");
        
        ASTNode progIdNode = new ASTNode("PROGRAM-ID", null, getLineNumber(ctx));
        
        if (ctx.programName() != null) {
            String progName = ctx.programName().getText();
            programName = progName;
            ASTNode nameNode = new ASTNode("PROGRAM-NAME", progName, getLineNumber(ctx));
            progIdNode.addChild(nameNode);
            log("✅ Found program name: " + programName);
        }
        
        return progIdNode;
    }
    
    @Override
    public ASTNode visitDataDivision(CobolParser.DataDivisionContext ctx) {
        log("🔍 Visiting DATA DIVISION");
        
        ASTNode dataDiv = new ASTNode("DATA-DIVISION", null, getLineNumber(ctx));
        
        // Visit data division sections
        for (CobolParser.DataDivisionSectionContext sectionCtx : ctx.dataDivisionSection()) {
            ASTNode sectionNode = visit(sectionCtx);
            if (sectionNode != null) dataDiv.addChild(sectionNode);
        }
        
        return dataDiv;
    }
    
    @Override
    public ASTNode visitDataDivisionSection(CobolParser.DataDivisionSectionContext ctx) {
        log("🔍 Visiting data division section");
        
        // Handle different types of sections
        if (ctx.fileSection() != null) {
            return visit(ctx.fileSection());
        } else if (ctx.workingStorageSection() != null) {
            return visit(ctx.workingStorageSection());
        } else if (ctx.linkageSection() != null) {
            return visit(ctx.linkageSection());
        } else if (ctx.communicationSection() != null) {
            return visit(ctx.communicationSection());
        } else if (ctx.localStorageSection() != null) {
            return visit(ctx.localStorageSection());
        } else if (ctx.screenSection() != null) {
            return visit(ctx.screenSection());
        } else if (ctx.reportSection() != null) {
            return visit(ctx.reportSection());
        } else if (ctx.dataDescriptionEntry() != null) {
            return visit(ctx.dataDescriptionEntry());
        } else if (ctx.copyStatement() != null) {
            return visit(ctx.copyStatement());
        }
        
        return null;
    }
    
    @Override
    public ASTNode visitLinkageSection(CobolParser.LinkageSectionContext ctx) {
        log("🔍 Visiting LINKAGE SECTION");
        
        String previousSection = currentSection;
        currentSection = "LINKAGE-SECTION";
        
        ASTNode linkageSection = new ASTNode("LINKAGE-SECTION", null, getLineNumber(ctx));
        
        try {
            // Process data description groups in linkage section
            for (CobolParser.DataDescriptionGroupContext groupCtx : ctx.dataDescriptionGroup()) {
                ASTNode groupNode = visit(groupCtx);
                if (groupNode != null) {
                    linkageSection.addChild(groupNode);
                }
            }
            
            log("✅ Processed LINKAGE SECTION with " + linkageSection.children.size() + " items");
            
        } finally {
            currentSection = previousSection;
        }
        
        return linkageSection;
    }

    @Override
    public ASTNode visitWorkingStorageSection(CobolParser.WorkingStorageSectionContext ctx) {
        log("🔍 Visiting WORKING-STORAGE SECTION");
        
        setCurrentSection("WORKING-STORAGE");
        
        ASTNode wsSection = new ASTNode("WORKING-STORAGE-SECTION", null, getLineNumber(ctx));
        
        // Step 1: Collect ALL data items in a flat list
        // WS creates hierarchy of data elements, preprocess to flatten based on 
        // level #
        List<ASTNode> allDataItems = new ArrayList<>();
        for (CobolParser.DataDescriptionGroupContext groupCtx : ctx.dataDescriptionGroup()) {
            collectAllDataItemsFlat(groupCtx, allDataItems);
        }
        
        // Step 2: Rebuild hierarchy based on level numbers
        ASTNode restructured = Postprocess.restructureByLevelNumbers(allDataItems);
        
        // Step 3: Add properly structured items to working storage
        for (ASTNode child : restructured.children) {
            wsSection.addChild(child);
        }
        
        log("✅ Processed WORKING-STORAGE SECTION with correct hierarchy: " + wsSection.children.size() + " top-level items");
        
        return wsSection;
    }

    
    private String getCurrentSection() {
        // Track current section context - you'd need to implement section tracking
        return currentSection ;
    }

    @Override
    public ASTNode visitDataDescriptionGroup(CobolParser.DataDescriptionGroupContext ctx) {
        log("🔍 Visiting data description group");
        
        ASTNode groupNode = null;
        
        // Process the main data description entry
        if (ctx.dataDescriptionEntryFormat1() != null) {
            groupNode = visit(ctx.dataDescriptionEntryFormat1());
        } else if (ctx.dataDescriptionEntryFormat2() != null) {
            groupNode = visit(ctx.dataDescriptionEntryFormat2());
        } else if (ctx.dataDescriptionEntryFormat3() != null) {
            groupNode = visit(ctx.dataDescriptionEntryFormat3());
        } else if (ctx.dataDescriptionEntryFormat4() != null) {
            groupNode = visit(ctx.dataDescriptionEntryFormat4());
        } else if (ctx.dataDescriptionEntryExecSql() != null) {
            groupNode = visit(ctx.dataDescriptionEntryExecSql());
        } else if (ctx.copyStatement() != null) {
            groupNode = visit(ctx.copyStatement());
        }
        
        // CRITICAL FIX: Process ALL subordinate data items
        if (groupNode != null && ctx.subordinateDataItem() != null && !ctx.subordinateDataItem().isEmpty()) {
            log("🔍 Processing " + ctx.subordinateDataItem().size() + " subordinate data items");
            
            for (CobolParser.SubordinateDataItemContext subCtx : ctx.subordinateDataItem()) {
                ASTNode subNode = visit(subCtx);
                if (subNode != null) {
                    groupNode.addChild(subNode);
                    log("✅ Added subordinate item: " + subNode.type);
                }
            }
        }
        
        return groupNode;
    }

    // Also need to implement visitSubordinateDataItem to handle the recursion
    @Override
    public ASTNode visitSubordinateDataItem(CobolParser.SubordinateDataItemContext ctx) {
        log("🔍 Visiting subordinate data item");
        
        ASTNode subNode = null;
        
        // Process the subordinate data description entry
        if (ctx.dataDescriptionEntryFormat1() != null) {
            subNode = visit(ctx.dataDescriptionEntryFormat1());
        } else if (ctx.dataDescriptionEntryFormat3() != null) {
            // 88-level condition names
            subNode = visit(ctx.dataDescriptionEntryFormat3());
        } else if (ctx.copyStatement() != null) {
            subNode = visit(ctx.copyStatement());
        }
        
        // RECURSIVE: Handle nested subordinate items (for deeper hierarchies)
        if (subNode != null && ctx.subordinateDataItem() != null && !ctx.subordinateDataItem().isEmpty()) {
            log("🔍 Processing nested subordinate items under " + subNode.value);
            
            for (CobolParser.SubordinateDataItemContext nestedCtx : ctx.subordinateDataItem()) {
                ASTNode nestedNode = visit(nestedCtx);
                if (nestedNode != null) {
                    subNode.addChild(nestedNode);
                    log("✅ Added nested subordinate item: " + nestedNode.type);
                }
            }
        }
        
        return subNode;
    }


    @Override
    public ASTNode visitDataDescriptionEntryFormat2(CobolParser.DataDescriptionEntryFormat2Context ctx) {
        log("🔍 Visiting data description entry format 2 (66-level RENAMES)");
        
        ASTNode dataEntry = new ASTNode("DATA-ITEM", null, getLineNumber(ctx));
        
        // Level 66
        ASTNode levelNode = new ASTNode("LEVEL", "66", getLineNumber(ctx));
        dataEntry.addChild(levelNode);
        
        // Extract data name
        String dataName = null;
        if (ctx.dataName() != null) {
            dataName = ctx.dataName().getText();
            ASTNode nameNode = new ASTNode("DATA-NAME", dataName, getLineNumber(ctx));
            dataEntry.addChild(nameNode);
        }
        
        // Process RENAMES clause
        if (ctx.dataRenamesClause() != null) {
            ASTNode renamesNode = visit(ctx.dataRenamesClause());
            if (renamesNode != null) {
                dataEntry.addChild(renamesNode);
            }
        }
        
        // Create data structure info for RENAMES items
        if (dataName != null && !dataName.equals("FILLER")) {
            DataStructureInfo dataInfo = new DataStructureInfo();
            dataInfo.name = dataName;
            dataInfo.level = "66";
            dataInfo.lineNumber = getLineNumber(ctx);
            dataInfo.section = currentSection;
            dataInfo.dataType = "RENAMES";
            dataInfo.javaType = "Object";
            
            dataStructures.add(dataInfo);
            log("✅ Added RENAMES data structure: " + dataName + " (level 66)");
        }
        
        return dataEntry;
    }

    @Override
    public ASTNode visitDataDescriptionEntryFormat3(CobolParser.DataDescriptionEntryFormat3Context ctx) {
        log("🔍 Visiting data description entry format 3 (88-level condition names)");
        
        ASTNode dataEntry = new ASTNode("DATA-ITEM", null, getLineNumber(ctx));
        
        // Level 88
        ASTNode levelNode = new ASTNode("LEVEL", "88", getLineNumber(ctx));
        dataEntry.addChild(levelNode);
        
        // Extract condition name
        String conditionName = null;
        if (ctx.conditionName() != null) {
            conditionName = ctx.conditionName().getText();
            ASTNode nameNode = new ASTNode("CONDITION-NAME", conditionName, getLineNumber(ctx));
            dataEntry.addChild(nameNode);
        }
        
        // Process VALUE clause (required for 88-level items)
        if (ctx.dataValueClause() != null) {
            ASTNode valueNode = visit(ctx.dataValueClause());
            if (valueNode != null) {
                dataEntry.addChild(valueNode);
            }
            
            // Create data structure info for condition names
            if (conditionName != null) {
                DataStructureInfo dataInfo = new DataStructureInfo();
                dataInfo.name = conditionName;
                dataInfo.level = "88";
                dataInfo.lineNumber = getLineNumber(ctx);
                dataInfo.section = currentSection;
                dataInfo.dataType = "CONDITION";
                dataInfo.javaType = "boolean";
                dataInfo.hasValue = true;
                
                // Extract value from VALUE clause
                CobolParser.DataValueIntervalContext interval = ctx.dataValueClause().dataValueInterval();
                if (interval != null) {
                    dataInfo.value = interval.dataValueIntervalFrom().getText();
                    if (interval.dataValueIntervalTo() != null) {
                        dataInfo.valueTo = interval.dataValueIntervalTo().getText();
                    }
                }
                
                dataStructures.add(dataInfo);
                log("✅ Added condition name: " + conditionName + " (value: " + dataInfo.value + ")");
            }
        }
        
        return dataEntry;
    }

    @Override
    public ASTNode visitDataDescriptionEntryFormat4(CobolParser.DataDescriptionEntryFormat4Context ctx) {
        log("🔍 Visiting data description entry format 4 (77-level)");
        
        ASTNode dataEntry = new ASTNode("DATA-ITEM", null, getLineNumber(ctx));
        
        // Level 77
        ASTNode levelNode = new ASTNode("LEVEL", "77", getLineNumber(ctx));
        dataEntry.addChild(levelNode);
        
        // Extract data name
        String dataName = null;
        if (ctx.dataName() != null) {
            dataName = ctx.dataName().getText();
            ASTNode nameNode = new ASTNode("DATA-NAME", dataName, getLineNumber(ctx));
            dataEntry.addChild(nameNode);
        }
        
        // Process data clauses
        for (CobolParser.DataClauseContext clauseCtx : ctx.dataClause()) {
            ASTNode clauseNode = visit(clauseCtx);
            if (clauseNode != null) {
                dataEntry.addChild(clauseNode);
            }
        }
        
        // Create data structure info for 77-level items
        if (dataName != null && !dataName.equals("FILLER")) {
            DataStructureInfo dataInfo = new DataStructureInfo();
            dataInfo.name = dataName;
            dataInfo.level = "77";
            dataInfo.lineNumber = getLineNumber(ctx);
            dataInfo.section = currentSection;
            
            // Extract additional info from clauses if needed
            // This would be similar to format1 processing
            
            dataStructures.add(dataInfo);
            log("✅ Added 77-level data structure: " + dataName);
        }
        
        return dataEntry;
    }

    @Override
    public ASTNode visitDataDescriptionEntryExecSql(CobolParser.DataDescriptionEntryExecSqlContext ctx) {
        log("🔍 Visiting EXEC SQL data description entry");
        
        ASTNode execSqlNode = new ASTNode("EXEC-SQL-DATA-ENTRY", null, getLineNumber(ctx));
        
        // Process SQL statement
        if (ctx.sqlStatement() != null) {
            String sqlText = ctx.sqlStatement().getText();
            ASTNode sqlNode = new ASTNode("SQL-STATEMENT", sqlText, getLineNumber(ctx));
            execSqlNode.addChild(sqlNode);
        }
        
        return execSqlNode;
    }
    
    // Enhanced visitDataDescriptionEntryFormat1 to better handle subordinate processing
    @Override
    public ASTNode visitDataDescriptionEntryFormat1(CobolParser.DataDescriptionEntryFormat1Context ctx) {
        log("🔍 Visiting data description entry format 1");

        ASTNode dataEntry = new ASTNode("DATA-ITEM", null, getLineNumber(ctx));

        // Extract level number
        String level = "01";
        if (ctx.integerLevelNumber() != null) {
            level = ctx.integerLevelNumber().getText();
            ASTNode levelNode = new ASTNode("LEVEL", level, getLineNumber(ctx));
            dataEntry.addChild(levelNode);
        }

        // Extract data name
        String dataName = null;
        if (ctx.dataName() != null) {
            dataName = ctx.dataName().getText();
            ASTNode nameNode = new ASTNode("DATA-NAME", dataName, getLineNumber(ctx));
            dataEntry.addChild(nameNode);
        } else if (ctx.FILLER() != null) {
            dataName = "FILLER";
            ASTNode nameNode = new ASTNode("DATA-NAME", dataName, getLineNumber(ctx));
            dataEntry.addChild(nameNode);
        }

        // Create data structure info
        DataStructureInfo dataInfo = new DataStructureInfo();
        dataInfo.name = dataName != null ? dataName : "UNNAMED";
        dataInfo.level = level;
        dataInfo.lineNumber = getLineNumber(ctx);
        dataInfo.section = getCurrentSection();

        // Process picture clause
        if (ctx.dataPictureClause() != null) {
            String picString = ctx.dataPictureClause().pictureString().getText();
            ASTNode picNode = new ASTNode("PICTURE-CLAUSE", picString, getLineNumber(ctx));
            dataEntry.addChild(picNode);
            dataInfo.picture = picString;
            dataInfo.dataType = inferDataTypeFromPicture(picString);
            dataInfo.javaType = suggestJavaType(picString);
            log("📸 Added PICTURE clause: " + picString + " (type: " + dataInfo.dataType + ")");
        }

        // Process value clause
        if (ctx.dataValueClause() != null) {
            processValueClause(ctx.dataValueClause(), dataEntry);
            CobolParser.DataValueIntervalContext interval = ctx.dataValueClause().dataValueInterval();
            if (interval != null) {
                dataInfo.value = interval.dataValueIntervalFrom().getText();
                dataInfo.hasValue = true;
                if (interval.dataValueIntervalTo() != null) {
                    dataInfo.valueTo = interval.dataValueIntervalTo().getText();
                }
            }
            log("💎 Processed VALUE clause: " + dataInfo.value);
        }

        // Process other clauses
        for (CobolParser.OtherDataClauseContext otherCtx : ctx.otherDataClause()) {
            ASTNode clauseNode = null;
            if (otherCtx.dataUsageClause() != null) {
                String usage = otherCtx.dataUsageClause().getText();
                clauseNode = new ASTNode("USAGE-CLAUSE", usage, getLineNumber(ctx));
                dataInfo.usage = usage;
                log("🛠 Added USAGE clause: " + usage);
            } else if (otherCtx.dataRedefinesClause() != null) {
                String redefines = otherCtx.dataRedefinesClause().dataName().getText();
                clauseNode = new ASTNode("REDEFINES-CLAUSE", redefines, getLineNumber(ctx));
                dataInfo.redefines = redefines;
                log("🔄 Added REDEFINES clause: " + redefines);
            } else if (otherCtx.dataOccursClause() != null) {
                String occurs = otherCtx.dataOccursClause().getText();
                clauseNode = new ASTNode("OCCURS-CLAUSE", occurs, getLineNumber(ctx));
                dataInfo.occurs = occurs;
                dataInfo.isArray = true;
                
                if (otherCtx.dataOccursClause().integerLiteral() != null) {
                    dataInfo.arraySize = otherCtx.dataOccursClause().integerLiteral().getText();
                }
                
                log("🔁 Added OCCURS clause: " + occurs + " (array size: " + dataInfo.arraySize + ")");
            }
            
            if (clauseNode != null) {
                dataEntry.addChild(clauseNode);
            }
            ASTNode otherClauseNode = visit(otherCtx);
            if (otherClauseNode != null) {
                dataEntry.addChild(otherClauseNode);
            }
        }

        // Enhanced filtering - include more data structures for complete analysis
        if (shouldIncludeDataStructureEnhanced(dataName, level, dataInfo)) {
            dataStructures.add(dataInfo);
            log("✅ Added data structure: " + dataName + " (level " + level + ", type: " + 
                dataInfo.dataType + ", section: " + dataInfo.section + ")");
        }

        return dataEntry;
    }


    @Override
    public ASTNode visitDataRenamesClause(CobolParser.DataRenamesClauseContext ctx) {
        log("🔍 Visiting RENAMES clause");
        
        ASTNode renamesNode = new ASTNode("RENAMES-CLAUSE", null, getLineNumber(ctx));
        
        // Starting field
        if (ctx.qualifiedDataName() != null && !ctx.qualifiedDataName().isEmpty()) {
            String startField = ctx.qualifiedDataName(0).getText();
            ASTNode startNode = new ASTNode("RENAMES-FROM", startField, getLineNumber(ctx));
            renamesNode.addChild(startNode);
            
            // Ending field (if THRU/THROUGH is used)
            if (ctx.qualifiedDataName().size() > 1) {
                String endField = ctx.qualifiedDataName(1).getText();
                ASTNode endNode = new ASTNode("RENAMES-TO", endField, getLineNumber(ctx));
                renamesNode.addChild(endNode);
            }
        }
        
        return renamesNode;
    }
    private void processValueClause(CobolParser.DataValueClauseContext ctx, ASTNode parentNode) {
        log("💎 Processing VALUE clause");
        ASTNode valueNode = new ASTNode("VALUE-CLAUSE", null, getLineNumber(ctx));
        CobolParser.DataValueIntervalContext intervalCtx = ctx.dataValueInterval();
        if (intervalCtx != null) {
            String value = intervalCtx.dataValueIntervalFrom().getText();
            ASTNode fromNode = new ASTNode("VALUE-FROM", value, getLineNumber(ctx));
            valueNode.addChild(fromNode);
            // Update DataStructureInfo if passed (not here, handled in caller)
            if (intervalCtx.dataValueIntervalTo() != null) {
                String toValue = intervalCtx.dataValueIntervalTo().getText();
                ASTNode toNode = new ASTNode("VALUE-TO", toValue, getLineNumber(ctx));
                valueNode.addChild(toNode);
            }
        }
        parentNode.addChild(valueNode);
    }

    private String getRuleName(RuleContext ctx) {
        return ctx.getClass().getSimpleName().replace("Context", "");
    }
    
    
    private void setCurrentSection(String section) {
        this.currentSection = section;
        log("📍 Current section: " + section);
    }
    
    @Override
    public ASTNode visitDataValueClause(CobolParser.DataValueClauseContext ctx) {
        log("🔍 Visiting VALUE clause");
        ASTNode valueNode = new ASTNode("VALUE-CLAUSE", null, getLineNumber(ctx));
        CobolParser.DataValueIntervalContext intervalCtx = ctx.dataValueInterval();
        if (intervalCtx != null) {
            String value = intervalCtx.dataValueIntervalFrom().getText();
            ASTNode fromNode = new ASTNode("VALUE-FROM", value, getLineNumber(ctx));
            valueNode.addChild(fromNode);
            if (intervalCtx.dataValueIntervalTo() != null) {
                String toValue = intervalCtx.dataValueIntervalTo().getText();
                ASTNode toNode = new ASTNode("VALUE-TO", toValue, getLineNumber(ctx));
                valueNode.addChild(toNode);
            }
        }
        return valueNode;
    }
    @Override
    public ASTNode visitDataClause(CobolParser.DataClauseContext ctx) {
        if (ctx.dataPictureClause() != null) {
            return visit(ctx.dataPictureClause());
        } else if (ctx.dataValueClause() != null) {
            return visit(ctx.dataValueClause());
        } else if (ctx.dataRedefinesClause() != null) {
            return visit(ctx.dataRedefinesClause());
        } else if (ctx.dataOccursClause() != null) {
            return visit(ctx.dataOccursClause());
        } else if (ctx.dataUsageClause() != null) {
            return visit(ctx.dataUsageClause());
        }
        
        // Handle other data clauses generically
        return new ASTNode("DATA-CLAUSE", ctx.getText(), getLineNumber(ctx));
    }
    
    @Override
    public ASTNode visitDataPictureClause(CobolParser.DataPictureClauseContext ctx) {
        log("🔍 Visiting PICTURE clause");
        
        ASTNode picNode = new ASTNode("PICTURE-CLAUSE", null, getLineNumber(ctx));
        
        if (ctx.pictureString() != null) {
            String picString = ctx.pictureString().getText();
            ASTNode picValueNode = new ASTNode("PICTURE-STRING", picString, getLineNumber(ctx));
            picNode.addChild(picValueNode);
        }
        
        return picNode;
    }
    
    
    @Override
    public ASTNode visitDataValueInterval(CobolParser.DataValueIntervalContext ctx) {
        ASTNode intervalNode = new ASTNode("VALUE-INTERVAL", null, getLineNumber(ctx));
        
        if (ctx.dataValueIntervalFrom() != null) {
            String fromValue = ctx.dataValueIntervalFrom().getText();
            ASTNode fromNode = new ASTNode("VALUE-FROM", fromValue, getLineNumber(ctx));
            intervalNode.addChild(fromNode);
        }
        
        if (ctx.dataValueIntervalTo() != null) {
            String toValue = ctx.dataValueIntervalTo().getText();
            ASTNode toNode = new ASTNode("VALUE-TO", toValue, getLineNumber(ctx));
            intervalNode.addChild(toNode);
        }
        
        return intervalNode;
    }
    
    @Override
    public ASTNode visitCommunicationSection(CobolParser.CommunicationSectionContext ctx) {
        log("🔍 Visiting COMMUNICATION SECTION");
        
        ASTNode commSection = new ASTNode("COMMUNICATION-SECTION", null, getLineNumber(ctx));
        
        // Visit communication description entries
        for (CobolParser.CommunicationDescriptionEntryContext entryCtx : ctx.communicationDescriptionEntry()) {
            ASTNode entryNode = visit(entryCtx);
            if (entryNode != null) commSection.addChild(entryNode);
        }
        
        // Visit data description groups
        for (CobolParser.DataDescriptionGroupContext groupCtx : ctx.dataDescriptionGroup()) {
            ASTNode groupNode = visit(groupCtx);
            if (groupNode != null) commSection.addChild(groupNode);
        }
        
        return commSection;
    }
    
    @Override
    public ASTNode visitCommunicationDescriptionEntryFormat1(CobolParser.CommunicationDescriptionEntryFormat1Context ctx) {
        log("🔍 Visiting CD entry for INPUT");
        
        ASTNode cdNode = new ASTNode("CD-INPUT", null, getLineNumber(ctx));
        
        if (ctx.cdName() != null) {
            String cdName = ctx.cdName().getText();
            ASTNode nameNode = new ASTNode("CD-NAME", cdName, getLineNumber(ctx));
            cdNode.addChild(nameNode);
        }
        
        // APPLY SAME HIERARCHY FIX AS WORKING STORAGE
        List<ASTNode> allDataItems = new ArrayList<>();
        for (CobolParser.DataDescriptionGroupContext groupCtx : ctx.dataDescriptionGroup()) {
            collectAllDataItemsFlat(groupCtx, allDataItems);
        }
        
        ASTNode restructured = Postprocess.restructureByLevelNumbers(allDataItems);
        for (ASTNode child : restructured.children) {
            cdNode.addChild(child);
        }
        
        return cdNode;
    }
    
    @Override
    public ASTNode visitCommunicationDescriptionEntryFormat2(CobolParser.CommunicationDescriptionEntryFormat2Context ctx) {
        log("🔍 Visiting CD entry for OUTPUT");
        
        ASTNode cdNode = new ASTNode("CD-OUTPUT", null, getLineNumber(ctx));
        
        if (ctx.cdName() != null) {
            String cdName = ctx.cdName().getText();
            ASTNode nameNode = new ASTNode("CD-NAME", cdName, getLineNumber(ctx));
            cdNode.addChild(nameNode);
            
            // Create communication info
            CommunicationInfo commInfo = new CommunicationInfo();
            commInfo.name = cdName;
            commInfo.type = "OUTPUT";
            commInfo.lineNumber = getLineNumber(ctx);
            communicationDescriptions.add(commInfo);
            
            log("✅ Added communication description: " + cdName + " (OUTPUT)");
        }
        
        return cdNode;
    }


    // Enhanced PROCEDURE DIVISION visitor methods

    @Override
    public ASTNode visitProcedureDivision(CobolParser.ProcedureDivisionContext ctx) {
        log("🔍 ========== Visiting PROCEDURE DIVISION ==========");
        
        ASTNode procDiv = new ASTNode("PROCEDURE-DIVISION", null, getLineNumber(ctx));
        
        // Handle USING clause
        if (ctx.procedureDivisionUsingClause() != null) {
            log("🔍 Processing USING clause");
            ASTNode usingNode = visit(ctx.procedureDivisionUsingClause());
            if (usingNode != null) {
                procDiv.addChild(usingNode);
                log("✅ Added USING clause with " + usingNode.children.size() + " parameters");
            }
        }
        
        // Handle GIVING clause
        if (ctx.procedureDivisionGivingClause() != null) {
            log("🔍 Processing GIVING clause");
            ASTNode givingNode = visit(ctx.procedureDivisionGivingClause());
            if (givingNode != null) {
                procDiv.addChild(givingNode);
                log("✅ Added GIVING clause");
            }
        }
        
        // Handle declaratives
        if (ctx.procedureDeclaratives() != null) {
            log("🔍 Processing DECLARATIVES");
            ASTNode declNode = visit(ctx.procedureDeclaratives());
            if (declNode != null) {
                procDiv.addChild(declNode);
                log("✅ Added DECLARATIVES section");
            }
        }
        
        // Handle body - This is the critical part!
        if (ctx.procedureDivisionBody() != null) {
            log("🔍 Processing PROCEDURE DIVISION BODY");
            ASTNode bodyNode = visit(ctx.procedureDivisionBody());
            if (bodyNode != null) {
                procDiv.addChild(bodyNode);
                log("✅ Added PROCEDURE BODY with " + bodyNode.children.size() + " children");
            } else {
                log("❌ PROCEDURE BODY returned null!");
            }
        } else {
            log("❌ No PROCEDURE DIVISION BODY found in context!");
        }
        
        log("🔍 ========== PROCEDURE DIVISION Complete: " + procDiv.children.size() + " children ==========");
        
        return procDiv;
    }

    @Override
    public ASTNode visitProcedureDivisionUsingClause(CobolParser.ProcedureDivisionUsingClauseContext ctx) {
        ASTNode usingNode = new ASTNode("USING-CLAUSE", null, getLineNumber(ctx));
        
        for (CobolParser.ProcedureDivisionUsingParameterContext paramCtx : ctx.procedureDivisionUsingParameter()) {
            ASTNode paramNode = visit(paramCtx);
            if (paramNode != null) usingNode.addChild(paramNode);
        }
        
        return usingNode;
    }

    @Override
    public ASTNode visitProcedureDivisionGivingClause(CobolParser.ProcedureDivisionGivingClauseContext ctx) {
        ASTNode givingNode = new ASTNode("GIVING-CLAUSE", ctx.getText(), getLineNumber(ctx));
        return givingNode;
    }

    @Override
    public ASTNode visitProcedureSection(CobolParser.ProcedureSectionContext ctx) {
        log("🔍 Visiting PROCEDURE SECTION");
        
        ASTNode sectionNode = new ASTNode("PROCEDURE-SECTION", null, getLineNumber(ctx));
        
        // Get section header
        if (ctx.procedureSectionHeader() != null) {
            ASTNode headerNode = visit(ctx.procedureSectionHeader());
            if (headerNode != null) {
                sectionNode.addChild(headerNode);
            }
        }
        
        // Process paragraphs
        if (ctx.paragraphs() != null) {
            ASTNode paragraphsNode = visit(ctx.paragraphs());
            if (paragraphsNode != null) {
                sectionNode.addChild(paragraphsNode);
            }
        }
        
        return sectionNode;
    }

    @Override
    public ASTNode visitExecStatement(CobolParser.ExecStatementContext ctx) {
        log("🔍 Visiting EXEC statement");
        
        ASTNode execNode = new ASTNode("EXEC-STATEMENT", null, getLineNumber(ctx));
        
        String execType = ctx.IDENTIFIER() != null ? ctx.IDENTIFIER().getText() : 
                        (ctx.SQL() != null ? "SQL" : "CICS");
        ASTNode typeNode = new ASTNode("EXEC-TYPE", execType, getLineNumber(ctx));
        execNode.addChild(typeNode);
        
        ASTNode contentNode = new ASTNode("EXEC-CONTENT", ctx.getText(), getLineNumber(ctx));
        execNode.addChild(contentNode);
        
        return execNode;
    }

    @Override
    public ASTNode visitUnknownStatement(CobolParser.UnknownStatementContext ctx) {
        log("🔍 Visiting UNKNOWN statement");
        
        ASTNode unknownNode = new ASTNode("UNKNOWN-STATEMENT", ctx.getText(), getLineNumber(ctx));
        ASTNode verbNode = new ASTNode("VERB", ctx.IDENTIFIER().getText(), getLineNumber(ctx));
        unknownNode.addChild(verbNode);
        
        return unknownNode;
    }

    
    @Override
    public ASTNode visitParagraphs(CobolParser.ParagraphsContext ctx) {
        log("🔍 Visiting paragraphs");
        
        ASTNode paragraphsNode = new ASTNode("PARAGRAPHS", null, getLineNumber(ctx));
        
        // Process each paragraph
        for (CobolParser.ParagraphContext paraCtx : ctx.paragraph()) {
            ASTNode paraNode = visit(paraCtx);
            if (paraNode != null) {
                paragraphsNode.addChild(paraNode);
            }
        }
        
        return paragraphsNode;
    }

    @Override
    public ASTNode visitParagraph(CobolParser.ParagraphContext ctx) {
        log("🔍 Visiting paragraph");
        
        ASTNode paragraphNode = new ASTNode("PARAGRAPH", null, getLineNumber(ctx));
        
        // Extract paragraph name
        String paragraphName = "UNKNOWN";
        if (ctx.paragraphName() != null) {
            paragraphName = ctx.paragraphName().getText();
            ASTNode nameNode = new ASTNode("PARAGRAPH-NAME", paragraphName, getLineNumber(ctx));
            paragraphNode.addChild(nameNode);
        }
        
        // Create procedure info
        ProcedureInfo procInfo = new ProcedureInfo();
        procInfo.name = paragraphName;
        procInfo.suggestedMethodName = toMethodName(paragraphName);
        procInfo.lineNumber = getLineNumber(ctx);
        
        // Visit sentences and collect referenced data items
        int statementCount = 0;
        Set<String> referencedDataItems = new HashSet<>();
        
        for (CobolParser.SentenceContext sentenceCtx : ctx.sentence()) {
            ASTNode sentenceNode = visit(sentenceCtx);
            if (sentenceNode != null) {
                paragraphNode.addChild(sentenceNode);
                statementCount += countStatements(sentenceCtx);
                collectReferencedDataItems(sentenceCtx, referencedDataItems);
            }
        }
        
        procInfo.statementCount = statementCount;
        procInfo.complexityScore = calculateComplexity(statementCount, ctx, referencedDataItems);
        procInfo.referencedDataItems = new ArrayList<>(referencedDataItems);
        procedures.add(procInfo);
        
        log("✅ Added procedure: " + paragraphName + " (" + statementCount + " statements, complexity: " + procInfo.complexityScore + ")");
        
        return paragraphNode;
    }

    @Override
    public ASTNode visitAddStatement(CobolParser.AddStatementContext ctx) {
        log("🔍 Visiting ADD statement");
        
        ASTNode addNode = new ASTNode("ADD-STATEMENT", null, getLineNumber(ctx));
        
        if (ctx.addToStatement() != null) {
            ASTNode addToNode = visit(ctx.addToStatement());
            if (addToNode != null) addNode.addChild(addToNode);
        } else if (ctx.addToGivingStatement() != null) {
            ASTNode addGivingNode = visit(ctx.addToGivingStatement());
            if (addGivingNode != null) addNode.addChild(addGivingNode);
        } else if (ctx.addCorrespondingStatement() != null) {
            ASTNode addCorrNode = visit(ctx.addCorrespondingStatement());
            if (addCorrNode != null) addNode.addChild(addCorrNode);
        }
        
        return addNode;
    }
    @Override
    public ASTNode visitSubtractStatement(CobolParser.SubtractStatementContext ctx) {
        log("🔍 Visiting SUBTRACT statement");
        
        ASTNode subtractNode = new ASTNode("SUBTRACT-STATEMENT", null, getLineNumber(ctx));
        
        if (ctx.subtractFromStatement() != null) {
            ASTNode fromNode = visit(ctx.subtractFromStatement());
            if (fromNode != null) subtractNode.addChild(fromNode);
        } else if (ctx.subtractFromGivingStatement() != null) {
            ASTNode givingNode = visit(ctx.subtractFromGivingStatement());
            if (givingNode != null) subtractNode.addChild(givingNode);
        } else if (ctx.subtractCorrespondingStatement() != null) {
            ASTNode corrNode = visit(ctx.subtractCorrespondingStatement());
            if (corrNode != null) subtractNode.addChild(corrNode);
        }
        
        return subtractNode;
    }
    
    @Override
    public ASTNode visitMultiplyStatement(CobolParser.MultiplyStatementContext ctx) {
        log("🔍 Visiting MULTIPLY statement");
        
        ASTNode multiplyNode = new ASTNode("MULTIPLY-STATEMENT", null, getLineNumber(ctx));
        
        // Source operand
        if (ctx.identifier() != null || ctx.literal() != null) {
            String source = ctx.identifier() != null ? ctx.identifier().getText() : ctx.literal().getText();
            ASTNode sourceNode = new ASTNode("MULTIPLY-SOURCE", source, getLineNumber(ctx));
            multiplyNode.addChild(sourceNode);
        }
        
        if (ctx.multiplyRegular() != null) {
            ASTNode regularNode = visit(ctx.multiplyRegular());
            if (regularNode != null) multiplyNode.addChild(regularNode);
        } else if (ctx.multiplyGiving() != null) {
            ASTNode givingNode = visit(ctx.multiplyGiving());
            if (givingNode != null) multiplyNode.addChild(givingNode);
        }
        
        return multiplyNode;
    }
    
    @Override
    public ASTNode visitDivideStatement(CobolParser.DivideStatementContext ctx) {
        log("🔍 Visiting DIVIDE statement");
        
        ASTNode divideNode = new ASTNode("DIVIDE-STATEMENT", null, getLineNumber(ctx));
        
        // Source operand
        if (ctx.identifier() != null || ctx.literal() != null) {
            String source = ctx.identifier() != null ? ctx.identifier().getText() : ctx.literal().getText();
            ASTNode sourceNode = new ASTNode("DIVIDE-SOURCE", source, getLineNumber(ctx));
            divideNode.addChild(sourceNode);
        }
        
        if (ctx.divideIntoStatement() != null) {
            ASTNode intoNode = visit(ctx.divideIntoStatement());
            if (intoNode != null) divideNode.addChild(intoNode);
        } else if (ctx.divideIntoGivingStatement() != null) {
            ASTNode givingNode = visit(ctx.divideIntoGivingStatement());
            if (givingNode != null) divideNode.addChild(givingNode);
        } else if (ctx.divideByGivingStatement() != null) {
            ASTNode byGivingNode = visit(ctx.divideByGivingStatement());
            if (byGivingNode != null) divideNode.addChild(byGivingNode);
        }
        
        return divideNode;
    }
    @Override
    public ASTNode visitReadStatement(CobolParser.ReadStatementContext ctx) {
        log("🔍 Visiting READ statement");
        
        ASTNode readNode = new ASTNode("READ-STATEMENT", null, getLineNumber(ctx));
        
        // File name
        if (ctx.fileName() != null) {
            ASTNode fileNode = new ASTNode("READ-FILE", ctx.fileName().getText(), getLineNumber(ctx));
            readNode.addChild(fileNode);
        }
        
        // NEXT option
        if (ctx.NEXT() != null) {
            ASTNode nextNode = new ASTNode("READ-NEXT", "true", getLineNumber(ctx));
            readNode.addChild(nextNode);
        }
        
        // INTO clause
        if (ctx.readInto() != null) {
            ASTNode intoNode = new ASTNode("READ-INTO", ctx.readInto().getText(), getLineNumber(ctx));
            readNode.addChild(intoNode);
        }
        
        return readNode;
    }

    // Updated complexity calculation
    private int calculateComplexity(int statementCount, CobolParser.ParagraphContext ctx, Set<String> referencedDataItems) {
        int complexity = statementCount;
        
        String text = ctx.getText().toUpperCase();
        complexity += countOccurrences(text, "IF") * 2;
        complexity += countOccurrences(text, "PERFORM");
        complexity += countOccurrences(text, "EVALUATE") * 2;
        complexity += countOccurrences(text, "GO TO");
        complexity += countOccurrences(text, "CALL") * 2;
        
        // Add complexity for data dependencies
        complexity += referencedDataItems.size();
        
        return complexity;
    }

    private void collectReferencedDataItems(CobolParser.SentenceContext ctx, Set<String> referencedDataItems) {
        Util.collectReferencedDataItems(ctx,  referencedDataItems);
    }
    
    private void collectFromStatement(CobolParser.StatementContext stmtCtx, Set<String> referencedDataItems) {
        Util.collectFromStatement(stmtCtx, referencedDataItems);
    }

    // Update ProcedureInfo class
    static class ProcedureInfo {
        String name;
        String suggestedMethodName;
        int statementCount;
        int complexityScore;
        int lineNumber;
        List<String> referencedDataItems = new ArrayList<>();
        List<String> usingParameters = new ArrayList<>();
        String givingReturn = null;
    }

    @Override
    public ASTNode visitProcedureDivisionBody(CobolParser.ProcedureDivisionBodyContext ctx) {
        log("🔍 Visiting PROCEDURE DIVISION BODY");
        
        ASTNode bodyNode = new ASTNode("PROCEDURE-BODY", null, getLineNumber(ctx));
        
        // Process both standalone paragraphs and procedure sections
        for (int i = 0; i < ctx.getChildCount(); i++) {
            ParseTree child = ctx.getChild(i);
            if (child instanceof CobolParser.ParagraphContext) {
                ASTNode paraNode = visit((CobolParser.ParagraphContext) child);
                if (paraNode != null) {
                    bodyNode.addChild(paraNode);
                }
            } else if (child instanceof CobolParser.ProcedureSectionContext) {
                ASTNode sectionNode = visit((CobolParser.ProcedureSectionContext) child);
                if (sectionNode != null) {
                    bodyNode.addChild(sectionNode);
                }
            }
        }
        
        return bodyNode;
    }

    /*  
    @Override
    public ASTNode visitProcedureDivision(CobolParser.ProcedureDivisionContext ctx) {
        log("🔍 Visiting PROCEDURE DIVISION");
        
        ASTNode procDiv = new ASTNode("PROCEDURE-DIVISION", null, getLineNumber(ctx));
        
        // Visit procedure division body
        if (ctx.procedureDivisionBody() != null) {
            ASTNode bodyNode = visit(ctx.procedureDivisionBody());
            if (bodyNode != null) procDiv.addChild(bodyNode);
        }
        
        return procDiv;
    }
    
    @Override
    public ASTNode visitParagraph(CobolParser.ParagraphContext ctx) {
        log("🔍 Visiting paragraph");
        
        ASTNode paragraphNode = new ASTNode("PARAGRAPH", null, getLineNumber(ctx));
        
        // Extract paragraph name
        String paragraphName = "UNKNOWN";
        if (ctx.paragraphName() != null) {
            paragraphName = ctx.paragraphName().getText();
            ASTNode nameNode = new ASTNode("PARAGRAPH-NAME", paragraphName, getLineNumber(ctx));
            paragraphNode.addChild(nameNode);
        }
        
        // Create procedure info
        ProcedureInfo procInfo = new ProcedureInfo();
        procInfo.name = paragraphName;
        procInfo.suggestedMethodName = toMethodName(paragraphName);
        procInfo.lineNumber = getLineNumber(ctx);
        
        // Visit sentences
        int statementCount = 0;
        for (CobolParser.SentenceContext sentenceCtx : ctx.sentence()) {
            ASTNode sentenceNode = visit(sentenceCtx);
            if (sentenceNode != null) {
                paragraphNode.addChild(sentenceNode);
                statementCount += countStatements(sentenceCtx);
            }
        }
        
        procInfo.statementCount = statementCount;
        procInfo.complexityScore = calculateComplexity(statementCount, ctx);
        procedures.add(procInfo);
        
        log("✅ Added procedure: " + paragraphName + " (" + statementCount + " statements)");
        
        return paragraphNode;
    }
    */
    
    @Override
    public ASTNode visitStatement(CobolParser.StatementContext ctx) {
        log("🔍 Visiting statement: " + ctx.getClass().getSimpleName());
        
        // Handle all statement types systematically
        if (ctx.acceptStatement() != null) {
            return visit(ctx.acceptStatement());
        } else if (ctx.addStatement() != null) {
            return visit(ctx.addStatement());
        } else if (ctx.alterStatement() != null) {
            return visit(ctx.alterStatement());
        } else if (ctx.allocateStatement() != null) {
            return visit(ctx.allocateStatement());
        } else if (ctx.callStatement() != null) {
            return visit(ctx.callStatement());
        } else if (ctx.cancelStatement() != null) {
            return visit(ctx.cancelStatement());
        } else if (ctx.closeStatement() != null) {
            return visit(ctx.closeStatement());
        } else if (ctx.computeStatement() != null) {
            return visit(ctx.computeStatement());
        } else if (ctx.continueStatement() != null) {
            return visit(ctx.continueStatement());
        } else if (ctx.deleteStatement() != null) {
            return visit(ctx.deleteStatement());
        } else if (ctx.disableStatement() != null) {
            return visit(ctx.disableStatement());
        } else if (ctx.displayStatement() != null) {
            return visit(ctx.displayStatement());
        } else if (ctx.divideStatement() != null) {
            return visit(ctx.divideStatement());
        } else if (ctx.enableStatement() != null) {
            return visit(ctx.enableStatement());
        } else if (ctx.entryStatement() != null) {
            return visit(ctx.entryStatement());
        } else if (ctx.evaluateStatement() != null) {
            return visit(ctx.evaluateStatement());
        } else if (ctx.exhibitStatement() != null) {
            return visit(ctx.exhibitStatement());
        } else if (ctx.execCicsStatement() != null) {
            return visit(ctx.execCicsStatement());
        } else if (ctx.execSqlStatement() != null) {
            return visit(ctx.execSqlStatement());
        } else if (ctx.execSqlImsStatement() != null) {
            return visit(ctx.execSqlImsStatement());
        } else if (ctx.exitStatement() != null) {
            return visit(ctx.exitStatement());
        } else if (ctx.freeStatement() != null) {
            return visit(ctx.freeStatement());
        } else if (ctx.generateStatement() != null) {
            return visit(ctx.generateStatement());
        } else if (ctx.gobackStatement() != null) {
            return visit(ctx.gobackStatement());
        } else if (ctx.goToStatement() != null) {
            return visit(ctx.goToStatement());
        } else if (ctx.ifStatement() != null) {
            return visit(ctx.ifStatement());
        } else if (ctx.initializeStatement() != null) {
            return visit(ctx.initializeStatement());
        } else if (ctx.initiateStatement() != null) {
            return visit(ctx.initiateStatement());
        } else if (ctx.inspectStatement() != null) {
            return visit(ctx.inspectStatement());
        } else if (ctx.invokeStatement() != null) {
            return visit(ctx.invokeStatement());
        } else if (ctx.jsonGenerateStatement() != null) {
            return visit(ctx.jsonGenerateStatement());
        } else if (ctx.jsonParseStatement() != null) {
            return visit(ctx.jsonParseStatement());
        } else if (ctx.mergeStatement() != null) {
            return visit(ctx.mergeStatement());
        } else if (ctx.moveStatement() != null) {
            return visit(ctx.moveStatement());
        } else if (ctx.multiplyStatement() != null) {
            return visit(ctx.multiplyStatement());
        } else if (ctx.nextSentenceStatement() != null) {
            return visit(ctx.nextSentenceStatement());
        } else if (ctx.openStatement() != null) {
            return visit(ctx.openStatement());
        } else if (ctx.performStatement() != null) {
            return visit(ctx.performStatement());
        } else if (ctx.purgeStatement() != null) {
            return visit(ctx.purgeStatement());
        } else if (ctx.raiseStatement() != null) {
            return visit(ctx.raiseStatement());
        } else if (ctx.readStatement() != null) {
            return visit(ctx.readStatement());
        } else if (ctx.receiveStatement() != null) {
            return visit(ctx.receiveStatement());
        } else if (ctx.releaseStatement() != null) {
            return visit(ctx.releaseStatement());
        } else if (ctx.resumeStatement() != null) {
            return visit(ctx.resumeStatement());
        } else if (ctx.returnStatement() != null) {
            return visit(ctx.returnStatement());
        } else if (ctx.rewriteStatement() != null) {
            return visit(ctx.rewriteStatement());
        } else if (ctx.searchStatement() != null) {
            return visit(ctx.searchStatement());
        } else if (ctx.sendStatement() != null) {
            return visit(ctx.sendStatement());
        } else if (ctx.setStatement() != null) {
            return visit(ctx.setStatement());
        } else if (ctx.sortStatement() != null) {
            return visit(ctx.sortStatement());
        } else if (ctx.startStatement() != null) {
            return visit(ctx.startStatement());
        } else if (ctx.stopStatement() != null) {
            return visit(ctx.stopStatement());
        } else if (ctx.stringStatement() != null) {
            return visit(ctx.stringStatement());
        } else if (ctx.subtractStatement() != null) {
            return visit(ctx.subtractStatement());
        } else if (ctx.terminateStatement() != null) {
            return visit(ctx.terminateStatement());
        } else if (ctx.unstringStatement() != null) {
            return visit(ctx.unstringStatement());
        } else if (ctx.writeStatement() != null) {
            return visit(ctx.writeStatement());
        } else if (ctx.xmlGenerateStatement() != null) {
            return visit(ctx.xmlGenerateStatement());
        } else if (ctx.xmlParseStatement() != null) {
            return visit(ctx.xmlParseStatement());
        } else if (ctx.execStatement() != null) {
            return visit(ctx.execStatement());
        } else if (ctx.unknownStatement() != null) {
            return visit(ctx.unknownStatement());
        }
        
        // Fallback for unhandled statements
        log("⚠️ Unhandled statement type: " + ctx.getText());
        return new ASTNode("UNHANDLED-STATEMENT", ctx.getText(), getLineNumber(ctx));
    }

    @Override
    public ASTNode visitGoToStatement(CobolParser.GoToStatementContext ctx) {
        log("🔍 Visiting GO TO statement");
        
        ASTNode gotoNode = new ASTNode("GOTO-STATEMENT", null, getLineNumber(ctx));
        
        // Handle simple GO TO
        if (ctx.goToStatementSimple() != null) {
            ASTNode simpleNode = visit(ctx.goToStatementSimple());
            if (simpleNode != null) {
                gotoNode.addChild(simpleNode);
            }
        }
        
        // Handle GO TO DEPENDING ON
        if (ctx.goToDependingOnStatement() != null) {
            ASTNode dependingNode = visit(ctx.goToDependingOnStatement());
            if (dependingNode != null) {
                gotoNode.addChild(dependingNode);
            }
        }
        
        return gotoNode;
    }

    @Override
    public ASTNode visitGoToStatementSimple(CobolParser.GoToStatementSimpleContext ctx) {
        log("🔍 Visiting simple GO TO statement");
        
        ASTNode simpleNode = new ASTNode("GOTO-SIMPLE", null, getLineNumber(ctx));
        
        // Get procedure name
        if (ctx.procedureName() != null) {
            String procName = ctx.procedureName().getText();
            ASTNode targetNode = new ASTNode("GOTO-TARGET", procName, getLineNumber(ctx));
            simpleNode.addChild(targetNode);
        }
        
        return simpleNode;
    }

    @Override
    public ASTNode visitStopStatement(CobolParser.StopStatementContext ctx) {
        log("🔍 Visiting STOP statement");
        
        ASTNode stopNode = new ASTNode("STOP-STATEMENT", null, getLineNumber(ctx));
        
        // Handle different STOP formats
        if (ctx.RUN() != null) {
            ASTNode runNode = new ASTNode("STOP-TYPE", "RUN", getLineNumber(ctx));
            stopNode.addChild(runNode);
        } else if (ctx.literal() != null) {
            ASTNode literalNode = new ASTNode("STOP-LITERAL", ctx.literal().getText(), getLineNumber(ctx));
            stopNode.addChild(literalNode);
        } else if (ctx.stopStatementGiving() != null) {
            ASTNode givingNode = visit(ctx.stopStatementGiving());
            if (givingNode != null) {
                stopNode.addChild(givingNode);
            }
        }
        
        return stopNode;
    }

    @Override
    public ASTNode visitStopStatementGiving(CobolParser.StopStatementGivingContext ctx) {
        ASTNode givingNode = new ASTNode("STOP-GIVING", null, getLineNumber(ctx));
        
        // Return value
        if (ctx.identifier() != null) {
            ASTNode returnNode = new ASTNode("RETURN-VALUE", ctx.identifier().getText(), getLineNumber(ctx));
            givingNode.addChild(returnNode);
        } else if (ctx.integerLiteral() != null) {
            ASTNode returnNode = new ASTNode("RETURN-VALUE", ctx.integerLiteral().getText(), getLineNumber(ctx));
            givingNode.addChild(returnNode);
        }
        
        return givingNode;
    }
    @Override
    public ASTNode visitCloseStatement(CobolParser.CloseStatementContext ctx) {
        log("🔍 Visiting CLOSE statement");
        
        ASTNode closeNode = new ASTNode("CLOSE-STATEMENT", null, getLineNumber(ctx));
        
        // Process close file entries
        for (CobolParser.CloseFileContext fileCtx : ctx.closeFile()) {
            ASTNode fileNode = visit(fileCtx);
            if (fileNode != null) {
                closeNode.addChild(fileNode);
            }
        }
        
        return closeNode;
    }

    @Override
    public ASTNode visitCloseFile(CobolParser.CloseFileContext ctx) {
        ASTNode fileNode = new ASTNode("CLOSE-FILE", null, getLineNumber(ctx));
        
        // File name
        if (ctx.fileName() != null) {
            ASTNode nameNode = new ASTNode("FILE-NAME", ctx.fileName().getText(), getLineNumber(ctx));
            fileNode.addChild(nameNode);
        }
        
        // Close options
        if (ctx.closeReelUnitStatement() != null) {
            ASTNode reelNode = new ASTNode("CLOSE-REEL-UNIT", ctx.closeReelUnitStatement().getText(), getLineNumber(ctx));
            fileNode.addChild(reelNode);
        } else if (ctx.closeRelativeStatement() != null) {
            ASTNode relativeNode = new ASTNode("CLOSE-RELATIVE", ctx.closeRelativeStatement().getText(), getLineNumber(ctx));
            fileNode.addChild(relativeNode);
        } else if (ctx.closePortFileIOStatement() != null) {
            ASTNode portNode = new ASTNode("CLOSE-PORT-FILE-IO", ctx.closePortFileIOStatement().getText(), getLineNumber(ctx));
            fileNode.addChild(portNode);
        }
        
        return fileNode;
    }

    @Override
    public ASTNode visitPerformStatement(CobolParser.PerformStatementContext ctx) {
        log("🔍 Visiting PERFORM statement");
        
        ASTNode performNode = new ASTNode("PERFORM-STATEMENT", null, getLineNumber(ctx));
        
        if (ctx.performInlineStatement() != null) {
            // Inline perform
            ASTNode inlineNode = visit(ctx.performInlineStatement());
            if (inlineNode != null) performNode.addChild(inlineNode);
        } else if (ctx.performProcedureStatement() != null) {
            // Procedure perform
            ASTNode procNode = visit(ctx.performProcedureStatement());
            if (procNode != null) performNode.addChild(procNode);
        }
        
        return performNode;
    }

    @Override
    public ASTNode visitPerformInlineStatement(CobolParser.PerformInlineStatementContext ctx) {
        ASTNode inlineNode = new ASTNode("PERFORM-INLINE", null, getLineNumber(ctx));
        
        // Perform type (TIMES, UNTIL, VARYING)
        if (ctx.performType() != null) {
            ASTNode typeNode = visit(ctx.performType());
            if (typeNode != null) inlineNode.addChild(typeNode);
        }
        
        // Inline statements
        for (CobolParser.StatementContext stmtCtx : ctx.statement()) {
            ASTNode stmtNode = visit(stmtCtx);
            if (stmtNode != null) inlineNode.addChild(stmtNode);
        }
        
        return inlineNode;
    }

    @Override
    public ASTNode visitPerformProcedureStatement(CobolParser.PerformProcedureStatementContext ctx) {
        ASTNode procNode = new ASTNode("PERFORM-PROCEDURE", null, getLineNumber(ctx));
        
        // Procedure name(s)
        if (ctx.procedureName() != null && !ctx.procedureName().isEmpty()) {
            String startProc = ctx.procedureName(0).getText();
            ASTNode startNode = new ASTNode("PERFORM-START", startProc, getLineNumber(ctx));
            procNode.addChild(startNode);
            
            // THRU clause
            if (ctx.procedureName().size() > 1) {
                String endProc = ctx.procedureName(1).getText();
                ASTNode endNode = new ASTNode("PERFORM-THRU", endProc, getLineNumber(ctx));
                procNode.addChild(endNode);
            }
        }
        
        // Perform type
        if (ctx.performType() != null) {
            ASTNode typeNode = visit(ctx.performType());
            if (typeNode != null) procNode.addChild(typeNode);
        }
        
        return procNode;
    }
   
    @Override
    public ASTNode visitIfStatement(CobolParser.IfStatementContext ctx) {
        log("🔍 Visiting IF statement");
        
        ASTNode ifNode = new ASTNode("IF-STATEMENT", null, getLineNumber(ctx));
        
        // Condition
        if (ctx.condition() != null) {
            ASTNode conditionNode = new ASTNode("IF-CONDITION", ctx.condition().getText(), getLineNumber(ctx));
            ifNode.addChild(conditionNode);
        }
        
        // THEN part
        if (ctx.ifThen() != null) {
            ASTNode thenNode = visit(ctx.ifThen());
            if (thenNode != null) ifNode.addChild(thenNode);
        }
        
        // ELSE part
        if (ctx.ifElse() != null) {
            ASTNode elseNode = visit(ctx.ifElse());
            if (elseNode != null) ifNode.addChild(elseNode);
        }
        
        return ifNode;
    }
    
    @Override
    public ASTNode visitIfThen(CobolParser.IfThenContext ctx) {
        ASTNode thenNode = new ASTNode("IF-THEN", null, getLineNumber(ctx));
        
        // Check for NEXT SENTENCE
        if (ctx.getText().toUpperCase().contains("NEXT SENTENCE")) {
            ASTNode nextSentenceNode = new ASTNode("NEXT-SENTENCE", "true", getLineNumber(ctx));
            thenNode.addChild(nextSentenceNode);
        } else {
            // Process statements
            for (CobolParser.StatementContext stmtCtx : ctx.statement()) {
                ASTNode stmtNode = visit(stmtCtx);
                if (stmtNode != null) thenNode.addChild(stmtNode);
            }
        }
        
        return thenNode;
    }
    
    @Override
    public ASTNode visitIfElse(CobolParser.IfElseContext ctx) {
        ASTNode elseNode = new ASTNode("IF-ELSE", null, getLineNumber(ctx));
        
        // Check for NEXT SENTENCE
        if (ctx.getText().toUpperCase().contains("NEXT SENTENCE")) {
            ASTNode nextSentenceNode = new ASTNode("NEXT-SENTENCE", "true", getLineNumber(ctx));
            elseNode.addChild(nextSentenceNode);
        } else {
            // Process statements
            for (CobolParser.StatementContext stmtCtx : ctx.statement()) {
                ASTNode stmtNode = visit(stmtCtx);
                if (stmtNode != null) elseNode.addChild(stmtNode);
            }
        }
        
        return elseNode;
    }
    

    @Override
    public ASTNode visitComputeStatement(CobolParser.ComputeStatementContext ctx) {
        log("🔍 Visiting COMPUTE statement");
        
        ASTNode computeNode = new ASTNode("COMPUTE-STATEMENT", null, getLineNumber(ctx));
        
        // Target variables (computeStore)
        for (CobolParser.ComputeStoreContext storeCtx : ctx.computeStore()) {
            ASTNode targetNode = new ASTNode("COMPUTE-TARGET", storeCtx.getText(), getLineNumber(storeCtx));
            computeNode.addChild(targetNode);
        }
        
        // Expression
        if (ctx.arithmeticExpression() != null) {
            ASTNode exprNode = new ASTNode("COMPUTE-EXPRESSION", ctx.arithmeticExpression().getText(), getLineNumber(ctx));
            computeNode.addChild(exprNode);
        }
        
        // Error handling phrases
        if (ctx.onSizeErrorPhrase() != null) {
            ASTNode errorNode = new ASTNode("ON-SIZE-ERROR", ctx.onSizeErrorPhrase().getText(), getLineNumber(ctx));
            computeNode.addChild(errorNode);
        }
        
        if (ctx.notOnSizeErrorPhrase() != null) {
            ASTNode notErrorNode = new ASTNode("NOT-ON-SIZE-ERROR", ctx.notOnSizeErrorPhrase().getText(), getLineNumber(ctx));
            computeNode.addChild(notErrorNode);
        }
        
        return computeNode;
    }


    @Override
    public ASTNode visitAcceptStatement(CobolParser.AcceptStatementContext ctx) {
        log("🔍 Visiting ACCEPT statement");
        
        ASTNode acceptNode = new ASTNode("ACCEPT-STATEMENT", null, getLineNumber(ctx));
        
        // Target identifier
        if (ctx.identifier() != null) {
            ASTNode targetNode = new ASTNode("ACCEPT-TARGET", ctx.identifier().getText(), getLineNumber(ctx));
            acceptNode.addChild(targetNode);
        }
        
        // FROM clause variants
        if (ctx.acceptFromDateStatement() != null) {
            ASTNode fromNode = new ASTNode("ACCEPT-FROM", ctx.acceptFromDateStatement().getText(), getLineNumber(ctx));
            acceptNode.addChild(fromNode);
        } else if (ctx.acceptFromEscapeKeyStatement() != null) {
            ASTNode fromNode = new ASTNode("ACCEPT-FROM", "ESCAPE-KEY", getLineNumber(ctx));
            acceptNode.addChild(fromNode);
        } else if (ctx.acceptFromMnemonicStatement() != null) {
            ASTNode fromNode = new ASTNode("ACCEPT-FROM", ctx.acceptFromMnemonicStatement().getText(), getLineNumber(ctx));
            acceptNode.addChild(fromNode);
        } else if (ctx.acceptMessageCountStatement() != null) {
            ASTNode fromNode = new ASTNode("ACCEPT-FROM", "MESSAGE-COUNT", getLineNumber(ctx));
            acceptNode.addChild(fromNode);
        }
        
        // Exception handling
        if (ctx.onExceptionClause() != null) {
            ASTNode exceptionNode = new ASTNode("ACCEPT-ON-EXCEPTION", ctx.onExceptionClause().getText(), getLineNumber(ctx));
            acceptNode.addChild(exceptionNode);
        }
        
        if (ctx.notOnExceptionClause() != null) {
            ASTNode notExceptionNode = new ASTNode("ACCEPT-NOT-ON-EXCEPTION", ctx.notOnExceptionClause().getText(), getLineNumber(ctx));
            acceptNode.addChild(notExceptionNode);
        }
        
        return acceptNode;
    }


    @Override
    public ASTNode visitWriteStatement(CobolParser.WriteStatementContext ctx) {
        log("🔍 Visiting WRITE statement");
        
        ASTNode writeNode = new ASTNode("WRITE-STATEMENT", null, getLineNumber(ctx));
        
        // Record name
        if (ctx.recordName() != null) {
            ASTNode recordNode = new ASTNode("RECORD-NAME", ctx.recordName().getText(), getLineNumber(ctx));
            writeNode.addChild(recordNode);
        }
        
        // FROM clause
        if (ctx.writeFromPhrase() != null) {
            ASTNode fromNode = new ASTNode("WRITE-FROM", ctx.writeFromPhrase().getText(), getLineNumber(ctx));
            writeNode.addChild(fromNode);
        }
        
        // ADVANCING clause
        if (ctx.writeAdvancingPhrase() != null) {
            ASTNode advancingNode = new ASTNode("WRITE-ADVANCING", ctx.writeAdvancingPhrase().getText(), getLineNumber(ctx));
            writeNode.addChild(advancingNode);
        }
        
        // AT END OF PAGE clause
        if (ctx.writeAtEndOfPagePhrase() != null) {
            ASTNode endPageNode = new ASTNode("WRITE-AT-END-OF-PAGE", ctx.writeAtEndOfPagePhrase().getText(), getLineNumber(ctx));
            writeNode.addChild(endPageNode);
        }
        
        // NOT AT END OF PAGE clause
        if (ctx.writeNotAtEndOfPagePhrase() != null) {
            ASTNode notEndPageNode = new ASTNode("WRITE-NOT-AT-END-OF-PAGE", ctx.writeNotAtEndOfPagePhrase().getText(), getLineNumber(ctx));
            writeNode.addChild(notEndPageNode);
        }
        
        // INVALID KEY clause
        if (ctx.invalidKeyPhrase() != null) {
            ASTNode invalidNode = new ASTNode("WRITE-INVALID-KEY", ctx.invalidKeyPhrase().getText(), getLineNumber(ctx));
            writeNode.addChild(invalidNode);
        }
        
        // NOT INVALID KEY clause
        if (ctx.notInvalidKeyPhrase() != null) {
            ASTNode notInvalidNode = new ASTNode("WRITE-NOT-INVALID-KEY", ctx.notInvalidKeyPhrase().getText(), getLineNumber(ctx));
            writeNode.addChild(notInvalidNode);
        }
        
        return writeNode;
    }

    @Override
    public ASTNode visitOpenInputStatement(CobolParser.OpenInputStatementContext ctx) {
        ASTNode inputNode = new ASTNode("OPEN-INPUT", null, getLineNumber(ctx));
        
        for (CobolParser.OpenInputContext inputCtx : ctx.openInput()) {
            ASTNode fileNode = new ASTNode("INPUT-FILE", inputCtx.getText(), getLineNumber(inputCtx));
            inputNode.addChild(fileNode);
        }
        
        return inputNode;
    }

    @Override
    public ASTNode visitOpenOutputStatement(CobolParser.OpenOutputStatementContext ctx) {
        ASTNode outputNode = new ASTNode("OPEN-OUTPUT", null, getLineNumber(ctx));
        
        for (CobolParser.OpenOutputContext outputCtx : ctx.openOutput()) {
            ASTNode fileNode = new ASTNode("OUTPUT-FILE", outputCtx.getText(), getLineNumber(outputCtx));
            outputNode.addChild(fileNode);
        }
        
        return outputNode;
    }

    @Override
    public ASTNode visitOpenStatement(CobolParser.OpenStatementContext ctx) {
        log("🔍 Visiting OPEN statement");
        
        ASTNode openNode = new ASTNode("OPEN-STATEMENT", null, getLineNumber(ctx));
        
        // Handle different open modes
        for (CobolParser.OpenInputStatementContext inputCtx : ctx.openInputStatement()) {
            ASTNode inputNode = visit(inputCtx);
            if (inputNode != null) {
                openNode.addChild(inputNode);
            }
        }
        
        for (CobolParser.OpenOutputStatementContext outputCtx : ctx.openOutputStatement()) {
            ASTNode outputNode = visit(outputCtx);
            if (outputNode != null) {
                openNode.addChild(outputNode);
            }
        }
        
        for (CobolParser.OpenIOStatementContext ioCtx : ctx.openIOStatement()) {
            ASTNode ioNode = visit(ioCtx);
            if (ioNode != null) {
                openNode.addChild(ioNode);
            }
        }
        
        for (CobolParser.OpenExtendStatementContext extendCtx : ctx.openExtendStatement()) {
            ASTNode extendNode = visit(extendCtx);
            if (extendNode != null) {
                openNode.addChild(extendNode);
            }
        }
        
        return openNode;
    }
    
    @Override
    public ASTNode visitDisplayStatement(CobolParser.DisplayStatementContext ctx) {
        log("🔍 Visiting DISPLAY statement");
        
        ASTNode displayNode = new ASTNode("DISPLAY-STATEMENT", null, getLineNumber(ctx));
        
        // Visit display operands
        for (CobolParser.DisplayOperandContext operandCtx : ctx.displayOperand()) {
            ASTNode operandNode = new ASTNode("DISPLAY-OPERAND", operandCtx.getText(), getLineNumber(operandCtx));
            displayNode.addChild(operandNode);
        }
        
        // Handle display options
        if (ctx.displayAt() != null) {
            ASTNode atNode = new ASTNode("DISPLAY-AT", ctx.displayAt().getText(), getLineNumber(ctx));
            displayNode.addChild(atNode);
        }
        
        if (ctx.displayUpon() != null) {
            ASTNode uponNode = new ASTNode("DISPLAY-UPON", ctx.displayUpon().getText(), getLineNumber(ctx));
            displayNode.addChild(uponNode);
        }
        
        return displayNode;
    }
    
    @Override
    public ASTNode visitMoveStatement(CobolParser.MoveStatementContext ctx) {
        log("🔍 Visiting MOVE statement");
        
        ASTNode moveNode = new ASTNode("MOVE-STATEMENT", null, getLineNumber(ctx));
        
        // Handle different move statement formats
        if (ctx.moveToStatement() != null) {
            ASTNode moveToNode = visit(ctx.moveToStatement());
            if (moveToNode != null) moveNode.addChild(moveToNode);
        } else if (ctx.moveCorrespondingToStatement() != null) {
            ASTNode moveCorrNode = visit(ctx.moveCorrespondingToStatement());
            if (moveCorrNode != null) moveNode.addChild(moveCorrNode);
        }
        
        return moveNode;
    }
    
    @Override
    public ASTNode visitMoveToStatement(CobolParser.MoveToStatementContext ctx) {
        ASTNode moveToNode = new ASTNode("MOVE-TO", null, getLineNumber(ctx));
        
        // Source
        if (ctx.moveToSendingArea() != null) {
            ASTNode sourceNode = new ASTNode("MOVE-SOURCE", ctx.moveToSendingArea().getText(), getLineNumber(ctx));
            moveToNode.addChild(sourceNode);
        }
        
        // Destinations
        for (CobolParser.IdentifierContext destCtx : ctx.identifier()) {
            ASTNode destNode = new ASTNode("MOVE-DESTINATION", destCtx.getText(), getLineNumber(destCtx));
            moveToNode.addChild(destNode);
        }
        
        return moveToNode;
    }
    
    @Override
    public ASTNode visitEnableStatement(CobolParser.EnableStatementContext ctx) {
        log("🔍 Visiting ENABLE statement");
        
        ASTNode enableNode = new ASTNode("ENABLE-STATEMENT", null, getLineNumber(ctx));
        
        // IO type
        String ioType = "";
        if (ctx.INPUT() != null) ioType = "INPUT";
        else if (ctx.OUTPUT() != null) ioType = "OUTPUT";
        else if (ctx.I_O() != null) ioType = "I-O";
        
        if (!ioType.isEmpty()) {
            ASTNode ioNode = new ASTNode("IO-TYPE", ioType, getLineNumber(ctx));
            enableNode.addChild(ioNode);
        }
        
        // CD name
        if (ctx.cdName() != null) {
            ASTNode cdNameNode = new ASTNode("CD-NAME", ctx.cdName().getText(), getLineNumber(ctx));
            enableNode.addChild(cdNameNode);
        }
        
        // Key value
        if (ctx.literal() != null) {
            ASTNode keyNode = new ASTNode("KEY-VALUE", ctx.literal().getText(), getLineNumber(ctx));
            enableNode.addChild(keyNode);
        } else if (ctx.identifier() != null) {
            ASTNode keyNode = new ASTNode("KEY-VALUE", ctx.identifier().getText(), getLineNumber(ctx));
            enableNode.addChild(keyNode);
        }
        
        return enableNode;
    }
    
    @Override
    public ASTNode visitDisableStatement(CobolParser.DisableStatementContext ctx) {
        log("🔍 Visiting DISABLE statement");
        
        ASTNode disableNode = new ASTNode("DISABLE-STATEMENT", null, getLineNumber(ctx));
        
        // IO type
        String ioType = "";
        if (ctx.INPUT() != null) ioType = "INPUT";
        else if (ctx.OUTPUT() != null) ioType = "OUTPUT";
        else if (ctx.I_O() != null) ioType = "I-O";
        
        if (!ioType.isEmpty()) {
            ASTNode ioNode = new ASTNode("IO-TYPE", ioType, getLineNumber(ctx));
            disableNode.addChild(ioNode);
        }
        
        // CD name
        if (ctx.cdName() != null) {
            ASTNode cdNameNode = new ASTNode("CD-NAME", ctx.cdName().getText(), getLineNumber(ctx));
            disableNode.addChild(cdNameNode);
        }
        
        // Key value
        if (ctx.literal() != null) {
            ASTNode keyNode = new ASTNode("KEY-VALUE", ctx.literal().getText(), getLineNumber(ctx));
            disableNode.addChild(keyNode);
        } else if (ctx.identifier() != null) {
            ASTNode keyNode = new ASTNode("KEY-VALUE", ctx.identifier().getText(), getLineNumber(ctx));
            disableNode.addChild(keyNode);
        }
        
        return disableNode;
    }
    
    @Override
    public ASTNode visitReceiveStatement(CobolParser.ReceiveStatementContext ctx) {
        log("🔍 Visiting RECEIVE statement");
        
        ASTNode receiveNode = new ASTNode("RECEIVE-STATEMENT", null, getLineNumber(ctx));
        
        if (ctx.receiveFromStatement() != null) {
            ASTNode receiveFromNode = visit(ctx.receiveFromStatement());
            if (receiveFromNode != null) receiveNode.addChild(receiveFromNode);
        } else if (ctx.receiveIntoStatement() != null) {
            ASTNode receiveIntoNode = visit(ctx.receiveIntoStatement());
            if (receiveIntoNode != null) receiveNode.addChild(receiveIntoNode);
        }
        
        return receiveNode;
    }
    
    @Override
    public ASTNode visitReceiveIntoStatement(CobolParser.ReceiveIntoStatementContext ctx) {
        ASTNode receiveIntoNode = new ASTNode("RECEIVE-INTO", null, getLineNumber(ctx));
        
        // CD name
        if (ctx.cdName() != null) {
            ASTNode cdNameNode = new ASTNode("CD-NAME", ctx.cdName().getText(), getLineNumber(ctx));
            receiveIntoNode.addChild(cdNameNode);
        }
        
        // Message type
        String messageType = "";
        if (ctx.MESSAGE() != null) messageType = "MESSAGE";
        else if (ctx.SEGMENT() != null) messageType = "SEGMENT";
        
        if (!messageType.isEmpty()) {
            ASTNode msgTypeNode = new ASTNode("MESSAGE-TYPE", messageType, getLineNumber(ctx));
            receiveIntoNode.addChild(msgTypeNode);
        }
        
        // Target identifier
        if (ctx.identifier() != null) {
            ASTNode targetNode = new ASTNode("RECEIVE-TARGET", ctx.identifier().getText(), getLineNumber(ctx));
            receiveIntoNode.addChild(targetNode);
        }
        
        // CRITICAL FIX: Handle NO DATA clause
        if (ctx.receiveNoData() != null) {
            ASTNode noDataNode = visit(ctx.receiveNoData());
            if (noDataNode != null) {
                receiveIntoNode.addChild(noDataNode);
            }
        }
        
        // Handle WITH DATA clause
        if (ctx.receiveWithData() != null) {
            ASTNode withDataNode = visit(ctx.receiveWithData());
            if (withDataNode != null) {
                receiveIntoNode.addChild(withDataNode);
            }
        }
        
        return receiveIntoNode;
    }
    
    
    @Override
    public ASTNode visitSendStatement(CobolParser.SendStatementContext ctx) {
        log("🔍 Visiting SEND statement");
        
        ASTNode sendNode = new ASTNode("SEND-STATEMENT", null, getLineNumber(ctx));
        
        if (ctx.sendStatementSync() != null) {
            ASTNode syncNode = visit(ctx.sendStatementSync());
            if (syncNode != null) sendNode.addChild(syncNode);
        } else if (ctx.sendStatementAsync() != null) {
            ASTNode asyncNode = visit(ctx.sendStatementAsync());
            if (asyncNode != null) sendNode.addChild(asyncNode);
        } else if (ctx.sendStatementComm() != null) {
            ASTNode commNode = visit(ctx.sendStatementComm());
            if (commNode != null) sendNode.addChild(commNode);
        }
        
        // Exception handling
        if (ctx.onExceptionClause() != null) {
            ASTNode exceptionNode = new ASTNode("SEND-ON-EXCEPTION", ctx.onExceptionClause().getText(), getLineNumber(ctx));
            sendNode.addChild(exceptionNode);
        }
        
        if (ctx.notOnExceptionClause() != null) {
            ASTNode notExceptionNode = new ASTNode("SEND-NOT-ON-EXCEPTION", ctx.notOnExceptionClause().getText(), getLineNumber(ctx));
            sendNode.addChild(notExceptionNode);
        }
        
        return sendNode;
    }

    @Override
    public ASTNode visitSendStatementSync(CobolParser.SendStatementSyncContext ctx) {
        log("🔍 Visiting SEND statement (sync)");
        
        ASTNode syncNode = new ASTNode("SEND-SYNC", null, getLineNumber(ctx));
        
        // CD name
        if (ctx.cdName() != null) {
            ASTNode cdNameNode = new ASTNode("CD-NAME", ctx.cdName().getText(), getLineNumber(ctx));
            syncNode.addChild(cdNameNode);
        }
        
        // FROM phrase
        if (ctx.getText().toUpperCase().contains("FROM")) {
            // Extract FROM identifier - this is a simplified approach
            String text = ctx.getText().toUpperCase();
            int fromIndex = text.indexOf("FROM");
            if (fromIndex != -1) {
                String fromPart = text.substring(fromIndex + 4).trim();
                // Extract the identifier after FROM
                String[] parts = fromPart.split("\\s+");
                if (parts.length > 0) {
                    ASTNode fromNode = new ASTNode("SEND-FROM", parts[0], getLineNumber(ctx));
                    syncNode.addChild(fromNode);
                }
            }
        }
        
        // WITH phrase
        if (ctx.getText().toUpperCase().contains("WITH")) {
            String text = ctx.getText().toUpperCase();
            int withIndex = text.indexOf("WITH");
            if (withIndex != -1) {
                String withPart = text.substring(withIndex + 4).trim();
                String[] parts = withPart.split("\\s+");
                if (parts.length > 0) {
                    ASTNode withNode = new ASTNode("SEND-WITH", parts[0], getLineNumber(ctx));
                    syncNode.addChild(withNode);
                }
            }
        }
        
        return syncNode;
    }

    @Override
    public ASTNode visitSendStatementComm(CobolParser.SendStatementCommContext ctx) {
        ASTNode commNode = new ASTNode("SEND-COMM", null, getLineNumber(ctx));
        
        // CD name
        if (ctx.cdName() != null) {
            ASTNode cdNameNode = new ASTNode("CD-NAME", ctx.cdName().getText(), getLineNumber(ctx));
            commNode.addChild(cdNameNode);
        }
        
        // CRITICAL FIX: Handle FROM phrase properly
        if (ctx.sendFromPhrase() != null) {
            ASTNode fromNode = new ASTNode("SEND-FROM", ctx.sendFromPhrase().identifier().getText(), getLineNumber(ctx));
            commNode.addChild(fromNode);
        }
        
        // WITH options (EGI, EMI, ESI, KEY)
        String text = ctx.getText().toUpperCase();
        if (text.contains("EGI")) {
            ASTNode egiNode = new ASTNode("SEND-WITH", "EGI", getLineNumber(ctx));
            commNode.addChild(egiNode);
        } else if (text.contains("EMI")) {
            ASTNode emiNode = new ASTNode("SEND-WITH", "EMI", getLineNumber(ctx));
            commNode.addChild(emiNode);
        } else if (text.contains("ESI")) {
            ASTNode esiNode = new ASTNode("SEND-WITH", "ESI", getLineNumber(ctx));
            commNode.addChild(esiNode);
        }
        
        return commNode;
    }

    @Override
    public ASTNode visitSentence(CobolParser.SentenceContext ctx) {
        if (ctx.statement().isEmpty()) {
            log("⚠️ Skipping empty sentence");
            return null;
        }
        ASTNode sentenceNode = new ASTNode("SENTENCE", null, getLineNumber(ctx));
        for (CobolParser.StatementContext stmtCtx : ctx.statement()) {
            ASTNode stmtNode = visit(stmtCtx);
            if (stmtNode != null) {
                sentenceNode.addChild(stmtNode);
            }
        }
        return sentenceNode.hasChildren() ? sentenceNode : null;
    }

    
    @Override
    public ASTNode visitCopyStatement(CobolParser.CopyStatementContext ctx) {
        log("🔍 Visiting COPY statement");
        
        ASTNode copyNode = new ASTNode("COPY-STATEMENT", null, getLineNumber(ctx));
        
        if (ctx.copyName() != null) {
            ASTNode nameNode = new ASTNode("COPY-NAME", ctx.copyName().getText(), getLineNumber(ctx));
            copyNode.addChild(nameNode);
        }
        
        if (ctx.libraryName() != null) {
            ASTNode libraryNode = new ASTNode("LIBRARY-NAME", ctx.libraryName().getText(), getLineNumber(ctx));
            copyNode.addChild(libraryNode);
        }
        
        return copyNode;
    }
    
    // Method to process linkage items specially for parameter detection
    private void processLinkageItem(DataStructureInfo dataInfo) {
        if ("LINKAGE-SECTION".equals(currentSection) && dataInfo.level.equals("01")) {
            LinkageDataStructureInfo linkageInfo = new LinkageDataStructureInfo(dataInfo);
            linkageInfo.isParameter = true;
            linkageInfo.parameterOrder = linkageItemCount;
            
            // Update the main data structures list
            if (!dataStructures.isEmpty()) {
                DataStructureInfo lastItem = dataStructures.get(dataStructures.size() - 1);
                if (lastItem.name.equals(dataInfo.name)) {
                    // Replace with enhanced linkage info
                    dataStructures.set(dataStructures.size() - 1, linkageInfo);
                }
            }
            
            log("📋 Processed linkage parameter: " + dataInfo.name + " (order: " + linkageInfo.parameterOrder + ")");
        }
    }

    private void collectAllDataItemsFlat(CobolParser.DataDescriptionGroupContext ctx, List<ASTNode> items) {
        // Get the main item
        ASTNode mainItem = null;
        if (ctx.dataDescriptionEntryFormat1() != null) {
            mainItem = visit(ctx.dataDescriptionEntryFormat1());
        } else if (ctx.dataDescriptionEntryFormat4() != null) {
            mainItem = visit(ctx.dataDescriptionEntryFormat4());
        }
        // Add other formats as needed
        
        if (mainItem != null) {
            items.add(mainItem);
        }
        
        // Get subordinate items recursively
        for (CobolParser.SubordinateDataItemContext subCtx : ctx.subordinateDataItem()) {
            collectSubordinateItemsFlat(subCtx, items);
        }
    }

    private void collectSubordinateItemsFlat(CobolParser.SubordinateDataItemContext ctx, List<ASTNode> items) {
        // Get this subordinate item
        ASTNode subItem = null;
        if (ctx.dataDescriptionEntryFormat1() != null) {
            subItem = visit(ctx.dataDescriptionEntryFormat1());
        } else if (ctx.dataDescriptionEntryFormat3() != null) {
            subItem = visit(ctx.dataDescriptionEntryFormat3());
        }
        
        if (subItem != null) {
            items.add(subItem);
        }
        
        // Get nested subordinate items recursively
        for (CobolParser.SubordinateDataItemContext nestedCtx : ctx.subordinateDataItem()) {
            collectSubordinateItemsFlat(nestedCtx, items);
        }
    }

    private boolean shouldIncludeDataStructureEnhanced(String dataName, String level, DataStructureInfo dataInfo) {
        if (dataName == null) {
            return false;
        }
        
        // Skip FILLER unless it has a VALUE (constants)
        if (dataName.equals("FILLER") && !dataInfo.hasValue) {
            return false;
        }
        
        // Include based on level and section
        switch (currentSection) {
            case "LINKAGE-SECTION":
                // Include all meaningful linkage items
                linkageItemCount++;
                if (level.equals("01") || level.equals("77")) {
                    linkageParameters.add(dataName);
                    return true;
                }
                // Include subordinate items for complete structure
                return !level.equals("88") && !dataName.equals("FILLER");
                
            case "WORKING-STORAGE":
            case "FILE-SECTION":
            case "LOCAL-STORAGE":
            case "COMMUNICATION-SECTION":
                // Include ALL meaningful data items for complete analysis
                if (level.equals("01") || level.equals("77")) {
                    return true; // Always include top-level items
                }
                if (level.equals("88")) {
                    return true; // Include condition names
                }
                if (level.equals("66")) {
                    return true; // Include RENAMES items
                }
                // Include subordinate items (02, 03, etc.) with names or values
                if (!dataName.equals("FILLER") || dataInfo.hasValue) {
                    return true;
                }
                return false;
                
            default:
                return level.equals("01") || level.equals("77");
        }
    }
    // ===========================================
    // UTILITY METHODS
    // ===========================================
    

    // Reset counters when starting new parsing
    public void resetCounters() {
        linkageItemCount = 0;
        linkageParameters.clear();
        currentSection = "WORKING-STORAGE";
    }

    private void updateDataStructureInfo(DataStructureInfo dataInfo, CobolParser.DataClauseContext clauseCtx) {
        if (clauseCtx.dataPictureClause() != null) {
            String picture = clauseCtx.dataPictureClause().pictureString().getText();
            dataInfo.picture = picture;
            dataInfo.dataType = inferDataTypeFromPicture(picture);
            dataInfo.javaType = suggestJavaType(picture);
        }
        
        if (clauseCtx.dataValueClause() != null) {
            dataInfo.hasValue = true;
            dataInfo.value = clauseCtx.dataValueClause().getText();
        }
        
        if (clauseCtx.dataOccursClause() != null) {
            dataInfo.isArray = true;
            if (clauseCtx.dataOccursClause().integerLiteral() != null) {
                dataInfo.arraySize = clauseCtx.dataOccursClause().integerLiteral().getText();
            }
        }
        
        if (clauseCtx.dataRedefinesClause() != null) {
            dataInfo.redefines = clauseCtx.dataRedefinesClause().dataName().getText();
        }
        
        if (clauseCtx.dataUsageClause() != null) {
            dataInfo.usage = clauseCtx.dataUsageClause().getText();
        }
    }
    
    private String inferDataTypeFromPicture(String picture) {
        if (picture == null) return "GROUP";
        
        String upperPic = picture.toUpperCase();
        
        if (upperPic.contains("9")) {
            if (upperPic.contains("V") || upperPic.contains(".")) {
                return "DECIMAL";
            }
            return "INTEGER";
        } else if (upperPic.contains("X")) {
            return "STRING";
        } else if (upperPic.contains("A")) {
            return "ALPHABETIC";
        } else if (upperPic.contains("S9")) {
            return "SIGNED_INTEGER";
        }
        
        return "GROUP";
    }
    
    private String suggestJavaType(String picture) {
        if (picture == null) return "Object";
        
        String dataType = inferDataTypeFromPicture(picture);
        switch (dataType) {
            case "INTEGER":
                if (picture.length() <= 4) return "int";
                else if (picture.length() <= 9) return "long";
                else return "BigInteger";
            case "SIGNED_INTEGER":
                if (picture.length() <= 4) return "int";
                else if (picture.length() <= 9) return "long";
                else return "BigInteger";
            case "DECIMAL":
                return "BigDecimal";
            case "STRING":
            case "ALPHABETIC":
                return "String";
            case "GROUP":
                return "Object";
            default:
                return "String";
        }
    }
    
    private int getLineNumber(ParserRuleContext ctx) {
        if (ctx.getStart() != null) {
            return ctx.getStart().getLine();
        }
        return 1;
    }
    
    private String toMethodName(String cobolName) {
        if (cobolName == null) return "unknownMethod";
        
        String[] parts = cobolName.toLowerCase().split("-");
        StringBuilder result = new StringBuilder(parts[0]);
        for (int i = 1; i < parts.length; i++) {
            if (parts[i].length() > 0) {
                result.append(Character.toUpperCase(parts[i].charAt(0)));
                if (parts[i].length() > 1) {
                    result.append(parts[i].substring(1));
                }
            }
        }
        return result.toString();
    }
    
    private int countStatements(CobolParser.SentenceContext ctx) {
        return ctx.statement().size();
    }
    
    private int calculateComplexity(int statementCount, CobolParser.ParagraphContext ctx) {
        int complexity = statementCount;
        
        // Add complexity for control structures (simplified analysis)
        String text = ctx.getText().toUpperCase();
        complexity += countOccurrences(text, "IF") * 2;
        complexity += countOccurrences(text, "PERFORM");
        complexity += countOccurrences(text, "EVALUATE") * 2;
        complexity += countOccurrences(text, "GO TO");
        
        return complexity;
    }
    
    private int countOccurrences(String text, String pattern) {
        int count = 0;
        int index = 0;
        while ((index = text.indexOf(pattern, index)) != -1) {
            count++;
            index += pattern.length();
        }
        return count;
    }
    
    private void log(String message) {
        if (debugMode) {
            System.out.println(message);
        }
    }
    
    private void generateDataStructuresJSON(String outputFile) throws IOException {
        StringBuilder json = new StringBuilder();
        json.append("{\n");
        json.append("  \"programName\": \"").append(programName).append("\",\n");
        json.append("  \"extractionTimestamp\": ").append(System.currentTimeMillis()).append(",\n");
        json.append("  \"dataStructures\": [\n");
        
        for (int i = 0; i < dataStructures.size(); i++) {
            DataStructureInfo ds = dataStructures.get(i);
            json.append("    {\n");
            json.append("      \"name\": \"").append(ds.name).append("\",\n");
            json.append("      \"level\": \"").append(ds.level).append("\",\n");
            json.append("      \"dataType\": \"").append(ds.dataType != null ? ds.dataType : "GROUP").append("\",\n");
            json.append("      \"picture\": \"").append(ds.picture != null ? ds.picture : "").append("\",\n");
            json.append("      \"hasValue\": ").append(ds.hasValue).append(",\n");
            json.append("      \"isArray\": ").append(ds.isArray).append(",\n");
            if (ds.arraySize != null) {
                json.append("      \"arraySize\": \"").append(ds.arraySize).append("\",\n");
            }
            if (ds.redefines != null) {
                json.append("      \"redefines\": \"").append(ds.redefines).append("\",\n");
            }
            json.append("      \"section\": \"").append(ds.section != null ? ds.section : "UNKNOWN").append("\",\n");
            json.append("      \"lineNumber\": ").append(ds.lineNumber).append(",\n");
            json.append("      \"suggestedJavaType\": \"").append(ds.javaType != null ? ds.javaType : "Object").append("\",\n");
            json.append("      \"suggestedFieldName\": \"").append(toJavaFieldName(ds.name)).append("\"\n");
            json.append("    }");
            if (i < dataStructures.size() - 1) json.append(",");
            json.append("\n");
        }
        
        json.append("  ],\n");
        json.append("  \"procedures\": [\n");
        
        for (int i = 0; i < procedures.size(); i++) {
            ProcedureInfo proc = procedures.get(i);
            json.append("    {\n");
            json.append("      \"name\": \"").append(proc.name).append("\",\n");
            json.append("      \"suggestedMethodName\": \"").append(proc.suggestedMethodName).append("\",\n");
            json.append("      \"statementCount\": ").append(proc.statementCount).append(",\n");
            json.append("      \"complexityScore\": ").append(proc.complexityScore).append(",\n");
            json.append("      \"lineNumber\": ").append(proc.lineNumber).append("\n");
            json.append("    }");
            if (i < procedures.size() - 1) json.append(",");
            json.append("\n");
        }
        
        json.append("  ],\n");
        json.append("  \"communicationDescriptions\": [\n");
        
        for (int i = 0; i < communicationDescriptions.size(); i++) {
            CommunicationInfo comm = communicationDescriptions.get(i);
            json.append("    {\n");
            json.append("      \"name\": \"").append(comm.name).append("\",\n");
            json.append("      \"type\": \"").append(comm.type).append("\",\n");
            json.append("      \"lineNumber\": ").append(comm.lineNumber).append("\n");
            json.append("    }");
            if (i < communicationDescriptions.size() - 1) json.append(",");
            json.append("\n");
        }
        
        json.append("  ]\n");
        json.append("}");
        
        try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile))) {
            writer.println(json.toString());
            System.out.println("📄 Data structures JSON saved to: " + outputFile);
        }
    }
    
    private void generateJavaClassSuggestions(String outputFile) throws IOException {
        StringBuilder java = new StringBuilder();
        java.append("// Generated Java class suggestions for COBOL program: ").append(programName).append("\n\n");
        
        // Generate main program class
        java.append("public class ").append(toJavaClassName(programName)).append(" {\n\n");
        
        // Generate field declarations from data structures
        java.append("    // Data structure fields\n");
        for (DataStructureInfo ds : dataStructures) {
            if (ds.isArray) {
                java.append("    private ").append(ds.javaType != null ? ds.javaType : "String");
                if (ds.arraySize != null) {
                    java.append("[] ").append(toJavaFieldName(ds.name)).append(" = new ");
                    java.append(ds.javaType != null ? ds.javaType : "String").append("[").append(ds.arraySize).append("];");
                } else {
                    java.append("[] ").append(toJavaFieldName(ds.name)).append(";");
                }
            } else {
                java.append("    private ").append(ds.javaType != null ? ds.javaType : "String");
                java.append(" ").append(toJavaFieldName(ds.name));
                if (ds.hasValue && ds.value != null) {
                    java.append(" = ").append(ds.value);
                }
                java.append(";");
            }
            
            if (ds.picture != null) {
                java.append(" // COBOL: PIC ").append(ds.picture);
            }
            java.append("\n");
        }
        
        java.append("\n    // Procedure methods\n");
        for (ProcedureInfo proc : procedures) {
            java.append("    public void ").append(proc.suggestedMethodName).append("() {\n");
            java.append("        // TODO: Implement ").append(proc.name).append(" logic\n");
            java.append("        // Complexity score: ").append(proc.complexityScore).append("\n");
            java.append("        // Statement count: ").append(proc.statementCount).append("\n");
            java.append("    }\n\n");
        }
        
        // Generate getters and setters
        java.append("    // Getters and Setters\n");
        for (DataStructureInfo ds : dataStructures) {
            String fieldName = toJavaFieldName(ds.name);
            String className = toJavaClassName(ds.name);
            String javaType = ds.javaType != null ? ds.javaType : "String";
            
            // Getter
            java.append("    public ").append(javaType);
            if (ds.isArray) java.append("[]");
            java.append(" get").append(className).append("() {\n");
            java.append("        return ").append(fieldName).append(";\n");
            java.append("    }\n\n");
            
            // Setter
            java.append("    public void set").append(className).append("(").append(javaType);
            if (ds.isArray) java.append("[]");
            java.append(" ").append(fieldName).append(") {\n");
            java.append("        this.").append(fieldName).append(" = ").append(fieldName).append(";\n");
            java.append("    }\n\n");
        }
        
        java.append("}\n");
        
        try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile))) {
            writer.println(java.toString());
            System.out.println("☕ Java class suggestions saved to: " + outputFile);
        }
    }
    
    private String toJavaFieldName(String cobolName) {
        return toMethodName(cobolName);
    }
    
    private String toJavaClassName(String cobolName) {
        String methodName = toMethodName(cobolName);
        if (methodName.length() > 0) {
            return Character.toUpperCase(methodName.charAt(0)) + methodName.substring(1);
        }
        return "UnknownClass";
    }
    
    // ===========================================
    // DATA CLASSES
    // ===========================================
    

    static class DataStructureInfo {
        String name;
        String level;
        String dataType;
        String picture;
        boolean hasValue = false;
        boolean isArray = false;
        String value;
        String redefines;
        String usage;
        String arraySize;
        String section;
        String javaType;
        String valueTo;
        String occurs;
        int lineNumber;
    }

    static class LinkageDataStructureInfo extends DataStructureInfo {
        boolean isParameter = false;
        int parameterOrder = -1;
        String parameterMode = "BY REFERENCE"; // Default COBOL parameter mode
        
        public LinkageDataStructureInfo(DataStructureInfo base) {
            this.name = base.name;
            this.level = base.level;
            this.dataType = base.dataType;
            this.picture = base.picture;
            this.hasValue = base.hasValue;
            this.isArray = base.isArray;
            this.value = base.value;
            this.redefines = base.redefines;
            this.usage = base.usage;
            this.arraySize = base.arraySize;
            this.section = base.section;
            this.javaType = base.javaType;
            this.valueTo = base.valueTo;
            this.occurs = base.occurs;
            this.lineNumber = base.lineNumber;
        }
    }
    

    static class FileOperationInfo {
        String operation;
        String fileName;
        int lineNumber;
    }
    
    static class CommunicationInfo {
        String name;
        String type;
        int lineNumber;
    }
}

/**
 * AST Node class for tree structure (reused from original ASTParser)
 */
class ASTNode {
    public final String type;
    public final String value;
    public final List<ASTNode> children;
    public final int line;
    
    public ASTNode(String type, String value, int line) {
        this.type = type;
        this.value = value;
        this.line = line;
        this.children = new ArrayList<>();
    }
    
    public ASTNode(String type, int line) {
        this(type, null, line);
    }
    
    public void addChild(ASTNode child) {
        if (child != null) {
            children.add(child);
        }
    }
    
    public boolean hasChildren() {
        return !children.isEmpty();
    }
    
    // Generate LISP-style representation
    public String toLisp() {
        return toLisp(0);
    }
    
    private String toLisp(int indent) {
        StringBuilder sb = new StringBuilder();
        String indentStr = "  ".repeat(indent);
        
        if (hasChildren()) {
            sb.append(indentStr).append("(").append(type);
            if (value != null && !value.isEmpty()) {
                sb.append(" \"").append(escapeString(value)).append("\"");
            }
            sb.append("\n");
            
            for (ASTNode child : children) {
                sb.append(child.toLisp(indent + 1));
            }
            
            sb.append(indentStr).append(")\n");
        } else {
            sb.append(indentStr).append("(").append(type);
            if (value != null && !value.isEmpty()) {
                sb.append(" \"").append(escapeString(value)).append("\"");
            }
            sb.append(")\n");
        }
        
        return sb.toString();
    }
    
    private String escapeString(String str) {
        if (str == null) return "";
        return str.replace("\"", "\\\"")
                 .replace("\n", "\\n")
                 .replace("\r", "\\r")
                 .replace("\t", "\\t");
    }
    
    @Override
    public String toString() {
        return type + (value != null ? ":" + value : "") + " @" + line;
    }
}

