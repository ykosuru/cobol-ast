import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;

/**
 * Standalone program to convert detailed AST output from Driver2 into LISP-style S-expressions.
 * 
 * Usage: java AST2SExp input_ast.txt output_lisp.txt
 * 
 * Converts AST format like:
 *   RULE: MoveStatement (2 children)
 *     TERMINAL: MOVE = 'MOVE'
 *     RULE: MoveToStatement (3 children)
 *       TERMINAL: IDENTIFIER = 'VAR1AR'
 * 
 * To LISP format like:
 *   (MoveStatement 
 *     MOVE 
 *     (MoveToStatement VAR1AR TO WS-VAR))
 */
public class AST2SExp {
    
    private static final Pattern RULE_PATTERN = Pattern.compile("^(\\s*)RULE: (\\w+)\\s*\\((\\d+) children\\)$");
    private static final Pattern TERMINAL_PATTERN = Pattern.compile("^(\\s*)TERMINAL: ([^=]+) = '([^']*)'$");
    
    private static class AstNode {
        String type;
        String value;
        List<AstNode> children;
        int depth;
        boolean isTerminal;
        
        AstNode(String type, String value, int depth, boolean isTerminal) {
            this.type = type.trim();
            this.value = value;
            this.depth = depth;
            this.isTerminal = isTerminal;
            this.children = new ArrayList<>();
        }
        
        void addChild(AstNode child) {
            children.add(child);
        }
        
        @Override
        public String toString() {
            return String.format("%s[%s]%s", 
                isTerminal ? "T" : "R", 
                type, 
                value != null ? "=" + value : "");
        }
    }
    
