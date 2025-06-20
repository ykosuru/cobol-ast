import java.io.*;
import java.util.*;

/**
 * Manual line splitter for fixing specific problematic COBOL lines
 */
public class ManualLineSplitter {
    
    public static void main(String[] args) {
        if (args.length == 0) {
            System.out.println("Usage: java ManualLineSplitter <input-file> [output-file]");
            return;
        }
        
        try {
            ManualLineSplitter splitter = new ManualLineSplitter();
            // If executed after FobolPreprocessor, this writes to the output directory,
            // which is already included in the first argument.
            String outputFile = args[0] + ".manual";
            splitter.processFile(args[0], outputFile);
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    public void processFile(String inputFile, String outputFile) throws IOException {
        System.out.println("🔧 Manually splitting problematic COBOL lines...");
        System.out.println("Input: " + inputFile + " -> Output: " + outputFile);
        
        List<String> processedLines = new ArrayList<>();
        
        try (BufferedReader reader = new BufferedReader(new FileReader(inputFile))) {
            String line;
            int lineNum = 0;
            
            while ((line = reader.readLine()) != null) {
                lineNum++;
                
                if (isProblemLine(line, lineNum)) {
                    System.out.println("Splitting problematic line " + lineNum + ":");
                    System.out.println("  Original: " + line.substring(0, Math.min(100, line.length())) + "...");
                    
                    List<String> split = manualSplit(line);
                    for (String splitLine : split) {
                        processedLines.add(splitLine);
                        System.out.println("  Split: " + splitLine);
                    }
                } else {
                    processedLines.add(line);
                }
            }
        }
        
        // Write processed file
        try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile))) {
            for (String line : processedLines) {
                writer.println(line);
            }
        }
        
        System.out.println("✅ Created " + processedLines.size() + " lines");
    }
    
    private boolean isProblemLine(String line, int lineNum) {
        // Target the specific problematic line pattern we keep seeing
        return line.contains("01REC-SKL-SUBPICTURE") ||
               line.contains("01") && line.contains("PICTURE") && line.contains("VALUE") && line.length() > 200;
    }
    
    private List<String> manualSplit(String line) {
        List<String> statements = new ArrayList<>();
        
        // This is the specific pattern we see in the error:
        // 01REC-SKL-SUBPICTURE9(2)VALUEZERO.01REC-CTPICTURE99VALUEZERO.01DELETE-CNT...
        
        // Strategy: Split on specific known patterns
        String remaining = line;
        
        // Pattern: "VALUE ZERO.01" or "VALUE SPACE.01" 
        while (remaining.contains(".01") && remaining.indexOf(".01") > 0) {
            int dotPos = remaining.indexOf(".01");
            
            // Extract statement up to the dot
            String statement = remaining.substring(0, dotPos + 1);
            
            // Clean up and format the statement
            statement = formatStatement(statement);
            statements.add(statement);
            
            // Continue with the rest starting from "01"
            remaining = remaining.substring(dotPos + 1);
            
            // If what's left doesn't start with a level number, we're done
            if (!remaining.matches("^(01|02|03|04|05|77|88).*")) {
                break;
            }
        }
        
        // Add any remaining content
        if (!remaining.trim().isEmpty() && !remaining.equals(line)) {
            remaining = formatStatement(remaining);
            statements.add(remaining);
        }
        
        // If we couldn't split it, try a different approach
        if (statements.isEmpty()) {
            statements.addAll(alternativeSplit(line));
        }
        
        return statements;
    }
    
    private List<String> alternativeSplit(String line) {
        List<String> statements = new ArrayList<>();
        
        // Alternative: Split on level numbers that appear after certain keywords
        String[] splitPoints = {
            "VALUEZERO.01", "VALUESPACE.01", "VALUE\".*?\".01",
            "ZERO.01", "SPACE.01", "HIGH-VALUE.01", "LOW-VALUE.01"
        };
        
        String remaining = line;
        
        for (String splitPoint : splitPoints) {
            int pos = 0;
            while ((pos = remaining.indexOf(splitPoint.replace("01", "").replace("VALUE", "VALUE"), pos)) != -1) {
                // Find the end of this pattern
                int endPos = pos;
                while (endPos < remaining.length() && remaining.charAt(endPos) != '.') {
                    endPos++;
                }
                if (endPos < remaining.length()) endPos++; // Include the dot
                
                if (endPos < remaining.length() - 2 && 
                    remaining.substring(endPos, endPos + 2).matches("01|02|03|04|05|77|88")) {
                    // We found a split point
                    String statement = remaining.substring(0, endPos);
                    statement = formatStatement(statement);
                    statements.add(statement);
                    remaining = remaining.substring(endPos);
                    pos = 0; // Reset search
                } else {
                    pos = endPos;
                }
            }
        }
        
        // If still no luck, add the original line formatted
        if (statements.isEmpty()) {
            statements.add(formatStatement(line));
        } else if (!remaining.trim().isEmpty()) {
            statements.add(formatStatement(remaining));
        }
        
        return statements;
    }
    
    private String formatStatement(String statement) {
        String formatted = statement.trim();
        
        // Add proper spacing
        // Level numbers
        formatted = formatted.replaceAll("^(01|02|03|04|05|77|88)([A-Z])", "$1 $2");
        
        // PICTURE
        formatted = formatted.replaceAll("PICTURE([9XA])", "PICTURE $1");
        formatted = formatted.replaceAll("PIC([9XA])", "PIC $1");
        
        // VALUE
        formatted = formatted.replaceAll("VALUE(ZERO|SPACE|SPACES)", "VALUE $1");
        formatted = formatted.replaceAll("VALUEIS", "VALUE IS");
        
        // Clean up multiple spaces
        formatted = formatted.replaceAll("\\s+", " ");
        
        return formatted;
    }
}

