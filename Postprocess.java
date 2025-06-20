import java.util.*;
import org.antlr.v4.runtime.tree.ParseTree;
import org.antlr.v4.runtime.tree.ParseTreeVisitor;
import org.antlr.v4.runtime.tree.TerminalNode;

public class Postprocess
{
    // THE KEY METHOD: Restructure based on COBOL level number rules
    public static ASTNode restructureByLevelNumbers(List<ASTNode> flatItems) {
        ASTNode root = new ASTNode("ROOT", null, 1);
        Stack<ASTNode> levelStack = new Stack<>();
        
        for (ASTNode item : flatItems) {
            int currentLevel = extractLevelNumber(item);
            
            // Pop stack until we find the correct parent level
            while (!levelStack.isEmpty()) {
                int stackTopLevel = extractLevelNumber(levelStack.peek());
                if (stackTopLevel < currentLevel) {
                    break; // Found correct parent
                }
                levelStack.pop(); // Remove items at same or higher level
            }
            
            // Add to correct parent
            if (levelStack.isEmpty()) {
                // This is a top-level item (01 or 77)
                root.addChild(item);
            } else {
                // This is a subordinate item
                levelStack.peek().addChild(item);
            }
            
            // Push current item if it can have children (not 88-level)
            if (currentLevel != 88) {
                levelStack.push(item);
            }
            
            log("📍 Processed level " + currentLevel + " item: " + extractDataName(item));
        }
        
        return root;
    }

    // Helper method to extract level number from AST node
    private static int extractLevelNumber(ASTNode node) {
        for (ASTNode child : node.children) {
            if ("LEVEL".equals(child.type)) {
                try {
                    return Integer.parseInt(child.value);
                } catch (NumberFormatException e) {
                    return 99; // Default for invalid levels
                }
            }
        }
        return 99; // Default if no level found
    }

    // Helper method to extract data name from AST node
    private static String extractDataName(ASTNode node) {
        for (ASTNode child : node.children) {
            if ("DATA-NAME".equals(child.type) || "CONDITION-NAME".equals(child.type)) {
                return child.value != null ? child.value : "UNKNOWN";
            }
        }
        return "UNKNOWN";
    }
    private static void log(String message) {
        //if (debugMode) {
            System.out.println(message);
        //}
    }
}