    public static void main(String[] args) {
        if (args.length != 2) {
            System.err.println("Usage: java AST2SExp <input_ast.txt> <output_lisp.txt>");
            System.err.println("Converts detailed AST output to LISP S-expressions");
            System.exit(1);
        }
        
        String inputFile = args[0];
        String outputFile = args[1];
        
        try {
            AST2SExp converter = new AST2SExp();
            String astContent = converter.extractAstSection(inputFile);
            AstNode rootNode = converter.parseAst(astContent);
            String lispFormat = converter.generateLispFormat(rootNode);
            
            Files.write(Paths.get(outputFile), lispFormat.getBytes());
            System.out.println("LISP S-expression written to: " + outputFile);
            System.out.println("\nPreview:");
            System.out.println(lispFormat.substring(0, Math.min(500, lispFormat.length())));
            if (lispFormat.length() > 500) {
                System.out.println("...[truncated]");
            }
            
        } catch (Exception e) {
            System.err.println("Error converting AST to LISP: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
    
    private String extractAstSection(String inputFile) throws IOException {
        String content = Files.readString(Paths.get(inputFile));
        
        // Find the "Abstract Syntax Tree:" section
        String astMarker = "Abstract Syntax Tree:";
        int astStart = content.indexOf(astMarker);
        if (astStart == -1) {
            throw new IllegalArgumentException("No 'Abstract Syntax Tree:' section found in input file");
        }
        
        // Skip the marker and separator lines to find first RULE
        int astContentStart = content.indexOf("RULE:", astStart);
        if (astContentStart == -1) {
            throw new IllegalArgumentException("No RULE entries found after AST marker");
        }
        
        return content.substring(astContentStart);
    }
    
    private AstNode parseAst(String astContent) {
        String[] lines = astContent.split("\n");
        Stack<AstNode> nodeStack = new Stack<>();
        AstNode root = null;
        
        System.out.println("Parsing AST with " + lines.length + " lines...");
        
        for (int lineNum = 0; lineNum < lines.length; lineNum++) {
            String line = lines[lineNum];
            
            if (line.trim().isEmpty()) continue;
            
            // Parse RULE lines
            Matcher ruleMatcher = RULE_PATTERN.matcher(line);
            if (ruleMatcher.matches()) {
                int depth = calculateDepth(ruleMatcher.group(1));
                String ruleName = ruleMatcher.group(2);
                int childCount = Integer.parseInt(ruleMatcher.group(3));
                
                AstNode node = new AstNode(ruleName, null, depth, false);
                
                // Pop nodes until we find the correct parent depth
                while (!nodeStack.isEmpty() && nodeStack.peek().depth >= depth) {
                    nodeStack.pop();
                }
                
                // Add to parent if exists
                if (!nodeStack.isEmpty()) {
                    nodeStack.peek().addChild(node);
                } else {
                    root = node; // This is the root node
                }
                
                nodeStack.push(node);
                continue;
            }
            
            // Parse TERMINAL lines
            Matcher terminalMatcher = TERMINAL_PATTERN.matcher(line);
            if (terminalMatcher.matches()) {
                int depth = calculateDepth(terminalMatcher.group(1));
                String tokenType = terminalMatcher.group(2).trim();
                String value = terminalMatcher.group(3);
                
                // Create terminal node
                AstNode terminal = new AstNode(tokenType, value, depth, true);
                
                // Add to current parent
                if (!nodeStack.isEmpty()) {
                    nodeStack.peek().addChild(terminal);
                } else {
                    System.err.println("Warning: Terminal node without parent at line " + (lineNum + 1));
                }
            }
        }
        
        if (root == null) {
            throw new IllegalStateException("No root node found in AST");
        }
        
        System.out.println("Successfully parsed AST with root: " + root.type);
        return root;
    }
    
    private int calculateDepth(String indentation) {
        // Each level is typically 2 spaces in the AST output
        return indentation.length() / 2;
    }
    
    private String generateLispFormat(AstNode node) {
        StringBuilder result = new StringBuilder();
        result.append(";; COBOL AST in LISP S-Expression Format\n");
        result.append(";; Generated from detailed AST output\n\n");
        
        generateLispFormatRecursive(node, result, 0, true);
        
        return result.toString();
    }
    
    private void generateLispFormatRecursive(AstNode node, StringBuilder result, int depth, boolean isRoot) {
        String indent = "  ".repeat(depth);
        
        if (node.isTerminal) {
            // For terminals, just output the value (or token type if value is empty/formatting)
            if (isValueMeaningful(node.value)) {
                result.append(node.value);
            } else {
                result.append(node.type);
            }
            return;
        }
        
        // For non-terminals (rules), create S-expression
        if (node.children.isEmpty()) {
            // Empty rule
            result.append("(").append(node.type).append(")");
            return;
        }
        
        // Start S-expression
        result.append("(").append(node.type);
        
        // Handle children based on type and number
        if (shouldInlineChildren(node)) {
            // Inline children on same line
            for (AstNode child : node.children) {
                result.append(" ");
                generateLispFormatRecursive(child, result, 0, false);
            }
        } else {
            // Multi-line format for complex structures
            for (AstNode child : node.children) {
                result.append("\n").append(indent).append("  ");
                generateLispFormatRecursive(child, result, depth + 1, false);
            }
            if (!node.children.isEmpty()) {
                result.append("\n").append(indent);
            }
        }
        
        result.append(")");
    }
    
    private boolean isValueMeaningful(String value) {
        if (value == null || value.trim().isEmpty()) {
            return false;
        }
        
        // Skip formatting-only values
        String trimmed = value.trim();
        return !trimmed.equals(".") && 
               !trimmed.equals("\n") && 
               !trimmed.equals(".\n") && 
               !trimmed.equals("(") && 
               !trimmed.equals(")") &&
               !trimmed.equals(",");
    }
    
    private boolean shouldInlineChildren(AstNode node) {
        // Inline simple nodes with few children or only terminals
        if (node.children.size() <= 3) {
            return true;
        }
        
        // Inline if all children are terminals
        boolean allTerminals = node.children.stream().allMatch(child -> child.isTerminal);
        if (allTerminals && node.children.size() <= 5) {
            return true;
        }
        
        // Inline specific node types that are naturally compact
        switch (node.type) {
            case "CobolWord":
            case "DataName":
            case "ProgramName":
            case "Literal":
            case "IntegerLiteral":
            case "QualifiedDataName":
            case "Identifier":
                return true;
            default:
                return false;
        }
    }
    
    /**
     * Alternative compact format generator for even more concise output
     */
    public String generateCompactLispFormat(AstNode node) {
        StringBuilder result = new StringBuilder();
        result.append(";; Compact COBOL AST in LISP Format\n\n");
        
        generateCompactLispRecursive(node, result);
        
        return result.toString();
    }
    
    private void generateCompactLispRecursive(AstNode node, StringBuilder result) {
        if (node.isTerminal) {
            if (isValueMeaningful(node.value)) {
                // Quote strings if they contain spaces or special characters
                if (node.value.contains(" ") || node.value.contains("'") || node.value.contains("\"")) {
                    result.append("\"").append(node.value.replace("\"", "\\\"")).append("\"");
                } else {
                    result.append(node.value);
                }
            } else {
                result.append(node.type);
            }
            return;
        }
        
        // Skip wrapper nodes that don't add semantic value
        if (isWrapperNode(node) && node.children.size() == 1) {
            generateCompactLispRecursive(node.children.get(0), result);
            return;
        }
        
        result.append("(").append(node.type);
        
        for (AstNode child : node.children) {
            result.append(" ");
            generateCompactLispRecursive(child, result);
        }
        
        result.append(")");
    }
    
    private boolean isWrapperNode(AstNode node) {
        return node.type.equals("CobolWord") ||
               node.type.equals("QualifiedDataName") ||
               node.type.equals("QualifiedDataNameFormat1") ||
               node.type.equals("Identifier") ||
               node.type.equals("MoveToSendingArea") ||
               node.type.equals("Literal") ||
               node.type.equals("IntegerLiteral");
    }
    
    /**
     * Test method to demonstrate different output formats
     */
    public static void demonstrateFormats(String inputFile) throws IOException {
        AST2SExp converter = new AST2SExp();
        String astContent = converter.extractAstSection(inputFile);
        AstNode rootNode = converter.parseAst(astContent);
        
        System.out.println("=== Standard LISP Format ===");
        System.out.println(converter.generateLispFormat(rootNode).substring(0, 300) + "...");
        
        System.out.println("\n=== Compact LISP Format ===");
        System.out.println(converter.generateCompactLispFormat(rootNode).substring(0, 300) + "...");
    }
}

